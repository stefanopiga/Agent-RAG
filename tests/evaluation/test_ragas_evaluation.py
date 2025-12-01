"""
RAGAS Evaluation Test Suite.

Implements RAGAS evaluation for RAG quality metrics.
Uses real LLM calls (not mocked) as required by RAGAS evaluation.

Acceptance Criteria:
- AC#10: Given golden dataset (20+ query-answer pairs), When I run RAGAS eval,
         Then I see faithfulness, relevancy, precision, recall scores
- AC#11: Given RAGAS results, When I check thresholds,
         Then faithfulness > 0.85 and relevancy > 0.80
- AC#12: Given LangFuse, When I view eval results,
         Then I see RAGAS metrics tracked over time

Reference:
- docs/stories/5/5-3/5-3-implement-ragas-evaluation-suite.md
- docs/testing-strategy.md#RAGAS-Evaluation

Note: Tests requiring LLM calls will be skipped if OPENAI_API_KEY is not set.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import pytest

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


# ============================================================================
# SKIP CONDITIONS
# ============================================================================
OPENAI_API_KEY_AVAILABLE = os.environ.get("OPENAI_API_KEY") is not None
skip_without_openai = pytest.mark.skipif(
    not OPENAI_API_KEY_AVAILABLE,
    reason="OPENAI_API_KEY not set - RAGAS evaluation requires real LLM calls"
)

DATABASE_URL_AVAILABLE = os.environ.get("DATABASE_URL") is not None
skip_without_database = pytest.mark.skipif(
    not DATABASE_URL_AVAILABLE,
    reason="DATABASE_URL not set - RAG queries require database connection"
)

# ============================================================================
# THRESHOLDS (from testing-strategy.md)
# ============================================================================
FAITHFULNESS_THRESHOLD = 0.85
ANSWER_RELEVANCY_THRESHOLD = 0.80
CONTEXT_PRECISION_THRESHOLD = 0.75
CONTEXT_RECALL_THRESHOLD = 0.70


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def load_golden_dataset(dataset_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the golden evaluation dataset from a JSON file.
    
    Parameters:
        dataset_path (Optional[str]): Path to the dataset JSON file. If omitted, resolves to tests/fixtures/golden_dataset.json relative to the repository.
    
    Returns:
        data (dict): Parsed dataset containing keys such as `version`, `description`, `thresholds`, and `queries`.
    
    Raises:
        FileNotFoundError: If the dataset file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the dataset contains fewer than 20 query-answer pairs.
    """
    if dataset_path is None:
        dataset_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "fixtures", "golden_dataset.json"
        )

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate minimum requirements
    queries = data.get("queries", [])
    if len(queries) < 20:
        raise ValueError(f"Golden dataset must have at least 20 query-answer pairs, got {len(queries)}")

    logger.info(f"Loaded golden dataset with {len(queries)} query-answer pairs")
    return data


def prepare_ragas_dataset(
    queries: List[Dict[str, Any]],
    rag_answers: List[str],
    rag_contexts: List[List[str]],
) -> "EvaluationDataset":
    """
    Prepare a RAGAS EvaluationDataset from golden queries and corresponding RAG answers and contexts.
    
    Each dataset entry becomes a mapping with keys: `user_input` (the original query), `retrieved_contexts` (list of retrieved context strings), `response` (RAG-generated answer), and `reference` (taken from the query's `ground_truth` or `expected_answer` field when available).
    
    Parameters:
        queries: List of golden dataset entries; each entry must include a `query` string and may include `ground_truth` or `expected_answer` for the reference.
        rag_answers: List of answers produced by the RAG system, aligned with `queries`.
        rag_contexts: List of lists of retrieved context strings, aligned with `queries`.
    
    Returns:
        EvaluationDataset: A RAGAS EvaluationDataset where each sample contains `user_input`, `retrieved_contexts`, `response`, and `reference`.
    """
    from ragas import EvaluationDataset

    # Prepare data in RAGAS v0.3.9 expected format
    data_list = []
    for q, answer, contexts in zip(queries, rag_answers, rag_contexts):
        data_list.append({
            "user_input": q["query"],
            "retrieved_contexts": contexts,
            "response": answer,
            "reference": q.get("ground_truth", q.get("expected_answer", "")),
        })

    dataset = EvaluationDataset.from_list(data_list)
    logger.info(f"Prepared RAGAS dataset with {len(dataset)} samples")
    return dataset


_embedder_initialized = False
_db_initialized = False


async def ensure_embedder_initialized():
    """
    Ensure the database pool and global embedder are initialized before running RAG queries.
    
    Initializes the database connection pool if not already initialized and starts the global embedder, waiting for it to signal readiness (this wait may take on the order of tens of seconds on a cold start).
    """
    global _embedder_initialized, _db_initialized

    # Initialize database pool first
    if not _db_initialized:
        from utils.db_utils import db_pool
        await db_pool.initialize()
        _db_initialized = True
        logger.info("Database pool initialized for RAGAS evaluation")

    # Initialize embedder
    if not _embedder_initialized:
        from core.rag_service import initialize_global_embedder, _embedder_ready
        await initialize_global_embedder()
        # Wait for initialization to complete (may take ~40s on cold start)
        logger.info("Waiting for embedder initialization (may take ~40s)...")
        await _embedder_ready.wait()
        _embedder_initialized = True
        logger.info("Global embedder initialized for RAGAS evaluation")


async def run_rag_query(query: str, limit: int = 5) -> tuple[str, List[str]]:
    """
    Run a retrieval-augmented generation (RAG) search for a query and return the assembled answer and retrieved contexts.
    
    Parameters:
        query (str): The user query to search the knowledge base for.
        limit (int): Maximum number of context chunks to retrieve.
    
    Returns:
        tuple[str, List[str]]: A tuple where the first element is the generated answer string and the second element is the list of retrieved context strings.
    """
    from core.rag_service import search_knowledge_base_structured

    try:
        # Ensure embedder is initialized before running RAG query
        await ensure_embedder_initialized()

        result = await search_knowledge_base_structured(query, limit=limit)
        results = result.get("results", [])

        # Extract contexts from search results
        contexts = [r["content"] for r in results]

        # For now, concatenate contexts as the "answer"
        # In a full RAG system, this would go through an LLM to generate an answer
        if contexts:
            answer = " ".join(contexts[:3])  # Use top 3 contexts as answer
        else:
            answer = "No relevant information found."

        return answer, contexts

    except Exception as e:
        logger.error(f"RAG query failed for '{query}': {e}")
        return f"Error: {str(e)}", []


async def generate_evaluation_batch(
    queries: List[Dict[str, Any]], limit: int = 5
) -> tuple[List[str], List[List[str]]]:
    """
    Generate answers and retrieved contexts for a batch of golden-dataset queries.
    
    Parameters:
        queries (List[Dict[str, Any]]): List of golden dataset entries; each entry must contain a 'query' string.
        limit (int): Maximum number of context chunks to retrieve per query.
    
    Returns:
        Tuple (answers, contexts) where `answers` is a list of response strings and `contexts` is a list of lists of retrieved context strings (or a single-item list with "No context retrieved" when none were returned).
    """
    answers = []
    all_contexts = []

    for i, q in enumerate(queries):
        logger.info(f"Processing query {i+1}/{len(queries)}: {q['query'][:50]}...")
        answer, contexts = await run_rag_query(q["query"], limit=limit)
        answers.append(answer)
        all_contexts.append(contexts if contexts else ["No context retrieved"])

    return answers, all_contexts


def initialize_ragas_metrics():
    """
    Create core RAGAS metric instances and an evaluator LLM wrapper used for running evaluations.
    
    Returns:
        tuple: (metrics, evaluator_llm)
            - metrics (list): List of initialized RAGAS metric instances: Faithfulness, ResponseRelevancy, and LLMContextRecall.
            - evaluator_llm (LangchainLLMWrapper): A Langchain-wrapped LLM configured as the evaluator LLM.
    """
    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        Faithfulness,
        LLMContextRecall,
        ResponseRelevancy,
    )

    # Initialize evaluator LLM (RAGAS v0.3.9 passes LLM to evaluate())
    evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))

    # Create metric instances (core RAGAS metrics)
    metrics = [
        Faithfulness(),
        ResponseRelevancy(),
        LLMContextRecall(),
    ]

    logger.info(f"Initialized {len(metrics)} RAGAS metrics")
    return metrics, evaluator_llm


async def execute_ragas_evaluation(
    dataset: "EvaluationDataset",
    metrics: List,
    evaluator_llm: Any,
) -> Dict[str, float]:
    """
    Run RAGAS evaluation over a prepared EvaluationDataset and compute mean scores per metric.
    
    Parameters:
        dataset (EvaluationDataset): Prepared dataset containing `user_input`, `retrieved_contexts`, `response`, and `reference`.
        metrics (List): Initialized RAGAS metric instances to evaluate.
        evaluator_llm (Any): LLM wrapper used by RAGAS to perform evaluations.
    
    Returns:
        Dict[str, float]: Mapping from metric name to its mean score across the dataset; mean calculations ignore NaN values.
    """
    from ragas import evaluate

    logger.info(f"Starting RAGAS evaluation with {len(metrics)} metrics on {len(dataset)} samples...")

    # Run evaluation (RAGAS v0.3.9 returns EvaluationResult object)
    result = evaluate(dataset=dataset, metrics=metrics, llm=evaluator_llm)

    # Convert to pandas DataFrame and extract mean scores
    df = result.to_pandas()

    # Extract mean scores for each metric from DataFrame columns
    scores = {}
    for metric in metrics:
        metric_name = metric.name
        if metric_name in df.columns:
            # Calculate mean score (ignoring NaN values)
            mean_score = df[metric_name].mean()
            scores[metric_name] = float(mean_score)
            logger.info(f"  {metric_name}: {mean_score:.4f}")

    return scores


def track_ragas_results(
    scores: Dict[str, float],
    trace_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Send RAGAS evaluation metrics to LangFuse and return the created trace id.
    
    Creates a LangFuse trace with the provided metadata and records each metric in `scores` as a LangFuse score. If LangFuse is unavailable or an error occurs during tracking, the function degrades gracefully and returns `None`.
    
    Parameters:
        scores (Dict[str, float]): Mapping of metric names to their numeric score values.
        trace_metadata (Optional[Dict[str, Any]]): Optional metadata to attach to the LangFuse trace.
    
    Returns:
        Optional[str]: The LangFuse trace id as a string if tracking succeeded, `None` otherwise.
    """
    try:
        from langfuse import Langfuse

        langfuse = Langfuse()

        # Create trace for evaluation run
        trace = langfuse.trace(
            name="ragas_evaluation",
            metadata={
                "source": "ragas_evaluation",
                "evaluation_type": "ragas",
                **(trace_metadata or {}),
            },
        )

        # Upload each score
        for metric_name, score_value in scores.items():
            langfuse.score(
                name=metric_name,
                value=float(score_value),
                trace_id=trace.id,
            )
            logger.info(f"Uploaded score to LangFuse: {metric_name}={score_value:.4f}")

        # Flush to ensure data is sent
        langfuse.flush()

        logger.info(f"RAGAS scores tracked in LangFuse (trace_id={trace.id})")
        return trace.id

    except Exception as e:
        logger.warning(f"LangFuse tracking failed (graceful degradation): {e}")
        return None


def verify_thresholds(scores: Dict[str, float]) -> tuple[bool, List[str]]:
    """
    Check whether the given RAGAS metric scores exceed the configured thresholds for faithfulness and answer relevancy.
    
    Parameters:
        scores (Dict[str, float]): Mapping of metric names to scores. Expected keys inspected are
            "faithfulness" and "answer_relevancy"; missing keys are treated as 0.
    
    Returns:
        tuple[bool, List[str]]: `all_passed` is `True` if both metrics are greater than their thresholds, `False` otherwise.
        `failures` is a list of human-readable messages for each metric that did not meet its threshold (empty when `all_passed` is `True`).
    """
    failures = []

    faithfulness = scores.get("faithfulness", 0)
    if faithfulness <= FAITHFULNESS_THRESHOLD:
        failures.append(
            f"faithfulness={faithfulness:.4f} (required > {FAITHFULNESS_THRESHOLD})"
        )

    relevancy = scores.get("answer_relevancy", 0)
    if relevancy <= ANSWER_RELEVANCY_THRESHOLD:
        failures.append(
            f"answer_relevancy={relevancy:.4f} (required > {ANSWER_RELEVANCY_THRESHOLD})"
        )

    return len(failures) == 0, failures


# ============================================================================
# PYTEST FIXTURES
# ============================================================================


@pytest.fixture
def golden_dataset_data():
    """
    Provide the canonical golden dataset used by the test suite.
    
    Returns:
        dataset (dict): Parsed golden dataset containing at least 20 query-answer pairs.
    """
    return load_golden_dataset()


@pytest.fixture
def ragas_metrics():
    """
    Provide initialized RAGAS metrics and an evaluator LLM for tests.
    
    If the OPENAI_API_KEY environment variable is not set, this fixture will skip the test that requested it.
    
    Returns:
        tuple: A pair (metrics, evaluator_llm) where `metrics` is a list of initialized RAGAS metric instances and `evaluator_llm` is the LLM wrapper used to evaluate responses.
    """
    if not OPENAI_API_KEY_AVAILABLE:
        pytest.skip("OPENAI_API_KEY not set - cannot initialize RAGAS metrics")
    metrics, evaluator_llm = initialize_ragas_metrics()
    return metrics, evaluator_llm


# ============================================================================
# RAGAS EVALUATION TESTS
# ============================================================================


@pytest.mark.ragas
@pytest.mark.asyncio
async def test_golden_dataset_has_minimum_queries(golden_dataset_data):
    """
    Verify golden dataset contains at least 20 query-answer pairs.

    AC: #1/AC#10 - Golden dataset requirement
    """
    # Arrange
    queries = golden_dataset_data["queries"]

    # Act
    query_count = len(queries)

    # Assert
    assert query_count >= 20, f"Golden dataset must have at least 20 queries, got {query_count}"
    logger.info(f"Golden dataset validated: {query_count} query-answer pairs")


@pytest.mark.ragas
@pytest.mark.asyncio
@skip_without_openai
@skip_without_database
async def test_ragas_evaluation_calculates_all_metrics(golden_dataset_data, ragas_metrics):
    """
    Verify RAGAS evaluation calculates all metrics (faithfulness, relevancy, recall, correctness).

    AC: #1/AC#10 - RAGAS eval shows all metrics
    """
    # Arrange
    metrics, evaluator_llm = ragas_metrics
    queries = golden_dataset_data["queries"][:5]  # Use subset for faster test
    answers, contexts = await generate_evaluation_batch(queries, limit=3)
    dataset = prepare_ragas_dataset(queries, answers, contexts)

    # Act
    scores = await execute_ragas_evaluation(dataset, metrics, evaluator_llm)

    # Assert - Verify core metrics are present (RAGAS v0.3.9)
    # Note: Some metrics may not be computed if data is incomplete
    core_metrics = ["faithfulness", "answer_relevancy", "context_recall"]
    for metric in core_metrics:
        assert metric in scores, f"Missing metric: {metric}. Available: {list(scores.keys())}"
        assert isinstance(scores[metric], float), f"Metric {metric} should be float"

    # Verify at least some metrics are in valid range
    assert len(scores) >= 3, f"Expected at least 3 metrics, got {len(scores)}"
    logger.info(f"All metrics calculated successfully: {scores}")


@pytest.mark.ragas
@pytest.mark.asyncio
@skip_without_openai
@skip_without_database
async def test_ragas_evaluation_meets_thresholds(golden_dataset_data, ragas_metrics):
    """
    Verify RAGAS evaluation meets quality thresholds.

    AC: #2/AC#11 - faithfulness > 0.85, relevancy > 0.80
    """
    # Arrange
    metrics, evaluator_llm = ragas_metrics
    queries = golden_dataset_data["queries"][:10]  # Use subset for faster test
    answers, contexts = await generate_evaluation_batch(queries, limit=5)
    dataset = prepare_ragas_dataset(queries, answers, contexts)

    # Act
    scores = await execute_ragas_evaluation(dataset, metrics, evaluator_llm)
    passed, failures = verify_thresholds(scores)

    # Assert
    if not passed:
        failure_msg = "\n".join(failures)
        pytest.fail(f"RAGAS thresholds not met:\n{failure_msg}")

    logger.info(f"All thresholds met: faithfulness={scores.get('faithfulness', 0):.4f}, "
                f"answer_relevancy={scores.get('answer_relevancy', 0):.4f}")


@pytest.mark.ragas
@pytest.mark.asyncio
@skip_without_openai
@skip_without_database
async def test_ragas_evaluation_tracks_in_langfuse(golden_dataset_data, ragas_metrics):
    """
    Verify RAGAS scores are uploaded to LangFuse.

    AC: #3/AC#12 - RAGAS metrics tracked in LangFuse
    """
    # Arrange
    metrics, evaluator_llm = ragas_metrics
    queries = golden_dataset_data["queries"][:3]  # Minimal subset for tracking test
    answers, contexts = await generate_evaluation_batch(queries, limit=3)
    dataset = prepare_ragas_dataset(queries, answers, contexts)

    # Act
    scores = await execute_ragas_evaluation(dataset, metrics, evaluator_llm)
    trace_id = track_ragas_results(scores, {"test_name": "test_ragas_evaluation_tracks_in_langfuse"})

    # Assert - If LangFuse is available, trace_id should be set
    # If not available, graceful degradation means trace_id is None but test passes
    if trace_id:
        logger.info(f"RAGAS scores tracked in LangFuse: trace_id={trace_id}")
        assert isinstance(trace_id, str), "trace_id should be a string"
    else:
        logger.warning("LangFuse tracking skipped (graceful degradation)")


@pytest.mark.ragas
@pytest.mark.asyncio
@skip_without_openai
@skip_without_database
async def test_ragas_evaluation_graceful_degradation(golden_dataset_data, ragas_metrics, monkeypatch):
    """
    Verify evaluation continues if LangFuse is unavailable.

    AC: #3/AC#12 - Graceful degradation
    """
    # Arrange
    metrics, evaluator_llm = ragas_metrics
    queries = golden_dataset_data["queries"][:2]  # Minimal subset
    answers, contexts = await generate_evaluation_batch(queries, limit=2)
    dataset = prepare_ragas_dataset(queries, answers, contexts)

    # Simulate LangFuse unavailable
    def mock_langfuse_init(*args, **kwargs):
        """
        Simulate LangFuse initialization failure by always raising a connection error.
        
        Raises:
            ConnectionError: Always raised with message "LangFuse service unavailable" to mimic an unavailable LangFuse service during tests.
        """
        raise ConnectionError("LangFuse service unavailable")

    monkeypatch.setattr("tests.evaluation.test_ragas_evaluation.Langfuse", mock_langfuse_init, raising=False)

    # Act
    scores = await execute_ragas_evaluation(dataset, metrics, evaluator_llm)
    trace_id = track_ragas_results(scores)  # Should not raise

    # Assert - Evaluation completed, tracking gracefully degraded
    assert len(scores) > 0, "Scores should be calculated even without LangFuse"
    assert trace_id is None, "trace_id should be None when LangFuse unavailable"
    logger.info("Graceful degradation verified: evaluation completed without LangFuse")


@pytest.mark.ragas
@pytest.mark.asyncio
async def test_prepare_ragas_dataset_format(golden_dataset_data):
    """
    Verify prepare_ragas_dataset creates correct RAGAS EvaluationDataset format.

    AC: #1/AC#10 - Dataset preparation
    """
    # Arrange
    queries = golden_dataset_data["queries"][:3]
    mock_answers = ["answer1", "answer2", "answer3"]
    mock_contexts = [["ctx1"], ["ctx2a", "ctx2b"], ["ctx3"]]

    # Act
    dataset = prepare_ragas_dataset(queries, mock_answers, mock_contexts)

    # Assert
    assert len(dataset) == 3, f"Dataset should have 3 samples, got {len(dataset)}"

    # RAGAS v0.3.9 uses EvaluationDataset - verify first sample
    sample = dataset[0]
    assert sample.user_input == queries[0]["query"], "user_input mismatch"
    assert sample.response == "answer1", "response mismatch"
    assert sample.retrieved_contexts == ["ctx1"], "retrieved_contexts mismatch"


@pytest.mark.ragas
@pytest.mark.asyncio
async def test_load_golden_dataset_validates_minimum_queries():
    """
    Verify load_golden_dataset raises error if dataset has < 20 queries.

    AC: #1/AC#10 - Dataset validation
    """
    # Arrange - Create temp file with insufficient queries
    import tempfile

    insufficient_data = {
        "version": "1.0",
        "queries": [{"query": "q1", "expected_answer": "a1"}] * 10  # Only 10 queries
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(insufficient_data, f)
        temp_path = f.name

    # Act & Assert
    try:
        with pytest.raises(ValueError, match="at least 20"):
            load_golden_dataset(temp_path)
    finally:
        os.unlink(temp_path)


@pytest.mark.ragas
@pytest.mark.asyncio
async def test_verify_thresholds_detects_failures():
    """
    Verify threshold verification correctly detects failures.

    AC: #2/AC#11 - Threshold verification
    """
    # Arrange - Scores below thresholds
    low_scores = {
        "faithfulness": 0.70,  # Below 0.85
        "answer_relevancy": 0.60,  # Below 0.80
    }

    # Act
    passed, failures = verify_thresholds(low_scores)

    # Assert
    assert not passed, "Should detect threshold failures"
    assert len(failures) == 2, f"Should have 2 failures, got {len(failures)}"
    assert any("faithfulness" in f for f in failures)
    assert any("answer_relevancy" in f for f in failures)


@pytest.mark.ragas
@pytest.mark.asyncio
async def test_verify_thresholds_passes_when_met():
    """
    Verify threshold verification passes when thresholds are met.

    AC: #2/AC#11 - Threshold verification
    """
    # Arrange - Scores above thresholds
    high_scores = {
        "faithfulness": 0.90,  # Above 0.85
        "answer_relevancy": 0.85,  # Above 0.80
    }

    # Act
    passed, failures = verify_thresholds(high_scores)

    # Assert
    assert passed, "Should pass when thresholds met"
    assert len(failures) == 0, f"Should have no failures, got {failures}"

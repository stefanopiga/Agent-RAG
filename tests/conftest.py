"""
Pytest configuration and shared fixtures.

Fixtures organized by category:
- Event loop: Async test support
- Database: mock_db_pool, test_db
- Embedder: mock_embedder
- LLM: test_model (PydanticAI TestModel)
- LangFuse: mock_langfuse
- HTTP: mock_httpx_response
- Search: mock_search_response, mock_list_documents_response

Reference: docs/stories/5/tech-spec-epic-5.md#Data-Models-and-Contracts
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# PYTEST MARKERS CONFIGURATION
# ============================================================================
def pytest_configure(config):
    """Register custom markers for test categorization."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated, mocked dependencies)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (mocked DB/API, real logic, <5s per test)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (real services, slow, <30s per test)"
    )
    config.addinivalue_line("markers", "slow: Slow tests (>5s execution time)")
    config.addinivalue_line("markers", "ragas: RAGAS evaluation tests (LLM calls, golden dataset)")


# ============================================================================
# EVENT LOOP FIXTURES (Async Test Support)
# ============================================================================
@pytest.fixture(scope="session")
def event_loop():
    """
    Provide a fresh asyncio event loop for the test session and close it on teardown.
    
    Returns:
        loop (asyncio.AbstractEventLoop): The event loop instance yielded to tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# DATABASE FIXTURES
# ============================================================================
@pytest.fixture
def mock_db_pool():
    """
    Create a mock DatabasePool for tests with a configurable mocked connection.
    
    Returns:
        mock_pool (MagicMock): A mocked pool whose `acquire` async context manager yields a mocked connection exposing:
            - `fetch()` -> default: [] (list of rows)
            - `fetchrow()` -> default: None (single row)
            - `fetchval()` -> default: 1 (scalar value)
            - `execute()` -> default: "OK" (DML result)
        The returned mock also provides `initialize`, `close`, and `pool` attributes (all mocks) and exposes the underlying connection as `_mock_connection` for easy test setup and assertions.
    """
    mock_pool = MagicMock()
    mock_connection = AsyncMock()

    # Mock connection.fetch() for SELECT queries
    mock_connection.fetch = AsyncMock(return_value=[])

    # Mock connection.fetchrow() for single row queries
    mock_connection.fetchrow = AsyncMock(return_value=None)

    # Mock connection.fetchval() for scalar queries
    mock_connection.fetchval = AsyncMock(return_value=1)

    # Mock connection.execute() for INSERT/UPDATE/DELETE
    mock_connection.execute = AsyncMock(return_value="OK")

    @asynccontextmanager
    async def mock_acquire():
        """
        Context manager that yields the mocked database connection used by the pool's acquire.
        
        Returns:
            mock_connection: The mocked database connection object.
        """
        yield mock_connection

    mock_pool.acquire = mock_acquire
    mock_pool.initialize = AsyncMock()
    mock_pool.close = AsyncMock()
    mock_pool.pool = MagicMock()

    # Expose connection mock for easy assertion setup
    mock_pool._mock_connection = mock_connection

    return mock_pool


@pytest.fixture
async def test_db(mock_db_pool):
    """
    Provide a mock database pool pre-populated with default document data and reset its mocks after use.
    
    Yields a mocked database pool (`mock_db_pool`) whose `_mock_connection` has default `fetch`, `fetchrow`, and `execute` behaviours suitable for integration tests; on teardown the connection's `fetch`, `fetchrow`, and `execute` mocks are reset.
    """
    # Setup: Configure mock with test data
    mock_connection = mock_db_pool._mock_connection

    # Default test data for documents
    mock_connection.fetch.return_value = [
        {
            "id": "test-doc-1",
            "title": "Test Document 1",
            "source": "test-source-1",
            "metadata": '{"type": "test"}',
            "created_at": MagicMock(isoformat=lambda: "2025-01-01T00:00:00Z"),
            "updated_at": MagicMock(isoformat=lambda: "2025-01-01T00:00:00Z"),
            "chunk_count": 5,
        }
    ]

    yield mock_db_pool

    # Teardown: Reset mock state
    mock_connection.fetch.reset_mock()
    mock_connection.fetchrow.reset_mock()
    mock_connection.execute.reset_mock()


# ============================================================================
# EMBEDDER FIXTURES
# ============================================================================
@pytest.fixture
def mock_embedder():
    """
    Provide a mocked embedder that produces deterministic embeddings for tests.
    
    The returned object exposes async methods `embed_query(text)` and `embed_documents(texts)`:
    - `embed_query(text)` returns a deterministic list of 1536 floats derived from `text`.
    - `embed_documents(texts)` returns a list of embeddings, one per input text.
    
    The mock also includes attributes `model_name` set to "text-embedding-3-small" and `cost_tracking_enabled` set to False.
    
    Returns:
        mock_embedder: A mock embedder object with async `embed_query` and `embed_documents` methods that produce deterministic 1536-dimensional embeddings.
    """
    mock = AsyncMock()

    # Standard embedding dimension for text-embedding-3-small
    embedding_dim = 1536

    # Generate deterministic mock embedding
    def generate_mock_embedding(text: str) -> List[float]:
        """
        Produce a deterministic embedding vector for the given text.
        
        Parameters:
            text (str): Input text to generate an embedding for.
        
        Returns:
            List[float]: A list of floats of length `embedding_dim` representing a deterministic embedding for the input text.
        """
        seed = hash(text) % 10000
        return [float(seed + i) / 10000.0 for i in range(embedding_dim)]

    async def mock_embed_query(text: str) -> List[float]:
        """
        Generate a deterministic mock embedding for the given text.
        
        Parameters:
            text (str): Input text to embed.
        
        Returns:
            List[float]: Deterministic embedding vector of length 1536 derived from `text`.
        """
        return generate_mock_embedding(text)

    async def mock_embed_documents(texts: List[str]) -> List[List[float]]:
        """
        Produce deterministic embeddings for each input text.
        
        Parameters:
            texts (List[str]): Sequence of input strings to embed.
        
        Returns:
            List[List[float]]: A list of embeddings where each embedding is a list of floats (length 1536) corresponding to the input texts; embeddings are deterministic for a given input.
        """
        return [generate_mock_embedding(t) for t in texts]

    mock.embed_query = AsyncMock(side_effect=mock_embed_query)
    mock.embed_documents = AsyncMock(side_effect=mock_embed_documents)
    mock.model_name = "text-embedding-3-small"
    mock.cost_tracking_enabled = False

    return mock


# ============================================================================
# PYDANTICAI TESTMODEL FIXTURES
# ============================================================================
@pytest.fixture
def test_model():
    """
    Provide a TestModel-compatible model for unit tests that produces structured outputs without real API calls.
    
    Attempts to instantiate pydantic_ai.models.test.TestModel. If pydantic_ai is not installed, returns a MagicMock fallback with its name set to "test".
    
    Returns:
        An instance of TestModel when available, otherwise a MagicMock with name "test".
    """
    try:
        from pydantic_ai.models.test import TestModel

        return TestModel()
    except ImportError:
        # Fallback mock if pydantic-ai not installed
        mock = MagicMock()
        mock.name = "test"
        return mock


@pytest.fixture
def disable_model_requests():
    """
    Temporarily disable real LLM API requests from pydantic_ai for the duration of a test.
    
    Sets pydantic_ai.models.ALLOW_MODEL_REQUESTS to False while the fixture is active and restores the previous value on teardown. If pydantic_ai is not installed, the fixture does nothing.
    """
    try:
        from pydantic_ai import models

        original_value = models.ALLOW_MODEL_REQUESTS
        models.ALLOW_MODEL_REQUESTS = False
        yield
        models.ALLOW_MODEL_REQUESTS = original_value
    except ImportError:
        yield


# ============================================================================
# LANGFUSE FIXTURES
# ============================================================================
@pytest.fixture
def mock_langfuse():
    """
    Provide a mocked LangFuse client that simulates tracing and scoring operations for tests.
    
    The returned mock simulates a LangFuse client with:
    - trace(): returns a mock trace with id "test-trace-id" and methods span() and generation().
    - span(): (on the trace) returns a mock span with id "test-span-id".
    - generation(): (on the trace) returns a mock generation with id "test-generation-id".
    - create_score(): returns a mock score object with id "test-score-id".
    - flush: a callable mock for flushing/sending data.
    
    Returns:
        MagicMock: A configured mock that imitates the LangFuse client API used in tests.
    """
    mock = MagicMock()

    # Mock trace creation
    mock_trace = MagicMock()
    mock_trace.id = "test-trace-id"
    mock.trace.return_value = mock_trace

    # Mock span creation
    mock_span = MagicMock()
    mock_span.id = "test-span-id"
    mock_trace.span.return_value = mock_span

    # Mock generation creation
    mock_generation = MagicMock()
    mock_generation.id = "test-generation-id"
    mock_trace.generation.return_value = mock_generation

    # Mock score creation (for RAGAS evaluation tracking)
    mock.create_score = MagicMock(return_value=MagicMock(id="test-score-id"))

    # Mock flush (for ensuring data is sent)
    mock.flush = MagicMock()

    return mock


@pytest.fixture
def mock_langfuse_disabled():
    """
    Temporarily disable LangFuse by setting LANGFUSE_ENABLED to "false" in the environment for the duration of a test.
    
    This fixture yields control to the test while the environment variable is set and restores the original environment afterwards, allowing tests to exercise behavior when LangFuse is not available.
    """
    with patch.dict("os.environ", {"LANGFUSE_ENABLED": "false"}):
        yield


# ============================================================================
# HTTP FIXTURES
# ============================================================================
@pytest.fixture
def mock_httpx_response():
    """
    Factory fixture that produces a callable for creating mocked httpx-like responses.
    
    The returned callable _create_response(status_code=200, json_data=None, text="") builds a MagicMock with these observable behaviors:
    - .status_code set to the provided status_code.
    - .text set to the provided text.
    - .json() returning the provided json_data or an empty dict when json_data is None.
    - .raise_for_status() does nothing for status codes below 400; for status_code >= 400 it raises an httpx.HTTPStatusError when invoked.
    
    Returns:
        callable: A function that accepts (status_code: int = 200, json_data: Optional[dict] = None, text: str = "") and returns a mocked httpx-like response object.
    """

    def _create_response(status_code=200, json_data=None, text=""):
        """
        Create a MagicMock that simulates an httpx-like Response for tests.
        
        Parameters:
            status_code (int): HTTP status code to set on the mock. Defaults to 200.
            json_data (Optional[dict]): Value to return from response.json(). If None, returns an empty dict.
            text (str): Value to set on response.text. Defaults to empty string.
        
        Returns:
            MagicMock: A mock response with `.status_code`, `.text`, and `.json()` configured.
                Its `.raise_for_status()` is a mock that will raise `httpx.HTTPStatusError` when
                `status_code` is 400 or greater, and do nothing otherwise.
        """
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.json = MagicMock(return_value=json_data or {})
        response.raise_for_status = MagicMock()
        if status_code >= 400:
            from httpx import HTTPStatusError

            response.raise_for_status.side_effect = HTTPStatusError(
                message=f"HTTP {status_code}", request=MagicMock(), response=response
            )
        return response

    return _create_response


# ============================================================================
# SEARCH RESPONSE FIXTURES
# ============================================================================
@pytest.fixture
def mock_search_response():
    """
    Provide a sample successful search API response for tests.
    
    Returns:
        response (dict): Mocked search response with keys:
            - results (list): List of result objects; each result contains:
                - title (str)
                - content (str)
                - source (str)
                - similarity (float)
                - metadata (dict)
            - count (int): Number of results
            - processing_time_ms (int): Processing time in milliseconds
    """
    return {
        "results": [
            {
                "title": "Test Document",
                "content": "This is test content about RAG systems.",
                "source": "test-source",
                "similarity": 0.95,
                "metadata": {"type": "documentation"},
            }
        ],
        "count": 1,
        "processing_time_ms": 100,
    }


@pytest.fixture
def mock_list_documents_response():
    """
    Provide a mocked response representing a successful listing of documents for tests.
    
    Returns:
        dict: A response dictionary with keys:
            - "documents": a list of document metadata dictionaries, each containing
              "title", "source", "chunk_count", and "updated_at".
            - "count": the total number of documents.
    """
    return {
        "documents": [
            {
                "title": "Test Document 1",
                "source": "test-source-1",
                "chunk_count": 10,
                "updated_at": "2025-01-01T00:00:00Z",
            },
            {
                "title": "Test Document 2",
                "source": "test-source-2",
                "chunk_count": 5,
                "updated_at": "2025-01-02T00:00:00Z",
            },
        ],
        "count": 2,
    }


# ============================================================================
# GOLDEN DATASET FIXTURES (RAGAS Evaluation)
# ============================================================================
@pytest.fixture
def golden_dataset_path():
    """
    Locate the golden_dataset.json fixture used for RAGAS evaluation.
    
    Returns:
        file_path (str): Path to the golden_dataset.json file in the "fixtures" subdirectory next to this file.
    """
    import os

    return os.path.join(os.path.dirname(__file__), "fixtures", "golden_dataset.json")


@pytest.fixture
def golden_dataset(golden_dataset_path):
    """
    Load and parse the golden dataset JSON used for RAGAS evaluation.
    
    If the file at golden_dataset_path does not exist, the current test is skipped.
    
    Returns:
        The parsed JSON content of the golden dataset (typically a dict containing `queries` and related fields).
    
    Raises:
        pytest.skip: If the golden dataset file is not found.
    """
    import json
    import os

    if not os.path.exists(golden_dataset_path):
        pytest.skip("Golden dataset not found - run Task 5 first")

    with open(golden_dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)
# Epic Technical Specification: Testing & Quality Assurance (TDD)

Date: 2025-01-27
Author: Stefano
Epic ID: 5
Status: Draft
Last Updated: 2025-12-01
Update Note: Corretto con informazioni verificate da fonti ufficiali (PydanticAI, pytest-playwright, RAGAS, LangFuse)

---

## Overview

Epic 5 implementa Test-Driven Development con suite completa di unit tests, RAG evaluation, e E2E tests per garantire qualità production-ready. Questo epic trasforma il sistema da codice non testato a sistema con coverage >70%, RAGAS evaluation per validare qualità RAG, e pytest-playwright E2E tests per workflow critici. L'implementazione segue rigorosamente il pattern Red-Green-Refactor (TDD), garantendo che ogni feature sia testabile e testata prima dell'implementazione. Epic 5 completa l'infrastruttura di testing necessaria per validare monitoring accuracy (Epic 2), prevenire regressions, e garantire RAG quality attraverso automation completa e golden dataset per RAGAS evaluation.

## Objectives and Scope

**In-Scope:**

- Setup testing infrastructure completa con pytest, fixtures, e configurazione coverage >70%
- Struttura TDD rigorosa: `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`
- Unit tests per tutti i moduli core (`core/`, `ingestion/`, `utils/`) con PydanticAI TestModel per LLM mocking
- RAGAS evaluation suite con golden dataset (20+ query-answer pairs) e threshold enforcement (faithfulness >0.85, relevancy >0.80)
- pytest-playwright E2E tests per workflow Streamlit critici con screenshot/video recording
- Integration tests per MCP server endpoints e API endpoints
- Coverage enforcement in CI/CD con fail build se coverage <70%
- LangFuse integration per tracking test results e RAGAS metrics nel tempo
- Test fixtures per database setup/teardown automatico
- pytest markers configurazione (unit, integration, e2e, slow, ragas)

**Out-of-Scope:**

- Performance testing o load testing in CI/CD - Future epic
- Security testing automatizzato (penetration testing) - Future epic
- Multi-browser E2E testing (solo Chromium per pytest-playwright) - Future enhancement
- Test data generation automatizzata - Future enhancement
- Mutation testing - Future enhancement

## System Architecture Alignment

Epic 5 si allinea direttamente con l'architettura documentata in `docs/architecture.md`, implementando la decisione architetturale ADR-003 (TDD Structure Rigorosa). I componenti principali coinvolti sono:

- **`tests/`**: Directory principale per tutta la test suite

  - `tests/unit/`: Unit tests isolati con mocked dependencies
  - `tests/integration/`: Integration tests con mocked DB/API, no real external services
  - `tests/e2e/`: E2E tests con pytest-playwright per workflow Streamlit
  - `tests/fixtures/`: Shared test data, golden dataset per RAGAS evaluation

- **`tests/conftest.py`**: Shared fixtures per database, embedder, LangFuse client mocking

- **`pyproject.toml`**: Configuration per pytest, coverage threshold >70%, markers

- **`.github/workflows/ci.yml`**: CI/CD pipeline già esistente (Epic 4) esteso con coverage enforcement

- **`core/rag_service.py`**: Target principale per unit tests con PydanticAI TestModel

- **`ingestion/embedder.py`**: Target per unit tests con mocked OpenAI embeddings

- **`docling_mcp/server.py`**: Target per integration tests MCP server

- **`app.py`**: Target per E2E tests Streamlit workflow

L'epic implementa il pattern "Test-Driven Development" per garantire che ogni feature sia testabile e testata, con coverage enforcement automatico e RAGAS evaluation per validare qualità RAG.

## Detailed Design

### Services and Modules

| Service/Module                            | Responsibility                          | Inputs                                    | Outputs                                         | Owner |
| ----------------------------------------- | --------------------------------------- | ----------------------------------------- | ----------------------------------------------- | ----- |
| `tests/conftest.py`                       | Shared fixtures e configurazione pytest | Test execution context                    | Fixtures disponibili per tutti i test           | QA    |
| `tests/unit/test_rag_service.py`          | Unit tests per RAG service logic        | Mocked LLM, mocked DB                     | Test results, coverage report                   | Dev   |
| `tests/unit/test_embedder.py`             | Unit tests per embedding generation     | Mocked OpenAI API                         | Test results, coverage report                   | Dev   |
| `tests/unit/test_chunker.py`              | Unit tests per chunking logic           | Document content                          | Test results, coverage report                   | Dev   |
| `tests/integration/test_mcp_server.py`    | Integration tests MCP server            | MCP client, mocked DB                     | Test results, integration coverage              | Dev   |
| `tests/integration/test_api_endpoints.py` | Integration tests API endpoints         | FastAPI TestClient, mocked DB             | Test results, integration coverage              | Dev   |
| `tests/e2e/test_streamlit_workflow.py`    | E2E tests Streamlit workflow            | pytest-playwright fixtures, real services | Screenshots, video, test results                | QA    |
| `tests/fixtures/golden_dataset.json`      | Golden dataset per RAGAS evaluation     | Query-answer pairs (20+)                  | RAGAS evaluation input                          | QA    |
| `tests/fixtures/test_db_setup.py`         | Database fixtures setup/teardown        | Test database connection                  | Clean test database state                       | Dev   |
| pytest                                    | Test execution framework                | Test files, fixtures                      | Test results, coverage report                   | QA    |
| pytest-cov                                | Coverage tracking                       | Test execution                            | Coverage report (HTML, terminal)                | QA    |
| pytest-asyncio                            | Async test support                      | Async test functions                      | Async test execution                            | Dev   |
| pytest-mock                               | Mocking utilities                       | Test functions                            | Mocked dependencies                             | Dev   |
| RAGAS                                     | RAG quality evaluation                  | Golden dataset, RAG responses             | Faithfulness, relevancy, precision, recall      | QA    |
| pytest-playwright                         | E2E browser automation                  | Streamlit app URL                         | Screenshots, video, test results, fixtures      | QA    |
| PydanticAI TestModel                      | LLM mocking per unit tests              | Test functions                            | Mocked LLM responses senza API calls            | Dev   |
| langchain-openai                          | LLM/embeddings wrappers per RAGAS       | RAGAS metrics                             | LangchainLLMWrapper, LangchainEmbeddingsWrapper | QA    |
| datasets                                  | Dataset format per RAGAS                | Evaluation data                           | HuggingFace Dataset                             | QA    |

### Data Models and Contracts

**Test Fixtures (`tests/conftest.py`):**

```python
@pytest.fixture
async def mock_db_pool():
    """Mock database pool for unit tests."""
    # Returns mocked AsyncPG pool
    pass

@pytest.fixture
async def mock_embedder():
    """Mock embedder for unit tests."""
    # Returns mocked EmbeddingGenerator
    pass

@pytest.fixture
def test_model():
    """PydanticAI TestModel for LLM mocking."""
    from pydantic_ai.models.test import TestModel
    return TestModel()

@pytest.fixture
async def test_db():
    """Test database with setup/teardown."""
    # Setup: Create test schema, insert test data
    # Teardown: Drop test schema
    pass
```

**Golden Dataset (`tests/fixtures/golden_dataset.json`):**

```json
{
  "queries": [
    {
      "query": "What is the main purpose of this system?",
      "expected_answer": "The system provides RAG capabilities...",
      "context": ["Document 1 content...", "Document 2 content..."],
      "metadata": {
        "source": "test_document_1.pdf",
        "expected_faithfulness": 0.9,
        "expected_relevancy": 0.85
      }
    }
    // ... 20+ query-answer pairs
  ]
}
```

**RAGAS Evaluation Results:**

```python
{
  "faithfulness": 0.87,  # Threshold: >0.85
  "answer_relevancy": 0.82,  # Threshold: >0.80
  "context_precision": 0.75,
  "context_recall": 0.78,
  "individual_scores": [
    {
      "query": "What is...",
      "faithfulness": 0.90,
      "answer_relevancy": 0.85
    }
    // ... per ogni query nel golden dataset
  ]
}
```

**Coverage Report Structure:**

- **HTML Report**: `htmlcov/index.html` con line-by-line coverage
- **Terminal Report**: Coverage summary con missing lines
- **CI/CD Report**: Coverage percentage con fail se <70%

### APIs and Interfaces

**Pytest CLI Interface:**

```bash
# Run all tests
pytest

# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration

# Run E2E tests only
pytest -m e2e

# Run with coverage
pytest --cov=core --cov=ingestion --cov-report=html

# Run with coverage threshold enforcement
pytest --cov=core --cov-fail-under=70

# Run RAGAS evaluation
pytest -m ragas

# Run slow tests (include E2E)
pytest -m slow
```

**PydanticAI TestModel Interface:**

```python
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from pydantic_ai import models

# Disable real API calls globally (optional safety measure)
models.ALLOW_MODEL_REQUESTS = False

# Create agent
agent = Agent(
    'openai:gpt-4o-mini',
    system_prompt='You are a helpful assistant.',
    result_type=str
)

# Override model with TestModel using context manager
# TestModel generates valid structured data automatically based on tool schemas
with agent.override(model=TestModel()):
    result = await agent.run("What is RAG?")
    # TestModel produces valid output without real API calls
    assert result.data is not None
```

**RAGAS Evaluation Interface:**

```python
from ragas import evaluate
from ragas.metrics import (
    Faithfulness,
    ResponseRelevancy,
    LLMContextPrecisionWithoutReference,
    ContextRecall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics.base import MetricWithLLM, MetricWithEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from datasets import Dataset
from langfuse import get_client

# Load golden dataset
with open("tests/fixtures/golden_dataset.json") as f:
    dataset_data = json.load(f)

# Prepare evaluation batch
evaluation_batch = {
    "question": [q["query"] for q in dataset_data["queries"]],
    "answer": [q["expected_answer"] for q in dataset_data["queries"]],
    "contexts": [q["context"] for q in dataset_data["queries"]],
    "ground_truth": [q.get("ground_truth", "") for q in dataset_data["queries"]],
}

# Create Dataset
dataset = Dataset.from_dict(evaluation_batch)

# Initialize metrics (classes, not variables)
metrics = [
    Faithfulness(),
    ResponseRelevancy(),
    LLMContextPrecisionWithoutReference(),
    ContextRecall(),
]

# Initialize metrics with LLM and embeddings wrappers
llm = LangchainLLMWrapper(ChatOpenAI())
embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings())

for metric in metrics:
    if isinstance(metric, MetricWithLLM):
        metric.llm = llm
    if isinstance(metric, MetricWithEmbeddings):
        metric.embeddings = embeddings

# Run evaluation
results = evaluate(dataset=dataset, metrics=metrics)

# Verify thresholds
assert results["faithfulness"] > 0.85
assert results["answer_relevancy"] > 0.80

# Upload scores to LangFuse for tracking
langfuse = get_client()
trace_id = "test-trace-id"  # From actual trace or test context

for metric_name, score_value in results.items():
    langfuse.create_score(
        name=metric_name,
        value=float(score_value),
        trace_id=trace_id,
    )
```

**Playwright E2E Interface:**

```python
# conftest.py - configurazione pytest-playwright fixtures
import pytest

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for E2E tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
    }

# test_streamlit_workflow.py
# page fixture è automaticamente disponibile da pytest-playwright
def test_streamlit_query_workflow(page):
    """Test complete Streamlit query workflow."""
    # Navigate to Streamlit app (usa --base-url da CLI o URL completo)
    page.goto("/")  # Se --base-url=http://localhost:8501 è configurato
    # Oppure: page.goto("http://localhost:8501")

    # Enter query
    query_input = page.locator('[data-testid="query-input"]')
    query_input.fill("What is RAG?")

    # Submit query
    submit_button = page.locator('[data-testid="submit-button"]')
    submit_button.click()

    # Wait for response
    response = page.locator('[data-testid="response"]')
    response.wait_for(state="visible", timeout=10000)

    # Verify response contains expected content
    assert "RAG" in response.text()

    # Take screenshot for debugging
    page.screenshot(path="tests/e2e/screenshots/query_workflow.png")
```

**CLI Usage:**

```bash
# Run E2E tests with base URL
pytest tests/e2e/ --base-url=http://localhost:8501

# Run with visible browser (debugging)
pytest tests/e2e/ --base-url=http://localhost:8501 --headed

# Run with specific browser
pytest tests/e2e/ --base-url=http://localhost:8501 --browser=chromium

# Run with tracing/video/screenshots
pytest tests/e2e/ --base-url=http://localhost:8501 --tracing=on --video=on --screenshot=on
```

### Workflows and Sequencing

**TDD Workflow (Red-Green-Refactor):**

1. **Red**: Scrivere test che fallisce (feature non implementata)
2. **Green**: Implementare codice minimo per far passare il test
3. **Refactor**: Migliorare codice mantenendo test verde
4. **Repeat**: Ripetere per ogni feature

**Test Execution Workflow:**

1. **Setup**: `conftest.py` fixtures inizializzano mock DB, embedder, LangFuse client
2. **Unit Tests**: Eseguono isolati con mocked dependencies (fast, <1s per test)
3. **Integration Tests**: Eseguono con mocked DB/API ma real logic (medium, <5s per test)
4. **E2E Tests**: Eseguono con real services (slow, <30s per test)
5. **Coverage Report**: Generato automaticamente dopo tutti i test
6. **Coverage Validation**: CI/CD verifica threshold >70%, fail build se non raggiunto

**RAGAS Evaluation Workflow:**

1. **Load Golden Dataset**: Carica `tests/fixtures/golden_dataset.json` (20+ query-answer pairs)
2. **Prepare Dataset**: Converti in HuggingFace `Dataset` format con `Dataset.from_dict()`
3. **Initialize Metrics**: Crea istanze metriche (classi: `Faithfulness()`, `ResponseRelevancy()`, etc.)
4. **Configure LLM/Embeddings**: Inizializza metriche con `LangchainLLMWrapper` e `LangchainEmbeddingsWrapper`
5. **Execute RAG Queries**: Per ogni query nel dataset, esegue RAG query reale
6. **Run RAGAS Evaluation**: Esegue `evaluate(dataset, metrics)` con Dataset e metriche inizializzate
7. **Verify Thresholds**: Verifica faithfulness >0.85, relevancy >0.80
8. **Upload to LangFuse**: Invia scores a LangFuse tramite `langfuse.create_score()` per tracking nel tempo
9. **Fail if Threshold Not Met**: Test fallisce se thresholds non raggiunti

**CI/CD Integration Workflow:**

1. **GitHub Actions Trigger**: Su ogni PR/push a main/develop
2. **Install Dependencies**: `uv sync --extra dev`
3. **Install Playwright Browsers**: `playwright install chromium` (solo Chromium per CI/CD)
4. **Run Lint**: `ruff check` (già esistente, Epic 4)
5. **Run Type Check**: `mypy` (già esistente, Epic 4)
6. **Run Tests**: `pytest --cov=core --cov=ingestion --cov-report=xml`
7. **Run E2E Tests**: `pytest tests/e2e/ --base-url=http://localhost:8501` (headless mode default)
8. **Upload Coverage**: Upload coverage XML a GitHub Actions artifacts
9. **Coverage Threshold Check**: Verifica coverage >70%, fail build se non raggiunto
10. **Publish Coverage Report**: Pubblica HTML report come artifact
11. **Publish E2E Artifacts**: Screenshots/videos/traces su test failure

## Non-Functional Requirements

### Performance

**Test Execution Performance:**

- **Unit Tests**: <1s per test (isolated, mocked dependencies)
- **Integration Tests**: <5s per test (mocked DB/API, real logic)
- **E2E Tests**: <30s per test (real services, browser automation)
- **Total Test Suite**: <5 minuti per esecuzione completa (NFR-T1)
- **RAGAS Evaluation**: <10 minuti per golden dataset completo (NFR-T2)

**Coverage Report Generation:**

- **HTML Report**: <10s per generazione
- **Terminal Report**: <1s per generazione
- **CI/CD Report**: <5s per upload

### Security

**Test Data Security:**

- **No Real API Keys**: Tutti i test usano mocked API keys o TestModel
- **No Real Database**: Unit tests usano mocked DB, integration tests usano test database isolato
- **Test Database Isolation**: Test database separato da production, dropped dopo ogni test run
- **Secrets Not Logged**: Nessun secret in test logs o coverage reports

**Test Environment Security:**

- **Isolated Test Environment**: Test eseguiti in ambiente isolato (Docker o virtualenv)
- **No Network Access**: Unit tests non richiedono network access (tutti mocked)
- **Controlled Network Access**: Integration/E2E tests usano test services, non production

### Reliability/Availability

**Test Reliability:**

- **Deterministic Tests**: Tutti i test sono deterministici (no random data, fixed seeds)
- **Test Isolation**: Ogni test è isolato, non dipende da altri test
- **Cleanup After Tests**: Fixtures garantiscono cleanup dopo ogni test (teardown automatico)
- **Retry Logic**: E2E tests hanno retry logic per transient failures (network, timing)

**Test Infrastructure Availability:**

- **Graceful Degradation**: Se LangFuse non disponibile, test continua senza tracking
- **Mock Fallback**: Se test database non disponibile, usa mocked DB
- **CI/CD Resilience**: Se test fallisce, CI/CD fornisce dettagliati error logs e artifacts

### Observability

**Test Results Observability:**

- **Coverage Reports**: HTML report con line-by-line coverage, missing lines evidenziate
- **Test Logs**: Structured logging per ogni test execution (pytest --verbose)
- **LangFuse Integration**: RAGAS evaluation results tracked in LangFuse per trend analysis
- **CI/CD Artifacts**: Coverage reports, test logs, screenshots pubblicati come GitHub Actions artifacts

**Test Metrics Tracking:**

- **Coverage Trends**: Coverage percentage tracked nel tempo (CI/CD reports)
- **RAGAS Trends**: Faithfulness, relevancy scores tracked nel tempo (LangFuse)
- **Test Execution Time**: Test execution time tracked per identificare slow tests
- **Test Failure Rate**: Test failure rate tracked per identificare flaky tests

## Dependencies and Integrations

**Testing Dependencies (`pyproject.toml`):**

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",           # Test framework
    "pytest-asyncio>=0.23.0",  # Async test support
    "pytest-cov>=4.1.0",       # Coverage tracking
    "pytest-mock>=3.12.0",     # Mocking utilities
    "pytest-playwright>=0.4.0", # E2E browser automation (includes playwright)
    "ragas>=0.1.0",            # RAG quality evaluation
    "langchain-openai>=0.1.0", # Required for RAGAS LLM/embeddings wrappers
    "datasets>=2.14.0",        # Required for RAGAS Dataset format
]
```

**Integration Points:**

- **PydanticAI TestModel**: Integrazione con `pydantic-ai>=0.7.4` per LLM mocking (già presente in dependencies)
- **LangFuse SDK**: Integrazione con `langfuse>=3.0.0` per tracking test results (già presente in dependencies)
- **PostgreSQL Test Database**: Integrazione con `asyncpg>=0.30.0` per test database (già presente in dependencies)
- **FastAPI TestClient**: Integrazione con `fastapi>=0.109.0` per API endpoint testing (già presente in dependencies)
- **pytest-playwright**: Integrazione con Playwright per E2E testing (nuova dependency, include playwright)
- **langchain-openai**: Richiesto per RAGAS LLM/embeddings wrappers
- **datasets**: Richiesto per RAGAS Dataset format (HuggingFace)

**Version Constraints:**

- **pytest**: >=8.0.0 (supporto async migliorato, coverage reporting)
- **pytest-asyncio**: >=0.23.0 (async mode "auto" support)
- **pytest-cov**: >=4.1.0 (coverage threshold enforcement)
- **pytest-playwright**: >=0.4.0 (E2E browser automation, include playwright)
- **ragas**: >=0.1.0 (RAG quality evaluation)
- **langchain-openai**: >=0.1.0 (RAGAS LLM/embeddings wrappers)
- **datasets**: >=2.14.0 (RAGAS Dataset format)

## Acceptance Criteria (Authoritative)

**Story 5.1: Setup Testing Infrastructure with TDD Structure**

1. **Given** the project, **When** I run `pytest`, **Then** all tests are discovered and executed
2. **Given** `tests/` directory, **When** I inspect it, **Then** I see rigorous organization: `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`
3. **Given** `tests/fixtures/`, **When** I check it, **Then** I see golden dataset for RAGAS evaluation (20+ query-answer pairs)
4. **Given** pytest config, **When** I check it, **Then** I see async support, coverage tracking with threshold > 70%, and markers configured
5. **Given** CI/CD pipeline, **When** it runs, **Then** coverage report is generated automatically and build fails if coverage < 70%
6. **Given** test workflow, **When** I follow TDD, **Then** I write test first (Red), implement code (Green), then refactor (Refactor)

**Story 5.2: Implement Unit Tests with TDD**

7. **Given** `core/rag_service.py`, **When** I run unit tests, **Then** all functions are tested with mocked LLM
   - **Nota:** Se contiene PydanticAI Agent, usare TestModel con `agent.override(model=TestModel())`. Per altre funzioni, usare mock appropriati.
8. **Given** `ingestion/embedder.py`, **When** I run tests, **Then** embedding logic is validated with mocked OpenAI client
   - **Nota:** TestModel è solo per PydanticAI Agent, non per EmbeddingGenerator. Per EmbeddingGenerator usare `pytest-mock` `mocker` fixture per mockare `LangfuseAsyncOpenAI` client.
9. **Given** coverage report, **When** I check it, **Then** core modules have > 70% coverage

**Story 5.3: Implement RAGAS Evaluation Suite**

10. **Given** golden dataset (20+ query-answer pairs), **When** I run RAGAS eval, **Then** I see faithfulness, relevancy, precision, recall scores
11. **Given** RAGAS results, **When** I check thresholds, **Then** faithfulness > 0.85 and relevancy > 0.80
12. **Given** LangFuse, **When** I view eval results, **Then** I see RAGAS metrics tracked over time

**Story 5.4: Implement pytest-playwright E2E Tests**

13. **Given** Streamlit app running, **When** pytest-playwright test runs, **Then** it simulates user query and validates response
14. **Given** E2E test, **When** it completes, **Then** I see screenshot/video recording for debugging
15. **Given** CI/CD, **When** tests run, **Then** E2E tests execute in headless mode

## Traceability Mapping

| AC   | Spec Section(s)                                       | Component(s)/API(s)                                                  | Test Idea                                                                    |
| ---- | ----------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| AC1  | Services and Modules, Workflows and Sequencing        | `pytest`, `tests/conftest.py`                                        | Run `pytest` command, verify all tests discovered                            |
| AC2  | Services and Modules                                  | `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/` | Inspect directory structure, verify organization                             |
| AC3  | Data Models and Contracts                             | `tests/fixtures/golden_dataset.json`                                 | Load JSON file, verify 20+ query-answer pairs                                |
| AC4  | Dependencies and Integrations                         | `pyproject.toml`, `[tool.pytest.ini_options]`                        | Check pytest config, verify async_mode, coverage threshold                   |
| AC5  | Workflows and Sequencing, Non-Functional Requirements | `.github/workflows/ci.yml`                                           | Run CI/CD pipeline, verify coverage report generation, fail if <70%          |
| AC6  | Workflows and Sequencing                              | TDD workflow documentation                                           | Document Red-Green-Refactor pattern in test workflow                         |
| AC7  | Services and Modules, APIs and Interfaces             | `tests/unit/test_rag_service.py`, `PydanticAI TestModel`             | Write unit tests for `core/rag_service.py` with TestModel                    |
| AC8  | Services and Modules, APIs and Interfaces             | `tests/unit/test_embedder.py`, `PydanticAI TestModel`                | Write unit tests for `ingestion/embedder.py` with TestModel                  |
| AC9  | Non-Functional Requirements                           | Coverage report                                                      | Run `pytest --cov=core --cov-report=html`, verify >70% coverage              |
| AC10 | Services and Modules, APIs and Interfaces             | `tests/fixtures/golden_dataset.json`, `ragas`                        | Run RAGAS evaluation, verify all metrics calculated                          |
| AC11 | Non-Functional Requirements                           | RAGAS evaluation results                                             | Verify faithfulness >0.85, relevancy >0.80 in test assertions                |
| AC12 | Services and Modules, Observability                   | LangFuse SDK integration                                             | Track RAGAS results in LangFuse, verify in dashboard                         |
| AC13 | Services and Modules, APIs and Interfaces             | `tests/e2e/test_streamlit_workflow.py`, `pytest-playwright`          | Write E2E test for Streamlit query workflow                                  |
| AC14 | Services and Modules                                  | pytest-playwright screenshot/video                                   | Configure pytest-playwright to capture screenshots/videos on test completion |
| AC15 | Workflows and Sequencing                              | CI/CD pipeline, pytest-playwright headless mode                      | Configure pytest-playwright to run in headless mode in CI/CD                 |

## Risks, Assumptions, Open Questions

**Risks:**

1. **Risk: Test Database Setup Complexity** (Probability: Medium, Impact: Medium)

   - **Description**: Setup/teardown test database può essere complesso con PostgreSQL
   - **Mitigation**: Usare fixtures pytest con async context managers, test database isolato
   - **Owner**: Dev team

2. **Risk: RAGAS Evaluation Cost** (Probability: Low, Impact: Low)

   - **Description**: RAGAS evaluation richiede LLM calls reali (costo API)
   - **Mitigation**: Eseguire RAGAS evaluation solo su golden dataset (20+ pairs), non su ogni test run
   - **Owner**: QA team

3. **Risk: E2E Test Flakiness** (Probability: Medium, Impact: Medium)

   - **Description**: E2E tests possono essere flaky per timing issues, network delays
   - **Mitigation**: Implementare retry logic, aumentare timeouts, usare `wait_for` invece di `sleep`
   - **Owner**: QA team

4. **Risk: Coverage Threshold Too High** (Probability: Low, Impact: Low)
   - **Description**: Coverage threshold >70% può essere difficile da raggiungere inizialmente
   - **Mitigation**: Iniziare con threshold più basso (es. 60%), aumentare gradualmente
   - **Owner**: Dev team

**Assumptions:**

1. **Assumption: PydanticAI TestModel Support**

   - **Description**: Assumiamo che PydanticAI TestModel supporti tutti i casi d'uso necessari per unit tests
   - **Validation**: Verificare documentazione PydanticAI, testare con casi d'uso reali
   - **Owner**: Dev team

2. **Assumption: RAGAS Metrics Accuracy**

   - **Description**: Assumiamo che RAGAS metrics (faithfulness, relevancy) siano accurate per validare RAG quality
   - **Validation**: Validare RAGAS results con manual review, confrontare con human evaluation
   - **Owner**: QA team

3. **Assumption: pytest-playwright Browser Compatibility**
   - **Description**: Assumiamo che pytest-playwright Chromium sia sufficiente per E2E testing (non multi-browser)
   - **Validation**: Verificare che Streamlit funzioni correttamente su Chromium
   - **Owner**: QA team

**Open Questions:**

1. **Question: Test Database Strategy**

   - **Description**: Usare test database separato o mocked DB per integration tests?
   - **Answer**: Usare test database separato per integration tests (più realistico), mocked DB per unit tests (più veloce)
   - **Owner**: Dev team

2. **Question: RAGAS Evaluation Frequency**

   - **Description**: Eseguire RAGAS evaluation su ogni PR o solo su release?
   - **Answer**: Eseguire su ogni PR per catch regressions early, ma con timeout per evitare costi eccessivi
   - **Owner**: QA team

3. **Question: Coverage Report Publishing**
   - **Description**: Pubblicare coverage report come GitHub Pages o solo come artifact?
   - **Answer**: Pubblicare come artifact per ora, considerare GitHub Pages in futuro se necessario
   - **Owner**: DevOps team

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests** (`tests/unit/`):

   - **Scope**: Isolated functions/modules con mocked dependencies
   - **Target**: `core/rag_service.py`, `ingestion/embedder.py`, `ingestion/chunker.py`
   - **Framework**: pytest con PydanticAI TestModel per LLM mocking
   - **Coverage Target**: >70% per core modules
   - **Execution Time**: <1s per test

2. **Integration Tests** (`tests/integration/`):

   - **Scope**: Component integration con mocked DB/API ma real logic
   - **Target**: MCP server endpoints, API endpoints
   - **Framework**: pytest con FastAPI TestClient, mocked DB
   - **Coverage Target**: >60% per integration paths
   - **Execution Time**: <5s per test

3. **E2E Tests** (`tests/e2e/`):

   - **Scope**: Complete user workflows con real services
   - **Target**: Streamlit query workflow, MCP server workflow
   - **Framework**: pytest-playwright con headless browser
   - **Coverage Target**: Critical user journeys (non percentage-based)
   - **Execution Time**: <30s per test

4. **RAGAS Evaluation** (`tests/fixtures/golden_dataset.json`):
   - **Scope**: RAG quality validation con golden dataset
   - **Target**: RAG responses per 20+ query-answer pairs
   - **Framework**: RAGAS con LangFuse integration
   - **Thresholds**: Faithfulness >0.85, relevancy >0.80
   - **Execution Time**: <10 minuti per full evaluation

**Test Execution Strategy:**

- **Local Development**: Run unit tests frequentemente, integration/E2E tests prima di commit
- **CI/CD**: Run tutti i test su ogni PR/push, coverage enforcement, RAGAS evaluation su PR
- **Pre-Release**: Run full test suite incluso RAGAS evaluation, verify coverage >70%

**Coverage Strategy:**

- **Enforcement**: CI/CD fail build se coverage <70%
- **Reporting**: HTML report con line-by-line coverage, missing lines evidenziate
- **Trends**: Track coverage percentage nel tempo via CI/CD reports

**RAGAS Evaluation Strategy:**

- **Golden Dataset**: 20+ query-answer pairs in `tests/fixtures/golden_dataset.json`
- **Thresholds**: Faithfulness >0.85, relevancy >0.80 (fail test se non raggiunti)
- **Tracking**: Results tracked in LangFuse per trend analysis
- **Frequency**: Run su ogni PR per catch regressions early

**E2E Testing Strategy:**

- **Browser**: pytest-playwright Chromium (headless mode in CI/CD, configurable via `--headed`)
- **Fixtures**: pytest-playwright fornisce automaticamente `page`, `context`, `browser` fixtures
- **Configuration**: `conftest.py` configura `browser_context_args` per viewport e altre impostazioni
- **Base URL**: Usa `--base-url` CLI option per evitare hardcoded URLs nei test
- **Screenshots**: Capture screenshots on test failure per debugging (automatico con `--screenshot=on`)
- **Video**: Optional video recording per debugging (`--video=on`)
- **Tracing**: Optional tracing per debugging (`--tracing=on`)
- **Selectors**: Use `data-testid` attributes per reliable element selection
- **CLI Options**: `--headed`, `--browser`, `--tracing`, `--video`, `--screenshot` disponibili

# Testing Strategy - docling-rag-agent

**Version:** 1.0  
**Last Updated:** 2025-01-27  
**Python Version:** >=3.10

## Overview

Questo documento definisce la strategia di testing per il progetto `docling-rag-agent`. La strategia segue principi **Test-Driven Development (TDD)** con organizzazione rigorosa dei test, coverage minimo del 70%, e integrazione completa con CI/CD.

**Principi Fondamentali:**
- **TDD First**: Scrivere test prima del codice (Red-Green-Refactor)
- **Coverage Enforcement**: Coverage minimo 70% per moduli core, 80% per moduli critici
- **Test Organization**: Organizzazione rigorosa in unit/integration/e2e
- **Quality Metrics**: RAGAS evaluation per validare qualità RAG
- **Observability**: Test integrati con LangFuse per tracking metriche

---

## 1. Test-Driven Development (TDD)

### 1.1 TDD Workflow

**Pattern Red-Green-Refactor:**

1. **Red**: Scrivere test che fallisce (definisce comportamento desiderato)
2. **Green**: Scrivere codice minimo per far passare il test
3. **Refactor**: Migliorare codice mantenendo test verde

**Esempio:**
```python
# Step 1: Red - Test che fallisce
def test_search_knowledge_base_returns_formatted_results():
    """Test that search returns formatted results."""
    result = search_knowledge_base("test query", limit=5)
    assert "test query" in result
    assert len(result.split("\n")) > 0

# Step 2: Green - Implementazione minima
def search_knowledge_base(query: str, limit: int = 5) -> str:
    """Search knowledge base."""
    return f"Results for: {query}"

# Step 3: Refactor - Migliorare implementazione
def search_knowledge_base(query: str, limit: int = 5) -> str:
    """Search knowledge base with proper formatting."""
    results = await search_knowledge_base_structured(query, limit)
    return format_results(results)
```

### 1.2 TDD Benefits

**Per questo progetto:**
- **Regression Prevention**: Test catturano regressioni prima del deploy
- **Design Guidance**: Test guidano design API pulite e testabili
- **Documentation**: Test servono come documentazione eseguibile
- **Confidence**: Refactoring sicuro con suite test completa

---

## 2. Test Organization

### 2.1 Directory Structure

**Struttura rigorosa:**
```
tests/
├── conftest.py              # Shared fixtures and configuration
├── README.md                # Test documentation
├── unit/                    # Unit tests (>70% coverage)
│   ├── test_rag_service.py
│   ├── test_embedder.py
│   ├── test_langfuse_integration.py
│   ├── test_performance_metrics.py
│   └── test_mcp_server_validation.py
├── integration/             # Integration tests
│   ├── test_mcp_server_integration.py
│   └── test_observability_endpoints.py
├── e2e/                    # End-to-end tests (Playwright)
│   └── test_streamlit_workflow.py
└── fixtures/               # Test fixtures + golden dataset
    └── golden_dataset.json  # 20+ query-answer pairs (RAGAS)
```

### 2.2 Test File Naming

**Convenzioni:**
- File: `test_*.py` o `*_test.py`
- Classe test: `Test<ComponentName>` (es. `TestPrometheusMetrics`)
- Funzione test: `test_<functionality>_<condition>_<expected_result>`

**Esempio:**
```python
# tests/unit/test_rag_service.py
class TestRAGService:
    """Test RAG service functionality."""
    
    def test_search_knowledge_base_with_valid_query_returns_results(self):
        """Test search returns results for valid query."""
        pass
    
    def test_search_knowledge_base_with_empty_query_raises_error(self):
        """Test search raises error for empty query."""
        pass
```

### 2.3 Test Categories

**Unit Tests:**
- Testano singole funzioni/moduli in isolamento
- Mock di dipendenze esterne (DB, API, LangFuse)
- Coverage target: >70% per moduli core

**Integration Tests:**
- Testano interazione tra componenti
- Usano test database o mock services
- Coverage target: >25% delle interazioni critiche

**E2E Tests:**
- Testano workflow completi end-to-end
- Usano servizi reali (test environment)
- Coverage target: >15% dei workflow critici

---

## 3. Unit Testing

### 3.1 Unit Test Structure

**Pattern AAA (Arrange-Act-Assert):**

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_search_knowledge_base_returns_formatted_results():
    # Arrange: Setup test data and mocks
    query = "test query"
    limit = 5
    mock_results = [
        {"content": "result 1", "source": "doc1"},
        {"content": "result 2", "source": "doc2"}
    ]
    
    with patch('core.rag_service.search_knowledge_base_structured') as mock_search:
        mock_search.return_value = mock_results
        
        # Act: Execute function under test
        result = await query_knowledge_base(query, limit)
        
        # Assert: Verify results
        assert "result 1" in result
        assert "doc1" in result
        mock_search.assert_called_once_with(query, limit)
```

### 3.2 Mocking Patterns

**LangFuse Mocking:**
```python
from unittest.mock import patch, MagicMock

def test_langfuse_span_creates_span_when_available():
    """Test LangFuse span creation when client available."""
    with patch('docling_mcp.server.get_langfuse_client') as mock_get_client:
        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.span.return_value = mock_span
        mock_get_client.return_value = mock_client
        
        # Test span creation
        async with langfuse_span("test-span") as span_ctx:
            assert span_ctx["span"] == mock_span
```

**Database Mocking:**
```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_search_db_with_mock_connection():
    """Test database search with mocked connection."""
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {"id": 1, "content": "test", "similarity": 0.95}
    ]
    
    with patch('utils.db_utils.db_pool.acquire') as mock_acquire:
        mock_acquire.return_value.__aenter__.return_value = mock_conn
        
        results = await search_vector_db(embedding, limit=5)
        assert len(results) == 1
        assert results[0]["content"] == "test"
```

**OpenAI/LLM Mocking:**
```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_embedding_generation_with_mock_openai():
    """Test embedding generation with mocked OpenAI client."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    
    with patch('ingestion.embedder.LangfuseAsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        embedder = EmbeddingGenerator()
        embedding = await embedder.embed_query("test query")
        assert len(embedding) == 3
```

### 3.3 Async Testing

**pytest-asyncio:**
- Usare `@pytest.mark.asyncio` per test async
- Configurare `asyncio_mode = "auto"` in `pyproject.toml`

**Esempio:**
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None

# Event loop fixture in conftest.py
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

### 3.4 Coverage Requirements

**Per Modulo:**
- **Core modules** (`core/`, `ingestion/`): >70% coverage
- **Critical modules** (`docling_mcp/`): >80% coverage
- **Utility modules** (`utils/`): >60% coverage

**Verifica Coverage:**
```bash
# Run tests with coverage
pytest --cov=core --cov=docling_mcp --cov-report=term-missing

# Generate HTML report
pytest --cov=core --cov=docling_mcp --cov-report=html

# Check specific threshold
pytest --cov=core --cov-fail-under=70
```

---

## 4. Integration Testing

### 4.1 Integration Test Patterns

**Test Database Integration:**
```python
import pytest
from utils.db_utils import DatabasePool

@pytest.fixture
async def test_db_pool():
    """Create test database pool."""
    pool = DatabasePool(database_url="postgresql://test:test@localhost/test_db")
    await pool.initialize()
    yield pool
    await pool.close()

@pytest.mark.asyncio
async def test_search_knowledge_base_with_real_db(test_db_pool):
    """Test search with real database connection."""
    # Setup test data
    await insert_test_documents(test_db_pool)
    
    # Execute search
    results = await search_knowledge_base_structured("test query", limit=5)
    
    # Verify results
    assert len(results) > 0
    assert all("content" in r for r in results)
```

**Test HTTP Endpoints:**
```python
from fastapi.testclient import TestClient

@pytest.fixture
def test_client():
    """Create test client for HTTP server."""
    from docling_mcp.http_server import app
    return TestClient(app)

def test_metrics_endpoint_returns_prometheus_format(test_client):
    """Test /metrics endpoint returns Prometheus format."""
    response = test_client.get("/metrics")
    
    assert response.status_code == 200
    assert "openmetrics-text" in response.headers.get("content-type", "")
    assert "# HELP" in response.text or "# TYPE" in response.text
```

**Test MCP Server Integration:**
```python
@pytest.mark.asyncio
async def test_mcp_tool_integration():
    """Test MCP tool with real service integration."""
    # Initialize test resources
    await initialize_test_resources()
    
    try:
        # Execute MCP tool
        result = await query_knowledge_base("test query", limit=5)
        
        # Verify result format
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Verify observability (LangFuse traces, Prometheus metrics)
        assert_trace_created("query_knowledge_base")
        assert_metrics_recorded("mcp_requests_total")
    finally:
        await cleanup_test_resources()
```

### 4.2 Test Fixtures

**Shared Fixtures (`conftest.py`):**
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_httpx_response():
    """Create mock httpx response."""
    def _create_response(status_code=200, json_data=None, text=""):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.json = MagicMock(return_value=json_data or {})
        return response
    return _create_response

@pytest.fixture
def mock_search_response():
    """Mock successful search response."""
    return {
        "results": [
            {
                "title": "Test Document",
                "content": "This is test content",
                "source": "test-source",
                "similarity": 0.95
            }
        ],
        "count": 1
    }
```

---

## 5. End-to-End Testing

### 5.1 Playwright E2E Tests

**Setup:**
```bash
# Install Playwright
pip install playwright pytest-playwright

# Install browsers
playwright install
```

**Test Structure:**
```python
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture(scope="session")
def streamlit_app_url():
    """Get Streamlit app URL for testing."""
    return "http://localhost:8501"

def test_streamlit_query_workflow(page: Page, streamlit_app_url):
    """Test complete Streamlit query workflow."""
    # Navigate to app
    page.goto(streamlit_app_url)
    
    # Wait for app to load
    page.wait_for_selector('[data-testid="query-input"]')
    
    # Enter query
    query_input = page.locator('[data-testid="query-input"]')
    query_input.fill("What is the main topic?")
    
    # Submit query
    submit_button = page.locator('[data-testid="submit-button"]')
    submit_button.click()
    
    # Wait for response
    page.wait_for_selector('[data-testid="response"]', timeout=10000)
    
    # Verify response
    response = page.locator('[data-testid="response"]')
    expect(response).to_contain_text("main topic")
    
    # Verify observability (check sidebar stats)
    sidebar_stats = page.locator('[data-testid="sidebar-stats"]')
    expect(sidebar_stats).to_be_visible()
```

**Screenshots e Video:**
```python
def test_streamlit_workflow_with_recording(page: Page):
    """Test with screenshot and video recording."""
    # Enable video recording
    page.video.path()  # Video saved automatically
    
    # Take screenshot on failure
    try:
        # Test logic
        pass
    except Exception:
        page.screenshot(path="test_failure.png")
        raise
```

### 5.2 E2E Test Data

**Golden Dataset:**
- 20+ query-answer pairs per RAGAS evaluation
- Stored in `tests/fixtures/golden_dataset.json`

**Esempio:**
```json
{
  "queries": [
    {
      "question": "What is the main topic of the document?",
      "ground_truth": "The document discusses RAG architecture patterns.",
      "expected_sources": ["doc1", "doc2"]
    },
    {
      "question": "How does embedding generation work?",
      "ground_truth": "Embedding generation uses OpenAI API to convert text to vectors.",
      "expected_sources": ["doc3"]
    }
  ]
}
```

---

## 6. RAGAS Evaluation

### 6.1 RAGAS Metrics

**Metriche Standard:**
- **Faithfulness** (0-1): Consistenza fattuale della risposta rispetto al contesto
- **Answer Relevancy** (0-1): Rilevanza della risposta alla domanda
- **Context Precision** (0-1): Precisione del retrieval (chunk rilevanti in top)
- **Context Recall** (0-1): Completezza del retrieval (tutti chunk rilevanti recuperati)

**Thresholds:**
- Faithfulness > 0.85
- Answer Relevancy > 0.80
- Context Precision > 0.75
- Context Recall > 0.70

### 6.2 RAGAS Implementation

**Setup:**
```bash
pip install ragas datasets
```

**Evaluation Script:**
```python
from ragas import evaluate
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall
)
from datasets import Dataset

async def run_ragas_evaluation():
    """Run RAGAS evaluation on golden dataset."""
    # Load golden dataset
    golden_dataset = load_golden_dataset("tests/fixtures/golden_dataset.json")
    
    # Generate answers using RAG pipeline
    evaluation_data = []
    for item in golden_dataset:
        answer, contexts = await generate_rag_response(item["question"])
        evaluation_data.append({
            "question": item["question"],
            "answer": answer,
            "contexts": contexts,
            "ground_truths": [item["ground_truth"]]
        })
    
    # Create dataset
    eval_dataset = Dataset.from_list(evaluation_data)
    
    # Run evaluation
    metrics = [
        Faithfulness(),
        AnswerRelevancy(),
        ContextPrecision(),
        ContextRecall()
    ]
    
    results = evaluate(
        dataset=eval_dataset,
        metrics=metrics,
        llm=evaluator_llm  # Separate LLM for evaluation
    )
    
    # Verify thresholds
    assert results["faithfulness"] > 0.85
    assert results["answer_relevancy"] > 0.80
    assert results["context_precision"] > 0.75
    assert results["context_recall"] > 0.70
    
    return results
```

### 6.3 LangFuse Integration

**Track RAGAS Metrics:**
```python
from langfuse import Langfuse

langfuse = Langfuse()

async def track_ragas_evaluation(results: dict):
    """Track RAGAS evaluation results in LangFuse."""
    trace = langfuse.trace(
        name="ragas_evaluation",
        metadata={
            "faithfulness": results["faithfulness"],
            "answer_relevancy": results["answer_relevancy"],
            "context_precision": results["context_precision"],
            "context_recall": results["context_recall"]
        }
    )
    
    # Track individual query scores
    for i, query_result in enumerate(results["individual_scores"]):
        trace.span(
            name=f"query_{i}",
            metadata=query_result
        )
    
    trace.end()
```

---

## 7. Test Configuration

### 7.1 pytest Configuration

**`pyproject.toml`:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests",
    "ragas: RAGAS evaluation tests"
]
```

### 7.2 Coverage Configuration

**Coverage Thresholds:**
```toml
[tool.coverage.run]
source = ["core", "docling_mcp", "ingestion", "utils"]
omit = ["*/tests/*", "*/test_*.py"]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
fail_under = 70

[tool.coverage.html]
directory = "htmlcov"
```

### 7.3 Test Markers

**Uso dei Markers:**
```python
import pytest

@pytest.mark.unit
def test_unit_functionality():
    """Unit test."""
    pass

@pytest.mark.integration
def test_integration_functionality():
    """Integration test."""
    pass

@pytest.mark.e2e
@pytest.mark.slow
def test_e2e_workflow():
    """E2E test (slow)."""
    pass

@pytest.mark.ragas
def test_ragas_evaluation():
    """RAGAS evaluation test."""
    pass
```

**Eseguire test per categoria:**
```bash
# Solo unit tests
pytest -m unit

# Solo integration tests
pytest -m integration

# Escludere test lenti
pytest -m "not slow"

# Solo RAGAS evaluation
pytest -m ragas
```

---

## 8. CI/CD Integration

### 8.1 GitHub Actions Workflow

**Test Pipeline:**
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"
      
      - name: Run unit tests
        run: |
          pytest tests/unit/ -v --cov=core --cov=docling_mcp --cov-report=xml
      
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v
      
      - name: Check coverage
        run: |
          pytest --cov=core --cov=docling_mcp --cov-fail-under=70
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### 8.2 Pre-commit Hooks

**Test Before Commit:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: pytest tests/unit/ -v
        language: system
        pass_filenames: false
        always_run: true
```

---

## 9. Test Best Practices

### 9.1 Test Isolation

**Principi:**
- Ogni test deve essere indipendente
- Non dipendere da ordine di esecuzione
- Cleanup dopo ogni test

**Esempio:**
```python
@pytest.fixture(autouse=True)
def cleanup_test_state():
    """Cleanup test state before and after each test."""
    # Setup
    yield
    # Cleanup
    reset_global_state()
    clear_test_cache()
```

### 9.2 Test Data Management

**Pattern:**
- Usare fixtures per test data riutilizzabili
- Golden dataset per RAGAS evaluation
- Test database separato per integration tests

**Esempio:**
```python
@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        {
            "id": "doc1",
            "title": "Test Document 1",
            "content": "This is test content for document 1.",
            "source": "test-source"
        },
        {
            "id": "doc2",
            "title": "Test Document 2",
            "content": "This is test content for document 2.",
            "source": "test-source"
        }
    ]
```

### 9.3 Error Testing

**Test Error Cases:**
```python
def test_search_with_invalid_query_raises_error():
    """Test search raises error for invalid query."""
    with pytest.raises(ValueError, match="Query cannot be empty"):
        search_knowledge_base("")

def test_database_connection_error_handled_gracefully():
    """Test graceful handling of database errors."""
    with patch('utils.db_utils.db_pool.acquire', side_effect=ConnectionError):
        # Should not crash, should return error message
        result = await query_knowledge_base("test")
        assert "error" in result.lower()
```

### 9.4 Performance Testing

**Test Performance Critical Paths:**
```python
import time

def test_embedding_generation_performance():
    """Test embedding generation meets performance SLO."""
    start_time = time.time()
    embedding = await generate_embedding("test query")
    duration = time.time() - start_time
    
    # SLO: <500ms for embedding generation
    assert duration < 0.5, f"Embedding took {duration}s, exceeds 500ms SLO"
    assert len(embedding) > 0
```

---

## 10. Test Maintenance

### 10.1 Test Documentation

**Documentare Test:**
- Docstring descrittivi per ogni test
- Spiegare cosa testa e perché
- Documentare setup requirements

**Esempio:**
```python
def test_langfuse_graceful_degradation():
    """
    Test LangFuse graceful degradation when unavailable.
    
    This test verifies that the system continues to function
    normally when LangFuse SDK is not installed or unavailable.
    This is critical for production reliability.
    """
    pass
```

### 10.2 Test Refactoring

**Quando Refactorare:**
- Test duplicati → Estrai fixture comune
- Test troppo lunghi → Suddividi in test più piccoli
- Test instabili → Isola dipendenze esterne

**Esempio:**
```python
# ❌ Errato - Test troppo lungo
def test_complete_workflow():
    # Setup (20 lines)
    # Test step 1 (10 lines)
    # Test step 2 (10 lines)
    # Test step 3 (10 lines)
    # Assertions (10 lines)
    pass

# ✅ Corretto - Test focalizzati
def test_workflow_step1():
    """Test workflow step 1."""
    pass

def test_workflow_step2():
    """Test workflow step 2."""
    pass

def test_workflow_integration():
    """Test complete workflow integration."""
    pass
```

---

## 11. Testing Checklist

Prima di considerare una feature completa:

- [ ] Unit tests scritti per tutte le funzioni pubbliche
- [ ] Integration tests per interazioni critiche
- [ ] E2E tests per workflow principali (se applicabile)
- [ ] Coverage >70% per moduli core
- [ ] Test error cases (invalid input, failures)
- [ ] Test performance critical paths (se applicabile)
- [ ] RAGAS evaluation per funzionalità RAG (se applicabile)
- [ ] Test documentati con docstring descrittivi
- [ ] Test isolati e indipendenti
- [ ] CI/CD pipeline passa tutti i test

---

## 12. References

### Internal Documentation

- **[Coding Standards](./coding-standards.md)**: Code style guide and testing standards section
- **[Unified Project Structure](./unified-project-structure.md)**: Test organization standards and directory structure
- **[Architecture](./architecture.md)**: System architecture and testing infrastructure decisions
- **[Epic 5 Requirements](./epics.md#Epic-5-Testing-&-Quality-Assurance)**: Complete Epic 5 requirements with acceptance criteria
- **[Development Guide](./development-guide.md)**: Setup instructions and test execution workflow

### External References

- **pytest Documentation**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **RAGAS Documentation**: https://docs.ragas.io/
- **Playwright Documentation**: https://playwright.dev/python/
- **PydanticAI Testing**: https://ai.pydantic.dev/testing/
- **Coverage.py**: https://coverage.readthedocs.io/

---

## Changelog

- **2025-01-27**: Initial version based on existing test structure and Epic 5 requirements


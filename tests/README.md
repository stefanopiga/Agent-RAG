# Test Suite for docling-rag-agent

## Overview

This test suite implements Test-Driven Development (TDD) with rigorous structure and comprehensive fixtures for testing the RAG system.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and pytest configuration
├── README.md                # This documentation
├── unit/                    # Unit tests (isolated, fast, <1s per test)
│   ├── __init__.py
│   ├── test_api_client.py
│   ├── test_embedder.py
│   ├── test_rag_service.py
│   └── ...
├── integration/             # Integration tests (mocked DB/API, <5s per test)
│   ├── __init__.py
│   ├── test_mcp_server_integration.py
│   ├── test_api_endpoints.py
│   └── ...
├── e2e/                     # End-to-end tests (real services, <30s per test)
│   ├── __init__.py
│   └── test_streamlit_workflow.py
└── fixtures/                # Test data and fixtures
    ├── __init__.py
    └── golden_dataset.json  # RAGAS evaluation dataset (25 query-answer pairs)
```

## TDD Workflow (Red-Green-Refactor)

### Pattern Overview

TDD follows a strict cycle for each feature:

1. **Red Phase**: Write a failing test first
2. **Green Phase**: Write minimal code to pass the test
3. **Refactor Phase**: Improve code while keeping tests green

### Example: Adding a New Feature

```python
# Step 1: RED - Write failing test first
# tests/unit/test_search_filter.py

import pytest
from core.rag_service import search_knowledge_base

@pytest.mark.unit
async def test_search_with_source_filter_returns_filtered_results():
    """Test that source_filter limits results to matching documents."""
    # Arrange
    query = "What is RAG?"
    source_filter = "langfuse-docs"

    # Act
    result = await search_knowledge_base(query, limit=5, source_filter=source_filter)

    # Assert
    assert "langfuse" in result.lower()  # This will FAIL initially


# Step 2: GREEN - Implement minimal code
# core/rag_service.py (add source_filter parameter and logic)

# Step 3: REFACTOR - Clean up while keeping test green
# - Extract filter logic to helper function
# - Improve SQL query builder
# - Run test to verify still passes
```

### Best Practices

1. **Write Test First**: Never write implementation before the test
2. **Minimal Implementation**: Only write enough code to pass the test
3. **One Test at a Time**: Complete Red-Green-Refactor before next test
4. **Run All Tests**: Ensure no regressions after each change
5. **Descriptive Names**: Use `test_<functionality>_<condition>_<expected_result>`

## Running Tests

### Run All Tests

```bash
pytest
```

### Run by Marker

```bash
# Unit tests only (fast, isolated)
pytest -m unit

# Integration tests only (mocked DB/API)
pytest -m integration

# E2E tests only (real services, slow)
pytest -m e2e

# RAGAS evaluation tests
pytest -m ragas

# Slow tests (>5s)
pytest -m slow
```

### Run with Coverage

```bash
# With HTML report
pytest --cov=core --cov=ingestion --cov=docling_mcp --cov=utils --cov-report=html

# With terminal report
pytest --cov=core --cov-report=term-missing

# With coverage threshold enforcement (CI/CD)
pytest --cov=core --cov=ingestion --cov=docling_mcp --cov=utils \
       --cov-report=xml --cov-report=term-missing --cov-fail-under=70
```

### Run Specific Tests

```bash
# Single file
pytest tests/unit/test_api_client.py

# Single test function
pytest tests/unit/test_api_client.py::test_client_handles_timeout

# By keyword
pytest -k "search"

# With verbose output
pytest -v

# Show print statements
pytest -s
```

## Pytest Markers

| Marker        | Description                             | Execution Time |
| ------------- | --------------------------------------- | -------------- |
| `unit`        | Isolated tests with mocked dependencies | <1s per test   |
| `integration` | Tests with real logic, mocked DB/API    | <5s per test   |
| `e2e`         | Full system tests with real services    | <30s per test  |
| `slow`        | Tests with >5s execution time           | Variable       |
| `ragas`       | RAGAS evaluation tests (LLM calls)      | <10min total   |

### Example Usage

```python
import pytest

@pytest.mark.unit
async def test_embedding_generation():
    """Fast isolated test."""
    pass

@pytest.mark.integration
async def test_mcp_tool_execution():
    """Test with real logic but mocked DB."""
    pass

@pytest.mark.e2e
@pytest.mark.slow
def test_streamlit_workflow():
    """Full E2E test with real services."""
    pass

@pytest.mark.ragas
async def test_rag_quality_evaluation():
    """RAGAS evaluation with golden dataset."""
    pass
```

## Coverage Reporting

### Coverage Modules

Coverage is tracked for core business logic:

- `core/` - RAG service, agent logic
- `ingestion/` - Document processing, chunking, embedding
- `docling_mcp/` - MCP server tools and endpoints
- `utils/` - Database utilities, session management

### Coverage Threshold

- **Required**: >70% for CI/CD to pass
- **Reports**: HTML (`htmlcov/`), XML (`coverage.xml`), terminal

### Viewing Coverage

```bash
# Generate HTML report
pytest --cov=core --cov=ingestion --cov-report=html

# Open report (Windows)
start htmlcov/index.html

# Open report (Mac/Linux)
open htmlcov/index.html
```

## Fixtures Reference

### Database Fixtures

```python
@pytest.fixture
def mock_db_pool():
    """Mock database pool for unit tests."""
    # Access mock connection: mock_db_pool._mock_connection
    pass

@pytest.fixture
async def test_db(mock_db_pool):
    """Test database with setup/teardown for integration tests."""
    pass
```

### Embedder Fixtures

```python
@pytest.fixture
def mock_embedder():
    """Mock embedder returning deterministic 1536-dim embeddings."""
    # Usage: await mock_embedder.embed_query("text")
    pass
```

### LLM Fixtures (PydanticAI)

```python
@pytest.fixture
def test_model():
    """PydanticAI TestModel for LLM mocking."""
    # Usage: agent.override(model=test_model)
    pass

@pytest.fixture
def disable_model_requests():
    """Disable real LLM API calls globally for safety."""
    pass
```

### LangFuse Fixtures

```python
@pytest.fixture
def mock_langfuse():
    """Mock LangFuse client for observability testing."""
    pass

@pytest.fixture
def mock_langfuse_disabled():
    """Simulate LangFuse unavailable for graceful degradation tests."""
    pass
```

### Golden Dataset Fixtures

```python
@pytest.fixture
def golden_dataset_path():
    """Path to golden dataset JSON file."""
    pass

@pytest.fixture
def golden_dataset(golden_dataset_path):
    """Loaded golden dataset with 25 query-answer pairs."""
    # Returns: {"queries": [...], "thresholds": {...}}
    pass
```

## Golden Dataset Format

The golden dataset (`tests/fixtures/golden_dataset.json`) contains 25 query-answer pairs for RAGAS evaluation:

```json
{
  "version": "1.0",
  "thresholds": {
    "faithfulness": 0.85,
    "answer_relevancy": 0.8
  },
  "queries": [
    {
      "id": "q001",
      "query": "What is the main purpose of the system?",
      "expected_answer": "The system provides RAG capabilities...",
      "context": ["Context document 1...", "Context document 2..."],
      "ground_truth": "Short reference answer",
      "metadata": {
        "category": "system_overview",
        "source": "docs/prd.md",
        "expected_faithfulness": 0.9,
        "expected_relevancy": 0.88
      }
    }
  ]
}
```

### Query Categories

- `system_overview` - General system understanding
- `technical_details` - Implementation specifics
- `infrastructure` - Database, Docker, deployment
- `testing` - TDD, coverage, RAGAS
- `features` - User-facing capabilities
- `performance` - Optimization, caching
- `observability` - LangFuse, monitoring
- `api` - MCP server, endpoints

## Test Patterns

### AAA Pattern (Arrange-Act-Assert)

```python
@pytest.mark.unit
async def test_search_returns_relevant_results():
    """Test that search returns relevant results for valid query."""
    # Arrange - Set up test data and dependencies
    query = "What is RAG?"
    mock_results = [{"content": "RAG is...", "similarity": 0.95}]

    # Act - Execute the code being tested
    result = await search_function(query)

    # Assert - Verify expected outcomes
    assert "RAG" in result
    assert len(result) > 0
```

### Async Testing

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    """Async tests use pytest-asyncio with auto mode."""
    result = await async_function()
    assert result is not None
```

### Mocking with pytest-mock

```python
@pytest.mark.unit
async def test_with_mocked_dependency(mocker):
    """Use pytest-mock for patching."""
    # Patch the dependency
    mock_embedder = mocker.patch('core.rag_service.get_global_embedder')
    mock_embedder.return_value.embed_query.return_value = [0.1] * 1536

    # Test code using the mock
    result = await search_function("query")

    # Verify mock was called
    mock_embedder.return_value.embed_query.assert_called_once()
```

### Using Fixtures

```python
@pytest.mark.unit
async def test_with_fixtures(mock_db_pool, mock_embedder):
    """Combine multiple fixtures for comprehensive mocking."""
    # Configure mock responses
    mock_db_pool._mock_connection.fetch.return_value = [
        {"content": "Test", "similarity": 0.9}
    ]

    # Test with mocked dependencies
    # ...
```

## CI/CD Integration

Tests run automatically in GitHub Actions on PR/push to main/develop:

1. **Lint** (Ruff): Code style and format checking
2. **Type Check** (Mypy): Static type analysis
3. **Test** (Pytest): Unit tests with coverage enforcement
4. **Build** (Docker): Image builds with size validation
5. **Secret Scan** (TruffleHog): Security scanning

### Coverage Enforcement

The CI/CD pipeline fails if coverage drops below 70%:

```yaml
# .github/workflows/ci.yml
- name: Run tests with coverage
  run: |
    pytest \
      --cov=core --cov=ingestion --cov=docling_mcp --cov=utils \
      --cov-report=xml --cov-report=term-missing \
      --cov-fail-under=70 \
      tests/unit/
```

## Troubleshooting

### Common Issues

1. **Test Discovery Fails**

   ```bash
   # Verify test file naming
   pytest --collect-only
   ```

2. **Async Tests Hang**

   ```bash
   # Check event_loop fixture scope
   pytest -v --tb=short
   ```

3. **Coverage Below Threshold**

   ```bash
   # Identify missing coverage
   pytest --cov=core --cov-report=term-missing
   ```

4. **Fixture Not Found**
   ```bash
   # Verify conftest.py location and imports
   pytest --fixtures
   ```

### Debug Mode

```bash
# Run with debugging enabled
pytest -v -s --tb=long

# Drop into debugger on failure
pytest --pdb

# Stop on first failure
pytest -x
```

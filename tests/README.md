# Test Suite for docling-rag-agent MCP Server

## Overview

This test suite validates the MCP server fixes and improvements implemented to resolve blocking issues. The suite includes unit tests, integration tests, and end-to-end tests covering error handling, retry logic, validation, observability, and complete user workflows.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures (unit + integration)
├── unit/                    # Unit tests (isolated, fast)
│   ├── test_api_client.py
│   ├── test_mcp_server_validation.py
│   ├── test_langfuse_integration.py
│   ├── test_langfuse_streamlit.py
│   ├── test_performance_metrics.py
│   └── test_session_manager.py
├── integration/            # Integration tests (with mocked dependencies)
│   ├── test_mcp_server_integration.py
│   ├── test_api_health.py
│   ├── test_langfuse_dashboard.py
│   ├── test_observability_endpoints.py
│   └── test_streamlit_observability.py
├── e2e/                    # End-to-end tests (requires running services)
│   ├── conftest.py         # E2E-specific fixtures
│   ├── test_streamlit_workflow.py
│   ├── test_streamlit_ui_observability.py
│   └── screenshots/        # Screenshot artifacts
└── evaluation/            # Evaluation and benchmarking tests
```

## Prerequisites

### Unit and Integration Tests

- No prerequisites required
- All external dependencies are mocked
- Tests are fast and isolated

### E2E Tests

- **Streamlit app must be running**: `uv run streamlit run app.py`
- **Browser installed**: Chromium via playwright (installed automatically with `uv run playwright install chromium`)
- **Environment variables configured**: See project `.env` file
- **Network access**: For health checks (can be mocked)

## Running Tests

### Run all tests

```bash
uv run pytest
```

### Run specific test category

```bash
# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/

# Run only E2E tests
uv run pytest -m e2e
```

### Run specific test file

```bash
uv run pytest tests/unit/test_api_client.py
```

### Run with markers

```bash
# Run only E2E tests
uv run pytest -m e2e

# Run excluding slow tests
uv run pytest -m "not slow"

# Run E2E tests excluding flaky ones
uv run pytest -m "e2e and not flaky"

# Run only critical path tests
uv run pytest -m "p0"
```

### Run with verbose output

```bash
uv run pytest -v
```

### Run with coverage

```bash
uv run pytest --cov=client --cov=mcp_server --cov-report=html
```

### Run E2E tests with visible browser

```bash
# Run E2E tests with browser visible (non-headless)
uv run pytest -m e2e --headed
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.e2e` - End-to-end tests (require running services)
- `@pytest.mark.slow` - Slow running tests (may take > 5 seconds)
- `@pytest.mark.flaky` - Tests that may be flaky (with automatic reruns)
- `@pytest.mark.p0` - Critical path tests (must pass)
- `@pytest.mark.p1` - Feature tests
- `@pytest.mark.p2` - Edge case tests

## Test Coverage

### Unit Tests (`tests/unit/`)

**test_api_client.py:**

- ✅ Error handling improvements (HTTP errors, timeouts, network errors)
- ✅ Retry logic for transient errors (timeout, network)
- ✅ No retry for HTTP status errors
- ✅ Successful operations

**test_mcp_server_validation.py:**

- ✅ Empty query validation
- ✅ Invalid limit clamping (1-100)
- ✅ Health check pre-flight validation
- ✅ ask_knowledge_base validation
- ✅ Tool error propagation

**test_langfuse_integration.py:**

- ✅ LangFuse client initialization from environment variables
- ✅ Graceful degradation when LangFuse is unavailable
- ✅ @observe decorator application to tools
- ✅ Cost tracking via langfuse.openai wrapper
- ✅ Nested spans for cost breakdown visibility

**test_langfuse_streamlit.py:**

- ✅ LangFuse integration in Streamlit app
- ✅ Trace creation and tracking
- ✅ Error handling in Streamlit context

**test_performance_metrics.py:**

- ✅ Prometheus metrics initialization and recording
- ✅ Health check status logic (ok/degraded/down)
- ✅ Timing measurement in LangFuse spans
- ✅ Graceful degradation without Prometheus

**test_session_manager.py:**

- ✅ Session state management
- ✅ Session isolation
- ✅ Session cleanup

### Integration Tests (`tests/integration/`)

**test_mcp_server_integration.py:**

- ✅ Complete query_knowledge_base flow
- ✅ Error propagation from client to MCP tool
- ✅ ask_knowledge_base as tool (not prompt)
- ✅ list_knowledge_base_documents flow
- ✅ get_knowledge_base_document flow
- ✅ get_knowledge_base_overview flow
- ✅ Error handling chain
- ✅ Tool registration verification

**test_api_health.py:**

- ✅ GET /health endpoint returns JSON with status and timestamp
- ✅ GET /health endpoint verifies database connection
- ✅ GET /health returns 503 when database unavailable
- ✅ Database connection error handling

**test_langfuse_dashboard.py:**

- ✅ LangFuse dashboard integration
- ✅ Trace visualization
- ✅ Cost tracking display

**test_observability_endpoints.py:**

- ✅ GET /metrics endpoint format validation
- ✅ GET /metrics histogram bucket configuration
- ✅ GET /health endpoint with all services available
- ✅ GET /health endpoint with database unavailable
- ✅ GET /health endpoint with LangFuse unavailable

**test_streamlit_observability.py:**

- ✅ Streamlit observability features
- ✅ Metrics display in UI
- ✅ Error handling UI

### E2E Tests (`tests/e2e/`)

**test_streamlit_workflow.py:**

- ✅ Streamlit app load verification
- ✅ Complete query workflow (input → submit → response)
- ✅ Sidebar stats visibility
- ✅ Session isolation tests
- ✅ Network interception (skipped, requires mocked backend)
- ✅ Screenshot capture on success and failure

**test_streamlit_ui_observability.py:**

- ✅ UI observability features
- ✅ Metrics display in Streamlit UI
- ✅ Error handling UI
- ✅ Session stats display

**Prerequisites for E2E tests:**

- Streamlit app must be running (`streamlit run app.py`)
- Browser installed (Chromium via playwright)
- Environment variables configured

**Running E2E tests:**

```bash
# Run all E2E tests
uv run pytest -m e2e

# Run with browser visible (non-headless)
uv run pytest -m e2e --headed

# Run specific E2E test file
uv run pytest tests/e2e/test_streamlit_workflow.py
```

**Screenshots:**
E2E tests automatically capture screenshots on failure and success.
Screenshots are saved to `tests/e2e/screenshots/`.

## Test Categories

### [P0] Critical Path Tests

- Query validation
- Health check validation
- Error handling
- E2E workflow verification

### [P1] Feature Tests

- Retry logic
- ask_knowledge_base functionality
- Error message clarity
- Observability features
- LangFuse integration

### [P2] Edge Case Tests

- Empty results
- Invalid inputs
- Network failures
- Service degradation scenarios

## Fixtures

### Unit and Integration Fixtures (`tests/conftest.py`)

**mock_httpx_response:**

- Creates mock httpx responses for testing
- Configurable status code and JSON data

**mock_search_response:**

- Mock successful search API response
- Includes results, count, and processing time

**mock_list_documents_response:**

- Mock successful list documents API response
- Includes document metadata and chunk counts

### E2E Fixtures (`tests/e2e/conftest.py`)

**streamlit_app_url:**

- Streamlit app URL (default: http://localhost:8501)
- Configurable via `STREAMLIT_E2E_URL` environment variable

**wait_for_streamlit_app:**

- Waits for Streamlit app to be ready before running tests
- Polls health endpoint until app is responsive
- Raises error if app not ready after max attempts

**e2e_timeouts:**

- E2E test timeout configuration
- Includes navigation, element_wait, api_call, short_wait timeouts
- Configurable via environment variables

**reset_streamlit_session:**

- Resets Streamlit session state before each test
- Ensures test isolation
- Clears cookies and storage

**mock_openai_api:**

- Mocks OpenAI API calls for deterministic tests
- Prevents API costs during testing
- Enables testing without real credentials

**mock_langfuse_api:**

- Mocks LangFuse API calls
- Prevents external API calls during testing

**mock_all_external_apis:**

- Combines OpenAI and LangFuse mocking
- Provides complete isolation from external services

**browser_context_args:**

- Configures pytest-playwright browser context
- Sets viewport, locale, timezone, user agent

**screenshot_on_failure:**

- Automatically captures screenshots on test failure
- Saves to `tests/e2e/screenshots/`

## Notes

- All tests use `pytest-asyncio` for async test support
- Unit and integration tests mock external dependencies (httpx, API calls)
- No real database or API connections required for unit/integration tests
- E2E tests require running Streamlit app and browser
- Tests are fast and isolated (except E2E which require services)
- E2E tests use `pytest-playwright` for browser automation
- Screenshots are automatically captured for E2E test failures

## Troubleshooting

### E2E Tests Fail with "Streamlit app not ready"

**Problem:** E2E tests fail immediately with error about Streamlit app not being ready.

**Solution:**

1. Ensure Streamlit app is running: `uv run streamlit run app.py`
2. Check that app is accessible at http://localhost:8501
3. Verify health endpoint: `curl http://localhost:8501/_stcore/health`
4. Check `STREAMLIT_E2E_URL` environment variable if using custom URL

### E2E Tests Timeout

**Problem:** E2E tests timeout waiting for elements or API responses.

**Solution:**

1. Increase timeout values via environment variables:
   ```bash
   export E2E_NAVIGATION_TIMEOUT=60000
   export E2E_ELEMENT_TIMEOUT=20000
   export E2E_API_TIMEOUT=120000
   ```
2. Run tests with `--headed` flag to see what's happening
3. Check screenshots in `tests/e2e/screenshots/` for visual debugging

### Browser Not Found

**Problem:** E2E tests fail with "Browser not found" error.

**Solution:**

```bash
# Install browsers for playwright
uv run playwright install chromium
```

### Test Isolation Issues

**Problem:** E2E tests see data from previous tests.

**Solution:**

- Ensure `reset_streamlit_session` fixture is working (it's autouse=True)
- Check that Streamlit app properly handles session reset
- Verify cookies are being cleared between tests

### Screenshots Not Saved

**Problem:** Screenshots directory doesn't exist or screenshots aren't saved.

**Solution:**

```bash
# Create screenshots directory
mkdir -p tests/e2e/screenshots
```

### Coverage Report Not Generated

**Problem:** Coverage HTML report not created.

**Solution:**

```bash
# Ensure dependencies are installed (coverage included)
uv sync

# Run with coverage
uv run pytest --cov=client --cov=mcp_server --cov-report=html

# Report will be in htmlcov/index.html
```

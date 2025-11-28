# Test Suite for docling-rag-agent MCP Server

## Overview

This test suite validates the MCP server fixes and improvements implemented to resolve blocking issues.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (isolated, fast)
│   ├── test_api_client.py  # RAGClient error handling and retry logic
│   └── test_mcp_server_validation.py  # Validation logic tests
├── integration/            # Integration tests (with mocked dependencies)
│   └── test_mcp_server_integration.py  # End-to-end flow tests
└── fixtures/                # Test data and fixtures
```

## Running Tests

### Run all tests

```bash
pytest
```

### Run specific test file

```bash
pytest tests/unit/test_api_client.py
```

### Run with verbose output

```bash
pytest -v
```

### Run with coverage

```bash
pytest --cov=client --cov=mcp_server --cov-report=html
```

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

### Integration Tests (`tests/integration/`)

**test_mcp_server_integration.py:**

- ✅ Complete query_knowledge_base flow
- ✅ Error propagation from client to MCP tool
- ✅ ask_knowledge_base as tool (not prompt)
- ✅ list_knowledge_base_documents flow
- ✅ Error handling chain

## Test Categories

### [P0] Critical Path Tests

- Query validation
- Health check validation
- Error handling

### [P1] Feature Tests

- Retry logic
- ask_knowledge_base functionality
- Error message clarity

### [P2] Edge Case Tests

- Empty results
- Invalid inputs
- Network failures

## Fixtures

See `tests/conftest.py` for shared fixtures:

- `mock_httpx_response` - Mock HTTP responses
- `mock_search_response` - Mock search API response
- `mock_list_documents_response` - Mock list documents API response

## Notes

- All tests use `pytest-asyncio` for async test support
- Tests mock external dependencies (httpx, API calls)
- No real database or API connections required
- Tests are fast and isolated





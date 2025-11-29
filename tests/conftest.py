"""
Pytest configuration and shared fixtures
"""

import asyncio
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_httpx_response():
    """Create a mock httpx response."""

    def _create_response(status_code=200, json_data=None, text=""):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.json = MagicMock(return_value=json_data or {})
        response.raise_for_status = MagicMock()
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
                "similarity": 0.95,
            }
        ],
        "count": 1,
        "processing_time_ms": 100,
    }


@pytest.fixture
def mock_list_documents_response():
    """Mock successful list documents response."""
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


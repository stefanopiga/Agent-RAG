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
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# DATABASE FIXTURES
# ============================================================================
@pytest.fixture
def mock_db_pool():
    """
    Mock database pool for unit tests.

    Returns a mocked DatabasePool that simulates async database operations
    without requiring a real PostgreSQL connection.

    Usage:
        async def test_search(mock_db_pool):
            mock_db_pool.fetch.return_value = [{"content": "test", "similarity": 0.95}]
            result = await search_function()
            assert "test" in result
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
    Test database fixture with setup/teardown for integration tests.

    Provides an isolated database state for each test with automatic cleanup.

    Usage:
        @pytest.mark.integration
        async def test_document_storage(test_db):
            # test_db is ready with mock data
            result = await list_documents()
            assert len(result) >= 0
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
    Mock embedder for unit tests.

    Returns a mocked EmbeddingGenerator that returns deterministic
    embeddings without calling OpenAI API.

    Usage:
        async def test_embedding(mock_embedder):
            embedding = await mock_embedder.embed_query("test")
            assert len(embedding) == 1536
    """
    mock = AsyncMock()

    # Standard embedding dimension for text-embedding-3-small
    embedding_dim = 1536

    # Generate deterministic mock embedding
    def generate_mock_embedding(text: str) -> List[float]:
        """Generate a deterministic embedding based on text hash."""
        seed = hash(text) % 10000
        return [float(seed + i) / 10000.0 for i in range(embedding_dim)]

    async def mock_embed_query(text: str) -> List[float]:
        return generate_mock_embedding(text)

    async def mock_embed_documents(texts: List[str]) -> List[List[float]]:
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
    PydanticAI TestModel for LLM mocking in unit tests.

    TestModel generates valid structured data automatically based on
    tool schemas without making real API calls.

    Usage:
        async def test_agent_response(test_model):
            agent = Agent('openai:gpt-4o-mini', result_type=str)
            with agent.override(model=test_model):
                result = await agent.run("What is RAG?")
                assert result.data is not None

    Reference: docs/stories/5/tech-spec-epic-5.md#PydanticAI-TestModel-Interface
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
    Disable real LLM API calls globally for safety in tests.

    Usage:
        def test_no_real_api_calls(disable_model_requests):
            # Any attempt to call real API will raise error
            pass
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
    Mock LangFuse client for graceful degradation testing.

    Returns a mocked LangFuse client that simulates tracing operations
    without requiring real LangFuse connection.

    Usage:
        def test_tracing(mock_langfuse):
            with patch('langfuse.get_client', return_value=mock_langfuse):
                # Test code that uses LangFuse
                pass
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
    # Note: LangFuse SDK uses .score() method, not .create_score()
    mock.score = MagicMock(return_value=MagicMock(id="test-score-id"))
    # Keep create_score for backwards compatibility
    mock.create_score = mock.score

    # Mock flush (for ensuring data is sent)
    mock.flush = MagicMock()

    return mock


@pytest.fixture
def mock_langfuse_disabled():
    """
    Fixture to simulate LangFuse being unavailable.

    Tests graceful degradation when LangFuse service is down.

    Usage:
        def test_without_langfuse(mock_langfuse_disabled):
            # Test code should work without LangFuse
            pass
    """
    with patch.dict("os.environ", {"LANGFUSE_ENABLED": "false"}):
        yield


# ============================================================================
# HTTP FIXTURES
# ============================================================================
@pytest.fixture
def mock_httpx_response():
    """Create a mock httpx response factory."""

    def _create_response(status_code=200, json_data=None, text=""):
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
    """Mock successful search response."""
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


# ============================================================================
# GOLDEN DATASET FIXTURES (RAGAS Evaluation)
# ============================================================================
@pytest.fixture
def golden_dataset_path():
    """Path to golden dataset for RAGAS evaluation."""
    import os

    return os.path.join(os.path.dirname(__file__), "fixtures", "golden_dataset.json")


@pytest.fixture
def golden_dataset(golden_dataset_path):
    """
    Load golden dataset for RAGAS evaluation.

    Returns the parsed JSON with 20+ query-answer pairs.

    Usage:
        @pytest.mark.ragas
        async def test_ragas_evaluation(golden_dataset):
            queries = golden_dataset["queries"]
            assert len(queries) >= 20
    """
    import json
    import os

    if not os.path.exists(golden_dataset_path):
        pytest.skip("Golden dataset not found - run Task 5 first")

    with open(golden_dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)

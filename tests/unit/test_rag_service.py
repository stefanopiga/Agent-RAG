"""
Unit tests for core/rag_service.py

Tests all public functions with mocked dependencies:
- Global embedder management (initialize, close, get)
- Query embedding generation
- Knowledge base search

Reference: docs/stories/5/5-2/5-2-implement-unit-tests-with-tdd.md
AC#7: All functions tested with mocked LLM
AC#9: >70% coverage for core modules
"""

import asyncio
import json
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# GLOBAL STATE CLEANUP FIXTURE (autouse=True)
# ============================================================================
@pytest.fixture(autouse=True)
def cleanup_global_embedder():
    """
    Reset module-level embedder state before and after a test to ensure test isolation.
    
    This autouse fixture clears the rag_service embedder globals: sets `_global_embedder` to `None`,
    replaces `_embedder_ready` with a new `asyncio.Event`, and sets `_initialization_task` to `None`
    both before the test runs and again after teardown.
    """
    # Setup: Reset state before test
    import core.rag_service as rag_service
    rag_service._global_embedder = None
    rag_service._embedder_ready = asyncio.Event()
    rag_service._initialization_task = None
    
    yield
    
    # Teardown: Reset state after test
    rag_service._global_embedder = None
    rag_service._embedder_ready = asyncio.Event()
    rag_service._initialization_task = None


# ============================================================================
# TEST: initialize_global_embedder
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_initialize_global_embedder_creates_embedder(mocker):
    """
    Test that initialize_global_embedder() creates embedder using mocked create_embedder.
    
    Arrange: Mock create_embedder to return mock embedder
    Act: Call initialize_global_embedder
    Assert: Embedder is created and ready event is set
    """
    # Arrange
    from core import rag_service
    mock_embedder = MagicMock()
    mock_embedder.generate_embedding = MagicMock()
    
    mocker.patch(
        'core.rag_service._create_embedder_sync',
        return_value=mock_embedder
    )
    
    # Act
    await rag_service.initialize_global_embedder()
    
    # Wait for background task to complete
    await asyncio.sleep(0.1)
    
    # Assert
    assert rag_service._global_embedder is not None
    assert rag_service._embedder_ready.is_set()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_initialize_global_embedder_idempotency(mocker):
    """
    Test that calling initialize_global_embedder() multiple times does not reinitialize.
    
    Arrange: Set _global_embedder to a mock value
    Act: Call initialize_global_embedder
    Assert: create_embedder_sync is not called again
    """
    # Arrange
    from core import rag_service
    existing_embedder = MagicMock()
    rag_service._global_embedder = existing_embedder
    
    mock_create = mocker.patch('core.rag_service._create_embedder_sync')
    
    # Act
    await rag_service.initialize_global_embedder()
    
    # Assert
    mock_create.assert_not_called()
    assert rag_service._global_embedder is existing_embedder


@pytest.mark.unit
@pytest.mark.asyncio
async def test_initialize_global_embedder_already_in_progress(mocker):
    """
    Test that calling initialize_global_embedder() while init in progress is ignored.
    
    Arrange: Set _initialization_task to a running task
    Act: Call initialize_global_embedder
    Assert: No new task is created
    """
    # Arrange
    from core import rag_service
    
    async def slow_task():
        """
        Waits for ten seconds.
        
        Suspends execution for ten seconds before returning.
        """
        await asyncio.sleep(10)
    
    rag_service._initialization_task = asyncio.create_task(slow_task())
    mock_create = mocker.patch('core.rag_service._create_embedder_sync')
    
    # Act
    await rag_service.initialize_global_embedder()
    
    # Assert
    mock_create.assert_not_called()
    
    # Cleanup
    rag_service._initialization_task.cancel()
    try:
        await rag_service._initialization_task
    except asyncio.CancelledError:
        pass


# ============================================================================
# TEST: close_global_embedder
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_global_embedder_cleanup():
    """
    Test that close_global_embedder() properly cleans up resources.
    
    Arrange: Set _global_embedder and _embedder_ready
    Act: Call close_global_embedder
    Assert: All global state is reset
    """
    # Arrange
    from core import rag_service
    rag_service._global_embedder = MagicMock()
    rag_service._embedder_ready.set()
    
    # Act
    await rag_service.close_global_embedder()
    
    # Assert
    assert rag_service._global_embedder is None
    assert not rag_service._embedder_ready.is_set()
    assert rag_service._initialization_task is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_global_embedder_cancels_pending_task():
    """
    Test that close_global_embedder() cancels pending initialization task.
    
    Arrange: Create a running initialization task and set _global_embedder
    Act: Call close_global_embedder
    Assert: Task is cancelled and state is reset
    """
    # Arrange
    from core import rag_service
    
    async def slow_init():
        """
        Simulates a slow initialization by delaying for 10 seconds.
        
        This coroutine awaits for 10 seconds to emulate a long-running initialization task (useful in tests).
        """
        await asyncio.sleep(10)
    
    rag_service._initialization_task = asyncio.create_task(slow_init())
    rag_service._global_embedder = MagicMock()  # Set embedder so cleanup proceeds fully
    
    # Act
    await rag_service.close_global_embedder()
    
    # Assert
    assert rag_service._initialization_task is None
    assert rag_service._global_embedder is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_global_embedder_when_not_initialized():
    """
    Test that close_global_embedder() is safe to call when not initialized.
    
    Arrange: Ensure _global_embedder is None
    Act: Call close_global_embedder
    Assert: No error raised
    """
    # Arrange
    from core import rag_service
    assert rag_service._global_embedder is None
    
    # Act & Assert (no exception)
    await rag_service.close_global_embedder()


# ============================================================================
# TEST: is_embedder_initializing
# ============================================================================
@pytest.mark.unit
def test_is_embedder_initializing_returns_true_when_task_running():
    """
    Test that is_embedder_initializing() returns True when task is running.
    
    Arrange: Create a running task
    Act: Call is_embedder_initializing
    Assert: Returns True
    """
    # Arrange
    from core import rag_service
    
    async def slow_task():
        """
        Waits for ten seconds.
        
        Suspends execution for ten seconds before returning.
        """
        await asyncio.sleep(10)
    
    loop = asyncio.new_event_loop()
    rag_service._initialization_task = loop.create_task(slow_task())
    
    # Act
    result = rag_service.is_embedder_initializing()
    
    # Assert
    assert result is True
    
    # Cleanup
    rag_service._initialization_task.cancel()
    loop.close()


@pytest.mark.unit
def test_is_embedder_initializing_returns_false_when_no_task():
    """
    Test that is_embedder_initializing() returns False when no task exists.
    
    Arrange: Ensure _initialization_task is None
    Act: Call is_embedder_initializing
    Assert: Returns False
    """
    # Arrange
    from core import rag_service
    rag_service._initialization_task = None
    
    # Act
    result = rag_service.is_embedder_initializing()
    
    # Assert
    assert result is False


@pytest.mark.unit
def test_is_embedder_initializing_returns_false_when_task_done():
    """
    Test that is_embedder_initializing() returns False when task is completed.
    
    Arrange: Create a completed task
    Act: Call is_embedder_initializing
    Assert: Returns False
    """
    # Arrange
    from core import rag_service
    
    async def quick_task():
        """
        A no-op asynchronous placeholder intended for lightweight scheduling or testing.
        
        This coroutine performs no operation and can be awaited where an asynchronous task is required (e.g., as a stub in tests or to yield control to the event loop).
        """
        pass
    
    loop = asyncio.new_event_loop()
    task = loop.create_task(quick_task())
    loop.run_until_complete(task)
    rag_service._initialization_task = task
    
    # Act
    result = rag_service.is_embedder_initializing()
    
    # Assert
    assert result is False
    
    # Cleanup
    loop.close()


# ============================================================================
# TEST: get_global_embedder
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_global_embedder_returns_embedder_when_ready():
    """
    Test that get_global_embedder() returns embedder when already initialized.
    
    Arrange: Set _global_embedder and _embedder_ready
    Act: Call get_global_embedder
    Assert: Returns the embedder
    """
    # Arrange
    from core import rag_service
    mock_embedder = MagicMock()
    rag_service._global_embedder = mock_embedder
    rag_service._embedder_ready.set()
    
    # Act
    result = await rag_service.get_global_embedder()
    
    # Assert
    assert result is mock_embedder


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_global_embedder_raises_when_not_initialized():
    """
    Test that get_global_embedder() raises RuntimeError when not initialized.
    
    Arrange: Ensure _global_embedder is None and no task
    Act: Call get_global_embedder
    Assert: Raises RuntimeError
    """
    # Arrange
    from core import rag_service
    rag_service._global_embedder = None
    rag_service._initialization_task = None
    
    # Act & Assert
    with pytest.raises(RuntimeError) as exc_info:
        await rag_service.get_global_embedder()
    
    assert "not initialized" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_global_embedder_waits_for_initialization(mocker):
    """
    Test that get_global_embedder() waits for initialization to complete.
    
    Arrange: Start initialization in background
    Act: Call get_global_embedder
    Assert: Returns embedder after wait
    """
    # Arrange
    from core import rag_service
    mock_embedder = MagicMock()
    
    async def delayed_init():
        """
        Perform a short delayed initialization of the global embedder and mark it as ready.
        
        This coroutine sets the test embedder into rag_service._global_embedder and signals readiness on rag_service._embedder_ready after a brief delay to simulate asynchronous initialization.
        """
        await asyncio.sleep(0.05)
        rag_service._global_embedder = mock_embedder
        rag_service._embedder_ready.set()
    
    rag_service._initialization_task = asyncio.create_task(delayed_init())
    
    # Act
    result = await rag_service.get_global_embedder()
    
    # Assert
    assert result is mock_embedder


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_global_embedder_timeout_scenario(mocker):
    """
    Test that get_global_embedder() raises RuntimeError on timeout.
    
    Arrange: Start slow initialization, mock timeout to be very short
    Act: Call get_global_embedder
    Assert: Raises RuntimeError with timeout message
    """
    # Arrange
    from core import rag_service
    
    async def very_slow_init():
        """
        Simulates a long-running initialization by delaying for approximately 100 seconds.
        
        This helper is used to emulate a very slow initialization task (for example, in tests that exercise initialization timeouts or concurrent startup behavior).
        """
        await asyncio.sleep(100)  # Very slow
    
    rag_service._initialization_task = asyncio.create_task(very_slow_init())
    
    # Mock wait_for to timeout immediately
    original_wait_for = asyncio.wait_for
    
    async def mock_wait_for(coro, timeout):
        """
        Simulate a timeout when awaiting a coroutine.
        
        Parameters:
            coro: The coroutine that would be awaited (ignored).
            timeout (float): The timeout value that would be used (ignored).
        
        Raises:
            asyncio.TimeoutError: Always raised to mimic a timeout from asyncio.wait_for.
        """
        raise asyncio.TimeoutError()
    
    mocker.patch.object(asyncio, 'wait_for', mock_wait_for)
    
    # Act & Assert
    with pytest.raises(RuntimeError) as exc_info:
        await rag_service.get_global_embedder()
    
    assert "Timeout" in str(exc_info.value)
    
    # Cleanup
    rag_service._initialization_task.cancel()
    try:
        await rag_service._initialization_task
    except asyncio.CancelledError:
        pass


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_global_embedder_raises_on_init_failure():
    """
    Test that get_global_embedder() raises when initialization completed but embedder is None.
    
    Arrange: Set _embedder_ready but leave _global_embedder as None (simulating init failure)
    Act: Call get_global_embedder
    Assert: Raises RuntimeError
    """
    # Arrange
    from core import rag_service
    
    async def failing_init():
        """
        Mark embedder initialization as completed while leaving the global embedder unset to simulate a failed initialization.
        
        This sets rag_service._embedder_ready and deliberately does not assign rag_service._global_embedder; intended for tests that need the initialization flag set but where embedder creation has failed.
        """
        rag_service._embedder_ready.set()
        # But don't set _global_embedder (simulating failure)
    
    rag_service._initialization_task = asyncio.create_task(failing_init())
    await asyncio.sleep(0.01)
    
    # Act & Assert
    with pytest.raises(RuntimeError) as exc_info:
        await rag_service.get_global_embedder()
    
    assert "failed to initialize" in str(exc_info.value)


# ============================================================================
# TEST: generate_query_embedding
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_query_embedding_with_mocked_embedder(mock_embedder):
    """
    Test that generate_query_embedding() uses embedder and returns embedding with timing.
    
    Arrange: Set up global embedder with mock
    Act: Call generate_query_embedding
    Assert: Returns embedding and duration > 0
    """
    # Arrange
    from core import rag_service
    rag_service._global_embedder = mock_embedder
    rag_service._embedder_ready.set()
    
    # Act
    embedding, duration_ms = await rag_service.generate_query_embedding("test query")
    
    # Assert
    assert isinstance(embedding, list)
    assert len(embedding) == 1536  # text-embedding-3-small dimension
    assert duration_ms >= 0
    mock_embedder.embed_query.assert_called_once_with("test query")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_query_embedding_error_propagation(mock_embedder):
    """
    Test that generate_query_embedding() propagates embedder errors.
    
    Arrange: Mock embedder to raise exception
    Act: Call generate_query_embedding
    Assert: Exception is propagated
    """
    # Arrange
    from core import rag_service
    mock_embedder.embed_query.side_effect = Exception("API Error")
    rag_service._global_embedder = mock_embedder
    rag_service._embedder_ready.set()
    
    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await rag_service.generate_query_embedding("test query")
    
    assert "API Error" in str(exc_info.value)


# ============================================================================
# TEST: search_with_embedding
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_embedding_returns_results(mock_db_pool, mocker):
    """
    Test that search_with_embedding() returns formatted results from database.
    
    Arrange: Mock database to return search results
    Act: Call search_with_embedding
    Assert: Returns structured results with timing
    """
    # Arrange
    mock_db_pool._mock_connection.fetch.return_value = [
        {
            "chunk_id": "chunk-1",
            "document_id": "doc-1",
            "content": "Test content about RAG",
            "similarity": 0.95,
            "metadata": '{"section": "intro"}',
            "document_title": "RAG Guide",
            "document_source": "docs/rag.md"
        }
    ]
    
    mocker.patch('core.rag_service.global_db_pool', mock_db_pool)
    
    from core import rag_service
    embedding = [0.1] * 1536
    
    # Act
    results, duration_ms = await rag_service.search_with_embedding(embedding, limit=5)
    
    # Assert
    assert len(results) == 1
    assert results[0]["content"] == "Test content about RAG"
    assert results[0]["similarity"] == 0.95
    assert results[0]["title"] == "RAG Guide"
    assert results[0]["source"] == "docs/rag.md"
    assert results[0]["metadata"] == {"section": "intro"}
    assert duration_ms >= 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_embedding_with_source_filter(mock_db_pool, mocker):
    """
    Test that search_with_embedding() applies source_filter using ILIKE.
    
    Arrange: Mock database with source filter
    Act: Call search_with_embedding with source_filter
    Assert: SQL query includes ILIKE pattern
    """
    # Arrange
    mock_db_pool._mock_connection.fetch.return_value = []
    mocker.patch('core.rag_service.global_db_pool', mock_db_pool)
    
    from core import rag_service
    embedding = [0.1] * 1536
    
    # Act
    results, _ = await rag_service.search_with_embedding(
        embedding, limit=5, source_filter="langfuse-docs"
    )
    
    # Assert
    call_args = mock_db_pool._mock_connection.fetch.call_args
    sql_query = call_args[0][0]
    args = call_args[0][1:]
    
    assert "ILIKE" in sql_query
    assert "%langfuse-docs%" in args


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_embedding_empty_results(mock_db_pool, mocker):
    """
    Test that search_with_embedding() handles empty results.
    
    Arrange: Mock database to return empty list
    Act: Call search_with_embedding
    Assert: Returns empty list
    """
    # Arrange
    mock_db_pool._mock_connection.fetch.return_value = []
    mocker.patch('core.rag_service.global_db_pool', mock_db_pool)
    
    from core import rag_service
    embedding = [0.1] * 1536
    
    # Act
    results, duration_ms = await rag_service.search_with_embedding(embedding)
    
    # Assert
    assert results == []
    assert duration_ms >= 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_embedding_handles_dict_metadata(mock_db_pool, mocker):
    """
    Test that search_with_embedding() handles metadata as dict (not string).
    
    Arrange: Mock database with metadata as dict
    Act: Call search_with_embedding
    Assert: Metadata is preserved as dict
    """
    # Arrange
    mock_db_pool._mock_connection.fetch.return_value = [
        {
            "chunk_id": "chunk-1",
            "document_id": "doc-1",
            "content": "Content",
            "similarity": 0.9,
            "metadata": {"key": "value"},  # Already a dict
            "document_title": "Title",
            "document_source": "source.md"
        }
    ]
    mocker.patch('core.rag_service.global_db_pool', mock_db_pool)
    
    from core import rag_service
    embedding = [0.1] * 1536
    
    # Act
    results, _ = await rag_service.search_with_embedding(embedding)
    
    # Assert
    assert results[0]["metadata"] == {"key": "value"}


# ============================================================================
# TEST: search_knowledge_base_structured
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_knowledge_base_structured_integration(mock_embedder, mock_db_pool, mocker):
    """
    Test that search_knowledge_base_structured() integrates embedding and search.
    
    Arrange: Mock embedder and database
    Act: Call search_knowledge_base_structured
    Assert: Returns structured results with timing
    """
    # Arrange
    from core import rag_service
    rag_service._global_embedder = mock_embedder
    rag_service._embedder_ready.set()
    
    mock_db_pool._mock_connection.fetch.return_value = [
        {
            "chunk_id": "chunk-1",
            "document_id": "doc-1",
            "content": "RAG system architecture",
            "similarity": 0.92,
            "metadata": '{}',
            "document_title": "Architecture",
            "document_source": "docs/arch.md"
        }
    ]
    mocker.patch('core.rag_service.global_db_pool', mock_db_pool)
    
    # Act
    result = await rag_service.search_knowledge_base_structured("What is RAG?", limit=3)
    
    # Assert
    assert "results" in result
    assert "timing" in result
    assert len(result["results"]) == 1
    assert "embedding_ms" in result["timing"]
    assert "db_ms" in result["timing"]
    assert "total_ms" in result["timing"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_knowledge_base_structured_error_handling(mock_embedder, mocker):
    """
    Test that search_knowledge_base_structured() raises on error.
    
    Arrange: Mock embedder to raise exception
    Act: Call search_knowledge_base_structured
    Assert: Exception is propagated
    """
    # Arrange
    from core import rag_service
    mock_embedder.embed_query.side_effect = Exception("Embedding failed")
    rag_service._global_embedder = mock_embedder
    rag_service._embedder_ready.set()
    
    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await rag_service.search_knowledge_base_structured("query")
    
    assert "Embedding failed" in str(exc_info.value)


# ============================================================================
# TEST: search_knowledge_base
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_knowledge_base_formatting(mock_embedder, mock_db_pool, mocker):
    """
    Test that search_knowledge_base() formats results correctly.
    
    Arrange: Mock embedder and database with results
    Act: Call search_knowledge_base
    Assert: Returns formatted string with sources
    """
    # Arrange
    from core import rag_service
    rag_service._global_embedder = mock_embedder
    rag_service._embedder_ready.set()
    
    mock_db_pool._mock_connection.fetch.return_value = [
        {
            "chunk_id": "chunk-1",
            "document_id": "doc-1",
            "content": "RAG combines retrieval with generation.",
            "similarity": 0.95,
            "metadata": '{}',
            "document_title": "RAG Overview",
            "document_source": "docs/rag.md"
        },
        {
            "chunk_id": "chunk-2",
            "document_id": "doc-2",
            "content": "Embeddings are vector representations.",
            "similarity": 0.88,
            "metadata": '{}',
            "document_title": "Embeddings Guide",
            "document_source": "docs/embed.md"
        }
    ]
    mocker.patch('core.rag_service.global_db_pool', mock_db_pool)
    
    # Act
    result = await rag_service.search_knowledge_base("What is RAG?", limit=2)
    
    # Assert
    assert "Found 2 relevant results" in result
    assert "[Source: RAG Overview]" in result
    assert "[Source: Embeddings Guide]" in result
    assert "RAG combines retrieval" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_knowledge_base_empty_results(mock_embedder, mock_db_pool, mocker):
    """
    Test that search_knowledge_base() handles empty results.
    
    Arrange: Mock database to return empty list
    Act: Call search_knowledge_base
    Assert: Returns 'no results' message
    """
    # Arrange
    from core import rag_service
    rag_service._global_embedder = mock_embedder
    rag_service._embedder_ready.set()
    
    mock_db_pool._mock_connection.fetch.return_value = []
    mocker.patch('core.rag_service.global_db_pool', mock_db_pool)
    
    # Act
    result = await rag_service.search_knowledge_base("obscure query")
    
    # Assert
    assert "No relevant information found" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_knowledge_base_with_source_filter(mock_embedder, mock_db_pool, mocker):
    """
    Test that search_knowledge_base() includes source_filter in output.
    
    Arrange: Mock database with source filter
    Act: Call search_knowledge_base with source_filter
    Assert: Output mentions the filter
    """
    # Arrange
    from core import rag_service
    rag_service._global_embedder = mock_embedder
    rag_service._embedder_ready.set()
    
    mock_db_pool._mock_connection.fetch.return_value = [
        {
            "chunk_id": "chunk-1",
            "document_id": "doc-1",
            "content": "LangFuse integration guide.",
            "similarity": 0.9,
            "metadata": '{}',
            "document_title": "LangFuse Docs",
            "document_source": "langfuse-docs/integration.md"
        }
    ]
    mocker.patch('core.rag_service.global_db_pool', mock_db_pool)
    
    # Act
    result = await rag_service.search_knowledge_base(
        "LangFuse", limit=5, source_filter="langfuse-docs"
    )
    
    # Assert
    assert "filtered by: langfuse-docs" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_knowledge_base_error_handling(mock_embedder, mocker):
    """
    Test that search_knowledge_base() returns error message on exception.
    
    Arrange: Mock embedder to raise exception
    Act: Call search_knowledge_base
    Assert: Returns error message string
    """
    # Arrange
    from core import rag_service
    mock_embedder.embed_query.side_effect = Exception("API unavailable")
    rag_service._global_embedder = mock_embedder
    rag_service._embedder_ready.set()
    
    # Act
    result = await rag_service.search_knowledge_base("query")
    
    # Assert
    assert "error searching the knowledge base" in result
    assert "API unavailable" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_knowledge_base_empty_results_with_source_filter(mock_embedder, mock_db_pool, mocker):
    """
    Test that search_knowledge_base() mentions filter in empty results message.
    
    Arrange: Mock database to return empty with source filter
    Act: Call search_knowledge_base with source_filter
    Assert: Empty message mentions filter
    """
    # Arrange
    from core import rag_service
    rag_service._global_embedder = mock_embedder
    rag_service._embedder_ready.set()
    
    mock_db_pool._mock_connection.fetch.return_value = []
    mocker.patch('core.rag_service.global_db_pool', mock_db_pool)
    
    # Act
    result = await rag_service.search_knowledge_base(
        "query", source_filter="nonexistent-source"
    )
    
    # Assert
    assert "No relevant information found" in result
    assert "nonexistent-source" in result

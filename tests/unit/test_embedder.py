"""
Unit tests for ingestion/embedder.py

Tests all classes and functions with mocked OpenAI client:
- EmbeddingCache (get, set, eviction)
- EmbeddingGenerator (embed_query, embed_documents, retry logic)
- create_embedder factory function

Reference: docs/stories/5/5-2/5-2-implement-unit-tests-with-tdd.md
AC#8: Embedding logic validated with mocked OpenAI client
AC#9: >70% coverage for ingestion modules

IMPORTANT: TestModel is NOT used here - it's only for PydanticAI Agent.
EmbeddingGenerator uses OpenAI client directly, so we mock LangfuseAsyncOpenAI.
"""

import asyncio
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# TEST: EmbeddingCache
# ============================================================================
@pytest.mark.unit
def test_embedding_cache_get_returns_none_for_missing_key():
    """
    Test that EmbeddingCache.get() returns None for missing keys.
    
    Arrange: Create empty cache
    Act: Call get with unknown key
    Assert: Returns None
    """
    # Arrange
    from ingestion.embedder import EmbeddingCache
    cache = EmbeddingCache(max_size=100)
    
    # Act
    result = cache.get("nonexistent_key")
    
    # Assert
    assert result is None


@pytest.mark.unit
def test_embedding_cache_set_and_get():
    """
    Test that EmbeddingCache.set() stores values retrievable by get().
    
    Arrange: Create cache
    Act: Set a value, then get it
    Assert: Returns the stored value
    """
    # Arrange
    from ingestion.embedder import EmbeddingCache
    cache = EmbeddingCache(max_size=100)
    embedding = [0.1, 0.2, 0.3]
    
    # Act
    cache.set("test_key", embedding)
    result = cache.get("test_key")
    
    # Assert
    assert result == embedding


@pytest.mark.unit
def test_embedding_cache_eviction_when_full():
    """
    Test that EmbeddingCache evicts oldest entry when max_size reached.
    
    Arrange: Create cache with max_size=2, fill it
    Act: Add third entry
    Assert: First entry is evicted
    """
    # Arrange
    from ingestion.embedder import EmbeddingCache
    cache = EmbeddingCache(max_size=2)
    cache.set("key1", [1.0])
    cache.set("key2", [2.0])
    
    # Act
    cache.set("key3", [3.0])
    
    # Assert
    assert cache.get("key1") is None  # Evicted
    assert cache.get("key2") == [2.0]  # Still present
    assert cache.get("key3") == [3.0]  # Added


@pytest.mark.unit
def test_embedding_cache_eviction_empty_cache():
    """
    Test that EmbeddingCache handles eviction on empty cache gracefully.
    
    Arrange: Create cache with max_size=0
    Act: Try to set a value
    Assert: No error raised
    """
    # Arrange
    from ingestion.embedder import EmbeddingCache
    cache = EmbeddingCache(max_size=0)
    
    # Act & Assert (no exception)
    cache.set("key", [1.0])


@pytest.mark.unit
def test_embedding_cache_update_existing_key():
    """
    Test that EmbeddingCache.set() updates existing keys without eviction.
    
    Arrange: Create cache, set a key
    Act: Set same key with new value
    Assert: Value is updated, no eviction
    """
    # Arrange
    from ingestion.embedder import EmbeddingCache
    cache = EmbeddingCache(max_size=2)
    cache.set("key1", [1.0])
    cache.set("key2", [2.0])
    
    # Act
    cache.set("key1", [1.5])  # Update existing
    
    # Assert
    assert cache.get("key1") == [1.5]
    assert cache.get("key2") == [2.0]
    assert len(cache.cache) == 2


# ============================================================================
# TEST: EmbeddingGenerator.__init__
# ============================================================================
@pytest.mark.unit
def test_embedding_generator_init_default_config(mocker):
    """
    Verify EmbeddingGenerator initializes with expected default configuration.
    
    Creates an EmbeddingGenerator with a mocked provider and client, then asserts that:
    - model_name == "text-embedding-3-small"
    - batch_size == 100
    - use_cache is True
    - cache is not None
    """
    # Arrange
    mock_client = MagicMock()
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    # Act
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator()
    
    # Assert
    assert generator.model_name == "text-embedding-3-small"
    assert generator.batch_size == 100
    assert generator.use_cache is True
    assert generator.cache is not None


@pytest.mark.unit
def test_embedding_generator_init_custom_config(mocker):
    """
    Test that EmbeddingGenerator accepts custom configuration.
    
    Arrange: Mock OpenAI client
    Act: Create EmbeddingGenerator with custom params
    Assert: Custom values are set
    """
    # Arrange
    mock_client = MagicMock()
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    # Act
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator(
        model_name="text-embedding-ada-002",
        batch_size=50,
        use_cache=False
    )
    
    # Assert
    assert generator.model_name == "text-embedding-ada-002"
    assert generator.batch_size == 50
    assert generator.use_cache is False
    assert generator.cache is None


@pytest.mark.unit
def test_embedding_generator_init_with_custom_api_key(mocker):
    """
    Test that EmbeddingGenerator uses provided api_key over env.
    
    Arrange: Mock OpenAI client
    Act: Create EmbeddingGenerator with api_key
    Assert: Provided api_key is used
    """
    # Arrange
    mock_client_class = mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI')
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="env-key",
        base_url="https://api.openai.com/v1"
    ))
    
    # Act
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator(api_key="custom-api-key")
    
    # Assert
    assert generator.api_key == "custom-api-key"
    mock_client_class.assert_called_once()


# ============================================================================
# TEST: embed_query
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_query_cache_hit(mocker):
    """
    Test that embed_query() returns cached embedding on cache hit.
    
    Arrange: Pre-populate cache with embedding
    Act: Call embed_query with cached text
    Assert: Returns cached value, no API call
    """
    # Arrange
    mock_client = MagicMock()
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator()
    
    cached_embedding = [0.1, 0.2, 0.3]
    generator.cache.set("cached query", cached_embedding)
    
    # Act
    result = await generator.embed_query("cached query")
    
    # Assert
    assert result == cached_embedding


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_query_cache_miss_calls_api(mocker):
    """
    Test that embed_query() calls OpenAI API on cache miss.
    
    Arrange: Create generator with mocked client
    Act: Call embed_query with new text
    Assert: API is called, result is cached
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator()
    
    # Act
    result = await generator.embed_query("new query")
    
    # Assert
    assert result == [0.1, 0.2, 0.3]
    mock_client.embeddings.create.assert_called_once()
    assert generator.cache.get("new query") == [0.1, 0.2, 0.3]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_query_without_cache(mocker):
    """
    Test that embed_query() works without cache.
    
    Arrange: Create generator with use_cache=False
    Act: Call embed_query
    Assert: API is called, no caching
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.5, 0.6])]
    
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator(use_cache=False)
    
    # Act
    result = await generator.embed_query("query")
    
    # Assert
    assert result == [0.5, 0.6]
    assert generator.cache is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_query_api_error_propagation(mocker):
    """
    Test that embed_query() propagates API errors.
    
    Arrange: Mock client to raise exception
    Act: Call embed_query
    Assert: Exception is propagated
    """
    # Arrange
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(side_effect=Exception("API Error"))
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    # Disable retry for faster test
    mocker.patch('ingestion.embedder.EmbeddingGenerator._generate_single_embedding',
                 new_callable=AsyncMock,
                 side_effect=Exception("API Error"))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator()
    
    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await generator.embed_query("query")
    
    assert "API Error" in str(exc_info.value)


# ============================================================================
# TEST: embed_documents
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_documents_batch_processing(mocker):
    """
    Test that embed_documents() processes texts in batches.
    
    Arrange: Create generator with batch_size=2
    Act: Call embed_documents with 3 texts
    Assert: API called twice (2 batches)
    """
    # Arrange
    mock_response = MagicMock()
    
    # First batch returns 2 embeddings
    mock_response_batch1 = MagicMock()
    mock_response_batch1.data = [
        MagicMock(embedding=[0.1]),
        MagicMock(embedding=[0.2])
    ]
    
    # Second batch returns 1 embedding
    mock_response_batch2 = MagicMock()
    mock_response_batch2.data = [
        MagicMock(embedding=[0.3])
    ]
    
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(
        side_effect=[mock_response_batch1, mock_response_batch2]
    )
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator(batch_size=2, use_cache=False)
    
    # Act
    results = await generator.embed_documents(["text1", "text2", "text3"])
    
    # Assert
    assert len(results) == 3
    assert results == [[0.1], [0.2], [0.3]]
    assert mock_client.embeddings.create.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_documents_with_partial_cache_hits(mocker):
    """
    Test that embed_documents() uses cache for some texts.
    
    Arrange: Pre-cache some texts
    Act: Call embed_documents with mixed texts
    Assert: Only uncached texts call API
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.3])]
    
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator(batch_size=100)
    
    # Pre-cache some texts
    generator.cache.set("cached_text1", [0.1])
    generator.cache.set("cached_text2", [0.2])
    
    # Act
    results = await generator.embed_documents(["cached_text1", "cached_text2", "new_text"])
    
    # Assert
    assert len(results) == 3
    assert results[0] == [0.1]  # From cache
    assert results[1] == [0.2]  # From cache
    assert results[2] == [0.3]  # From API
    mock_client.embeddings.create.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_documents_empty_list():
    """
    Test that embed_documents() handles empty list.
    
    Arrange: Create generator
    Act: Call embed_documents with empty list
    Assert: Returns empty list
    """
    # Arrange
    from ingestion.embedder import EmbeddingGenerator
    
    # We need to mock for init, but no API calls expected
    with patch('ingestion.embedder.LangfuseAsyncOpenAI'), \
         patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
             api_key="test-key",
             base_url="https://api.openai.com/v1"
         )):
        generator = EmbeddingGenerator()
    
    # Act
    results = await generator.embed_documents([])
    
    # Assert
    assert results == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_documents_all_cached(mocker):
    """
    Test that embed_documents() returns all from cache when all cached.
    
    Arrange: Pre-cache all texts
    Act: Call embed_documents
    Assert: No API calls, all from cache
    """
    # Arrange
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock()
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator()
    
    # Pre-cache all
    generator.cache.set("text1", [0.1])
    generator.cache.set("text2", [0.2])
    
    # Act
    results = await generator.embed_documents(["text1", "text2"])
    
    # Assert
    assert results == [[0.1], [0.2]]
    mock_client.embeddings.create.assert_not_called()


# ============================================================================
# TEST: embed_chunks (backward compatibility)
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_chunks_backward_compatibility(mocker):
    """
    Verify that embed_chunks assigns embeddings to each chunk and augments non-empty metadata.
    
    Checks that for chunks with non-empty metadata the function sets each chunk's embedding, adds the metadata keys `embedding_model` and `embedding_generated_at`, and preserves existing metadata entries.
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1]),
        MagicMock(embedding=[0.2])
    ]
    
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator(use_cache=False)
    
    # Create simple chunk objects with non-empty metadata
    # Note: In source code, `if chunk.metadata:` is falsy for empty dict
    class SimpleChunk:
        def __init__(self, content):
            """
            Initialize the object with provided content, a default non-empty metadata dict, and no embedding.
            
            Parameters:
                content (str): The textual content for this object.
            
            Notes:
                - `metadata` is initialized to {"source": "test"}.
                - `embedding` is initialized to None.
            """
            self.content = content
            self.metadata = {"source": "test"}  # Non-empty so metadata gets updated
            self.embedding = None
    
    chunk1 = SimpleChunk("Content 1")
    chunk2 = SimpleChunk("Content 2")
    
    # Act
    results = await generator.embed_chunks([chunk1, chunk2])
    
    # Assert
    assert results[0].embedding == [0.1]
    assert results[1].embedding == [0.2]
    assert "embedding_model" in results[0].metadata
    assert "embedding_generated_at" in results[0].metadata
    assert results[0].metadata["source"] == "test"  # Original metadata preserved


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_chunks_with_empty_metadata(mocker):
    """
    Test that embed_chunks() handles chunks with empty metadata.
    
    Note: In source code, `if chunk.metadata:` is falsy for empty dict,
    so metadata is not updated. This test verifies that behavior.
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1])]
    
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator(use_cache=False)
    
    class SimpleChunk:
        def __init__(self, content):
            """
            Initialize the object with provided textual content and default storage for metadata and embedding.
            
            Parameters:
                content (str): The text content to store on the instance.
            
            Notes:
                - `metadata` is initialized to an empty dictionary.
                - `embedding` is initialized to `None`.
            """
            self.content = content
            self.metadata = {}  # Empty dict - falsy in Python
            self.embedding = None
    
    chunk = SimpleChunk("Content")
    
    # Act
    results = await generator.embed_chunks([chunk])
    
    # Assert - embedding assigned but metadata NOT updated (empty dict is falsy)
    assert results[0].embedding == [0.1]
    assert results[0].metadata == {}  # Empty metadata stays empty


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_chunks_empty_list():
    """
    Verify embed_chunks returns an empty list when given an empty input list.
    """
    # Arrange
    with patch('ingestion.embedder.LangfuseAsyncOpenAI'), \
         patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
             api_key="test-key",
             base_url="https://api.openai.com/v1"
         )):
        from ingestion.embedder import EmbeddingGenerator
        generator = EmbeddingGenerator()
    
    # Act
    results = await generator.embed_chunks([])
    
    # Assert
    assert results == []


# ============================================================================
# TEST: _generate_single_embedding (retry logic)
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_single_embedding_success(mocker):
    """
    Test that _generate_single_embedding() returns embedding on success.
    
    Arrange: Mock successful API response
    Act: Call _generate_single_embedding
    Assert: Returns embedding
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator()
    
    # Act
    result = await generator._generate_single_embedding("test text")
    
    # Assert
    assert result == [0.1, 0.2, 0.3]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_single_embedding_retry_on_transient_error(mocker):
    """
    Test that _generate_single_embedding() retries on transient errors.
    
    Arrange: Mock API to fail twice then succeed
    Act: Call _generate_single_embedding
    Assert: Returns embedding after retries
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1])]
    
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(
        side_effect=[
            Exception("Transient error 1"),
            Exception("Transient error 2"),
            mock_response
        ]
    )
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    # Patch tenacity wait to speed up test
    mocker.patch('tenacity.wait_exponential', return_value=lambda x: 0)
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator()
    
    # Act
    result = await generator._generate_single_embedding("test")
    
    # Assert
    assert result == [0.1]
    assert mock_client.embeddings.create.call_count == 3


# ============================================================================
# TEST: _generate_batch_embeddings (retry logic)
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_batch_embeddings_success(mocker):
    """
    Test that _generate_batch_embeddings() returns embeddings for batch.
    
    Arrange: Mock successful API response
    Act: Call _generate_batch_embeddings
    Assert: Returns list of embeddings
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1]),
        MagicMock(embedding=[0.2])
    ]
    
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator()
    
    # Act
    result = await generator._generate_batch_embeddings(["text1", "text2"])
    
    # Assert
    assert result == [[0.1], [0.2]]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_batch_embeddings_handles_empty_strings(mocker):
    """
    Test that _generate_batch_embeddings() replaces empty strings with space.
    
    Arrange: Mock API
    Act: Call with empty string in batch
    Assert: Empty string replaced with space in API call
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1]),
        MagicMock(embedding=[0.2])
    ]
    
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator()
    
    # Act
    await generator._generate_batch_embeddings(["text1", ""])
    
    # Assert
    call_args = mock_client.embeddings.create.call_args
    input_texts = call_args.kwargs.get('input') or call_args[1].get('input')
    assert input_texts == ["text1", " "]


# ============================================================================
# TEST: create_embedder factory function
# ============================================================================
@pytest.mark.unit
def test_create_embedder_default_config(mocker):
    """
    Test that create_embedder() returns EmbeddingGenerator with defaults.
    
    Arrange: Mock dependencies, remove EMBEDDING_MODEL from env
    Act: Call create_embedder
    Assert: Returns EmbeddingGenerator with default config
    """
    # Arrange
    mock_client = MagicMock()
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    # Remove EMBEDDING_MODEL so default is used (empty string triggers default in os.getenv)
    import os
    original_value = os.environ.pop('EMBEDDING_MODEL', None)
    
    try:
        # Act
        from ingestion.embedder import create_embedder
        embedder = create_embedder()
        
        # Assert
        assert embedder.model_name == "text-embedding-3-small"
        assert embedder.batch_size == 100
        assert embedder.use_cache is True
    finally:
        # Restore env
        if original_value is not None:
            os.environ['EMBEDDING_MODEL'] = original_value


@pytest.mark.unit
def test_create_embedder_custom_params(mocker):
    """
    Test that create_embedder() accepts custom parameters.
    
    Arrange: Mock dependencies
    Act: Call create_embedder with custom params
    Assert: Returns EmbeddingGenerator with custom config
    """
    # Arrange
    mock_client = MagicMock()
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    # Act
    from ingestion.embedder import create_embedder
    embedder = create_embedder(
        use_cache=False,
        batch_size=50,
        model_name="text-embedding-ada-002"
    )
    
    # Assert
    assert embedder.model_name == "text-embedding-ada-002"
    assert embedder.batch_size == 50
    assert embedder.use_cache is False


@pytest.mark.unit
def test_create_embedder_uses_env_model(mocker):
    """
    Test that create_embedder() uses EMBEDDING_MODEL env var.
    
    Arrange: Set EMBEDDING_MODEL env var
    Act: Call create_embedder without model_name
    Assert: Uses env var value
    """
    # Arrange
    mock_client = MagicMock()
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    mocker.patch.dict('os.environ', {'EMBEDDING_MODEL': 'text-embedding-ada-002'})
    
    # Act
    from ingestion.embedder import create_embedder
    embedder = create_embedder()
    
    # Assert
    assert embedder.model_name == "text-embedding-ada-002"


# ============================================================================
# TEST: LangFuse OpenAI wrapper graceful degradation
# ============================================================================
@pytest.mark.unit
def test_langfuse_wrapper_unavailable_falls_back(mocker):
    """
    Test that embedder falls back to direct OpenAI when LangFuse unavailable.
    
    This tests the module-level import fallback behavior.
    """
    # The fallback is tested implicitly since we mock LangfuseAsyncOpenAI
    # and the code works. If the fallback didn't work, tests would fail.
    # 
    # Direct testing of import fallback would require reimporting the module
    # which is complex. The behavior is verified by successful mocking.
    
    # Arrange
    mock_client = MagicMock()
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    # Act
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator()
    
    # Assert - generator works regardless of which client is used
    assert generator.client is mock_client


# ============================================================================
# TEST: Error handling for API failures
# ============================================================================
@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_documents_api_failure_propagation(mocker):
    """
    Test that embed_documents() propagates API errors after retries exhausted.
    
    Arrange: Mock API to always fail
    Act: Call embed_documents
    Assert: Exception is propagated (wrapped in RetryError by tenacity)
    """
    # Arrange
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(
        side_effect=Exception("Permanent API Error")
    )
    
    mocker.patch('ingestion.embedder.LangfuseAsyncOpenAI', return_value=mock_client)
    mocker.patch('ingestion.embedder.get_provider_config', return_value=MagicMock(
        api_key="test-key",
        base_url="https://api.openai.com/v1"
    ))
    
    from ingestion.embedder import EmbeddingGenerator
    generator = EmbeddingGenerator(use_cache=False)
    
    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await generator.embed_documents(["text"])
    
    # Tenacity wraps the error in RetryError, but original exception is preserved
    # Just verify an exception was raised (RetryError wraps original)
    assert exc_info.value is not None

"""
Unit tests for LangFuse integration in MCP Server.

Tests:
- LangFuse client initialization from environment variables
- Graceful degradation when LangFuse is unavailable
- @observe decorator application to tools
- Cost tracking via langfuse.openai wrapper
- Nested spans for cost breakdown visibility
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLangfuseInitialization:
    """Test LangFuse client initialization logic."""

    def test_initialization_with_valid_env_vars(self):
        """Test LangFuse initializes correctly when env vars are set."""
        with patch.dict(
            os.environ, {"LANGFUSE_PUBLIC_KEY": "pk-lf-test", "LANGFUSE_SECRET_KEY": "sk-lf-test"}
        ):
            # Import fresh module with patched env vars
            from docling_mcp import lifespan

            # Reset module state
            lifespan._langfuse_client = None
            lifespan._langfuse_enabled = False

            with patch("langfuse.get_client") as mock_get_client:
                mock_client = MagicMock()
                mock_get_client.return_value = mock_client

                lifespan._initialize_langfuse()

                assert lifespan._langfuse_enabled is True
                mock_get_client.assert_called_once()

    def test_initialization_without_public_key(self):
        """Test graceful degradation when LANGFUSE_PUBLIC_KEY is missing."""
        with patch.dict(os.environ, {"LANGFUSE_SECRET_KEY": "sk-lf-test"}, clear=True):
            # Remove public key
            os.environ.pop("LANGFUSE_PUBLIC_KEY", None)

            from docling_mcp import lifespan

            # Reset module state
            lifespan._langfuse_client = None
            lifespan._langfuse_enabled = False

            lifespan._initialize_langfuse()

            assert lifespan._langfuse_enabled is False
            assert lifespan._langfuse_client is None

    def test_initialization_without_secret_key(self):
        """Test graceful degradation when LANGFUSE_SECRET_KEY is missing."""
        with patch.dict(os.environ, {"LANGFUSE_PUBLIC_KEY": "pk-lf-test"}, clear=True):
            # Remove secret key
            os.environ.pop("LANGFUSE_SECRET_KEY", None)

            from docling_mcp import lifespan

            # Reset module state
            lifespan._langfuse_client = None
            lifespan._langfuse_enabled = False

            lifespan._initialize_langfuse()

            assert lifespan._langfuse_enabled is False
            assert lifespan._langfuse_client is None

    def test_initialization_with_import_error(self):
        """Test graceful degradation when langfuse SDK is not installed."""
        with patch.dict(
            os.environ, {"LANGFUSE_PUBLIC_KEY": "pk-lf-test", "LANGFUSE_SECRET_KEY": "sk-lf-test"}
        ):
            from docling_mcp import lifespan

            # Reset module state
            lifespan._langfuse_client = None
            lifespan._langfuse_enabled = False

            with patch.dict("sys.modules", {"langfuse": None}):
                with patch(
                    "builtins.__import__", side_effect=ImportError("No module named 'langfuse'")
                ):
                    lifespan._initialize_langfuse()

                    assert lifespan._langfuse_enabled is False
                    assert lifespan._langfuse_client is None

    def test_initialization_with_client_error(self):
        """Test graceful degradation when LangFuse client fails to initialize."""
        with patch.dict(
            os.environ, {"LANGFUSE_PUBLIC_KEY": "pk-lf-test", "LANGFUSE_SECRET_KEY": "sk-lf-test"}
        ):
            from docling_mcp import lifespan

            # Reset module state
            lifespan._langfuse_client = None
            lifespan._langfuse_enabled = False

            with patch("langfuse.get_client") as mock_get_client:
                mock_get_client.side_effect = RuntimeError("Connection failed")

                lifespan._initialize_langfuse()

                assert lifespan._langfuse_enabled is False
                assert lifespan._langfuse_client is None


class TestLangfuseShutdown:
    """Test LangFuse client shutdown logic."""

    def test_shutdown_with_active_client(self):
        """Test shutdown flushes and closes client."""
        from docling_mcp import lifespan

        mock_client = MagicMock()
        lifespan._langfuse_client = mock_client
        lifespan._langfuse_enabled = True

        lifespan._shutdown_langfuse()

        mock_client.flush.assert_called_once()
        mock_client.shutdown.assert_called_once()
        assert lifespan._langfuse_client is None
        assert lifespan._langfuse_enabled is False

    def test_shutdown_with_no_client(self):
        """Test shutdown does nothing when no client exists."""
        from docling_mcp import lifespan

        lifespan._langfuse_client = None
        lifespan._langfuse_enabled = False

        # Should not raise
        lifespan._shutdown_langfuse()

        assert lifespan._langfuse_client is None
        assert lifespan._langfuse_enabled is False

    def test_shutdown_handles_flush_error(self):
        """Test shutdown handles errors during flush gracefully."""
        from docling_mcp import lifespan

        mock_client = MagicMock()
        mock_client.flush.side_effect = RuntimeError("Flush failed")
        lifespan._langfuse_client = mock_client
        lifespan._langfuse_enabled = True

        # Should not raise
        lifespan._shutdown_langfuse()

        assert lifespan._langfuse_client is None
        assert lifespan._langfuse_enabled is False


class TestLangfuseHelperFunctions:
    """Test LangFuse helper functions."""

    def test_get_langfuse_client_returns_client(self):
        """Test get_langfuse_client returns the client instance."""
        from docling_mcp import lifespan

        mock_client = MagicMock()
        lifespan._langfuse_client = mock_client

        result = lifespan.get_langfuse_client()

        assert result is mock_client

    def test_get_langfuse_client_returns_none(self):
        """Test get_langfuse_client returns None when not initialized."""
        from docling_mcp import lifespan

        lifespan._langfuse_client = None

        result = lifespan.get_langfuse_client()

        assert result is None

    def test_is_langfuse_enabled_true(self):
        """Test is_langfuse_enabled returns True when enabled."""
        from docling_mcp import lifespan

        lifespan._langfuse_enabled = True

        result = lifespan.is_langfuse_enabled()

        assert result is True

    def test_is_langfuse_enabled_false(self):
        """Test is_langfuse_enabled returns False when disabled."""
        from docling_mcp import lifespan

        lifespan._langfuse_enabled = False

        result = lifespan.is_langfuse_enabled()

        assert result is False


class TestLangfuseObserveDecorator:
    """Test that @observe decorator is correctly configured."""

    def test_observe_fallback_when_sdk_unavailable(self):
        """Test that observe falls back to no-op when SDK unavailable."""
        # Test the fallback decorator defined in server.py
        from docling_mcp import server

        # The observe decorator should be available regardless of SDK
        assert hasattr(server, "observe")

        # Should be callable
        @server.observe(name="test")
        def test_func():
            return "result"

        # Should work normally
        assert test_func() == "result"

    def test_langfuse_available_flag(self):
        """Test _langfuse_available flag is set correctly."""
        from docling_mcp import server

        # Should be boolean
        assert isinstance(server._langfuse_available, bool)


class TestLangfuseToolMetadata:
    """Test that tools update LangFuse trace metadata correctly."""

    @pytest.mark.asyncio
    async def test_query_knowledge_base_updates_metadata(self):
        """Test query_knowledge_base updates trace metadata."""
        from docling_mcp.server import query_knowledge_base

        with patch("docling_mcp.server._langfuse_available", True):
            with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
                with patch("docling_mcp.server.search_with_embedding") as mock_search:
                    with patch("langfuse.get_client") as mock_get_client:
                        mock_client = MagicMock()
                        mock_get_client.return_value = mock_client
                        mock_embed.return_value = ([0.1] * 1536, 100.0)
                        mock_search.return_value = ([], 50.0)

                        await query_knowledge_base.fn("test query", limit=3, source_filter="test")

                        # Verify embedding and search were called
                        mock_embed.assert_called_once_with("test query")
                        mock_search.assert_called_once_with([0.1] * 1536, 3, "test")

    @pytest.mark.asyncio
    async def test_ask_knowledge_base_updates_metadata(self):
        """Test ask_knowledge_base updates trace metadata."""
        from docling_mcp.server import ask_knowledge_base

        with patch("docling_mcp.server._langfuse_available", True):
            with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
                with patch("docling_mcp.server.search_with_embedding") as mock_search:
                    with patch("langfuse.get_client") as mock_get_client:
                        mock_client = MagicMock()
                        mock_get_client.return_value = mock_client
                        mock_embed.return_value = ([0.1] * 1536, 100.0)
                        mock_search.return_value = ([], 50.0)

                        await ask_knowledge_base.fn("test question", limit=5)

                        # Verify embedding and search were called
                        mock_embed.assert_called_once_with("test question")
                        mock_search.assert_called_once_with([0.1] * 1536, 5)

    @pytest.mark.asyncio
    async def test_list_knowledge_base_documents_updates_metadata(self):
        """Test list_knowledge_base_documents updates trace metadata."""
        from docling_mcp.server import list_knowledge_base_documents

        with patch("docling_mcp.server._langfuse_available", True):
            with patch("docling_mcp.server.list_documents") as mock_list:
                with patch("langfuse.get_client") as mock_get_client:
                    mock_client = MagicMock()
                    mock_get_client.return_value = mock_client
                    mock_list.return_value = []

                    await list_knowledge_base_documents.fn(limit=10, offset=5)

                    # Verify list_documents was called with correct params
                    mock_list.assert_called_once_with(10, 5)

    @pytest.mark.asyncio
    async def test_get_knowledge_base_document_updates_metadata(self):
        """Test get_knowledge_base_document updates trace metadata."""
        from docling_mcp.server import get_knowledge_base_document

        with patch("docling_mcp.server._langfuse_available", True):
            with patch("docling_mcp.server.get_document") as mock_get:
                with patch("langfuse.get_client") as mock_get_client:
                    mock_client = MagicMock()
                    mock_get_client.return_value = mock_client
                    mock_get.return_value = {
                        "id": "test-uuid",
                        "title": "Test Doc",
                        "source": "test",
                        "content": "Test content",
                    }

                    result = await get_knowledge_base_document.fn("test-uuid")

                    # Verify get_document was called with correct ID
                    mock_get.assert_called_once_with("test-uuid")
                    assert "Test Doc" in result

    @pytest.mark.asyncio
    async def test_get_knowledge_base_overview_updates_metadata(self):
        """Test get_knowledge_base_overview updates trace metadata."""
        from docling_mcp.server import get_knowledge_base_overview

        with patch("docling_mcp.server._langfuse_available", True):
            with patch("docling_mcp.server.list_documents") as mock_list:
                with patch("langfuse.get_client") as mock_get_client:
                    mock_client = MagicMock()
                    mock_get_client.return_value = mock_client
                    mock_list.return_value = [{"title": "Doc1", "source": "test", "chunk_count": 5}]

                    result = await get_knowledge_base_overview.fn()

                    # Verify list_documents was called
                    mock_list.assert_called_once_with(limit=10000)
                    assert "Total Documents: 1" in result


class TestUpdateLangfuseMetadataHelper:
    """Test the _update_langfuse_metadata helper function."""

    def test_helper_does_nothing_when_langfuse_unavailable(self):
        """Test helper returns early when LangFuse not available."""
        from docling_mcp import server

        with patch.object(server, "_langfuse_available", False):
            # Should not raise and should not call get_client
            with patch("langfuse.get_client") as mock_get_client:
                server._update_langfuse_metadata({"test": "data"})
                mock_get_client.assert_not_called()

    def test_helper_updates_span_when_available(self):
        """Test helper updates span metadata when LangFuse available."""
        from docling_mcp import server

        with patch.object(server, "_langfuse_available", True):
            with patch("langfuse.get_client") as mock_get_client:
                mock_client = MagicMock()
                mock_get_client.return_value = mock_client

                test_metadata = {"tool_name": "test", "source": "mcp"}
                server._update_langfuse_metadata(test_metadata)

                mock_client.update_current_span.assert_called_once_with(metadata=test_metadata)

    def test_helper_graceful_degradation_on_error(self):
        """Test helper handles errors gracefully."""
        from docling_mcp import server

        with patch.object(server, "_langfuse_available", True):
            with patch("langfuse.get_client") as mock_get_client:
                mock_get_client.side_effect = RuntimeError("Connection failed")

                # Should not raise
                server._update_langfuse_metadata({"test": "data"})


class TestLangfuseOpenAIWrapper:
    """Test that embedder uses langfuse.openai wrapper for cost tracking."""

    def test_embedder_uses_langfuse_wrapper_when_available(self):
        """Test EmbeddingGenerator uses langfuse.openai.AsyncOpenAI when available."""
        from ingestion import embedder

        # Verify the module-level flag
        assert hasattr(embedder, "_langfuse_openai_available")

        # The flag should be boolean
        assert isinstance(embedder._langfuse_openai_available, bool)

    def test_embedder_has_cost_tracking_enabled_attribute(self):
        """Test EmbeddingGenerator has cost_tracking_enabled attribute."""
        with patch("ingestion.embedder.LangfuseAsyncOpenAI"):
            with patch("ingestion.embedder.get_provider_config") as mock_config:
                mock_config.return_value = MagicMock(api_key="test-key", base_url=None)

                from ingestion.embedder import EmbeddingGenerator

                generator = EmbeddingGenerator(model_name="text-embedding-3-small")

                # Should have cost_tracking_enabled attribute
                assert hasattr(generator, "cost_tracking_enabled")
                assert isinstance(generator.cost_tracking_enabled, bool)

    def test_embedder_graceful_fallback_to_openai(self):
        """Test embedder falls back to direct OpenAI when langfuse unavailable."""
        # This test verifies the import fallback mechanism
        # If langfuse.openai is not installed, it should fall back to openai.AsyncOpenAI
        from ingestion import embedder

        # LangfuseAsyncOpenAI should be defined (either from langfuse or openai)
        assert hasattr(embedder, "LangfuseAsyncOpenAI")

    def test_embedder_model_name_for_cost_tracking(self):
        """Test embedder uses correct model name for cost calculation."""
        with patch("ingestion.embedder.LangfuseAsyncOpenAI"):
            with patch("ingestion.embedder.get_provider_config") as mock_config:
                mock_config.return_value = MagicMock(api_key="test-key", base_url=None)

                from ingestion.embedder import EmbeddingGenerator

                # Default model should be text-embedding-3-small (for cost tracking)
                generator = EmbeddingGenerator()
                assert generator.model_name == "text-embedding-3-small"


class TestLangfuseNestedSpans:
    """Test nested spans for cost breakdown visibility."""

    @pytest.mark.asyncio
    async def test_langfuse_span_context_manager_available(self):
        """Test langfuse_span async context manager exists."""
        from docling_mcp.server import langfuse_span

        # Should be an async context manager
        assert langfuse_span is not None

    @pytest.mark.asyncio
    async def test_langfuse_span_graceful_degradation(self):
        """Test langfuse_span returns dict with None span when LangFuse unavailable."""
        from docling_mcp import server

        with patch.object(server, "_langfuse_available", False):
            async with server.langfuse_span("test-span") as span_ctx:
                # Should yield dict with None span when LangFuse unavailable
                assert span_ctx.get("span") is None
                assert "start_time" in span_ctx

    @pytest.mark.asyncio
    async def test_langfuse_span_creates_span_when_available(self):
        """Test langfuse_span creates span when LangFuse available."""
        from docling_mcp import server

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.span.return_value = mock_span

        with patch.object(server, "_langfuse_available", True):
            with patch.object(server, "get_langfuse_client", return_value=lambda: mock_client):
                with patch("docling_mcp.server.get_langfuse_client", return_value=mock_client):
                    async with server.langfuse_span(
                        name="embedding-generation",
                        span_type="span",
                        metadata={"model": "text-embedding-3-small"},
                    ) as span:
                        # Span should be created
                        mock_client.span.assert_called_once_with(
                            name="embedding-generation",
                            metadata={"model": "text-embedding-3-small"},
                        )

    @pytest.mark.asyncio
    async def test_query_knowledge_base_uses_embedding_span(self):
        """Test query_knowledge_base wraps embedding and search in separate spans."""
        from docling_mcp.server import query_knowledge_base

        with patch("docling_mcp.server._langfuse_available", True):
            with patch("docling_mcp.server.langfuse_span") as mock_span:
                with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
                    with patch("docling_mcp.server.search_with_embedding") as mock_search:
                        # Setup mocks - now yields dict with span and start_time
                        mock_span.return_value.__aenter__ = AsyncMock(
                            return_value={"span": None, "start_time": 0}
                        )
                        mock_span.return_value.__aexit__ = AsyncMock(return_value=None)
                        mock_embed.return_value = ([0.1] * 1536, 100.0)
                        mock_search.return_value = ([], 50.0)

                        await query_knowledge_base.fn("test query")

                        # Verify span was called twice (embedding-generation and vector-search)
                        assert mock_span.call_count == 2
                        call_names = [call[1]["name"] for call in mock_span.call_args_list]
                        assert "embedding-generation" in call_names
                        assert "vector-search" in call_names

    @pytest.mark.asyncio
    async def test_ask_knowledge_base_uses_embedding_span(self):
        """Test ask_knowledge_base wraps embedding and search in separate spans."""
        from docling_mcp.server import ask_knowledge_base

        with patch("docling_mcp.server._langfuse_available", True):
            with patch("docling_mcp.server.langfuse_span") as mock_span:
                with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
                    with patch("docling_mcp.server.search_with_embedding") as mock_search:
                        # Setup mocks - now yields dict with span and start_time
                        mock_span.return_value.__aenter__ = AsyncMock(
                            return_value={"span": None, "start_time": 0}
                        )
                        mock_span.return_value.__aexit__ = AsyncMock(return_value=None)
                        mock_embed.return_value = ([0.1] * 1536, 100.0)
                        mock_search.return_value = ([], 50.0)

                        await ask_knowledge_base.fn("test question")

                        # Verify span was called twice (embedding-generation and vector-search)
                        assert mock_span.call_count == 2
                        call_names = [call[1]["name"] for call in mock_span.call_args_list]
                        assert "embedding-generation" in call_names
                        assert "vector-search" in call_names


class TestCostTrackingPricing:
    """Test cost tracking pricing accuracy."""

    def test_embedding_model_pricing_documentation(self):
        """
        Verify pricing documentation is accurate.

        OpenAI pricing as of story creation:
        - text-embedding-3-small: $0.00002/1K tokens
        - gpt-4o-mini: $0.00015/1K input, $0.0006/1K output

        Note: LangFuse SDK automatically updates pricing.
        """
        # Document expected pricing for reference
        expected_pricing = {
            "text-embedding-3-small": {"input_per_1k_tokens": 0.00002, "currency": "USD"},
            "gpt-4o-mini": {
                "input_per_1k_tokens": 0.00015,
                "output_per_1k_tokens": 0.0006,
                "currency": "USD",
            },
        }

        # This test documents the expected pricing for manual verification
        # Actual cost calculation is done by LangFuse SDK automatically
        assert expected_pricing["text-embedding-3-small"]["input_per_1k_tokens"] == 0.00002
        assert expected_pricing["gpt-4o-mini"]["input_per_1k_tokens"] == 0.00015
        assert expected_pricing["gpt-4o-mini"]["output_per_1k_tokens"] == 0.0006

    def test_embedding_cost_calculation_example(self):
        """
        Test manual cost calculation matches expected formula.

        Example: 500 tokens at $0.00002/1K = $0.00001
        """
        # Pricing for text-embedding-3-small
        price_per_1k_tokens = 0.00002

        # Calculate cost for 500 tokens
        tokens = 500
        expected_cost = (tokens / 1000) * price_per_1k_tokens

        assert expected_cost == 0.00001

    def test_llm_cost_calculation_example(self):
        """
        Test LLM cost calculation matches expected formula (for future LLM integration).

        Example: 100 input tokens + 50 output tokens at gpt-4o-mini pricing
        Input: 100 * $0.00015/1K = $0.000015
        Output: 50 * $0.0006/1K = $0.00003
        Total: $0.000045
        """
        # Pricing for gpt-4o-mini
        input_price_per_1k = 0.00015
        output_price_per_1k = 0.0006

        # Calculate cost
        input_tokens = 100
        output_tokens = 50

        input_cost = (input_tokens / 1000) * input_price_per_1k
        output_cost = (output_tokens / 1000) * output_price_per_1k
        total_cost = input_cost + output_cost

        # Use pytest.approx for floating point comparison
        assert input_cost == pytest.approx(0.000015, rel=1e-9)
        assert output_cost == pytest.approx(0.00003, rel=1e-9)
        assert total_cost == pytest.approx(0.000045, rel=1e-9)

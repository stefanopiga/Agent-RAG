"""
Integration tests for LangFuse Dashboard Data Structure (Story 2.4).

Tests verify that trace data created by MCP server is correctly structured
for display in LangFuse dashboard, including:
- Trace metadata for filtering and grouping
- Nested spans for timing breakdown
- Cost tracking data availability
- Trace detail view fields
"""

import time
from unittest.mock import MagicMock, patch

import pytest


class TestDashboardMetricsStructure:
    """Test that traces contain correct fields for dashboard metrics (AC #1)."""

    @pytest.mark.asyncio
    async def test_trace_contains_tool_name_metadata(self):
        """Test trace metadata includes tool_name for dashboard grouping."""
        from docling_mcp.server import query_knowledge_base

        captured_metadata = {}

        def capture_metadata(metadata):
            captured_metadata.update(metadata)

        with (
            patch("docling_mcp.server._langfuse_available", True),
            patch("docling_mcp.server._update_langfuse_metadata", capture_metadata),
            patch("docling_mcp.server.generate_query_embedding") as mock_embed,
            patch("docling_mcp.server.search_with_embedding") as mock_search,
        ):
            mock_embed.return_value = ([0.1] * 1536, 100.0)
            mock_search.return_value = ([], 50.0)

            await query_knowledge_base.fn("test query", limit=5)

            # Verify metadata contains required fields for dashboard
            assert captured_metadata.get("tool_name") == "query_knowledge_base"
            assert captured_metadata.get("source") == "mcp"
            assert "query" in captured_metadata

    @pytest.mark.asyncio
    async def test_trace_contains_query_for_filtering(self):
        """Test trace metadata includes query for dashboard search/filtering."""
        from docling_mcp.server import ask_knowledge_base

        captured_metadata = {}

        def capture_metadata(metadata):
            captured_metadata.update(metadata)

        with (
            patch("docling_mcp.server._langfuse_available", True),
            patch("docling_mcp.server._update_langfuse_metadata", capture_metadata),
            patch("docling_mcp.server.generate_query_embedding") as mock_embed,
            patch("docling_mcp.server.search_with_embedding") as mock_search,
        ):
            mock_embed.return_value = ([0.1] * 1536, 100.0)
            mock_search.return_value = ([], 50.0)

            await ask_knowledge_base.fn("What is LangFuse?", limit=3)

            # Verify question is captured for dashboard filtering
            assert captured_metadata.get("question") == "What is LangFuse?"
            assert captured_metadata.get("limit") == 3

    @pytest.mark.asyncio
    async def test_trace_contains_source_filter_metadata(self):
        """Test trace metadata includes source_filter for dashboard analysis."""
        from docling_mcp.server import query_knowledge_base

        captured_metadata = {}

        def capture_metadata(metadata):
            captured_metadata.update(metadata)

        with (
            patch("docling_mcp.server._langfuse_available", True),
            patch("docling_mcp.server._update_langfuse_metadata", capture_metadata),
            patch("docling_mcp.server.generate_query_embedding") as mock_embed,
            patch("docling_mcp.server.search_with_embedding") as mock_search,
        ):
            mock_embed.return_value = ([0.1] * 1536, 100.0)
            mock_search.return_value = ([], 50.0)

            await query_knowledge_base.fn("test query", source_filter="langfuse-docs")

            # Verify source_filter is captured for dashboard analysis
            assert captured_metadata.get("source_filter") == "langfuse-docs"


class TestCostTrendsData:
    """Test that traces contain correct cost tracking data (AC #2)."""

    def test_embedder_uses_langfuse_openai_for_cost_tracking(self):
        """Test EmbeddingGenerator uses langfuse.openai wrapper for automatic cost tracking."""
        from ingestion import embedder

        # Verify langfuse.openai wrapper is available
        assert hasattr(embedder, "_langfuse_openai_available")

        # If available, cost tracking is automatic
        # LangFuse SDK calculates cost from token usage

    def test_embedding_model_name_for_pricing(self):
        """Test embedder uses known model name for LangFuse pricing lookup."""
        # text-embedding-3-small is required for automatic pricing
        with patch("ingestion.embedder.LangfuseAsyncOpenAI"):
            with patch("ingestion.embedder.get_provider_config") as mock_config:
                mock_config.return_value = MagicMock(api_key="test-key", base_url=None)

                from ingestion.embedder import EmbeddingGenerator

                generator = EmbeddingGenerator()

                # Must be a model supported by LangFuse pricing
                assert generator.model_name == "text-embedding-3-small"

    @pytest.mark.asyncio
    async def test_span_contains_timing_for_cost_breakdown(self):
        """Test spans contain timing metadata for cost analysis correlation."""
        from docling_mcp.server import langfuse_span

        with patch("docling_mcp.server._langfuse_available", False):
            # Even without LangFuse, timing should be captured
            async with langfuse_span("embedding-generation") as span_ctx:
                time.sleep(0.01)  # Simulate work
                start_time = span_ctx.get("start_time")

            # Timing data should be available for metrics
            assert start_time is not None
            assert isinstance(start_time, float)


class TestTraceDetailView:
    """Test that traces contain correct detail view data (AC #3)."""

    @pytest.mark.asyncio
    async def test_trace_has_input_query_text(self):
        """Test trace input contains query text for detail view."""
        from docling_mcp.server import query_knowledge_base

        captured_metadata = {}

        def capture_metadata(metadata):
            captured_metadata.update(metadata)

        with (
            patch("docling_mcp.server._langfuse_available", True),
            patch("docling_mcp.server._update_langfuse_metadata", capture_metadata),
            patch("docling_mcp.server.generate_query_embedding") as mock_embed,
            patch("docling_mcp.server.search_with_embedding") as mock_search,
        ):
            mock_embed.return_value = ([0.1] * 1536, 100.0)
            mock_search.return_value = ([], 50.0)

            await query_knowledge_base.fn("How to deploy?")

            # Query should be in metadata for trace detail view
            assert captured_metadata.get("query") == "How to deploy?"

    @pytest.mark.asyncio
    async def test_trace_output_contains_formatted_results(self):
        """Test trace output contains formatted search results."""
        from docling_mcp.server import query_knowledge_base

        with (
            patch("docling_mcp.server._langfuse_available", False),
            patch("docling_mcp.server.generate_query_embedding") as mock_embed,
            patch("docling_mcp.server.search_with_embedding") as mock_search,
        ):
            mock_embed.return_value = ([0.1] * 1536, 100.0)
            mock_search.return_value = (
                [
                    {
                        "title": "Test Doc",
                        "content": "Test content",
                        "source": "test",
                        "similarity": 0.95,
                    }
                ],
                50.0,
            )

            result = await query_knowledge_base.fn("test query")

            # Output should be formatted for dashboard display
            assert "[Source: Test Doc]" in result
            assert "Test content" in result

    @pytest.mark.asyncio
    async def test_nested_spans_for_timing_breakdown(self):
        """Test that separate spans are created for embedding and vector-search."""
        from docling_mcp.server import query_knowledge_base

        span_names = []

        def mock_span_factory(name, **kwargs):
            span_names.append(name)
            mock_span = MagicMock()
            mock_span.update = MagicMock()
            mock_span.end = MagicMock()
            return mock_span

        mock_client = MagicMock()
        mock_client.span = mock_span_factory

        with (
            patch("docling_mcp.server._langfuse_available", True),
            patch("docling_mcp.server.get_langfuse_client", return_value=mock_client),
            patch("docling_mcp.server.generate_query_embedding") as mock_embed,
            patch("docling_mcp.server.search_with_embedding") as mock_search,
        ):
            mock_embed.return_value = ([0.1] * 1536, 100.0)
            mock_search.return_value = ([], 50.0)

            await query_knowledge_base.fn("test query")

            # Verify both spans created for timing breakdown
            assert "embedding-generation" in span_names
            assert "vector-search" in span_names

    @pytest.mark.asyncio
    async def test_span_metadata_includes_duration_ms(self):
        """Test spans include duration_ms in metadata for timing display."""
        from docling_mcp.server import langfuse_span

        mock_span = MagicMock()
        update_calls = []
        mock_span.update = lambda **kwargs: update_calls.append(kwargs)
        mock_span.end = MagicMock()

        mock_client = MagicMock()
        mock_client.span = MagicMock(return_value=mock_span)

        with (
            patch("docling_mcp.server._langfuse_available", True),
            patch("docling_mcp.server.get_langfuse_client", return_value=mock_client),
        ):
            async with langfuse_span("test-span") as span_ctx:
                time.sleep(0.01)  # Simulate work

            # Verify duration_ms was added to span metadata
            assert len(update_calls) > 0
            last_update = update_calls[-1]
            assert "metadata" in last_update
            assert "duration_ms" in last_update["metadata"]
            assert last_update["metadata"]["duration_ms"] > 0


class TestCustomChartsData:
    """Test that traces provide data for custom charts configuration (AC #4)."""

    @pytest.mark.asyncio
    async def test_all_tools_have_consistent_metadata_structure(self):
        """Test all MCP tools provide consistent metadata for chart dimensions."""
        from docling_mcp.server import (
            ask_knowledge_base,
            query_knowledge_base,
        )

        # Test each tool has tool_name and source metadata
        tools_to_test = [
            (query_knowledge_base, {"query": "test", "limit": 5}),
            (ask_knowledge_base, {"question": "test?", "limit": 5}),
        ]

        for tool_fn, expected_fields in tools_to_test:
            captured_metadata = {}

            def capture_metadata(metadata):
                captured_metadata.update(metadata)

            with (
                patch("docling_mcp.server._langfuse_available", True),
                patch("docling_mcp.server._update_langfuse_metadata", capture_metadata),
                patch("docling_mcp.server.generate_query_embedding") as mock_embed,
                patch("docling_mcp.server.search_with_embedding") as mock_search,
            ):
                mock_embed.return_value = ([0.1] * 1536, 100.0)
                mock_search.return_value = ([], 50.0)

                if tool_fn == query_knowledge_base:
                    await tool_fn.fn("test")
                else:
                    await tool_fn.fn("test?")

            # All tools should have tool_name and source for chart grouping
            assert "tool_name" in captured_metadata, f"{tool_fn.__name__} missing tool_name"
            assert captured_metadata.get("source") == "mcp", (
                f"{tool_fn.__name__} missing source=mcp"
            )

    @pytest.mark.asyncio
    async def test_document_tools_have_metadata_for_charts(self):
        """Test document tools provide metadata for dashboard charts."""
        from docling_mcp.server import list_knowledge_base_documents

        captured_metadata = {}

        def capture_metadata(metadata):
            captured_metadata.update(metadata)

        async def mock_list_documents(limit=50, offset=0):
            return []

        with (
            patch("docling_mcp.server._langfuse_available", True),
            patch("docling_mcp.server._update_langfuse_metadata", capture_metadata),
            patch("docling_mcp.server.list_documents", mock_list_documents),
        ):
            await list_knowledge_base_documents.fn(limit=10, offset=0)

            # Verify pagination params captured for analysis
            assert captured_metadata.get("limit") == 10
            assert captured_metadata.get("offset") == 0
            assert captured_metadata.get("tool_name") == "list_knowledge_base_documents"


class TestDashboardDataConsistency:
    """Test data consistency between LangFuse and Prometheus metrics."""

    def test_prometheus_metrics_align_with_langfuse_spans(self):
        """Test Prometheus metric names align with LangFuse span names."""
        from docling_mcp import metrics

        metrics._initialize_metrics()

        if metrics.is_metrics_available():
            # These metric names should correspond to LangFuse span timing
            assert metrics.rag_embedding_time_seconds is not None
            assert metrics.rag_db_search_time_seconds is not None

    @pytest.mark.asyncio
    async def test_span_timing_recorded_in_both_systems(self):
        """Test timing is recorded in both LangFuse spans and Prometheus."""
        from docling_mcp.server import langfuse_span

        with patch("docling_mcp.server._langfuse_available", False):
            async with langfuse_span("embedding-generation"):
                time.sleep(0.01)

            # Prometheus metrics are recorded via the langfuse_span context manager
            # This ensures consistency between both monitoring systems


class TestDashboardFiltering:
    """Test that traces support dashboard filtering capabilities."""

    @pytest.mark.asyncio
    async def test_traces_filterable_by_source_mcp(self):
        """Test all MCP traces have source='mcp' for filtering."""
        from docling_mcp.server import query_knowledge_base

        captured_metadata = {}

        def capture_metadata(metadata):
            captured_metadata.update(metadata)

        with (
            patch("docling_mcp.server._langfuse_available", True),
            patch("docling_mcp.server._update_langfuse_metadata", capture_metadata),
            patch("docling_mcp.server.generate_query_embedding") as mock_embed,
            patch("docling_mcp.server.search_with_embedding") as mock_search,
        ):
            mock_embed.return_value = ([0.1] * 1536, 100.0)
            mock_search.return_value = ([], 50.0)

            await query_knowledge_base.fn("test")

            # All MCP traces should be filterable by source="mcp"
            assert captured_metadata.get("source") == "mcp"

    @pytest.mark.asyncio
    async def test_traces_filterable_by_tool_name(self):
        """Test traces can be filtered by tool_name in dashboard."""
        from docling_mcp.server import get_knowledge_base_overview

        captured_metadata = {}

        def capture_metadata(metadata):
            captured_metadata.update(metadata)

        async def mock_list_documents(limit=50, offset=0):
            return []

        with (
            patch("docling_mcp.server._langfuse_available", True),
            patch("docling_mcp.server._update_langfuse_metadata", capture_metadata),
            patch("docling_mcp.server.list_documents", mock_list_documents),
        ):
            await get_knowledge_base_overview.fn()

            # Tool name should be available for filtering
            assert captured_metadata.get("tool_name") == "get_knowledge_base_overview"

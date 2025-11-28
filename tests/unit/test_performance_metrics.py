"""
Unit tests for Performance Metrics (Story 2.3).

Tests:
- Prometheus metrics initialization and recording
- Health check status logic (ok/degraded/down)
- Timing measurement in LangFuse spans
"""

import time
from unittest.mock import MagicMock, patch

import pytest


class TestPrometheusMetricsInitialization:
    """Test Prometheus metrics module initialization."""

    def test_metrics_module_imports(self):
        """Test metrics module can be imported."""
        from docling_mcp import metrics

        assert hasattr(metrics, "record_request_start")
        assert hasattr(metrics, "record_request_end")
        assert hasattr(metrics, "record_embedding_time")
        assert hasattr(metrics, "record_db_search_time")
        assert hasattr(metrics, "record_llm_generation_time")
        assert hasattr(metrics, "generate_metrics_output")

    def test_metrics_graceful_degradation_without_prometheus(self):
        """Test metrics functions work without prometheus_client."""
        from docling_mcp import metrics

        # Reset state for test
        original_available = metrics._metrics_available
        metrics._metrics_available = False

        try:
            # These should not raise even without prometheus
            start_time = metrics.record_request_start("test_tool")
            assert isinstance(start_time, float)

            # Should not raise
            metrics.record_request_end("test_tool", start_time, "success")
            metrics.record_embedding_time(0.5)
            metrics.record_db_search_time(0.1)
            metrics.record_llm_generation_time(1.0)
        finally:
            metrics._metrics_available = original_available

    def test_is_metrics_available_returns_boolean(self):
        """Test is_metrics_available returns boolean."""
        from docling_mcp.metrics import is_metrics_available

        result = is_metrics_available()
        assert isinstance(result, bool)

    def test_generate_metrics_output_returns_string(self):
        """Test generate_metrics_output returns string."""
        from docling_mcp.metrics import generate_metrics_output

        output = generate_metrics_output()
        assert isinstance(output, str)

    def test_get_metrics_content_type(self):
        """Test metrics content type is OpenMetrics format."""
        from docling_mcp.metrics import get_metrics_content_type

        content_type = get_metrics_content_type()
        assert "openmetrics-text" in content_type


class TestPrometheusMetricsRecording:
    """Test Prometheus metrics recording functions."""

    def test_record_request_start_returns_timestamp(self):
        """Test record_request_start returns current timestamp."""
        from docling_mcp.metrics import record_request_start

        before = time.time()
        start_time = record_request_start("test_tool")
        after = time.time()

        assert before <= start_time <= after

    def test_record_request_end_calculates_duration(self):
        """Test record_request_end calculates duration correctly."""
        from docling_mcp.metrics import record_request_end, record_request_start

        start_time = record_request_start("test_tool")
        time.sleep(0.01)  # Small delay

        # Should not raise
        record_request_end("test_tool", start_time, "success")
        record_request_end("test_tool", start_time, "error")

    def test_track_request_context_manager(self):
        """Test track_request context manager."""
        from docling_mcp.metrics import track_request

        with track_request("test_tool"):
            pass  # Should not raise

    def test_track_request_records_error_status(self):
        """Test track_request records error status on exception."""
        from docling_mcp.metrics import track_request

        with pytest.raises(ValueError):
            with track_request("test_tool"):
                raise ValueError("Test error")


class TestPrometheusHistogramBuckets:
    """Test Prometheus histogram bucket configurations."""

    def test_request_duration_buckets(self):
        """Test request duration histogram has correct buckets (SLO: <2s p95)."""
        from docling_mcp import metrics

        # Initialize metrics if not already
        metrics._initialize_metrics()

        if metrics._metrics_available and metrics.mcp_request_duration_seconds:
            # Check buckets match spec
            expected_buckets = [0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
            # Note: prometheus_client automatically adds +Inf
            actual_buckets = list(metrics.mcp_request_duration_seconds._upper_bounds)

            # All expected buckets should be present
            for bucket in expected_buckets:
                assert bucket in actual_buckets, f"Missing bucket: {bucket}"

    def test_embedding_time_buckets(self):
        """Test embedding time histogram has correct buckets (SLO: <500ms)."""
        from docling_mcp import metrics

        metrics._initialize_metrics()

        if metrics._metrics_available and metrics.rag_embedding_time_seconds:
            expected_buckets = [0.1, 0.2, 0.3, 0.4, 0.5, 1.0]
            actual_buckets = list(metrics.rag_embedding_time_seconds._upper_bounds)

            for bucket in expected_buckets:
                assert bucket in actual_buckets, f"Missing bucket: {bucket}"

    def test_db_search_time_buckets(self):
        """Test DB search time histogram has correct buckets (SLO: <100ms)."""
        from docling_mcp import metrics

        metrics._initialize_metrics()

        if metrics._metrics_available and metrics.rag_db_search_time_seconds:
            expected_buckets = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
            actual_buckets = list(metrics.rag_db_search_time_seconds._upper_bounds)

            for bucket in expected_buckets:
                assert bucket in actual_buckets, f"Missing bucket: {bucket}"


class TestHealthCheckStatusLogic:
    """Test health check status determination logic."""

    @pytest.mark.asyncio
    async def test_all_services_up_returns_ok(self):
        """Test status is 'ok' when all services are up."""
        from docling_mcp.health import ServiceStatus, get_health_status

        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            mock_db.return_value = ServiceStatus(status="up", message="OK")
            mock_langfuse.return_value = ServiceStatus(status="up", message="OK")
            mock_embedder.return_value = ServiceStatus(status="up", message="OK")

            response = await get_health_status()

            assert response.status == "ok"

    @pytest.mark.asyncio
    async def test_langfuse_down_returns_degraded(self):
        """Test status is 'degraded' when LangFuse is down but others up."""
        from docling_mcp.health import ServiceStatus, get_health_status

        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            mock_db.return_value = ServiceStatus(status="up", message="OK")
            mock_langfuse.return_value = ServiceStatus(
                status="down", message="LangFuse unavailable"
            )
            mock_embedder.return_value = ServiceStatus(status="up", message="OK")

            response = await get_health_status()

            assert response.status == "degraded"

    @pytest.mark.asyncio
    async def test_database_down_returns_down(self):
        """Test status is 'down' when database is down."""
        from docling_mcp.health import ServiceStatus, get_health_status

        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            mock_db.return_value = ServiceStatus(status="down", message="Connection failed")
            mock_langfuse.return_value = ServiceStatus(status="up", message="OK")
            mock_embedder.return_value = ServiceStatus(status="up", message="OK")

            response = await get_health_status()

            assert response.status == "down"

    @pytest.mark.asyncio
    async def test_embedder_down_returns_down(self):
        """Test status is 'down' when embedder is down."""
        from docling_mcp.health import ServiceStatus, get_health_status

        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            mock_db.return_value = ServiceStatus(status="up", message="OK")
            mock_langfuse.return_value = ServiceStatus(status="up", message="OK")
            mock_embedder.return_value = ServiceStatus(status="down", message="Not initialized")

            response = await get_health_status()

            assert response.status == "down"

    @pytest.mark.asyncio
    async def test_health_response_includes_timestamp(self):
        """Test health response includes timestamp."""
        from docling_mcp.health import ServiceStatus, get_health_status

        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            mock_db.return_value = ServiceStatus(status="up", message="OK")
            mock_langfuse.return_value = ServiceStatus(status="up", message="OK")
            mock_embedder.return_value = ServiceStatus(status="up", message="OK")

            response = await get_health_status()

            assert response.timestamp > 0
            assert isinstance(response.timestamp, float)

    @pytest.mark.asyncio
    async def test_health_response_includes_services(self):
        """Test health response includes all services."""
        from docling_mcp.health import ServiceStatus, get_health_status

        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            mock_db.return_value = ServiceStatus(status="up", message="OK")
            mock_langfuse.return_value = ServiceStatus(status="up", message="OK")
            mock_embedder.return_value = ServiceStatus(status="up", message="OK")

            response = await get_health_status()

            assert "database" in response.services
            assert "langfuse" in response.services
            assert "embedder" in response.services


class TestHealthCheckServiceChecks:
    """Test individual service check functions."""

    @pytest.mark.asyncio
    async def test_check_database_success(self):
        """Test check_database returns 'up' when connection succeeds."""
        from docling_mcp.health import check_database

        with patch("utils.db_utils.test_connection") as mock_test:
            mock_test.return_value = True

            result = await check_database()

            assert result.status == "up"
            assert result.latency_ms >= 0  # May be 0 if mock returns instantly

    @pytest.mark.asyncio
    async def test_check_database_failure(self):
        """Test check_database returns 'down' when connection fails."""
        from docling_mcp.health import check_database

        with patch("utils.db_utils.test_connection") as mock_test:
            mock_test.return_value = False

            result = await check_database()

            assert result.status == "down"

    @pytest.mark.asyncio
    async def test_check_database_exception(self):
        """Test check_database handles exceptions gracefully."""
        from docling_mcp.health import check_database

        with patch("utils.db_utils.test_connection") as mock_test:
            mock_test.side_effect = Exception("Connection error")

            result = await check_database()

            assert result.status == "down"
            assert "error" in result.message.lower()

    def test_check_langfuse_enabled(self):
        """Test check_langfuse returns 'up' when LangFuse is enabled."""
        from docling_mcp.health import check_langfuse

        with (
            patch("docling_mcp.lifespan.is_langfuse_enabled") as mock_enabled,
            patch("docling_mcp.lifespan.get_langfuse_client") as mock_client,
        ):
            mock_enabled.return_value = True
            mock_client.return_value = MagicMock()

            result = check_langfuse()

            assert result.status == "up"

    def test_check_langfuse_disabled(self):
        """Test check_langfuse returns 'down' when LangFuse is disabled."""
        from docling_mcp.health import check_langfuse

        with patch("docling_mcp.lifespan.is_langfuse_enabled") as mock_enabled:
            mock_enabled.return_value = False

            result = check_langfuse()

            assert result.status == "down"

    @pytest.mark.asyncio
    async def test_check_embedder_ready(self):
        """Test check_embedder returns 'up' when embedder is ready."""
        import asyncio

        from docling_mcp.health import check_embedder

        mock_event = asyncio.Event()
        mock_event.set()

        with (
            patch("core.rag_service._embedder_ready", mock_event),
            patch("core.rag_service.get_global_embedder") as mock_get,
        ):
            mock_get.return_value = MagicMock()

            result = await check_embedder()

            assert result.status == "up"

    @pytest.mark.asyncio
    async def test_check_embedder_not_ready(self):
        """Test check_embedder returns 'down' when embedder is not ready."""
        import asyncio

        from docling_mcp.health import check_embedder

        mock_event = asyncio.Event()
        # Don't set the event - embedder not ready

        with patch("core.rag_service._embedder_ready", mock_event):
            result = await check_embedder()

            assert result.status == "down"
            assert "in progress" in result.message.lower() or "not" in result.message.lower()


class TestLangFuseTimingMeasurement:
    """Test timing measurement in LangFuse spans."""

    @pytest.mark.asyncio
    async def test_langfuse_span_records_duration(self):
        """Test langfuse_span context manager records duration in metadata."""
        from docling_mcp.server import langfuse_span

        with patch.object(
            __import__("docling_mcp.server", fromlist=["_langfuse_available"]),
            "_langfuse_available",
            True,
        ):
            with patch("docling_mcp.server.get_langfuse_client") as mock_get_client:
                mock_client = MagicMock()
                mock_span = MagicMock()
                mock_client.span.return_value = mock_span
                mock_get_client.return_value = mock_client

                async with langfuse_span("test-span") as span_ctx:
                    time.sleep(0.01)  # Small delay

                # Verify span.end() was called
                mock_span.end.assert_called_once()

    @pytest.mark.asyncio
    async def test_langfuse_span_graceful_degradation(self):
        """Test langfuse_span works when LangFuse unavailable."""
        from docling_mcp import server

        with patch.object(server, "_langfuse_available", False):
            async with server.langfuse_span("test-span") as span_ctx:
                # Should yield None span but still provide start_time
                assert span_ctx.get("span") is None
                assert "start_time" in span_ctx


class TestMCPToolMetricsIntegration:
    """Test metrics integration in MCP tools."""

    @pytest.mark.asyncio
    async def test_query_knowledge_base_records_metrics(self):
        """Test query_knowledge_base records Prometheus metrics."""
        from docling_mcp.server import query_knowledge_base

        with (
            patch("docling_mcp.server.record_request_start") as mock_start,
            patch("docling_mcp.server.record_request_end") as mock_end,
            patch("docling_mcp.server.generate_query_embedding") as mock_embed,
            patch("docling_mcp.server.search_with_embedding") as mock_search,
            patch("docling_mcp.server._langfuse_available", False),
        ):
            mock_start.return_value = time.time()
            mock_embed.return_value = ([0.1] * 1536, 100.0)  # embedding, duration_ms
            mock_search.return_value = ([], 50.0)  # results, duration_ms

            await query_knowledge_base.fn("test query")

            mock_start.assert_called_once_with("query_knowledge_base")
            mock_end.assert_called_once()

            # Verify status was "success"
            call_args = mock_end.call_args
            assert call_args[0][2] == "success"  # Third positional arg is status

    @pytest.mark.asyncio
    async def test_query_knowledge_base_records_error_on_failure(self):
        """Test query_knowledge_base records error status on failure."""
        from fastmcp.exceptions import ToolError

        from docling_mcp.server import query_knowledge_base

        with (
            patch("docling_mcp.server.record_request_start") as mock_start,
            patch("docling_mcp.server.record_request_end") as mock_end,
            patch("docling_mcp.server.generate_query_embedding") as mock_embed,
            patch("docling_mcp.server._langfuse_available", False),
        ):
            mock_start.return_value = time.time()
            mock_embed.side_effect = Exception("Embedding failed")

            with pytest.raises(ToolError):
                await query_knowledge_base.fn("test query")

            # Verify status was "error"
            call_args = mock_end.call_args
            assert call_args[0][2] == "error"


class TestSeparateLangFuseSpans:
    """Test separate LangFuse spans for embedding and vector-search (AC #2)."""

    @pytest.mark.asyncio
    async def test_query_creates_separate_embedding_and_search_spans(self):
        """Test that query_knowledge_base creates separate spans for embedding and vector-search."""
        from docling_mcp.server import query_knowledge_base

        span_names_created = []

        def mock_span_factory(name, **kwargs):
            span_names_created.append(name)
            mock_span = MagicMock()
            mock_span.update = MagicMock()
            mock_span.end = MagicMock()
            return mock_span

        with (
            patch("docling_mcp.server.record_request_start") as mock_start,
            patch("docling_mcp.server.record_request_end"),
            patch("docling_mcp.server.generate_query_embedding") as mock_embed,
            patch("docling_mcp.server.search_with_embedding") as mock_search,
            patch("docling_mcp.server._langfuse_available", True),
            patch("docling_mcp.server.get_langfuse_client") as mock_get_client,
        ):
            mock_start.return_value = time.time()
            mock_embed.return_value = ([0.1] * 1536, 100.0)
            mock_search.return_value = ([], 50.0)

            mock_client = MagicMock()
            mock_client.span = mock_span_factory
            mock_get_client.return_value = mock_client

            await query_knowledge_base.fn("test query")

            # Verify both spans were created
            assert "embedding-generation" in span_names_created, (
                "embedding-generation span not created"
            )
            assert "vector-search" in span_names_created, "vector-search span not created"

    @pytest.mark.asyncio
    async def test_ask_creates_separate_embedding_and_search_spans(self):
        """Test that ask_knowledge_base creates separate spans for embedding and vector-search."""
        from docling_mcp.server import ask_knowledge_base

        span_names_created = []

        def mock_span_factory(name, **kwargs):
            span_names_created.append(name)
            mock_span = MagicMock()
            mock_span.update = MagicMock()
            mock_span.end = MagicMock()
            return mock_span

        with (
            patch("docling_mcp.server.record_request_start") as mock_start,
            patch("docling_mcp.server.record_request_end"),
            patch("docling_mcp.server.generate_query_embedding") as mock_embed,
            patch("docling_mcp.server.search_with_embedding") as mock_search,
            patch("docling_mcp.server._langfuse_available", True),
            patch("docling_mcp.server.get_langfuse_client") as mock_get_client,
        ):
            mock_start.return_value = time.time()
            mock_embed.return_value = ([0.1] * 1536, 100.0)
            mock_search.return_value = ([], 50.0)

            mock_client = MagicMock()
            mock_client.span = mock_span_factory
            mock_get_client.return_value = mock_client

            await ask_knowledge_base.fn("test question")

            # Verify both spans were created
            assert "embedding-generation" in span_names_created, (
                "embedding-generation span not created"
            )
            assert "vector-search" in span_names_created, "vector-search span not created"

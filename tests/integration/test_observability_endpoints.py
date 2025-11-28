"""
Integration tests for Observability Endpoints (Story 2.3).

Tests:
- GET /metrics endpoint format validation
- GET /metrics histogram bucket configuration
- GET /health endpoint with all services available
- GET /health endpoint with database unavailable
- GET /health endpoint with LangFuse unavailable
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create test client for HTTP server."""
    from docling_mcp.http_server import app

    return TestClient(app)


class TestMetricsEndpoint:
    """Test /metrics endpoint."""

    def test_metrics_endpoint_returns_200(self, test_client):
        """Test /metrics endpoint returns 200 OK."""
        response = test_client.get("/metrics")

        assert response.status_code == 200

    def test_metrics_endpoint_content_type(self, test_client):
        """Test /metrics endpoint returns OpenMetrics content type."""
        response = test_client.get("/metrics")

        content_type = response.headers.get("content-type", "")
        assert "openmetrics-text" in content_type or "text/plain" in content_type

    def test_metrics_endpoint_returns_prometheus_format(self, test_client):
        """Test /metrics endpoint returns Prometheus format."""
        # Initialize metrics first
        from docling_mcp.metrics import _initialize_metrics, is_metrics_available

        _initialize_metrics()

        response = test_client.get("/metrics")
        content = response.text

        # If metrics available, should contain standard Prometheus format elements
        if is_metrics_available():
            # Should contain HELP or TYPE comments for at least one metric
            assert (
                "# HELP" in content or "# TYPE" in content or "mcp_" in content or "rag_" in content
            )

    def test_metrics_contains_mcp_request_metrics(self, test_client):
        """Test /metrics contains MCP request metrics."""
        from docling_mcp.metrics import (
            _initialize_metrics,
            is_metrics_available,
            record_request_end,
            record_request_start,
        )

        _initialize_metrics()

        if is_metrics_available():
            # Record a test request to ensure metrics exist
            start = record_request_start("test_tool")
            record_request_end("test_tool", start, "success")

        response = test_client.get("/metrics")
        content = response.text

        if is_metrics_available():
            # Should contain request-related metrics
            assert "mcp_request" in content or "# Prometheus metrics not available" in content


class TestMetricsHistogramBuckets:
    """Test histogram bucket configurations via /metrics endpoint."""

    def test_request_duration_histogram_exists(self, test_client):
        """Test request duration histogram is exposed."""
        from docling_mcp.metrics import (
            _initialize_metrics,
            is_metrics_available,
            record_request_end,
            record_request_start,
        )

        _initialize_metrics()

        if is_metrics_available():
            # Generate some metrics data
            start = record_request_start("test_tool")
            record_request_end("test_tool", start, "success")

        response = test_client.get("/metrics")
        content = response.text

        if is_metrics_available():
            # Histogram should be present
            assert (
                "mcp_request_duration_seconds" in content
                or "# Prometheus metrics not available" in content
            )

    def test_histogram_buckets_include_slo_threshold(self, test_client):
        """Test histogram buckets include SLO threshold (2.0s for p95)."""
        from docling_mcp.metrics import (
            _initialize_metrics,
            is_metrics_available,
            mcp_request_duration_seconds,
        )

        _initialize_metrics()

        if is_metrics_available() and mcp_request_duration_seconds:
            # 2.0s bucket should exist for p95 SLO monitoring
            buckets = list(mcp_request_duration_seconds._upper_bounds)
            assert 2.0 in buckets, "Missing 2.0s bucket for p95 SLO"


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_endpoint_returns_json(self, test_client):
        """Test /health endpoint returns JSON."""
        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            from docling_mcp.health import ServiceStatus

            mock_db.return_value = ServiceStatus(status="up", message="OK")
            mock_langfuse.return_value = ServiceStatus(status="up", message="OK")
            mock_embedder.return_value = ServiceStatus(status="up", message="OK")

            response = test_client.get("/health")

            assert response.headers.get("content-type", "").startswith("application/json")

    def test_health_endpoint_all_services_up(self, test_client):
        """Test /health returns 'ok' when all services up."""
        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            from docling_mcp.health import ServiceStatus

            mock_db.return_value = ServiceStatus(status="up", message="OK")
            mock_langfuse.return_value = ServiceStatus(status="up", message="OK")
            mock_embedder.return_value = ServiceStatus(status="up", message="OK")

            response = test_client.get("/health")
            data = response.json()

            assert response.status_code == 200
            assert data["status"] == "ok"
            assert "timestamp" in data
            assert "services" in data

    def test_health_endpoint_database_unavailable(self, test_client):
        """Test /health returns 'down' when database unavailable."""
        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            from docling_mcp.health import ServiceStatus

            mock_db.return_value = ServiceStatus(status="down", message="Connection failed")
            mock_langfuse.return_value = ServiceStatus(status="up", message="OK")
            mock_embedder.return_value = ServiceStatus(status="up", message="OK")

            response = test_client.get("/health")
            data = response.json()

            assert response.status_code == 503  # Service unavailable
            assert data["status"] == "down"
            assert data["services"]["database"]["status"] == "down"

    def test_health_endpoint_langfuse_unavailable(self, test_client):
        """Test /health returns 'degraded' when LangFuse unavailable."""
        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            from docling_mcp.health import ServiceStatus

            mock_db.return_value = ServiceStatus(status="up", message="OK")
            mock_langfuse.return_value = ServiceStatus(status="down", message="Not configured")
            mock_embedder.return_value = ServiceStatus(status="up", message="OK")

            response = test_client.get("/health")
            data = response.json()

            assert response.status_code == 200  # Still operational
            assert data["status"] == "degraded"
            assert data["services"]["langfuse"]["status"] == "down"

    def test_health_endpoint_embedder_unavailable(self, test_client):
        """Test /health returns 'down' when embedder unavailable."""
        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            from docling_mcp.health import ServiceStatus

            mock_db.return_value = ServiceStatus(status="up", message="OK")
            mock_langfuse.return_value = ServiceStatus(status="up", message="OK")
            mock_embedder.return_value = ServiceStatus(status="down", message="Not initialized")

            response = test_client.get("/health")
            data = response.json()

            assert response.status_code == 503
            assert data["status"] == "down"

    def test_health_response_includes_all_services(self, test_client):
        """Test /health response includes all service statuses."""
        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            from docling_mcp.health import ServiceStatus

            mock_db.return_value = ServiceStatus(status="up", message="OK", latency_ms=5.0)
            mock_langfuse.return_value = ServiceStatus(status="up", message="OK", latency_ms=1.0)
            mock_embedder.return_value = ServiceStatus(status="up", message="OK", latency_ms=2.0)

            response = test_client.get("/health")
            data = response.json()

            assert "database" in data["services"]
            assert "langfuse" in data["services"]
            assert "embedder" in data["services"]

            # Each service should have status, message, latency_ms
            for service_name in ["database", "langfuse", "embedder"]:
                service = data["services"][service_name]
                assert "status" in service
                assert "message" in service
                assert "latency_ms" in service


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint_returns_info(self, test_client):
        """Test root endpoint returns service info."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "endpoints" in data

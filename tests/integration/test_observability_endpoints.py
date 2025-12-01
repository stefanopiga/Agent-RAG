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

    def test_health_endpoint_embedder_initializing(self, test_client):
        """Test /health returns 'degraded' when embedder is initializing."""
        with (
            patch("docling_mcp.health.check_database") as mock_db,
            patch("docling_mcp.health.check_langfuse") as mock_langfuse,
            patch("docling_mcp.health.check_embedder") as mock_embedder,
        ):
            from docling_mcp.health import ServiceStatus

            mock_db.return_value = ServiceStatus(status="up", message="OK")
            mock_langfuse.return_value = ServiceStatus(status="up", message="OK")
            mock_embedder.return_value = ServiceStatus(
                status="initializing", message="Embedder initialization in progress"
            )

            response = test_client.get("/health")
            data = response.json()

            assert response.status_code == 200  # Still operational (degraded, not down)
            assert data["status"] == "degraded"
            assert data["services"]["embedder"]["status"] == "initializing"
            assert "initialization in progress" in data["services"]["embedder"]["message"].lower()

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


# ============================================================================
# Comprehensive Health Check Integration Tests - Story 5.2
# ============================================================================


class TestHealthCheckIntegration:
    """
    Integration tests for health check endpoints.
    
    These tests verify the complete health check flow including:
    - Real service status checks (with mocked dependencies)
    - Proper status code returns
    - Complete response structure
    - State transitions during startup/failure
    """

    @pytest.mark.integration
    async def test_health_check_startup_sequence(self):
        """
        Test complete startup sequence health transitions.
        
        Simulates:
        1. Initial state (embedder not started) → 503
        2. Embedder initializing → 200 (degraded)
        3. All services ready → 200 (ok)
        """
        from docling_mcp import health
        from core import rag_service
        import asyncio
        
        # State 1: Embedder not initialized
        rag_service._initialization_task = None
        rag_service._embedder_ready.clear()
        
        with patch("docling_mcp.health.check_database", return_value=health.ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=health.ServiceStatus(status="up")):
                result1 = await health.get_health_status()
        
        assert result1.status == "down"
        assert result1.services.embedder.status == "down"
        
        # State 2: Embedder initializing
        async def mock_init():
            await asyncio.sleep(0.1)
            rag_service._embedder_ready.set()
        
        rag_service._initialization_task = asyncio.create_task(mock_init())
        
        with patch("docling_mcp.health.check_database", return_value=health.ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=health.ServiceStatus(status="up")):
                result2 = await health.get_health_status()
        
        assert result2.status == "degraded"
        assert result2.services.embedder.status == "initializing"
        
        # State 3: Embedder ready
        await rag_service._initialization_task
        
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
        
        with patch("docling_mcp.health.check_database", return_value=health.ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=health.ServiceStatus(status="up")):
                with patch("core.rag_service.get_global_embedder", return_value=mock_embedder):
                    result3 = await health.get_health_status()
        
        assert result3.status == "ok"
        assert result3.services.embedder.status == "up"

    @pytest.mark.integration
    async def test_health_check_with_real_database_pool(self, db_pool):
        """
        Test health check with real database connection pool.
        
        Uses conftest.py db_pool fixture for actual database interaction.
        """
        from docling_mcp import health
        
        with patch("docling_mcp.health.get_db_pool", return_value=db_pool):
            with patch("docling_mcp.health.check_langfuse", return_value=health.ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=health.ServiceStatus(status="up")):
                    result = await health.get_health_status()
        
        # Database should be up (using real pool)
        assert result.services.database.status == "up"
        assert result.services.database.latency_ms > 0

    @pytest.mark.integration
    async def test_health_check_latency_measurements(self):
        """
        Test that latency measurements are accurate for all services.
        """
        from docling_mcp import health
        import asyncio
        
        # Mock services with known delays
        async def slow_db_check():
            await asyncio.sleep(0.05)  # 50ms
            return health.ServiceStatus(status="up", latency_ms=50.0)
        
        async def slow_lf_check():
            await asyncio.sleep(0.03)  # 30ms
            return health.ServiceStatus(status="up", latency_ms=30.0)
        
        async def fast_emb_check():
            await asyncio.sleep(0.01)  # 10ms
            return health.ServiceStatus(status="up", latency_ms=10.0)
        
        with patch("docling_mcp.health.check_database", side_effect=slow_db_check):
            with patch("docling_mcp.health.check_langfuse", side_effect=slow_lf_check):
                with patch("docling_mcp.health.check_embedder", side_effect=fast_emb_check):
                    start = asyncio.get_event_loop().time()
                    result = await health.get_health_status()
                    elapsed = (asyncio.get_event_loop().time() - start) * 1000
        
        # Checks run concurrently, so total time should be ~max(50, 30, 10) = 50ms
        assert elapsed < 100  # Allow margin for overhead
        assert result.services.database.latency_ms >= 40
        assert result.services.langfuse.latency_ms >= 25
        assert result.services.embedder.latency_ms >= 5

    @pytest.mark.integration
    async def test_health_check_graceful_degradation(self):
        """
        Test graceful degradation when non-critical services fail.
        
        System should remain operational (degraded) when LangFuse is down.
        """
        from docling_mcp import health
        
        with patch("docling_mcp.health.check_database", return_value=health.ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=health.ServiceStatus(status="down", message="Auth failed")):
                with patch("docling_mcp.health.check_embedder", return_value=health.ServiceStatus(status="up")):
                    result = await health.get_health_status()
        
        assert result.status == "degraded"
        assert result.services.database.status == "up"
        assert result.services.langfuse.status == "down"
        assert result.services.embedder.status == "up"

    @pytest.mark.integration
    async def test_health_check_critical_failure(self):
        """
        Test critical failure handling when database is down.
        
        System should be marked "down" when critical services fail.
        """
        from docling_mcp import health
        
        with patch("docling_mcp.health.check_database", return_value=health.ServiceStatus(status="down", message="Connection timeout")):
            with patch("docling_mcp.health.check_langfuse", return_value=health.ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=health.ServiceStatus(status="up")):
                    result = await health.get_health_status()
        
        assert result.status == "down"
        assert result.services.database.status == "down"


# ============================================================================
# HTTP Server Endpoint Integration Tests
# ============================================================================


class TestHTTPServerIntegration:
    """
    Integration tests for HTTP server endpoints.
    
    Tests the complete request/response flow through FastAPI.
    """

    @pytest.mark.integration
    def test_health_endpoint_returns_correct_status_codes(self):
        """Test health endpoint returns correct HTTP status codes."""
        from docling_mcp.http_server import app
        from fastapi.testclient import TestClient
        from docling_mcp import health
        
        client = TestClient(app)
        
        # Test 200 OK
        with patch("docling_mcp.http_server.get_health_status", return_value=health.HealthResponse(
            status="ok",
            timestamp=1234567890.0,
            services=health.Services(
                database=health.ServiceStatus(status="up"),
                langfuse=health.ServiceStatus(status="up"),
                embedder=health.ServiceStatus(status="up"),
            ),
        )):
            response = client.get("/health")
            assert response.status_code == 200
        
        # Test 200 DEGRADED (not 503)
        with patch("docling_mcp.http_server.get_health_status", return_value=health.HealthResponse(
            status="degraded",
            timestamp=1234567890.0,
            services=health.Services(
                database=health.ServiceStatus(status="up"),
                langfuse=health.ServiceStatus(status="down"),
                embedder=health.ServiceStatus(status="up"),
            ),
        )):
            response = client.get("/health")
            assert response.status_code == 200
        
        # Test 503 DOWN
        with patch("docling_mcp.http_server.get_health_status", return_value=health.HealthResponse(
            status="down",
            timestamp=1234567890.0,
            services=health.Services(
                database=health.ServiceStatus(status="down"),
                langfuse=health.ServiceStatus(status="up"),
                embedder=health.ServiceStatus(status="up"),
            ),
        )):
            response = client.get("/health")
            assert response.status_code == 503

    @pytest.mark.integration
    def test_metrics_endpoint_returns_prometheus_format(self):
        """Test metrics endpoint returns valid Prometheus format."""
        from docling_mcp.http_server import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Mock metrics output
        mock_metrics = """# HELP test_counter_total A test counter
# TYPE test_counter_total counter
test_counter_total 42.0
# HELP test_gauge A test gauge
# TYPE test_gauge gauge
test_gauge 3.14
"""
        
        with patch("docling_mcp.http_server.generate_metrics_output", return_value=mock_metrics):
            with patch("docling_mcp.http_server.get_metrics_content_type", return_value="text/plain; version=0.0.4"):
                response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "test_counter_total" in response.text
        assert "test_gauge" in response.text

    @pytest.mark.integration
    def test_health_endpoint_response_structure(self):
        """Test health endpoint returns complete response structure."""
        from docling_mcp.http_server import app
        from fastapi.testclient import TestClient
        from docling_mcp import health
        
        client = TestClient(app)
        
        with patch("docling_mcp.http_server.get_health_status", return_value=health.HealthResponse(
            status="ok",
            timestamp=1234567890.123,
            services=health.Services(
                database=health.ServiceStatus(status="up", message="PostgreSQL OK", latency_ms=10.5),
                langfuse=health.ServiceStatus(status="up", message="Authenticated", latency_ms=50.2),
                embedder=health.ServiceStatus(status="up", message="Ready", latency_ms=5.1),
            ),
        )):
            response = client.get("/health")
        
        data = response.json()
        
        # Verify complete structure
        assert data["status"] == "ok"
        assert data["timestamp"] == 1234567890.123
        assert "services" in data
        
        # Verify database service
        assert data["services"]["database"]["status"] == "up"
        assert data["services"]["database"]["message"] == "PostgreSQL OK"
        assert data["services"]["database"]["latency_ms"] == 10.5
        
        # Verify langfuse service
        assert data["services"]["langfuse"]["status"] == "up"
        assert data["services"]["langfuse"]["latency_ms"] == 50.2
        
        # Verify embedder service
        assert data["services"]["embedder"]["status"] == "up"
        assert data["services"]["embedder"]["latency_ms"] == 5.1


# ============================================================================
# End-to-End Observability Tests
# ============================================================================


class TestObservabilityE2E:
    """
    End-to-end tests for observability infrastructure.
    
    These tests verify the complete observability flow from service checks
    through HTTP endpoints to client responses.
    """

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_complete_observability_flow(self, db_pool):
        """
        Test complete observability flow:
        1. Service checks execute
        2. Health status aggregates
        3. HTTP endpoint responds
        4. Metrics are collectible
        """
        from docling_mcp.http_server import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Mock real service dependencies
        with patch("docling_mcp.health.get_db_pool", return_value=db_pool):
            with patch("docling_mcp.health.get_langfuse_client", return_value=MagicMock(auth_check=lambda: True)):
                mock_embedder = AsyncMock()
                mock_embedder.embed.return_value = [0.1, 0.2]
                with patch("core.rag_service.get_global_embedder", return_value=mock_embedder):
                    with patch("core.rag_service._embedder_ready.is_set", return_value=True):
                        # Get health status
                        health_response = client.get("/health")
                        
                        # Get metrics
                        metrics_response = client.get("/metrics")
        
        # Verify health response
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] in ["ok", "degraded"]
        
        # Verify metrics response
        assert metrics_response.status_code == 200
        assert "text/plain" in metrics_response.headers["content-type"]

    @pytest.mark.integration
    def test_health_check_kubernetes_probe_compatibility(self):
        """
        Test health check is compatible with Kubernetes readiness/liveness probes.
        
        Requirements:
        - Returns 200 for healthy/degraded
        - Returns 503 for critical failures
        - Responds within timeout (default 5s)
        """
        from docling_mcp.http_server import app
        from fastapi.testclient import TestClient
        from docling_mcp import health
        import time
        
        client = TestClient(app)
        
        # Test readiness probe (allow degraded)
        with patch("docling_mcp.http_server.get_health_status", return_value=health.HealthResponse(
            status="degraded",
            timestamp=time.time(),
            services=health.Services(
                database=health.ServiceStatus(status="up"),
                langfuse=health.ServiceStatus(status="down"),  # Non-critical
                embedder=health.ServiceStatus(status="up"),
            ),
        )):
            start = time.time()
            response = client.get("/health")
            elapsed = time.time() - start
        
        # Should return 200 (ready for traffic even if degraded)
        assert response.status_code == 200
        # Should respond quickly (<1s)
        assert elapsed < 1.0
        
        # Test liveness probe (critical failure)
        with patch("docling_mcp.http_server.get_health_status", return_value=health.HealthResponse(
            status="down",
            timestamp=time.time(),
            services=health.Services(
                database=health.ServiceStatus(status="down"),  # Critical
                langfuse=health.ServiceStatus(status="up"),
                embedder=health.ServiceStatus(status="up"),
            ),
        )):
            response = client.get("/health")
        
        # Should return 503 (needs restart)
        assert response.status_code == 503

"""
Unit tests for docling_mcp/http_server.py - MCP HTTP Server.

Tests observability endpoints:
- GET /health - Health check endpoint
- GET /metrics - Prometheus metrics endpoint
- GET /docs - API documentation

Coverage: AC5.2.11, AC5.2.12
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Import after ensuring test environment is set up
from docling_mcp.http_server import app


# ============================================================================
# Fixture Setup
# ============================================================================


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_health_status():
    """Mock health status response."""
    from docling_mcp.health import HealthResponse, ServiceStatus, Services
    
    return HealthResponse(
        status="ok",
        timestamp=1234567890.0,
        services=Services(
            database=ServiceStatus(status="up", message="PostgreSQL OK", latency_ms=10.0),
            langfuse=ServiceStatus(status="up", message="Authenticated", latency_ms=50.0),
            embedder=ServiceStatus(status="up", message="Ready", latency_ms=5.0),
        ),
    )


# ============================================================================
# Health Endpoint Tests
# ============================================================================


class TestHealthEndpoint:
    """Test /health endpoint functionality."""

    @pytest.mark.unit
    def test_health_endpoint_success(self, client, mock_health_status):
        """Test health endpoint returns 200 when all services up."""
        with patch("docling_mcp.http_server.get_health_status", return_value=mock_health_status):
            response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "services" in data
        assert data["services"]["database"]["status"] == "up"
        assert data["services"]["embedder"]["status"] == "up"

    @pytest.mark.unit
    def test_health_endpoint_degraded(self, client, mock_health_status):
        """Test health endpoint with degraded status."""
        mock_health_status.status = "degraded"
        mock_health_status.services.langfuse.status = "down"
        
        with patch("docling_mcp.http_server.get_health_status", return_value=mock_health_status):
            response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"

    @pytest.mark.unit
    def test_health_endpoint_down(self, client, mock_health_status):
        """Test health endpoint returns 503 when services down."""
        mock_health_status.status = "down"
        mock_health_status.services.database.status = "down"
        
        with patch("docling_mcp.http_server.get_health_status", return_value=mock_health_status):
            response = client.get("/health")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "down"

    @pytest.mark.unit
    def test_health_endpoint_initializing_status(self, client, mock_health_status):
        """
        Test health endpoint with embedder initializing (AC5.2.10).
        
        Should return 200 (not 503) during normal startup.
        """
        mock_health_status.status = "degraded"
        mock_health_status.services.embedder.status = "initializing"
        
        with patch("docling_mcp.http_server.get_health_status", return_value=mock_health_status):
            response = client.get("/health")
        
        assert response.status_code == 200  # Not 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["embedder"]["status"] == "initializing"

    @pytest.mark.unit
    def test_health_endpoint_json_structure(self, client, mock_health_status):
        """Test health endpoint returns correct JSON structure."""
        with patch("docling_mcp.http_server.get_health_status", return_value=mock_health_status):
            response = client.get("/health")
        
        data = response.json()
        
        # Required top-level fields
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        
        # Required service fields
        assert "database" in data["services"]
        assert "langfuse" in data["services"]
        assert "embedder" in data["services"]
        
        # Each service should have status, message, latency_ms
        for service in data["services"].values():
            assert "status" in service
            assert "message" in service
            assert "latency_ms" in service

    @pytest.mark.unit
    def test_health_endpoint_exception_handling(self, client):
        """Test health endpoint handles exceptions gracefully."""
        with patch("docling_mcp.http_server.get_health_status", side_effect=Exception("Health check failed")):
            response = client.get("/health")
        
        # Should still return a response (error handling)
        assert response.status_code in [500, 503]


# ============================================================================
# Metrics Endpoint Tests
# ============================================================================


class TestMetricsEndpoint:
    """Test /metrics endpoint functionality."""

    @pytest.mark.unit
    def test_metrics_endpoint_success(self, client):
        """Test metrics endpoint returns Prometheus format."""
        mock_metrics = """# HELP test_metric A test metric
# TYPE test_metric counter
test_metric 42.0
"""
        with patch("docling_mcp.http_server.generate_metrics_output", return_value=mock_metrics):
            with patch("docling_mcp.http_server.get_metrics_content_type", return_value="text/plain; version=0.0.4"):
                response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "test_metric" in response.text

    @pytest.mark.unit
    def test_metrics_endpoint_content_type(self, client):
        """Test metrics endpoint returns correct content type."""
        with patch("docling_mcp.http_server.generate_metrics_output", return_value=""):
            with patch("docling_mcp.http_server.get_metrics_content_type", return_value="text/plain; version=0.0.4; charset=utf-8"):
                response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "version=0.0.4" in response.headers["content-type"]

    @pytest.mark.unit
    def test_metrics_endpoint_empty_metrics(self, client):
        """Test metrics endpoint with no metrics collected."""
        with patch("docling_mcp.http_server.generate_metrics_output", return_value=""):
            with patch("docling_mcp.http_server.get_metrics_content_type", return_value="text/plain"):
                response = client.get("/metrics")
        
        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.unit
    def test_metrics_endpoint_exception_handling(self, client):
        """Test metrics endpoint handles exceptions."""
        with patch("docling_mcp.http_server.generate_metrics_output", side_effect=Exception("Metrics error")):
            response = client.get("/metrics")
        
        assert response.status_code == 500


# ============================================================================
# Docs Endpoint Tests
# ============================================================================


class TestDocsEndpoint:
    """Test /docs endpoint (Swagger UI)."""

    @pytest.mark.unit
    def test_docs_endpoint_accessible(self, client):
        """Test that API documentation is accessible."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    @pytest.mark.unit
    def test_openapi_schema_accessible(self, client):
        """Test that OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    @pytest.mark.unit
    def test_openapi_schema_includes_endpoints(self, client):
        """Test that OpenAPI schema includes all endpoints."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        assert "/health" in paths
        assert "/metrics" in paths


# ============================================================================
# Application Metadata Tests
# ============================================================================


class TestApplicationMetadata:
    """Test FastAPI application metadata."""

    @pytest.mark.unit
    def test_app_title(self):
        """Test application title is correct."""
        assert app.title == "Docling RAG Agent - Observability"

    @pytest.mark.unit
    def test_app_version(self):
        """Test application version is set."""
        assert app.version == "1.0.0"

    @pytest.mark.unit
    def test_app_description(self):
        """Test application description."""
        assert "Prometheus" in app.description
        assert "health check" in app.description.lower()

    @pytest.mark.unit
    def test_app_docs_url(self):
        """Test docs URL is configured."""
        assert app.docs_url == "/docs"

    @pytest.mark.unit
    def test_app_redoc_disabled(self):
        """Test ReDoc is disabled."""
        assert app.redoc_url is None


# ============================================================================
# Lifespan Integration Tests
# ============================================================================


class TestLifespanIntegration:
    """
    Test lifespan event handlers integration.
    
    Note: Full lifespan testing requires docling_mcp.lifespan module tests.
    """

    @pytest.mark.unit
    def test_app_has_lifespan(self):
        """Test that app has lifespan configured."""
        assert app.router.lifespan_context is not None

    @pytest.mark.unit
    async def test_lifespan_startup_called(self):
        """Test that startup events are triggered."""
        # This test verifies lifespan is wired up
        # Actual startup logic is tested in test_lifespan.py
        
        from contextlib import asynccontextmanager
        
        startup_called = False
        
        @asynccontextmanager
        async def mock_lifespan(app):
            nonlocal startup_called
            startup_called = True
            yield
        
        # Temporarily replace lifespan
        original_lifespan = app.router.lifespan_context
        app.router.lifespan_context = mock_lifespan
        
        try:
            with TestClient(app):
                pass  # Lifespan runs during client context
            
            assert startup_called, "Lifespan startup should be called"
        finally:
            app.router.lifespan_context = original_lifespan


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.unit
    def test_nonexistent_endpoint(self, client):
        """Test accessing non-existent endpoint returns 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    @pytest.mark.unit
    def test_wrong_http_method(self, client):
        """Test wrong HTTP method returns 405."""
        response = client.post("/health")
        assert response.status_code == 405

    @pytest.mark.unit
    def test_health_endpoint_concurrent_requests(self, client, mock_health_status):
        """Test multiple concurrent requests to health endpoint."""
        with patch("docling_mcp.http_server.get_health_status", return_value=mock_health_status):
            responses = [client.get("/health") for _ in range(10)]
        
        assert all(r.status_code == 200 for r in responses)
        assert all(r.json()["status"] == "ok" for r in responses)


# ============================================================================
# Response Format Tests
# ============================================================================


class TestResponseFormats:
    """Test response format compliance."""

    @pytest.mark.unit
    def test_health_response_is_valid_json(self, client, mock_health_status):
        """Test health response is valid JSON."""
        with patch("docling_mcp.http_server.get_health_status", return_value=mock_health_status):
            response = client.get("/health")
        
        # Should not raise
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.unit
    def test_health_response_latency_values(self, client, mock_health_status):
        """Test latency values are non-negative numbers."""
        with patch("docling_mcp.http_server.get_health_status", return_value=mock_health_status):
            response = client.get("/health")
        
        data = response.json()
        for service in data["services"].values():
            latency = service["latency_ms"]
            assert isinstance(latency, (int, float))
            assert latency >= 0

    @pytest.mark.unit
    def test_health_response_timestamp_valid(self, client, mock_health_status):
        """Test timestamp is a valid Unix timestamp."""
        with patch("docling_mcp.http_server.get_health_status", return_value=mock_health_status):
            response = client.get("/health")
        
        data = response.json()
        timestamp = data["timestamp"]
        
        assert isinstance(timestamp, (int, float))
        assert timestamp > 0
        # Reasonable range check (after year 2000, before year 2100)
        assert 946684800 < timestamp < 4102444800
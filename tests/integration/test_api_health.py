"""
Integration tests for API Server Health Check Endpoint (Story 4.2).

Tests:
- GET /health endpoint returns JSON with status and timestamp (AC4.2.6)
- GET /health endpoint verifies database connection (AC4.2.7)
- GET /health returns 503 when database unavailable
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """Create test client for API server."""
    from api.main import app

    return TestClient(app)


class TestAPIHealthEndpoint:
    """Test API server /health endpoint."""

    def test_health_endpoint_returns_json(self, api_client):
        """Test /health endpoint returns JSON (AC4.2.6)."""
        with patch("utils.db_utils.test_connection", new_callable=AsyncMock) as mock_conn:
            mock_conn.return_value = True

            response = api_client.get("/health")

            assert response.headers.get("content-type", "").startswith("application/json")

    def test_health_endpoint_returns_status_and_timestamp(self, api_client):
        """Test /health returns status 'ok' and timestamp (AC4.2.6)."""
        with patch("utils.db_utils.test_connection", new_callable=AsyncMock) as mock_conn:
            mock_conn.return_value = True

            response = api_client.get("/health")
            data = response.json()

            assert response.status_code == 200
            assert data["status"] == "ok"
            assert "timestamp" in data
            assert isinstance(data["timestamp"], float)

    def test_health_endpoint_verifies_database_connection(self, api_client):
        """Test /health verifies database connection and includes status (AC4.2.7)."""
        with patch("utils.db_utils.test_connection", new_callable=AsyncMock) as mock_conn:
            mock_conn.return_value = True

            response = api_client.get("/health")
            data = response.json()

            assert response.status_code == 200
            assert "services" in data
            assert "database" in data["services"]
            assert data["services"]["database"]["status"] == "up"
            assert "message" in data["services"]["database"]

    def test_health_endpoint_database_unavailable_returns_503(self, api_client):
        """Test /health returns 503 when database unavailable."""
        with patch("utils.db_utils.test_connection", new_callable=AsyncMock) as mock_conn:
            mock_conn.return_value = False

            response = api_client.get("/health")
            data = response.json()

            assert response.status_code == 503
            assert data["status"] == "down"
            assert data["services"]["database"]["status"] == "down"

    def test_health_endpoint_database_connection_error(self, api_client):
        """Test /health handles database connection errors gracefully."""
        with patch("utils.db_utils.test_connection", new_callable=AsyncMock) as mock_conn:
            mock_conn.side_effect = Exception("Connection refused")

            response = api_client.get("/health")
            data = response.json()

            assert response.status_code == 503
            assert data["status"] == "down"
            assert data["services"]["database"]["status"] == "down"
            assert "Connection refused" in data["services"]["database"]["message"]

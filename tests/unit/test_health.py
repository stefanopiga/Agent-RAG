"""
Unit tests for docling_mcp/health.py module.

Tests health check functionality including:
- Database connectivity checks
- LangFuse integration checks  
- Embedder initialization status checks
- Overall health status aggregation
- Status transitions (ok → degraded → down)

Coverage: AC5.2.10, AC5.2.11, AC5.2.12
"""

import asyncio
import time
from typing import Literal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docling_mcp.health import (
    HealthResponse,
    ServiceStatus,
    check_database,
    check_embedder,
    check_langfuse,
    get_health_status,
)


# ============================================================================
# ServiceStatus Tests
# ============================================================================


class TestServiceStatus:
    """Test ServiceStatus model validation and serialization."""

    @pytest.mark.unit
    def test_service_status_up(self):
        """Test creating ServiceStatus with 'up' status."""
        status = ServiceStatus(status="up", message="Service healthy", latency_ms=10.5)
        
        assert status.status == "up"
        assert status.message == "Service healthy"
        assert status.latency_ms == 10.5

    @pytest.mark.unit
    def test_service_status_down(self):
        """Test creating ServiceStatus with 'down' status."""
        status = ServiceStatus(status="down", message="Connection failed", latency_ms=5000.0)
        
        assert status.status == "down"
        assert status.message == "Connection failed"

    @pytest.mark.unit
    def test_service_status_initializing(self):
        """Test creating ServiceStatus with 'initializing' status (new in Story 5.2)."""
        status = ServiceStatus(status="initializing", message="Starting up", latency_ms=0.0)
        
        assert status.status == "initializing"
        assert status.message == "Starting up"

    @pytest.mark.unit
    def test_service_status_defaults(self):
        """Test ServiceStatus default values."""
        status = ServiceStatus(status="up")
        
        assert status.status == "up"
        assert status.message == ""
        assert status.latency_ms == 0.0

    @pytest.mark.unit
    def test_service_status_invalid_status(self):
        """Test that invalid status values are rejected."""
        with pytest.raises(ValueError):
            ServiceStatus(status="unknown")  # type: ignore


# ============================================================================
# check_database() Tests
# ============================================================================


class TestCheckDatabase:
    """Test database health check functionality."""

    @pytest.mark.unit
    async def test_check_database_success(self):
        """Test successful database connection."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = 1
        
        with patch("docling_mcp.health.get_db_pool", return_value=mock_pool):
            result = await check_database()
        
        assert result.status == "up"
        assert "PostgreSQL" in result.message
        assert result.latency_ms > 0
        mock_conn.fetchval.assert_called_once_with("SELECT 1")

    @pytest.mark.unit
    async def test_check_database_connection_failure(self):
        """Test database connection failure."""
        with patch("docling_mcp.health.get_db_pool", side_effect=Exception("Connection refused")):
            result = await check_database()
        
        assert result.status == "down"
        assert "Connection refused" in result.message
        assert result.latency_ms > 0

    @pytest.mark.unit
    async def test_check_database_query_failure(self):
        """Test database query execution failure."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchval.side_effect = Exception("Query timeout")
        
        with patch("docling_mcp.health.get_db_pool", return_value=mock_pool):
            result = await check_database()
        
        assert result.status == "down"
        assert "Query timeout" in result.message

    @pytest.mark.unit
    async def test_check_database_measures_latency(self):
        """Test that database check measures latency accurately."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        async def slow_query(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return 1
        
        mock_conn.fetchval = slow_query
        
        with patch("docling_mcp.health.get_db_pool", return_value=mock_pool):
            result = await check_database()
        
        assert result.status == "up"
        assert result.latency_ms >= 100  # At least 100ms


# ============================================================================
# check_langfuse() Tests
# ============================================================================


class TestCheckLangfuse:
    """Test LangFuse integration health check."""

    @pytest.mark.unit
    async def test_check_langfuse_success(self):
        """Test successful LangFuse connection."""
        mock_client = MagicMock()
        mock_client.auth_check.return_value = True
        
        with patch("docling_mcp.health.get_langfuse_client", return_value=mock_client):
            result = await check_langfuse()
        
        assert result.status == "up"
        assert "authenticated" in result.message.lower()
        assert result.latency_ms > 0

    @pytest.mark.unit
    async def test_check_langfuse_auth_failure(self):
        """Test LangFuse authentication failure."""
        mock_client = MagicMock()
        mock_client.auth_check.return_value = False
        
        with patch("docling_mcp.health.get_langfuse_client", return_value=mock_client):
            result = await check_langfuse()
        
        assert result.status == "down"
        assert "failed" in result.message.lower()

    @pytest.mark.unit
    async def test_check_langfuse_client_unavailable(self):
        """Test when LangFuse client is not available."""
        with patch("docling_mcp.health.get_langfuse_client", return_value=None):
            result = await check_langfuse()
        
        assert result.status == "down"
        assert "not available" in result.message.lower()

    @pytest.mark.unit
    async def test_check_langfuse_exception(self):
        """Test handling of exceptions during LangFuse check."""
        with patch("docling_mcp.health.get_langfuse_client", side_effect=Exception("API error")):
            result = await check_langfuse()
        
        assert result.status == "down"
        assert "API error" in result.message


# ============================================================================
# check_embedder() Tests - Critical for Story 5.2
# ============================================================================


class TestCheckEmbedder:
    """
    Test embedder health check functionality.
    
    Critical AC5.2.10: Must distinguish between:
    - "initializing" (normal startup, task in progress)
    - "down" (failed initialization or not started)
    - "up" (ready and functional)
    """

    @pytest.mark.unit
    async def test_check_embedder_ready_and_functional(self):
        """Test embedder when ready and functional."""
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
        
        mock_ready = MagicMock()
        mock_ready.is_set.return_value = True
        
        with patch("docling_mcp.health._embedder_ready", mock_ready):
            with patch("docling_mcp.health.get_global_embedder", return_value=mock_embedder):
                with patch("docling_mcp.health.is_embedder_initializing", return_value=False):
                    result = await check_embedder()
        
        assert result.status == "up"
        assert "ready" in result.message.lower()
        assert result.latency_ms > 0

    @pytest.mark.unit
    async def test_check_embedder_initializing(self):
        """
        Test embedder during initialization (AC5.2.10).
        
        Should return "initializing" status, not "down".
        """
        mock_ready = MagicMock()
        mock_ready.is_set.return_value = False
        
        with patch("docling_mcp.health._embedder_ready", mock_ready):
            with patch("docling_mcp.health.is_embedder_initializing", return_value=True):
                result = await check_embedder()
        
        assert result.status == "initializing"
        assert "in progress" in result.message.lower()
        assert result.latency_ms >= 0

    @pytest.mark.unit
    async def test_check_embedder_failed_initialization(self):
        """
        Test embedder when initialization failed.
        
        Not initializing but also not ready → failed state.
        """
        mock_ready = MagicMock()
        mock_ready.is_set.return_value = False
        
        with patch("docling_mcp.health._embedder_ready", mock_ready):
            with patch("docling_mcp.health.is_embedder_initializing", return_value=False):
                result = await check_embedder()
        
        assert result.status == "down"
        assert "failed" in result.message.lower() or "not started" in result.message.lower()

    @pytest.mark.unit
    async def test_check_embedder_ready_but_embed_fails(self):
        """Test embedder marked ready but embed operation fails."""
        mock_embedder = AsyncMock()
        mock_embedder.embed.side_effect = Exception("Embedding model error")
        
        mock_ready = MagicMock()
        mock_ready.is_set.return_value = True
        
        with patch("docling_mcp.health._embedder_ready", mock_ready):
            with patch("docling_mcp.health.get_global_embedder", return_value=mock_embedder):
                with patch("docling_mcp.health.is_embedder_initializing", return_value=False):
                    result = await check_embedder()
        
        assert result.status == "down"
        assert "Embedding model error" in result.message

    @pytest.mark.unit
    async def test_check_embedder_exception_during_check(self):
        """Test handling of exceptions during embedder check."""
        with patch("docling_mcp.health._embedder_ready", side_effect=Exception("Unexpected error")):
            result = await check_embedder()
        
        assert result.status == "down"
        assert "Unexpected error" in result.message


# ============================================================================
# get_health_status() Tests - Overall Health Aggregation
# ============================================================================


class TestGetHealthStatus:
    """
    Test overall health status aggregation logic.
    
    Status precedence:
    - "down": Database down OR embedder down (failed)
    - "degraded": LangFuse down OR embedder initializing
    - "ok": All services up
    """

    @pytest.mark.unit
    async def test_get_health_status_all_services_up(self):
        """Test when all services are healthy."""
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="up", message="DB OK")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up", message="LF OK")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="up", message="EMB OK")):
                    result = await get_health_status()
        
        assert result.status == "ok"
        assert result.services.database.status == "up"
        assert result.services.langfuse.status == "up"
        assert result.services.embedder.status == "up"
        assert result.timestamp > 0

    @pytest.mark.unit
    async def test_get_health_status_database_down(self):
        """Test when database is down (critical failure)."""
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="down", message="DB fail")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="up")):
                    result = await get_health_status()
        
        assert result.status == "down"
        assert result.services.database.status == "down"

    @pytest.mark.unit
    async def test_get_health_status_embedder_down(self):
        """Test when embedder is down (critical failure)."""
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="down", message="EMB fail")):
                    result = await get_health_status()
        
        assert result.status == "down"
        assert result.services.embedder.status == "down"

    @pytest.mark.unit
    async def test_get_health_status_embedder_initializing(self):
        """
        Test when embedder is initializing (AC5.2.10).
        
        Should return "degraded" not "down" - this is normal startup.
        """
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="initializing")):
                    result = await get_health_status()
        
        assert result.status == "degraded"
        assert result.services.embedder.status == "initializing"

    @pytest.mark.unit
    async def test_get_health_status_langfuse_down(self):
        """Test when LangFuse is down (non-critical, graceful degradation)."""
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="down")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="up")):
                    result = await get_health_status()
        
        assert result.status == "degraded"
        assert result.services.langfuse.status == "down"

    @pytest.mark.unit
    async def test_get_health_status_multiple_services_down(self):
        """Test when multiple services are down."""
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="down")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="down")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="down")):
                    result = await get_health_status()
        
        # Database down takes precedence → overall "down"
        assert result.status == "down"

    @pytest.mark.unit
    async def test_get_health_status_timestamp_accuracy(self):
        """Test that timestamp is set correctly."""
        before = time.time()
        
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="up")):
                    result = await get_health_status()
        
        after = time.time()
        
        assert before <= result.timestamp <= after


# ============================================================================
# Status Transition Tests
# ============================================================================


class TestHealthStatusTransitions:
    """
    Test state transitions during application lifecycle.
    
    Expected transitions:
    1. Startup: down → degraded (initializing) → ok
    2. Failure: ok → degraded → down
    3. Recovery: down → degraded → ok
    """

    @pytest.mark.unit
    async def test_startup_sequence(self):
        """
        Test typical startup sequence.
        
        1. Database up, embedder not started → down
        2. Database up, embedder initializing → degraded
        3. Database up, embedder ready → ok
        """
        # State 1: Embedder not started
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="down")):
                    result1 = await get_health_status()
        
        assert result1.status == "down"
        
        # State 2: Embedder initializing
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="initializing")):
                    result2 = await get_health_status()
        
        assert result2.status == "degraded"
        
        # State 3: All ready
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="up")):
                    result3 = await get_health_status()
        
        assert result3.status == "ok"

    @pytest.mark.unit
    async def test_degradation_sequence(self):
        """
        Test graceful degradation when non-critical service fails.
        
        LangFuse failure should not cause overall "down" status.
        """
        # Start healthy
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="up")):
                    result1 = await get_health_status()
        
        assert result1.status == "ok"
        
        # LangFuse goes down → degraded (not down)
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="down")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="up")):
                    result2 = await get_health_status()
        
        assert result2.status == "degraded"


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestHealthCheckEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.unit
    async def test_concurrent_health_checks(self):
        """Test multiple concurrent health check requests."""
        with patch("docling_mcp.health.check_database", return_value=ServiceStatus(status="up")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="up")):
                    results = await asyncio.gather(
                        get_health_status(),
                        get_health_status(),
                        get_health_status(),
                    )
        
        # All should succeed
        assert len(results) == 3
        assert all(r.status == "ok" for r in results)

    @pytest.mark.unit
    async def test_health_check_with_slow_service(self):
        """Test health check when one service is slow but functional."""
        async def slow_db_check():
            await asyncio.sleep(0.1)
            return ServiceStatus(status="up", message="Slow DB", latency_ms=100.0)
        
        with patch("docling_mcp.health.check_database", side_effect=slow_db_check):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="up")):
                    result = await get_health_status()
        
        # Should still report "ok" even if slow
        assert result.status == "ok"
        assert result.services.database.latency_ms >= 100

    @pytest.mark.unit
    async def test_health_check_exception_handling(self):
        """Test that exceptions in one check don't crash overall health check."""
        with patch("docling_mcp.health.check_database", side_effect=Exception("Unexpected")):
            with patch("docling_mcp.health.check_langfuse", return_value=ServiceStatus(status="up")):
                with patch("docling_mcp.health.check_embedder", return_value=ServiceStatus(status="up")):
                    # Should not raise, should handle gracefully
                    result = await get_health_status()
        
        # Database check failed → overall down
        assert result.status == "down"
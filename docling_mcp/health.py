"""
Health Check Module
===================
Provides health check functionality for the MCP server.

Endpoints:
- GET /health: Returns JSON with status (ok/degraded/down), timestamp, and services status

Status Logic:
- "ok": All services (database, langfuse, embedder) are UP
- "degraded": LangFuse unavailable but database and embedder UP
- "down": Database unavailable (critical dependency)
"""

import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Literal

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Status of an individual service."""

    status: Literal["up", "down"]
    message: str = ""
    latency_ms: float = 0.0


@dataclass
class HealthResponse:
    """Health check response structure."""

    status: Literal["ok", "degraded", "down"]
    timestamp: float
    services: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"status": self.status, "timestamp": self.timestamp, "services": self.services}


async def check_database() -> ServiceStatus:
    """
    Check database connectivity.

    Returns:
        ServiceStatus with database health information
    """
    start_time = time.time()

    try:
        from utils.db_utils import test_connection

        is_connected = await test_connection()
        latency_ms = (time.time() - start_time) * 1000

        if is_connected:
            return ServiceStatus(
                status="up",
                message="Database connection successful (Supabase/PostgreSQL)",
                latency_ms=latency_ms,
            )
        else:
            return ServiceStatus(
                status="down",
                message="Database connection failed (check DATABASE_URL and network)",
                latency_ms=latency_ms,
            )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"Database health check failed: {e}")
        return ServiceStatus(
            status="down", message=f"Database connection error: {str(e)}", latency_ms=latency_ms
        )


def check_langfuse() -> ServiceStatus:
    """
    Check LangFuse client status.

    Returns:
        ServiceStatus with LangFuse health information
    """
    start_time = time.time()

    try:
        from docling_mcp.lifespan import get_langfuse_client, is_langfuse_enabled

        latency_ms = (time.time() - start_time) * 1000

        if is_langfuse_enabled():
            client = get_langfuse_client()
            if client is not None:
                return ServiceStatus(
                    status="up", message="LangFuse client initialized", latency_ms=latency_ms
                )
            else:
                return ServiceStatus(
                    status="down",
                    message="LangFuse enabled but client is None",
                    latency_ms=latency_ms,
                )
        else:
            return ServiceStatus(
                status="down",
                message="LangFuse not enabled (missing API keys or SDK)",
                latency_ms=latency_ms,
            )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"LangFuse health check failed: {e}")
        return ServiceStatus(
            status="down", message=f"LangFuse check error: {str(e)}", latency_ms=latency_ms
        )


async def check_embedder() -> ServiceStatus:
    """
    Check embedder readiness.

    Returns:
        ServiceStatus with embedder health information
    """
    start_time = time.time()

    try:
        from core.rag_service import _embedder_ready, get_global_embedder

        # Check if embedder is ready (non-blocking check)
        if _embedder_ready.is_set():
            embedder = await get_global_embedder()
            latency_ms = (time.time() - start_time) * 1000

            if embedder is not None:
                return ServiceStatus(
                    status="up", message="Embedder initialized and ready", latency_ms=latency_ms
                )
            else:
                return ServiceStatus(
                    status="down",
                    message="Embedder is None after initialization",
                    latency_ms=latency_ms,
                )
        else:
            latency_ms = (time.time() - start_time) * 1000
            return ServiceStatus(
                status="down", message="Embedder initialization in progress", latency_ms=latency_ms
            )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"Embedder health check failed: {e}")
        return ServiceStatus(
            status="down", message=f"Embedder check error: {str(e)}", latency_ms=latency_ms
        )


async def get_health_status() -> HealthResponse:
    """
    Get overall health status of the MCP server.

    Returns:
        HealthResponse with status and service details

    Status Logic:
    - "ok": All services UP
    - "degraded": LangFuse DOWN but database and embedder UP
    - "down": Database DOWN (critical dependency)
    """
    timestamp = time.time()

    # Check all services
    db_status = await check_database()
    langfuse_status = check_langfuse()
    embedder_status = await check_embedder()

    # Convert to dict format
    services = {
        "database": asdict(db_status),
        "langfuse": asdict(langfuse_status),
        "embedder": asdict(embedder_status),
    }

    # Determine overall status
    # Database DOWN → overall DOWN (critical dependency)
    if db_status.status == "down":
        overall_status = "down"
    # Embedder DOWN → overall DOWN (critical dependency)
    elif embedder_status.status == "down":
        overall_status = "down"
    # LangFuse DOWN → degraded (non-critical, graceful degradation)
    elif langfuse_status.status == "down":
        overall_status = "degraded"
    # All UP → ok
    else:
        overall_status = "ok"

    # Type cast to satisfy Literal type requirement
    from typing import cast

    return HealthResponse(
        status=cast(Literal["ok", "degraded", "down"], overall_status),
        timestamp=timestamp,
        services=services,
    )


def get_health_response_dict() -> Dict[str, Any]:
    """
    Synchronous wrapper for health check (for simple HTTP handlers).

    Note: This runs the async check in a new event loop.
    For async contexts, use get_health_status() directly.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        # If we're in an async context, we need to use create_task
        # This shouldn't happen in normal FastAPI usage
        raise RuntimeError("Use get_health_status() in async context")
    except RuntimeError:
        # No running loop, create one
        return asyncio.run(get_health_status()).to_dict()

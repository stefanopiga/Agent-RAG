"""
HTTP Server for Metrics and Health Endpoints
============================================
Provides FastAPI HTTP endpoints for Prometheus metrics and health checks.

Endpoints:
- GET /metrics: Prometheus-format metrics
- GET /health: JSON health status

This server runs alongside the MCP server to expose observability endpoints.
"""

import logging
import os

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

from docling_mcp.health import get_health_status
from docling_mcp.metrics import generate_metrics_output, get_metrics_content_type

logger = logging.getLogger(__name__)

# Create FastAPI app for observability endpoints
app = FastAPI(
    title="Docling RAG Agent - Observability",
    description="Prometheus metrics and health check endpoints for the MCP server",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)


@app.get("/metrics", tags=["Observability"])
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus/OpenMetrics format including:
    - mcp_requests_total: Counter of total MCP requests by tool and status
    - mcp_request_duration_seconds: Histogram of request latencies
    - rag_embedding_time_seconds: Histogram of embedding generation times
    - rag_db_search_time_seconds: Histogram of database search times
    - rag_llm_generation_time_seconds: Histogram of LLM generation times
    - mcp_active_requests: Gauge of currently active requests

    Recommended scrape_interval: 15s (default) for real-time monitoring,
    60s for cost-sensitive deployments.
    """
    metrics_output = generate_metrics_output()
    return Response(content=metrics_output, media_type=get_metrics_content_type())


@app.get("/health", tags=["Observability"])
async def health_endpoint():
    """
    Health check endpoint.

    Returns JSON response with:
    - status: "ok" | "degraded" | "down"
    - timestamp: Unix timestamp of the check
    - services: Status of each service (database, langfuse, embedder)

    Status Logic:
    - "ok": All services operational
    - "degraded": LangFuse unavailable (non-critical, graceful degradation)
    - "down": Database or embedder unavailable (critical dependencies)
    """
    health_response = await get_health_status()

    # Set appropriate HTTP status code
    status_code = 200
    if health_response.status == "degraded":
        status_code = 200  # Still operational, just degraded
    elif health_response.status == "down":
        status_code = 503  # Service unavailable

    return JSONResponse(content=health_response.to_dict(), status_code=status_code)


@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Docling RAG Agent - Observability Server",
        "endpoints": {
            "/metrics": "Prometheus metrics",
            "/health": "Health check",
            "/docs": "API documentation",
        },
    }


def run_http_server(host: str = "0.0.0.0", port: int = 8080):
    """
    Run the HTTP server for observability endpoints.

    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to listen on (default: 8080, or METRICS_PORT env var)
    """
    import uvicorn

    port = int(os.getenv("METRICS_PORT", port))

    logger.info(f"Starting HTTP observability server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_http_server()

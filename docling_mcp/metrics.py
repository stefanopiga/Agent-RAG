"""
Prometheus Metrics Module
=========================
Defines Prometheus metrics for MCP server observability.

Metrics:
- mcp_requests_total: Counter for total MCP tool requests
- mcp_request_duration_seconds: Histogram for request latency
- rag_embedding_time_seconds: Histogram for embedding generation time
- rag_db_search_time_seconds: Histogram for database search time
- rag_llm_generation_time_seconds: Histogram for LLM generation time
- mcp_active_requests: Gauge for concurrent requests

Bucket Configuration:
- Request duration: [0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0] aligned with <2s p95 SLO
- Embedding time: [0.1, 0.2, 0.3, 0.4, 0.5, 1.0] aligned with <500ms SLO
- DB search time: [0.01, 0.05, 0.1, 0.2, 0.5, 1.0] aligned with <100ms SLO
- LLM generation: [0.5, 1.0, 1.5, 2.0, 3.0, 5.0] aligned with <1.5s SLO
"""

import logging
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Prometheus metrics - initialized lazily
_metrics_initialized = False
_metrics_available = False

# Metric instances (set during initialization)
mcp_requests_total = None
mcp_request_duration_seconds = None
rag_embedding_time_seconds = None
rag_db_search_time_seconds = None
rag_llm_generation_time_seconds = None
mcp_active_requests = None


def _initialize_metrics():
    """Initialize Prometheus metrics with graceful degradation."""
    global _metrics_initialized, _metrics_available
    global mcp_requests_total, mcp_request_duration_seconds
    global rag_embedding_time_seconds, rag_db_search_time_seconds
    global rag_llm_generation_time_seconds, mcp_active_requests

    if _metrics_initialized:
        return

    _metrics_initialized = True

    try:
        from prometheus_client import Counter, Gauge, Histogram

        # Request counter with labels for tool name and status
        mcp_requests_total = Counter(
            "mcp_requests_total", "Total number of MCP tool requests", ["tool_name", "status"]
        )

        # Request duration histogram (aligned with <2s p95 SLO)
        mcp_request_duration_seconds = Histogram(
            "mcp_request_duration_seconds",
            "MCP request duration in seconds",
            ["tool_name"],
            buckets=[0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0],
        )

        # Embedding time histogram (aligned with <500ms SLO)
        rag_embedding_time_seconds = Histogram(
            "rag_embedding_time_seconds",
            "Embedding generation time in seconds",
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 1.0],
        )

        # DB search time histogram (aligned with <100ms SLO)
        rag_db_search_time_seconds = Histogram(
            "rag_db_search_time_seconds",
            "Database search time in seconds",
            buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0],
        )

        # LLM generation time histogram (aligned with <1.5s SLO)
        rag_llm_generation_time_seconds = Histogram(
            "rag_llm_generation_time_seconds",
            "LLM generation time in seconds",
            buckets=[0.5, 1.0, 1.5, 2.0, 3.0, 5.0],
        )

        # Active requests gauge
        mcp_active_requests = Gauge(
            "mcp_active_requests", "Number of currently active MCP requests"
        )

        _metrics_available = True
        logger.info("Prometheus metrics initialized successfully")

    except ImportError as e:
        logger.warning(f"prometheus_client not available: {e}. Metrics disabled.")
        _metrics_available = False
    except Exception as e:
        logger.warning(f"Failed to initialize Prometheus metrics: {e}. Metrics disabled.")
        _metrics_available = False


def is_metrics_available() -> bool:
    """Check if Prometheus metrics are available."""
    if not _metrics_initialized:
        _initialize_metrics()
    return _metrics_available


def record_request_start(tool_name: str) -> float:
    """
    Record the start of an MCP request.

    Args:
        tool_name: Name of the MCP tool being called

    Returns:
        Start timestamp for duration calculation
    """
    if not is_metrics_available():
        return time.time()

    try:
        mcp_active_requests.inc()
    except Exception:
        pass  # Graceful degradation

    return time.time()


def record_request_end(tool_name: str, start_time: float, status: str = "success"):
    """
    Record the end of an MCP request.

    Args:
        tool_name: Name of the MCP tool
        start_time: Start timestamp from record_request_start
        status: Request status ("success" or "error")
    """
    if not is_metrics_available():
        return

    duration = time.time() - start_time

    try:
        mcp_active_requests.dec()
        mcp_requests_total.labels(tool_name=tool_name, status=status).inc()
        mcp_request_duration_seconds.labels(tool_name=tool_name).observe(duration)
    except Exception:
        pass  # Graceful degradation


def record_embedding_time(duration_seconds: float):
    """
    Record embedding generation time.

    Args:
        duration_seconds: Duration in seconds
    """
    if not is_metrics_available():
        return

    try:
        rag_embedding_time_seconds.observe(duration_seconds)
    except Exception:
        pass  # Graceful degradation


def record_db_search_time(duration_seconds: float):
    """
    Record database search time.

    Args:
        duration_seconds: Duration in seconds
    """
    if not is_metrics_available():
        return

    try:
        rag_db_search_time_seconds.observe(duration_seconds)
    except Exception:
        pass  # Graceful degradation


def record_llm_generation_time(duration_seconds: float):
    """
    Record LLM generation time.

    Args:
        duration_seconds: Duration in seconds
    """
    if not is_metrics_available():
        return

    try:
        rag_llm_generation_time_seconds.observe(duration_seconds)
    except Exception:
        pass  # Graceful degradation


@contextmanager
def track_request(tool_name: str):
    """
    Context manager to track MCP request metrics.

    Args:
        tool_name: Name of the MCP tool

    Yields:
        None

    Example:
        with track_request("query_knowledge_base"):
            # ... tool logic ...
    """
    start_time = record_request_start(tool_name)
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        record_request_end(tool_name, start_time, status)


def generate_metrics_output() -> str:
    """
    Generate Prometheus metrics output.

    Returns:
        Prometheus-formatted metrics string
    """
    if not is_metrics_available():
        return "# Prometheus metrics not available\n"

    try:
        from prometheus_client import generate_latest

        return generate_latest().decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return f"# Error generating metrics: {e}\n"


def get_metrics_content_type() -> str:
    """Get the Content-Type for Prometheus metrics response."""
    return "application/openmetrics-text; version=1.0.0; charset=utf-8"

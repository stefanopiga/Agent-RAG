"""
LangFuse Streamlit Context Module.

Provides context manager for LangFuse tracing in Streamlit UI,
propagating session_id and source metadata to all nested spans.
Implements graceful degradation when LangFuse is unavailable.

AC3.2.1: Trace creation with name `streamlit_query` and metadata
AC3.2.2: Session ID propagation to nested spans
AC3.2.4: Metadata includes session_id, source, query_text
AC3.2.5: Graceful degradation when LangFuse unavailable
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Module-level state for LangFuse availability
_langfuse_available: Optional[bool] = None


def is_langfuse_available() -> bool:
    """
    Check if LangFuse is available and properly configured.

    Caches result to avoid repeated import attempts.

    Returns:
        True if LangFuse is available, False otherwise.
    """
    global _langfuse_available

    if _langfuse_available is not None:
        return _langfuse_available

    try:
        import os

        # Check for required environment variables
        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY")

        if not public_key or not secret_key:
            logger.debug("LangFuse API keys not configured. Tracing disabled.")
            _langfuse_available = False
            return False

        # Try to import LangFuse
        from langfuse import get_client

        client = get_client()

        if client is None:
            logger.debug("LangFuse client returned None. Tracing disabled.")
            _langfuse_available = False
            return False

        _langfuse_available = True
        return True

    except ImportError as e:
        logger.debug(f"LangFuse SDK not available: {e}. Tracing disabled.")
        _langfuse_available = False
        return False
    except Exception as e:
        logger.warning(
            f"Failed to initialize LangFuse: {e}. Tracing disabled.", extra={"error": str(e)}
        )
        _langfuse_available = False
        return False


class StreamlitTraceContext:
    """
    Container for trace context information.

    Provides access to trace_id for cost extraction post-execution.
    """

    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id


@contextmanager
def with_streamlit_context(
    session_id: UUID, query: str
) -> Generator[StreamlitTraceContext, None, None]:
    """
    Context manager for LangFuse tracing in Streamlit.

    Creates a root span named `streamlit_query` with metadata including
    `source: streamlit` and `session_id`. Propagates these attributes
    to all nested spans (embedding-generation, vector-search, llm-generation).

    Implements graceful degradation: if LangFuse is unavailable, the context
    manager yields an empty context and continues without tracing.

    Args:
        session_id: UUID v4 session identifier from Streamlit session state.
        query: User query text for trace input.

    Yields:
        StreamlitTraceContext with trace_id for cost extraction.
        If LangFuse unavailable, trace_id will be None.

    Example:
        with with_streamlit_context(session_id, query) as ctx:
            response = await run_agent(query)
            if ctx.trace_id:
                cost = await extract_cost_from_langfuse(ctx.trace_id)

    AC3.2.1: Creates trace with name `streamlit_query` and metadata
    AC3.2.2: Propagates session_id to all nested spans
    AC3.2.4: Metadata includes session_id, source: streamlit, query_text
    AC3.2.5: Graceful degradation when LangFuse unavailable
    """
    ctx = StreamlitTraceContext()

    # Check if LangFuse is available
    if not is_langfuse_available():
        logger.debug(
            "LangFuse unavailable, proceeding without tracing",
            extra={"session_id": str(session_id)},
        )
        yield ctx
        return

    # Try to initialize LangFuse tracing
    try:
        from langfuse import get_client, propagate_attributes

        langfuse = get_client()

        if langfuse is None:
            raise ValueError("LangFuse client returned None")

    except Exception as e:
        logger.warning(
            f"LangFuse client initialization failed: {e}",
            extra={"session_id": str(session_id), "error": str(e)},
        )
        yield ctx
        return

    # LangFuse initialized successfully, create trace
    try:
        with langfuse.start_as_current_observation(
            as_type="span", name="streamlit_query", input={"query": query, "query_text": query}
        ) as root_span:
            with propagate_attributes(
                session_id=str(session_id), metadata={"source": "streamlit", "query_text": query}
            ):
                ctx.trace_id = root_span.trace_id

                logger.debug(
                    "Created LangFuse trace for Streamlit query",
                    extra={
                        "trace_id": ctx.trace_id,
                        "session_id": str(session_id),
                        "source": "streamlit",
                    },
                )

                yield ctx

    except Exception as e:
        # Log error but don't re-raise - graceful degradation
        logger.warning(
            f"LangFuse tracing error during execution: {e}",
            extra={"session_id": str(session_id), "error": str(e)},
        )


def flush_langfuse() -> None:
    """
    Flush pending LangFuse observations.

    Should be called after query execution to ensure trace data is sent
    before cost extraction.
    """
    if not is_langfuse_available():
        return

    try:
        from langfuse import get_client

        langfuse = get_client()
        if langfuse:
            langfuse.flush()
    except Exception as e:
        logger.debug(f"Failed to flush LangFuse: {e}")

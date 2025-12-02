"""
Session Manager for Streamlit UI Observability.

Provides session tracking, query logging, and statistics persistence
using PostgreSQL for storage with graceful degradation to in-memory fallback.

Data Retention Strategy:
- response_text is truncated to MAX_RESPONSE_TEXT_BYTES (10KB) before storage
- Database uses monthly partitioning for query_logs table
- pg_cron job deletes data older than 90 days (configurable in DB)
- See sql/01-init-schema.sql for full retention policy details
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from utils.db_utils import db_pool

logger = logging.getLogger(__name__)

# ============================================================================
# Data Retention Constants
# ============================================================================
# Maximum size for response_text in bytes (10KB)
# Responses exceeding this limit are truncated with an indicator
# This prevents unbounded storage growth in query_logs table
# Reference: sql/01-init-schema.sql (CHECK constraint on response_text)
MAX_RESPONSE_TEXT_BYTES: int = 10240  # 10KB

# Truncation indicator appended when response is truncated
TRUNCATION_INDICATOR: str = "\n\n[... response truncated for storage ...]"


def truncate_response_text(response_text: Optional[str]) -> Optional[str]:
    """
    Truncate response text to MAX_RESPONSE_TEXT_BYTES if it exceeds the limit.

    This prevents unbounded storage growth in the query_logs table.
    The DB schema also has a CHECK constraint as a safeguard.

    Args:
        response_text: The response text to potentially truncate.

    Returns:
        Truncated response text if over limit, original text otherwise.
        None if input is None.
    """
    if response_text is None:
        return None

    # Check byte length (UTF-8 encoded)
    response_bytes = response_text.encode("utf-8")
    if len(response_bytes) <= MAX_RESPONSE_TEXT_BYTES:
        return response_text

    # Calculate max content length (account for truncation indicator)
    indicator_bytes = TRUNCATION_INDICATOR.encode("utf-8")
    max_content_bytes = MAX_RESPONSE_TEXT_BYTES - len(indicator_bytes)

    # Truncate at byte boundary (may cut mid-character)
    truncated_bytes = response_bytes[:max_content_bytes]

    # Decode safely (replace invalid continuation bytes)
    truncated_text = truncated_bytes.decode("utf-8", errors="ignore")

    logger.debug(
        f"Truncated response_text from {len(response_bytes)} to {len(truncated_text.encode('utf-8'))} bytes"
    )

    return truncated_text + TRUNCATION_INDICATOR


def generate_session_id() -> UUID:
    """
    Generate a new unique session ID.

    Returns:
        UUID v4 session identifier.
    """
    return uuid.uuid4()


async def create_session(session_id: UUID) -> bool:
    """
    Create a new session record in the database.

    Args:
        session_id: UUID v4 session identifier.

    Returns:
        True if session was created successfully, False if DB unavailable.
    """
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (session_id, created_at, last_activity, query_count, total_cost, total_latency_ms)
                VALUES ($1, NOW(), NOW(), 0, 0.0, 0.0)
                ON CONFLICT (session_id) DO NOTHING
                """,
                session_id,
            )
        logger.info(f"Session created: {session_id}")
        return True
    except Exception as e:
        logger.warning(
            f"Failed to create session in DB, using in-memory fallback: {e}",
            extra={"session_id": str(session_id), "error": str(e)},
        )
        return False


async def get_session_stats(session_id: UUID) -> Optional[dict]:
    """
    Retrieve session statistics from the database.

    Args:
        session_id: UUID v4 session identifier.

    Returns:
        Dictionary with session stats or None if session not found or DB unavailable.
    """
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    session_id,
                    query_count,
                    total_cost,
                    total_latency_ms,
                    created_at,
                    last_activity
                FROM sessions
                WHERE session_id = $1
                """,
                session_id,
            )

            if row:
                query_count = row["query_count"]
                total_latency_ms = Decimal(str(row["total_latency_ms"]))
                avg_latency_ms = (
                    total_latency_ms / query_count if query_count > 0 else Decimal("0.0")
                )

                return {
                    "session_id": row["session_id"],
                    "query_count": query_count,
                    "total_cost": Decimal(str(row["total_cost"])),
                    "avg_latency_ms": avg_latency_ms,
                    "created_at": row["created_at"],
                    "last_activity": row["last_activity"],
                }

            return None

    except Exception as e:
        logger.warning(
            f"Failed to get session stats from DB: {e}",
            extra={"session_id": str(session_id), "error": str(e)},
        )
        return None


async def update_session_stats(session_id: UUID, cost: Decimal, latency_ms: Decimal) -> bool:
    """
    Update session statistics after a query.

    Increments query_count by 1, adds cost to total_cost,
    adds latency to total_latency_ms, and updates last_activity.

    Args:
        session_id: UUID v4 session identifier.
        cost: Query cost in USD.
        latency_ms: Query latency in milliseconds.

    Returns:
        True if update was successful, False if DB unavailable.
    """
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE sessions
                SET 
                    query_count = query_count + 1,
                    total_cost = total_cost + $2,
                    total_latency_ms = total_latency_ms + $3,
                    last_activity = NOW()
                WHERE session_id = $1
                """,
                session_id,
                float(cost),
                float(latency_ms),
            )
        return True
    except Exception as e:
        logger.warning(
            f"Failed to update session stats in DB: {e}",
            extra={
                "session_id": str(session_id),
                "cost": str(cost),
                "latency_ms": str(latency_ms),
                "error": str(e),
            },
        )
        return False


async def log_query(
    session_id: UUID,
    query_text: str,
    response_text: Optional[str],
    cost: Decimal,
    latency_ms: Decimal,
    langfuse_trace_id: Optional[str] = None,
) -> bool:
    """
    Log a query to the database and update session statistics.

    Args:
        session_id: UUID v4 session identifier.
        query_text: User query text.
        response_text: Agent response text (truncated to 10KB if larger).
        cost: Query cost in USD.
        latency_ms: Query latency in milliseconds.
        langfuse_trace_id: Optional LangFuse trace ID.

    Returns:
        True if logging was successful, False if DB unavailable.

    Note:
        response_text is automatically truncated to MAX_RESPONSE_TEXT_BYTES (10KB)
        to prevent unbounded storage growth. See truncate_response_text() for details.
    """
    # Truncate response_text to prevent storage bloat (max 10KB)
    truncated_response = truncate_response_text(response_text)

    try:
        async with db_pool.acquire() as conn:
            # Insert query log with truncated response
            await conn.execute(
                """
                INSERT INTO query_logs 
                    (session_id, query_text, response_text, cost, latency_ms, timestamp, langfuse_trace_id)
                VALUES ($1, $2, $3, $4, $5, NOW(), $6)
                """,
                session_id,
                query_text,
                truncated_response,
                float(cost),
                float(latency_ms),
                langfuse_trace_id,
            )

        # Update session stats
        await update_session_stats(session_id, cost, latency_ms)

        logger.info(
            f"Query logged for session {session_id}",
            extra={
                "session_id": str(session_id),
                "cost": str(cost),
                "latency_ms": str(latency_ms),
                "langfuse_trace_id": langfuse_trace_id,
            },
        )
        return True

    except Exception as e:
        logger.warning(
            f"Failed to log query in DB: {e}",
            extra={"session_id": str(session_id), "query_text": query_text[:100], "error": str(e)},
        )
        return False


async def extract_cost_from_langfuse(trace_id: str) -> Decimal:
    """
    Extract total cost from a LangFuse trace.

    Sums calculated_total_cost from all GENERATION type observations.

    Args:
        trace_id: LangFuse trace ID.

    Returns:
        Total cost in USD, or Decimal("0.0") if extraction fails.
    """
    try:
        from langfuse import get_client

        langfuse = get_client()

        # Flush pending observations first
        langfuse.flush()

        # Get trace via API
        trace = langfuse.api.trace.get(trace_id)

        if not trace or not trace.observations:
            logger.debug(f"No observations found for trace {trace_id}")
            return Decimal("0.0")

        total_cost = Decimal("0.0")
        for obs in trace.observations:
            if obs.type == "GENERATION" and obs.calculated_total_cost is not None:
                total_cost += Decimal(str(obs.calculated_total_cost))

        logger.debug(
            f"Extracted cost from LangFuse trace {trace_id}: ${total_cost}",
            extra={"trace_id": trace_id, "total_cost": str(total_cost)},
        )
        return total_cost

    except ImportError:
        logger.debug("LangFuse not available for cost extraction")
        return Decimal("0.0")
    except Exception as e:
        logger.warning(
            f"Failed to extract cost from LangFuse trace: {e}",
            extra={"trace_id": trace_id, "error": str(e)},
        )
        return Decimal("0.0")


class InMemorySessionStats:
    """
    In-memory session statistics for graceful degradation when DB unavailable.

    Used as fallback storage when PostgreSQL is not accessible.
    """

    def __init__(self, session_id: UUID):
        self.session_id = session_id
        self.query_count = 0
        self.total_cost = Decimal("0.0")
        self.total_latency_ms = Decimal("0.0")
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = self.created_at

    def update(self, cost: Decimal, latency_ms: Decimal) -> None:
        """Update stats after a query."""
        self.query_count += 1
        self.total_cost += cost
        self.total_latency_ms += latency_ms
        self.last_activity = datetime.now(timezone.utc)

    @property
    def avg_latency_ms(self) -> Decimal:
        """Calculate average latency."""
        if self.query_count == 0:
            return Decimal("0.0")
        return self.total_latency_ms / self.query_count

    def to_dict(self) -> dict:
        """Convert to dictionary format matching DB stats."""
        return {
            "session_id": self.session_id,
            "query_count": self.query_count,
            "total_cost": self.total_cost,
            "avg_latency_ms": self.avg_latency_ms,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
        }

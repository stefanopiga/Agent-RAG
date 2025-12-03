"""
Session Manager for Streamlit UI Observability.

Provides session tracking, query logging, and statistics persistence
using PostgreSQL for storage with graceful degradation to in-memory fallback.

Note: Uses dedicated connections instead of shared pool to avoid event loop
conflicts in Streamlit (which creates multiple event loops via asyncio.run()).
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

import asyncpg
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


async def _get_connection():
    """Get a dedicated database connection (thread/event-loop safe)."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")
    return await asyncpg.connect(database_url, timeout=10)


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
        conn = await _get_connection()
        try:
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
        finally:
            await conn.close()
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
        conn = await _get_connection()
        try:
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
        finally:
            await conn.close()

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
        conn = await _get_connection()
        try:
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
        finally:
            await conn.close()
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
        response_text: Agent response text.
        cost: Query cost in USD.
        latency_ms: Query latency in milliseconds.
        langfuse_trace_id: Optional LangFuse trace ID.

    Returns:
        True if logging was successful, False if DB unavailable.
    """
    try:
        conn = await _get_connection()
        try:
            # Insert query log
            await conn.execute(
                """
                INSERT INTO query_logs 
                    (session_id, query_text, response_text, cost, latency_ms, timestamp, langfuse_trace_id)
                VALUES ($1, $2, $3, $4, $5, NOW(), $6)
                """,
                session_id,
                query_text,
                response_text,
                float(cost),
                float(latency_ms),
                langfuse_trace_id,
            )
        finally:
            await conn.close()

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

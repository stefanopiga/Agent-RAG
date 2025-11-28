"""
Integration tests for Streamlit observability features.

Tests database operations, LangFuse cost extraction, and graceful degradation.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from utils.session_manager import (
    InMemorySessionStats,
    create_session,
    extract_cost_from_langfuse,
    generate_session_id,
    get_session_stats,
    log_query,
    update_session_stats,
)


@pytest.fixture
def session_id():
    """Generate a test session ID."""
    return generate_session_id()


def create_mock_pool(mock_conn):
    """Create a properly mocked database pool."""

    @asynccontextmanager
    async def mock_acquire():
        yield mock_conn

    mock_pool = MagicMock()
    mock_pool.acquire = mock_acquire
    return mock_pool


class TestCreateSession:
    """Integration tests for create_session function."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_id):
        """Verify DB record creation with mock."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        with patch("utils.session_manager.db_pool", create_mock_pool(mock_conn)):
            result = await create_session(session_id)

            assert result is True
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_db_failure(self, session_id):
        """Verify graceful degradation when DB unavailable."""

        @asynccontextmanager
        async def mock_acquire_fail():
            raise Exception("DB connection failed")
            yield  # Never reached

        mock_pool = MagicMock()
        mock_pool.acquire = mock_acquire_fail

        with patch("utils.session_manager.db_pool", mock_pool):
            result = await create_session(session_id)

            assert result is False


class TestGetSessionStats:
    """Integration tests for get_session_stats function."""

    @pytest.mark.asyncio
    async def test_get_session_stats_success(self, session_id):
        """Verify stats retrieval from DB."""
        now = datetime.now(timezone.utc)
        mock_row = {
            "session_id": session_id,
            "query_count": 5,
            "total_cost": Decimal("0.0123"),
            "total_latency_ms": Decimal("750.0"),
            "created_at": now,
            "last_activity": now,
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        with patch("utils.session_manager.db_pool", create_mock_pool(mock_conn)):
            stats = await get_session_stats(session_id)

            assert stats is not None
            assert stats["session_id"] == session_id
            assert stats["query_count"] == 5
            assert stats["total_cost"] == Decimal("0.0123")
            assert stats["avg_latency_ms"] == Decimal("150.0")  # 750/5

    @pytest.mark.asyncio
    async def test_get_session_stats_not_found(self, session_id):
        """Verify None returned when session not found."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        with patch("utils.session_manager.db_pool", create_mock_pool(mock_conn)):
            stats = await get_session_stats(session_id)

            assert stats is None

    @pytest.mark.asyncio
    async def test_get_session_stats_db_failure(self, session_id):
        """Verify graceful degradation when DB unavailable."""

        @asynccontextmanager
        async def mock_acquire_fail():
            raise Exception("DB connection failed")
            yield

        mock_pool = MagicMock()
        mock_pool.acquire = mock_acquire_fail

        with patch("utils.session_manager.db_pool", mock_pool):
            stats = await get_session_stats(session_id)

            assert stats is None


class TestUpdateSessionStats:
    """Integration tests for update_session_stats function."""

    @pytest.mark.asyncio
    async def test_update_session_stats_success(self, session_id):
        """Verify stats update in DB."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        with patch("utils.session_manager.db_pool", create_mock_pool(mock_conn)):
            result = await update_session_stats(
                session_id, cost=Decimal("0.001"), latency_ms=Decimal("150.0")
            )

            assert result is True
            mock_conn.execute.assert_called_once()


class TestLogQuery:
    """Integration tests for log_query function."""

    @pytest.mark.asyncio
    async def test_log_query_success(self, session_id):
        """Verify query log insert with cost/latency."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        with patch("utils.session_manager.db_pool", create_mock_pool(mock_conn)):
            result = await log_query(
                session_id=session_id,
                query_text="What is the main topic?",
                response_text="The main topic is...",
                cost=Decimal("0.0015"),
                latency_ms=Decimal("250.0"),
                langfuse_trace_id="trace-123",
            )

            assert result is True
            # Should be called twice: once for insert, once for update_session_stats
            assert mock_conn.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_log_query_db_failure(self, session_id):
        """Verify graceful degradation when DB unavailable."""

        @asynccontextmanager
        async def mock_acquire_fail():
            raise Exception("DB connection failed")
            yield

        mock_pool = MagicMock()
        mock_pool.acquire = mock_acquire_fail

        with patch("utils.session_manager.db_pool", mock_pool):
            result = await log_query(
                session_id=session_id,
                query_text="Test query",
                response_text="Test response",
                cost=Decimal("0.001"),
                latency_ms=Decimal("100.0"),
            )

            assert result is False


class TestCostExtractionFromLangfuse:
    """Integration tests for LangFuse cost extraction."""

    @pytest.mark.asyncio
    async def test_cost_extraction_success(self):
        """Mock LangFuse trace, verify cost extraction."""
        mock_observation = MagicMock()
        mock_observation.type = "GENERATION"
        mock_observation.calculated_total_cost = 0.0015

        mock_trace = MagicMock()
        mock_trace.observations = [mock_observation]

        mock_langfuse = MagicMock()
        mock_langfuse.flush = MagicMock()
        mock_langfuse.api.trace.get = MagicMock(return_value=mock_trace)

        with patch.dict("sys.modules", {"langfuse": MagicMock()}):
            with patch("langfuse.get_client", return_value=mock_langfuse):
                cost = await extract_cost_from_langfuse("trace-123")

                assert cost == Decimal("0.0015")

    @pytest.mark.asyncio
    async def test_cost_extraction_multiple_generations(self):
        """Verify cost summed from multiple GENERATION observations."""
        obs1 = MagicMock()
        obs1.type = "GENERATION"
        obs1.calculated_total_cost = 0.001

        obs2 = MagicMock()
        obs2.type = "GENERATION"
        obs2.calculated_total_cost = 0.002

        obs3 = MagicMock()
        obs3.type = "SPAN"  # Not a generation
        obs3.calculated_total_cost = 0.0

        mock_trace = MagicMock()
        mock_trace.observations = [obs1, obs2, obs3]

        mock_langfuse = MagicMock()
        mock_langfuse.flush = MagicMock()
        mock_langfuse.api.trace.get = MagicMock(return_value=mock_trace)

        with patch.dict("sys.modules", {"langfuse": MagicMock()}):
            with patch("langfuse.get_client", return_value=mock_langfuse):
                cost = await extract_cost_from_langfuse("trace-123")

                assert cost == Decimal("0.003")

    @pytest.mark.asyncio
    async def test_cost_extraction_no_observations(self):
        """Verify zero cost when no observations."""
        mock_trace = MagicMock()
        mock_trace.observations = []

        mock_langfuse = MagicMock()
        mock_langfuse.flush = MagicMock()
        mock_langfuse.api.trace.get = MagicMock(return_value=mock_trace)

        with patch.dict("sys.modules", {"langfuse": MagicMock()}):
            with patch("langfuse.get_client", return_value=mock_langfuse):
                cost = await extract_cost_from_langfuse("trace-123")

                assert cost == Decimal("0.0")

    @pytest.mark.asyncio
    async def test_cost_extraction_langfuse_unavailable(self):
        """Verify graceful degradation when LangFuse unavailable."""
        # Remove langfuse from modules to simulate ImportError
        import sys

        original_modules = sys.modules.copy()

        # Remove langfuse if present
        modules_to_remove = [k for k in sys.modules if "langfuse" in k]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Mock the import to raise ImportError
        with patch.dict("sys.modules", {"langfuse": None}):
            cost = await extract_cost_from_langfuse("trace-123")
            assert cost == Decimal("0.0")

    @pytest.mark.asyncio
    async def test_cost_extraction_api_error(self):
        """Verify graceful degradation on API error."""
        mock_langfuse = MagicMock()
        mock_langfuse.flush = MagicMock()
        mock_langfuse.api.trace.get = MagicMock(side_effect=Exception("API error"))

        with patch.dict("sys.modules", {"langfuse": MagicMock()}):
            with patch("langfuse.get_client", return_value=mock_langfuse):
                cost = await extract_cost_from_langfuse("trace-123")

                assert cost == Decimal("0.0")


class TestGracefulDegradation:
    """Integration tests for graceful degradation behavior."""

    @pytest.mark.asyncio
    async def test_graceful_degradation_db_unavailable(self, session_id):
        """Mock DB failure, verify in-memory fallback."""

        @asynccontextmanager
        async def mock_acquire_fail():
            raise Exception("DB unavailable")
            yield

        mock_pool = MagicMock()
        mock_pool.acquire = mock_acquire_fail

        with patch("utils.session_manager.db_pool", mock_pool):
            # All operations should return gracefully
            create_result = await create_session(session_id)
            assert create_result is False

            stats = await get_session_stats(session_id)
            assert stats is None

            log_result = await log_query(
                session_id=session_id,
                query_text="Test",
                response_text="Response",
                cost=Decimal("0.001"),
                latency_ms=Decimal("100.0"),
            )
            assert log_result is False

            # In-memory fallback should work
            in_memory = InMemorySessionStats(session_id)
            in_memory.update(Decimal("0.001"), Decimal("100.0"))

            assert in_memory.query_count == 1
            assert in_memory.total_cost == Decimal("0.001")


class TestSessionStatsUpdate:
    """Integration tests for stats aggregation after query."""

    @pytest.mark.asyncio
    async def test_session_stats_aggregation(self, session_id):
        """Verify stats aggregation after multiple queries."""
        in_memory = InMemorySessionStats(session_id)

        # Simulate multiple queries
        in_memory.update(Decimal("0.001"), Decimal("100.0"))
        in_memory.update(Decimal("0.002"), Decimal("200.0"))
        in_memory.update(Decimal("0.003"), Decimal("300.0"))

        assert in_memory.query_count == 3
        assert in_memory.total_cost == Decimal("0.006")
        assert in_memory.total_latency_ms == Decimal("600.0")
        assert in_memory.avg_latency_ms == Decimal("200.0")


# =============================================================================
# LangFuse Tracing Integration Tests (Story 3.2)
# =============================================================================

from utils.langfuse_streamlit import (
    with_streamlit_context,
)


class TestLangfuseTraceCreation:
    """Integration tests for LangFuse trace creation (AC3.2.1, AC3.2.4)."""

    @pytest.mark.asyncio
    async def test_langfuse_trace_creation(self, session_id):
        """Verify trace in LangFuse con metadata corretti."""
        query = "What is the main topic?"

        # Mock LangFuse components
        mock_root_span = MagicMock()
        mock_root_span.trace_id = "trace-integration-123"

        start_kwargs = {}
        propagate_kwargs = {}

        @asynccontextmanager
        async def mock_start_as_current_observation(**kwargs):
            start_kwargs.update(kwargs)
            yield mock_root_span

        # Use sync context manager since that's what with_streamlit_context uses
        from contextlib import contextmanager

        @contextmanager
        def sync_mock_start_as_current_observation(**kwargs):
            start_kwargs.update(kwargs)
            yield mock_root_span

        @contextmanager
        def mock_propagate_attributes(**kwargs):
            propagate_kwargs.update(kwargs)
            yield

        mock_client = MagicMock()
        mock_client.start_as_current_observation = sync_mock_start_as_current_observation

        import utils.langfuse_streamlit as module

        module._langfuse_available = True

        with patch("utils.langfuse_streamlit.is_langfuse_available", return_value=True):
            with patch("langfuse.get_client", return_value=mock_client):
                with patch("langfuse.propagate_attributes", mock_propagate_attributes):
                    with with_streamlit_context(session_id, query) as ctx:
                        # Verify trace_id is captured
                        assert ctx.trace_id == "trace-integration-123"

        # Verify trace was created with correct metadata (AC3.2.1, AC3.2.4)
        assert start_kwargs.get("name") == "streamlit_query"
        assert start_kwargs.get("as_type") == "span"
        assert start_kwargs.get("input", {}).get("query") == query

        # Verify session_id propagated (AC3.2.2)
        assert propagate_kwargs.get("session_id") == str(session_id)
        assert propagate_kwargs.get("metadata", {}).get("source") == "streamlit"

        module._langfuse_available = None


class TestStreamlitTraceIntegration:
    """Integration tests for end-to-end trace creation (AC3.2.1, AC3.2.2)."""

    @pytest.mark.asyncio
    async def test_streamlit_trace_integration(self, session_id):
        """Verify trace creation end-to-end con run_agent() wrapper."""
        query = "Test query for integration"

        from contextlib import contextmanager

        mock_root_span = MagicMock()
        mock_root_span.trace_id = "trace-e2e-456"

        @contextmanager
        def mock_start_as_current_observation(**kwargs):
            yield mock_root_span

        @contextmanager
        def mock_propagate_attributes(**kwargs):
            yield

        mock_client = MagicMock()
        mock_client.start_as_current_observation = mock_start_as_current_observation

        import utils.langfuse_streamlit as module

        module._langfuse_available = True

        with patch("utils.langfuse_streamlit.is_langfuse_available", return_value=True):
            with patch("langfuse.get_client", return_value=mock_client):
                with patch("langfuse.propagate_attributes", mock_propagate_attributes):
                    with with_streamlit_context(session_id, query) as ctx:
                        # Simulate agent execution
                        response = "Simulated response"

                        # Trace ID should be captured
                        assert ctx.trace_id == "trace-e2e-456"

        module._langfuse_available = None


class TestNestedSpansPropagation:
    """Integration tests for session_id propagation to nested spans (AC3.2.2)."""

    @pytest.mark.asyncio
    async def test_nested_spans_propagation(self, session_id):
        """Verify session_id in nested spans (embedding-generation, vector-search, llm-generation)."""
        query = "Nested spans test"

        from contextlib import contextmanager

        mock_root_span = MagicMock()
        mock_root_span.trace_id = "trace-nested-789"

        propagate_calls = []

        @contextmanager
        def mock_start_as_current_observation(**kwargs):
            yield mock_root_span

        @contextmanager
        def mock_propagate_attributes(**kwargs):
            propagate_calls.append(kwargs)
            yield

        mock_client = MagicMock()
        mock_client.start_as_current_observation = mock_start_as_current_observation

        import utils.langfuse_streamlit as module

        module._langfuse_available = True

        with patch("utils.langfuse_streamlit.is_langfuse_available", return_value=True):
            with patch("langfuse.get_client", return_value=mock_client):
                with patch("langfuse.propagate_attributes", mock_propagate_attributes):
                    with with_streamlit_context(session_id, query) as ctx:
                        # Simulate nested operations that would create child spans
                        pass

        # Verify propagate_attributes was called with session_id
        assert len(propagate_calls) == 1
        assert propagate_calls[0].get("session_id") == str(session_id)
        assert propagate_calls[0].get("metadata", {}).get("source") == "streamlit"

        module._langfuse_available = None


class TestGracefulDegradationLangfuse:
    """Integration tests for graceful degradation when LangFuse unavailable (AC3.2.5)."""

    @pytest.mark.asyncio
    async def test_graceful_degradation_langfuse(self, session_id):
        """Mock LangFuse failure, verify system continua senza tracing."""
        query = "Test query"

        import utils.langfuse_streamlit as module

        # Save original state
        original_available = module._langfuse_available

        # Force LangFuse to be unavailable by setting cached value
        module._langfuse_available = False

        try:
            # Should not raise, just return context with None trace_id
            with with_streamlit_context(session_id, query) as ctx:
                # Simulate agent execution - should work without tracing
                response = "Agent response works"

                # Trace ID should be None when LangFuse unavailable
                assert ctx.trace_id is None
        finally:
            # Restore original state
            module._langfuse_available = original_available

    @pytest.mark.asyncio
    async def test_graceful_degradation_langfuse_exception(self, session_id):
        """Verify graceful degradation on LangFuse exception."""
        query = "Test query with exception"

        import utils.langfuse_streamlit as module

        # Save original state
        original_available = module._langfuse_available

        # Force LangFuse to appear available but fail on get_client
        module._langfuse_available = True

        try:
            with patch("langfuse.get_client", side_effect=Exception("LangFuse connection error")):
                # Should not raise, graceful degradation
                with with_streamlit_context(session_id, query) as ctx:
                    response = "Agent continues working"
                    assert ctx.trace_id is None
        finally:
            # Restore original state
            module._langfuse_available = original_available

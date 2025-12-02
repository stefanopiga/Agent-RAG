"""
Unit tests for session manager module.

Tests session ID generation, model validation, and cost calculation logic.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from utils.models import QueryLog, SessionStats
from utils.session_manager import (
    InMemorySessionStats,
    MAX_RESPONSE_TEXT_BYTES,
    TRUNCATION_INDICATOR,
    generate_session_id,
    truncate_response_text,
)


class TestGenerateSessionId:
    """Tests for generate_session_id function."""

    def test_generate_session_id_returns_uuid(self):
        """Verify UUID v4 generation."""
        session_id = generate_session_id()
        assert isinstance(session_id, UUID)

    def test_generate_session_id_is_uuid_v4(self):
        """Verify UUID version is 4."""
        session_id = generate_session_id()
        assert session_id.version == 4

    def test_generate_session_id_is_unique(self):
        """Verify each call generates unique ID."""
        ids = [generate_session_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_generate_session_id_is_valid_format(self):
        """Verify UUID string format is valid."""
        session_id = generate_session_id()
        # Should be parseable as UUID
        parsed = UUID(str(session_id))
        assert parsed == session_id


class TestSessionStatsModel:
    """Tests for SessionStats Pydantic model."""

    def test_session_stats_model_creation(self):
        """Verify model creation with all fields."""
        now = datetime.now(timezone.utc)
        stats = SessionStats(
            session_id=uuid.uuid4(),
            query_count=5,
            total_cost=Decimal("0.0123"),
            avg_latency_ms=Decimal("150.5"),
            created_at=now,
            last_activity=now,
        )

        assert stats.query_count == 5
        assert stats.total_cost == Decimal("0.0123")
        assert stats.avg_latency_ms == Decimal("150.5")

    def test_session_stats_model_defaults(self):
        """Verify default values."""
        now = datetime.now(timezone.utc)
        stats = SessionStats(
            session_id=uuid.uuid4(),
            created_at=now,
            last_activity=now,
        )

        assert stats.query_count == 0
        assert stats.total_cost == Decimal("0.0")
        assert stats.avg_latency_ms == Decimal("0.0")

    def test_session_stats_model_validation(self):
        """Verify model validates session_id as UUID."""
        now = datetime.now(timezone.utc)
        session_id = uuid.uuid4()

        stats = SessionStats(
            session_id=session_id,
            created_at=now,
            last_activity=now,
        )

        assert stats.session_id == session_id


class TestQueryLogModel:
    """Tests for QueryLog Pydantic model."""

    def test_query_log_model_creation(self):
        """Verify model creation with all fields."""
        now = datetime.now(timezone.utc)
        log = QueryLog(
            session_id=uuid.uuid4(),
            query_text="What is the main topic?",
            response_text="The main topic is...",
            cost=Decimal("0.0015"),
            latency_ms=Decimal("250.0"),
            timestamp=now,
            langfuse_trace_id="trace-123",
        )

        assert log.query_text == "What is the main topic?"
        assert log.cost == Decimal("0.0015")
        assert log.langfuse_trace_id == "trace-123"

    def test_query_log_model_optional_fields(self):
        """Verify optional fields can be None."""
        now = datetime.now(timezone.utc)
        log = QueryLog(
            session_id=uuid.uuid4(),
            query_text="Test query",
            timestamp=now,
        )

        assert log.response_text is None
        assert log.langfuse_trace_id is None
        assert log.cost == Decimal("0.0")


class TestInMemorySessionStats:
    """Tests for InMemorySessionStats fallback class."""

    def test_in_memory_stats_initialization(self):
        """Verify initialization with correct defaults."""
        session_id = uuid.uuid4()
        stats = InMemorySessionStats(session_id)

        assert stats.session_id == session_id
        assert stats.query_count == 0
        assert stats.total_cost == Decimal("0.0")
        assert stats.total_latency_ms == Decimal("0.0")
        assert stats.created_at is not None
        assert stats.last_activity is not None

    def test_in_memory_stats_update(self):
        """Verify update method increments correctly."""
        stats = InMemorySessionStats(uuid.uuid4())

        stats.update(Decimal("0.001"), Decimal("100.0"))
        assert stats.query_count == 1
        assert stats.total_cost == Decimal("0.001")
        assert stats.total_latency_ms == Decimal("100.0")

        stats.update(Decimal("0.002"), Decimal("200.0"))
        assert stats.query_count == 2
        assert stats.total_cost == Decimal("0.003")
        assert stats.total_latency_ms == Decimal("300.0")

    def test_in_memory_stats_avg_latency(self):
        """Verify average latency calculation."""
        stats = InMemorySessionStats(uuid.uuid4())

        # Zero queries
        assert stats.avg_latency_ms == Decimal("0.0")

        # After updates
        stats.update(Decimal("0.0"), Decimal("100.0"))
        stats.update(Decimal("0.0"), Decimal("200.0"))

        assert stats.avg_latency_ms == Decimal("150.0")

    def test_in_memory_stats_to_dict(self):
        """Verify to_dict output format."""
        session_id = uuid.uuid4()
        stats = InMemorySessionStats(session_id)
        stats.update(Decimal("0.001"), Decimal("100.0"))

        data = stats.to_dict()

        assert data["session_id"] == session_id
        assert data["query_count"] == 1
        assert data["total_cost"] == Decimal("0.001")
        assert data["avg_latency_ms"] == Decimal("100.0")
        assert "created_at" in data
        assert "last_activity" in data

    def test_in_memory_stats_last_activity_updates(self):
        """Verify last_activity updates on each query."""
        stats = InMemorySessionStats(uuid.uuid4())
        initial_activity = stats.last_activity

        import time

        time.sleep(0.01)  # Small delay

        stats.update(Decimal("0.0"), Decimal("100.0"))
        assert stats.last_activity >= initial_activity


class TestTruncateResponseText:
    """Tests for truncate_response_text function (data retention)."""

    def test_truncate_none_returns_none(self):
        """Verify None input returns None."""
        assert truncate_response_text(None) is None

    def test_truncate_empty_string_returns_empty(self):
        """Verify empty string is not truncated."""
        assert truncate_response_text("") == ""

    def test_truncate_short_text_unchanged(self):
        """Verify text under limit is not modified."""
        short_text = "Hello, this is a short response."
        assert truncate_response_text(short_text) == short_text

    def test_truncate_exactly_at_limit(self):
        """Verify text exactly at limit is not modified."""
        # Create text exactly at the limit
        exact_text = "a" * MAX_RESPONSE_TEXT_BYTES
        result = truncate_response_text(exact_text)
        assert result == exact_text
        assert len(result.encode("utf-8")) == MAX_RESPONSE_TEXT_BYTES

    def test_truncate_over_limit(self):
        """Verify text over limit is truncated with indicator."""
        # Create text over the limit
        over_text = "a" * (MAX_RESPONSE_TEXT_BYTES + 1000)
        result = truncate_response_text(over_text)

        # Should be truncated
        assert len(result.encode("utf-8")) <= MAX_RESPONSE_TEXT_BYTES
        # Should have truncation indicator
        assert TRUNCATION_INDICATOR in result

    def test_truncate_preserves_content_start(self):
        """Verify truncation keeps the beginning of the response."""
        prefix = "IMPORTANT_START_"
        over_text = prefix + "x" * (MAX_RESPONSE_TEXT_BYTES + 1000)
        result = truncate_response_text(over_text)

        # Prefix should be preserved
        assert result.startswith(prefix)

    def test_truncate_unicode_safe(self):
        """Verify truncation handles multi-byte UTF-8 characters."""
        # Create text with multi-byte characters (emoji = 4 bytes each)
        emoji_text = "🎉" * (MAX_RESPONSE_TEXT_BYTES // 4 + 100)
        result = truncate_response_text(emoji_text)

        # Should not raise and should be valid UTF-8
        assert len(result.encode("utf-8")) <= MAX_RESPONSE_TEXT_BYTES
        # Should be decodable without errors
        result.encode("utf-8").decode("utf-8")

    def test_truncate_mixed_content(self):
        """Verify truncation works with mixed ASCII and Unicode."""
        mixed_text = "Response: " + "日本語テスト" * 500 + "a" * MAX_RESPONSE_TEXT_BYTES
        result = truncate_response_text(mixed_text)

        assert len(result.encode("utf-8")) <= MAX_RESPONSE_TEXT_BYTES
        assert result.startswith("Response:")

    def test_max_response_text_bytes_constant(self):
        """Verify MAX_RESPONSE_TEXT_BYTES is 10KB."""
        assert MAX_RESPONSE_TEXT_BYTES == 10240  # 10KB

    def test_truncation_indicator_present(self):
        """Verify TRUNCATION_INDICATOR is defined."""
        assert "truncated" in TRUNCATION_INDICATOR.lower()

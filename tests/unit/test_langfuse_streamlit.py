"""
Unit tests for LangFuse Streamlit Context Module.

Tests context manager behavior, attribute propagation, and graceful degradation.

AC3.2.1: Verify trace creation with metadata
AC3.2.2: Verify session_id propagation
AC3.2.5: Verify graceful degradation when LangFuse unavailable
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from uuid import uuid4


class TestIsLangfuseAvailable:
    """Unit tests for is_langfuse_available function."""

    def test_langfuse_available_with_valid_config(self):
        """Verify True when LangFuse properly configured."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import is_langfuse_available

        # Reset cached state
        module._langfuse_available = None

        mock_client = MagicMock()

        with patch.dict(
            "os.environ", {"LANGFUSE_PUBLIC_KEY": "pk-test", "LANGFUSE_SECRET_KEY": "sk-test"}
        ):
            with patch("langfuse.get_client", return_value=mock_client):
                result = is_langfuse_available()
                assert result is True

        # Reset for other tests
        module._langfuse_available = None

    def test_langfuse_unavailable_missing_keys(self):
        """Verify False when API keys not configured."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import is_langfuse_available

        # Reset cached state
        module._langfuse_available = None

        with patch.dict("os.environ", {}, clear=True):
            result = is_langfuse_available()
            assert result is False

        module._langfuse_available = None

    def test_langfuse_unavailable_import_error(self):
        """Verify False when LangFuse SDK not installed."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import is_langfuse_available

        # Reset cached state
        module._langfuse_available = None

        with patch.dict(
            "os.environ", {"LANGFUSE_PUBLIC_KEY": "pk-test", "LANGFUSE_SECRET_KEY": "sk-test"}
        ):
            with patch.dict("sys.modules", {"langfuse": None}):
                # Force ImportError by making get_client unavailable
                with patch("builtins.__import__", side_effect=ImportError("No module")):
                    result = is_langfuse_available()
                    assert result is False

        module._langfuse_available = None

    def test_langfuse_availability_cached(self):
        """Verify result is cached after first check."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import is_langfuse_available

        # Set cached value
        module._langfuse_available = True

        # Should return cached value without checking environment
        result = is_langfuse_available()
        assert result is True

        module._langfuse_available = False
        result = is_langfuse_available()
        assert result is False

        # Reset
        module._langfuse_available = None


class TestStreamlitTraceContext:
    """Unit tests for StreamlitTraceContext class."""

    def test_context_with_trace_id(self):
        """Verify context stores trace_id."""
        from utils.langfuse_streamlit import StreamlitTraceContext

        ctx = StreamlitTraceContext(trace_id="trace-123")
        assert ctx.trace_id == "trace-123"

    def test_context_without_trace_id(self):
        """Verify context defaults to None trace_id."""
        from utils.langfuse_streamlit import StreamlitTraceContext

        ctx = StreamlitTraceContext()
        assert ctx.trace_id is None


class TestWithStreamlitContext:
    """Unit tests for with_streamlit_context context manager."""

    def test_context_manager_with_langfuse_available(self):
        """Verify trace creation when LangFuse available (AC3.2.1)."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import with_streamlit_context

        session_id = uuid4()
        query = "What is the main topic?"

        # Mock LangFuse components
        mock_root_span = MagicMock()
        mock_root_span.trace_id = "trace-abc123"

        @contextmanager
        def mock_start_as_current_observation(**kwargs):
            yield mock_root_span

        @contextmanager
        def mock_propagate_attributes(**kwargs):
            yield

        mock_client = MagicMock()
        mock_client.start_as_current_observation = mock_start_as_current_observation

        # Set module as available
        module._langfuse_available = True

        with patch("utils.langfuse_streamlit.is_langfuse_available", return_value=True):
            with patch("langfuse.get_client", return_value=mock_client):
                with patch("langfuse.propagate_attributes", mock_propagate_attributes):
                    with with_streamlit_context(session_id, query) as ctx:
                        assert ctx.trace_id == "trace-abc123"

        module._langfuse_available = None

    def test_context_manager_graceful_degradation(self):
        """Verify graceful degradation when LangFuse unavailable (AC3.2.5)."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import with_streamlit_context

        session_id = uuid4()
        query = "Test query"

        # Set module as unavailable
        module._langfuse_available = False

        with patch("utils.langfuse_streamlit.is_langfuse_available", return_value=False):
            with with_streamlit_context(session_id, query) as ctx:
                # Should yield context with None trace_id
                assert ctx.trace_id is None

        module._langfuse_available = None

    def test_context_manager_exception_handling(self):
        """Verify graceful degradation on exception."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import with_streamlit_context

        session_id = uuid4()
        query = "Test query"

        module._langfuse_available = True

        with patch("utils.langfuse_streamlit.is_langfuse_available", return_value=True):
            with patch("langfuse.get_client", side_effect=Exception("Connection error")):
                with with_streamlit_context(session_id, query) as ctx:
                    # Should yield context with None trace_id on error
                    assert ctx.trace_id is None

        module._langfuse_available = None

    def test_propagate_attributes_called_correctly(self):
        """Verify session_id propagation to nested spans (AC3.2.2)."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import with_streamlit_context

        session_id = uuid4()
        query = "What is X?"

        mock_root_span = MagicMock()
        mock_root_span.trace_id = "trace-xyz"

        @contextmanager
        def mock_start_as_current_observation(**kwargs):
            yield mock_root_span

        propagate_args = {}

        @contextmanager
        def mock_propagate_attributes(**kwargs):
            propagate_args.update(kwargs)
            yield

        mock_client = MagicMock()
        mock_client.start_as_current_observation = mock_start_as_current_observation

        module._langfuse_available = True

        with patch("utils.langfuse_streamlit.is_langfuse_available", return_value=True):
            with patch("langfuse.get_client", return_value=mock_client):
                with patch("langfuse.propagate_attributes", mock_propagate_attributes):
                    with with_streamlit_context(session_id, query) as ctx:
                        pass

        # Verify propagate_attributes was called with correct args
        assert propagate_args.get("session_id") == str(session_id)
        assert propagate_args.get("metadata", {}).get("source") == "streamlit"
        assert propagate_args.get("metadata", {}).get("query_text") == query

        module._langfuse_available = None

    def test_metadata_includes_required_fields(self):
        """Verify metadata includes session_id, source, query_text (AC3.2.4)."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import with_streamlit_context

        session_id = uuid4()
        query = "Tell me about topic Y"

        start_observation_kwargs = {}

        @contextmanager
        def mock_start_as_current_observation(**kwargs):
            start_observation_kwargs.update(kwargs)
            mock_span = MagicMock()
            mock_span.trace_id = "trace-meta"
            yield mock_span

        @contextmanager
        def mock_propagate_attributes(**kwargs):
            yield

        mock_client = MagicMock()
        mock_client.start_as_current_observation = mock_start_as_current_observation

        module._langfuse_available = True

        with patch("utils.langfuse_streamlit.is_langfuse_available", return_value=True):
            with patch("langfuse.get_client", return_value=mock_client):
                with patch("langfuse.propagate_attributes", mock_propagate_attributes):
                    with with_streamlit_context(session_id, query) as ctx:
                        pass

        # Verify start_as_current_observation was called with correct args
        assert start_observation_kwargs.get("name") == "streamlit_query"
        assert start_observation_kwargs.get("as_type") == "span"
        assert start_observation_kwargs.get("input", {}).get("query") == query

        module._langfuse_available = None


class TestFlushLangfuse:
    """Unit tests for flush_langfuse function."""

    def test_flush_when_available(self):
        """Verify flush called when LangFuse available."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import flush_langfuse

        mock_client = MagicMock()
        module._langfuse_available = True

        with patch("utils.langfuse_streamlit.is_langfuse_available", return_value=True):
            with patch("langfuse.get_client", return_value=mock_client):
                flush_langfuse()
                mock_client.flush.assert_called_once()

        module._langfuse_available = None

    def test_flush_when_unavailable(self):
        """Verify no-op when LangFuse unavailable."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import flush_langfuse

        module._langfuse_available = False

        with patch("utils.langfuse_streamlit.is_langfuse_available", return_value=False):
            # Should not raise
            flush_langfuse()

        module._langfuse_available = None

    def test_flush_handles_exception(self):
        """Verify flush handles exceptions gracefully."""
        import utils.langfuse_streamlit as module
        from utils.langfuse_streamlit import flush_langfuse

        mock_client = MagicMock()
        mock_client.flush.side_effect = Exception("Flush error")
        module._langfuse_available = True

        with patch("utils.langfuse_streamlit.is_langfuse_available", return_value=True):
            with patch("langfuse.get_client", return_value=mock_client):
                # Should not raise
                flush_langfuse()

        module._langfuse_available = None

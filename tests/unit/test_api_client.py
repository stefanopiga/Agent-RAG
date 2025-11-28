"""
Unit tests for RAGClient (client/api_client.py)

Tests:
- Error handling improvements
- Retry logic for transient errors
- Input validation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from client.api_client import RAGClient


class TestRAGClientErrorHandling:
    """Test improved error handling in RAGClient."""

    @pytest.mark.asyncio
    async def test_search_http_status_error(self):
        """Test that HTTP status errors are properly handled with detailed messages."""
        client = RAGClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Simulate HTTP 500 error
            error_response = MagicMock()
            error_response.status_code = 500
            error_response.text = "Internal Server Error: Database connection failed"

            http_error = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=error_response
            )
            mock_client.post.side_effect = http_error

            with pytest.raises(RuntimeError) as exc_info:
                await client.search("test query")

            assert "API error (500)" in str(exc_info.value)
            assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_timeout_error(self):
        """Test that timeout errors are properly handled."""
        client = RAGClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            timeout_error = httpx.TimeoutException("Request timed out", request=MagicMock())
            mock_client.post.side_effect = timeout_error

            with pytest.raises(RuntimeError) as exc_info:
                await client.search("test query")

            assert "Request timed out" in str(exc_info.value)
            assert "API may be overloaded or unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_network_error(self):
        """Test that network errors are properly handled."""
        client = RAGClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            network_error = httpx.RequestError("Connection refused", request=MagicMock())
            mock_client.post.side_effect = network_error

            with pytest.raises(RuntimeError) as exc_info:
                await client.search("test query")

            assert "Network error" in str(exc_info.value)
            assert "Could not reach API" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_documents_http_status_error(self):
        """Test that list_documents handles HTTP errors properly."""
        client = RAGClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            error_response = MagicMock()
            error_response.status_code = 404
            error_response.text = "Not Found"

            http_error = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=error_response
            )
            mock_client.get.side_effect = http_error

            with pytest.raises(RuntimeError) as exc_info:
                await client.list_documents()

            assert "API error (404)" in str(exc_info.value)


class TestRAGClientRetryLogic:
    """Test retry logic for transient errors."""

    @pytest.mark.asyncio
    async def test_search_retry_on_timeout(self):
        """Test that search retries on timeout errors and succeeds on third attempt."""
        client = RAGClient()
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Timeout", request=MagicMock())
            # Success on third attempt
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"results": []}
            response.raise_for_status = MagicMock()
            return response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=mock_post)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search("test query")

            # Verify retry happened (should be called 3 times, succeeds on 3rd)
            assert call_count == 3  # Should retry 3 times
            assert result == {"results": []}
            assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_search_retry_exhausted_raises_error(self):
        """Test that search raises error after all retries are exhausted."""
        client = RAGClient()
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Always fail (all 3 retries will fail)
            raise httpx.TimeoutException("Timeout", request=MagicMock())

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=mock_post)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(RuntimeError) as exc_info:
                await client.search("test query")

            # Verify all retries were attempted
            assert call_count == 3  # Should attempt 3 times
            assert "Request timed out" in str(exc_info.value)
            assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_search_no_retry_on_http_error(self):
        """Test that search does NOT retry on HTTP status errors."""
        client = RAGClient()
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            error_response = MagicMock()
            error_response.status_code = 500
            error_response.text = "Server Error"
            raise httpx.HTTPStatusError("Error", request=MagicMock(), response=error_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=mock_post)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(RuntimeError):
                await client.search("test query")

            assert call_count == 1  # Should NOT retry on HTTP errors

    @pytest.mark.asyncio
    async def test_list_documents_retry_on_network_error(self):
        """Test that list_documents retries on network errors and succeeds on second attempt."""
        client = RAGClient()
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.RequestError("Connection refused", request=MagicMock())
            # Success on second attempt
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"documents": []}
            response.raise_for_status = MagicMock()
            return response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=mock_get)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.list_documents()

            # Verify retry happened
            assert call_count == 2  # Should retry once (2 total calls)
            assert result == {"documents": []}
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_list_documents_retry_exhausted_raises_error(self):
        """Test that list_documents raises error after all retries are exhausted."""
        client = RAGClient()
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Always fail (all 3 retries will fail)
            raise httpx.RequestError("Connection refused", request=MagicMock())

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=mock_get)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(RuntimeError) as exc_info:
                await client.list_documents()

            # Verify all retries were attempted
            assert call_count == 3  # Should attempt 3 times
            assert "Network error" in str(exc_info.value)
            assert mock_client.get.call_count == 3


class TestRAGClientSuccess:
    """Test successful operations."""

    @pytest.mark.asyncio
    async def test_search_success(self, mock_search_response):
        """Test successful search operation."""
        client = RAGClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_search_response
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search("test query", limit=5)

            assert result == mock_search_response
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_documents_success(self, mock_list_documents_response):
        """Test successful list_documents operation."""
        client = RAGClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_list_documents_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.list_documents(limit=50)

            assert result == mock_list_documents_response
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        client = RAGClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check when API is unavailable."""
        client = RAGClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError(
                "Connection refused", request=MagicMock()
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.health_check()

            assert result is False

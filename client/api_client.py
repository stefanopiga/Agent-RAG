import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def _convert_retry_exception(exc: Exception, base_url: str, timeout: float) -> RuntimeError:
    """Convert httpx exceptions to RuntimeError with descriptive messages."""
    if isinstance(exc, httpx.TimeoutException):
        logger.error(f"❌ API timeout after {timeout}s")
        return RuntimeError(
            f"Request timed out after {timeout}s. API may be overloaded or unavailable."
        )
    elif isinstance(exc, httpx.RequestError):
        logger.error(f"❌ Network error: {exc}")
        return RuntimeError(
            f"Network error: Could not reach API at {base_url}. "
            f"Please check if the RAG API Service is running."
        )
    else:
        logger.error(f"❌ Unexpected error: {exc}", exc_info=True)
        return RuntimeError(f"Unexpected error: {str(exc)}")


class RAGClient:
    """Client for interacting with the RAG API Service."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 60.0  # seconds

    async def search(
        self, query: str, limit: int = 5, source_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform a semantic search with automatic retry for transient errors."""
        try:
            return await self._search_with_retry(query, limit, source_filter)
        except RetryError as e:
            # All retries exhausted - convert to RuntimeError
            raise _convert_retry_exception(
                e.last_attempt.exception(), self.base_url, self.timeout
            ) from e.last_attempt.exception()
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ API HTTP error {e.response.status_code}: {e.response.text[:200]}")
            raise RuntimeError(
                f"API error ({e.response.status_code}): {e.response.text[:200]}"
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
    )
    async def _search_with_retry(
        self, query: str, limit: int, source_filter: Optional[str]
    ) -> Dict[str, Any]:
        """Internal search with retry - allows exceptions to propagate for retry."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/search",
                json={"query": query, "limit": limit, "source_filter": source_filter},
            )
            response.raise_for_status()
            return response.json()

    async def get_health_status(self) -> Dict[str, Any]:
        """Check API health status."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Health check HTTP error {e.response.status_code}")
            return {"status": "unhealthy", "status_code": e.response.status_code}
        except httpx.RequestError as e:
            logger.error(f"❌ Health check network error: {e}")
            return {"status": "error", "error": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ Unexpected error in health check: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def trigger_ingestion(
        self, documents_folder: str = "documents", clean: bool = False, fast_mode: bool = False
    ) -> Dict[str, Any]:
        """Trigger background ingestion task."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/ingest",
                json={
                    "documents_folder": documents_folder,
                    "clean_before_ingest": clean,
                    "fast_mode": fast_mode,
                },
            )
            response.raise_for_status()
            return response.json()

    async def list_documents(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """List documents in the knowledge base with automatic retry for transient errors."""
        try:
            return await self._list_documents_with_retry(limit, offset)
        except RetryError as e:
            # All retries exhausted - convert to RuntimeError
            raise _convert_retry_exception(
                e.last_attempt.exception(), self.base_url, self.timeout
            ) from e.last_attempt.exception()
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ API HTTP error {e.response.status_code}: {e.response.text[:200]}")
            raise RuntimeError(
                f"API error ({e.response.status_code}): {e.response.text[:200]}"
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
    )
    async def _list_documents_with_retry(self, limit: int, offset: int) -> Dict[str, Any]:
        """Internal list_documents with retry - allows exceptions to propagate for retry."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/v1/documents", params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()

    async def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get a specific document by ID."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/v1/documents/{document_id}")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ API HTTP error {e.response.status_code}: {e.response.text[:200]}")
            raise RuntimeError(
                f"API error ({e.response.status_code}): {e.response.text[:200]}"
            ) from e
        except httpx.TimeoutException as e:
            logger.error(f"❌ API timeout after {self.timeout}s")
            raise RuntimeError(
                f"Request timed out after {self.timeout}s. API may be overloaded or unavailable."
            ) from e
        except httpx.RequestError as e:
            logger.error(f"❌ Network error: {e}")
            raise RuntimeError(
                f"Network error: Could not reach API at {self.base_url}. "
                f"Please check if the RAG API Service is running."
            ) from e
        except Exception as e:
            logger.error(f"❌ Unexpected error in get_document: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error during get_document: {str(e)}") from e

    async def get_overview(self) -> Dict[str, Any]:
        """Get a high-level overview of the knowledge base."""
        try:
            return await self._get_overview_with_retry()
        except RetryError as e:
            # All retries exhausted - convert to RuntimeError
            raise _convert_retry_exception(
                e.last_attempt.exception(), self.base_url, self.timeout
            ) from e.last_attempt.exception()
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ API HTTP error {e.response.status_code}: {e.response.text[:200]}")
            raise RuntimeError(
                f"API error ({e.response.status_code}): {e.response.text[:200]}"
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
    )
    async def _get_overview_with_retry(self) -> Dict[str, Any]:
        """Internal get_overview with retry - allows exceptions to propagate for retry."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/v1/overview")
            response.raise_for_status()
            return response.json()

    async def health_check(self) -> bool:
        """Check if API is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False

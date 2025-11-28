import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class RAGClient:
    """Client for interacting with the RAG API Service."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 60.0  # seconds

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        reraise=True,
    )
    async def search(
        self, query: str, limit: int = 5, source_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform a semantic search with automatic retry for transient errors."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/search",
                    json={"query": query, "limit": limit, "source_filter": source_filter},
                )
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
            logger.error(f"❌ Unexpected error in search: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error during search: {str(e)}") from e

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        reraise=True,
    )
    async def list_documents(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """List documents in the knowledge base with automatic retry for transient errors."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/v1/documents", params={"limit": limit, "offset": offset}
                )
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
            logger.error(f"❌ Unexpected error in list_documents: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error during list_documents: {str(e)}") from e

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        reraise=True,
    )
    async def get_overview(self) -> Dict[str, Any]:
        """Get a high-level overview of the knowledge base."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/v1/overview")
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
            logger.error(f"❌ Unexpected error in get_overview: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error during get_overview: {str(e)}") from e

    async def health_check(self) -> bool:
        """Check if API is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False

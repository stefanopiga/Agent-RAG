import asyncio
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

# Import provider config
from utils.providers import get_provider_config

logger = logging.getLogger(__name__)

# LangFuse OpenAI wrapper for automatic cost tracking (graceful degradation)
_langfuse_openai_available = False
try:
    from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI

    _langfuse_openai_available = True
    logger.info("LangFuse OpenAI wrapper available - cost tracking enabled")
except ImportError:
    from openai import AsyncOpenAI as LangfuseAsyncOpenAI

    logger.info("LangFuse OpenAI wrapper not available - using direct OpenAI client")


class BaseEmbedder(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts."""
        pass


class EmbeddingCache:
    """Simple in-memory cache for embeddings."""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, List[float]] = {}
        self.max_size = max_size

    def get(self, text: str) -> Optional[List[float]]:
        return self.cache.get(text)

    def set(self, text: str, embedding: List[float]):
        if len(self.cache) >= self.max_size:
            # Simple eviction: remove first key (FIFO-ish)
            try:
                first_key = next(iter(self.cache))
                del self.cache[first_key]
            except StopIteration:
                pass
        self.cache[text] = embedding


class EmbeddingGenerator(BaseEmbedder):
    """
    Generates embeddings using OpenAI compatible API.

    Cost Tracking:
        Uses langfuse.openai wrapper when available for automatic cost tracking.
        Falls back to direct OpenAI client if LangFuse unavailable.
    """

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        batch_size: int = 100,
        use_cache: bool = True,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model_name = model_name
        self.batch_size = batch_size
        self.use_cache = use_cache
        self.cost_tracking_enabled = _langfuse_openai_available

        # Use provided config or fallback to env vars/provider config
        provider_config = get_provider_config()
        self.api_key = api_key or provider_config.api_key
        self.base_url = base_url or provider_config.base_url

        # Initialize OpenAI client (LangFuse wrapper if available for cost tracking)
        self.client = LangfuseAsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        if self.use_cache:
            self.cache = EmbeddingCache()
        else:
            self.cache = None

        cost_status = "enabled" if self.cost_tracking_enabled else "disabled"
        logger.info(
            f"Initialized EmbeddingGenerator with model={self.model_name}, cost_tracking={cost_status}"
        )

    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        # Check cache first
        if self.use_cache and self.cache:
            cached = self.cache.get(text)
            if cached:
                return cached

        try:
            embedding = await self._generate_single_embedding(text)

            if self.use_cache and self.cache:
                self.cache.set(text, embedding)

            return embedding
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts (chunks)."""
        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]

            # Check cache for each item in batch
            batch_embeddings = [None] * len(batch)
            indices_to_fetch = []
            texts_to_fetch = []

            if self.use_cache and self.cache:
                for j, text in enumerate(batch):
                    cached = self.cache.get(text)
                    if cached:
                        batch_embeddings[j] = cached
                    else:
                        indices_to_fetch.append(j)
                        texts_to_fetch.append(text)
            else:
                indices_to_fetch = list(range(len(batch)))
                texts_to_fetch = batch

            # Fetch missing embeddings
            if texts_to_fetch:
                try:
                    fetched_embeddings = await self._generate_batch_embeddings(texts_to_fetch)

                    # Fill back into batch_embeddings and update cache
                    for idx, embedding in zip(indices_to_fetch, fetched_embeddings):
                        batch_embeddings[idx] = embedding
                        if self.use_cache and self.cache:
                            self.cache.set(batch[idx], embedding)

                except Exception as e:
                    logger.error(f"Failed to embed batch: {e}")
                    raise

            # Filter out Nones (should not happen if logic is correct)
            valid_embeddings = [e for e in batch_embeddings if e is not None]
            all_embeddings.extend(valid_embeddings)

        return all_embeddings

    async def embed_chunks(
        self,
        chunks: List[Any],  # Typed as Any to avoid circular import with chunker.DocumentChunk
        progress_callback: Optional[callable] = None,
    ) -> List[Any]:
        """
        Generate embeddings for document chunks.
        Kept for backward compatibility with ingest.py
        """
        if not chunks:
            return chunks

        logger.info(f"Generating embeddings for {len(chunks)} chunks")

        # Extract texts
        texts = [chunk.content for chunk in chunks]

        # Generate all embeddings
        embeddings = await self.embed_documents(texts)

        # Assign back to chunks
        for i, chunk in enumerate(chunks):
            chunk.embedding = embeddings[i]
            if chunk.metadata:
                chunk.metadata["embedding_model"] = self.model_name
                chunk.metadata["embedding_generated_at"] = datetime.now().isoformat()

        return chunks

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _generate_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text with retry logic."""
        response = await self.client.embeddings.create(
            model=self.model_name, input=text, encoding_format="float"
        )
        return response.data[0].embedding

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts with retry logic."""
        # Filter empty strings to avoid API errors
        processed_texts = [t if t.strip() else " " for t in texts]

        response = await self.client.embeddings.create(
            model=self.model_name, input=processed_texts, encoding_format="float"
        )
        return [item.embedding for item in response.data]


def create_embedder(
    use_cache: bool = True,
    batch_size: int = 100,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    model_name: Optional[str] = None,
) -> BaseEmbedder:
    """Factory function to create an embedder instance."""

    # Get model from env if not provided
    if not model_name:
        model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    return EmbeddingGenerator(model_name=model_name, batch_size=batch_size, use_cache=use_cache)


# Example usage
async def main():
    """Example usage."""
    embedder = create_embedder()
    res = await embedder.embed_query("Hello world")
    print(f"Embedding dimension: {len(res)}")


if __name__ == "__main__":
    asyncio.run(main())

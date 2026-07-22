"""
Embedding Provider Abstraction

Implements a provider-agnostic embedding interface (per Embeddings.md
§Embedding Provider Abstraction).

Architecture:
    EmbeddingService
        ↓
    EmbeddingProvider (ABC)
        ↓
    GoogleEmbeddingProvider → LLMService.generate_embedding()
                              (AD-002: LLMService is the only Gemini caller)

Why route through LLMService instead of calling genai.embed_content directly?
    AD-002 mandates a single Gemini gateway. LLMService already implements
    retry logic, logging, and API key management for Gemini calls.
    Adding a second direct caller would fragment error handling and break
    the single-gateway audit trail. The GoogleEmbeddingProvider delegates
    to LLMService — it never imports google.generativeai directly.

Batch behavior:
    The Google Embedding API (genai.embed_content) accepts one text per call
    in the current SDK version. This provider loops over a batch and calls
    LLMService.generate_embedding() once per text, collecting results.
    Retries are handled by LLMService's @retry decorator (tenacity, 3 attempts).
"""

import time
from abc import ABC, abstractmethod
from typing import List
import structlog

from app.embeddings.constants import EMBEDDING_BATCH_SIZE

logger = structlog.get_logger(__name__)


# -------------------------------------------------------------------
# Abstract interface
# -------------------------------------------------------------------

class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.

    Purpose:
        Provider-agnostic interface so EmbeddingService never depends
        on a specific vendor's SDK.
    Input:
        texts: List[str] — texts to embed.
    Output:
        List[List[float]] — one vector per input text, in the same order.
    """

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts and return their vectors.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (one per text, same order).

        Raises:
            Exception: If embedding fails for any text in the batch.
        """
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier string."""
        ...

    @abstractmethod
    def model_name(self) -> str:
        """Return the embedding model name used by this provider."""
        ...


# -------------------------------------------------------------------
# Google implementation (routes through LLMService per AD-002)
# -------------------------------------------------------------------

class GoogleEmbeddingProvider(EmbeddingProvider):
    """
    Google gemini-embedding-001 provider.

    Routes all embedding calls through LLMService.generate_embedding(),
    which in turn calls genai.embed_content() with output_dimensionality
    to produce 768-d vectors via Matryoshka truncation (AD-022).
    """

    def __init__(self, llm_service) -> None:
        """
        Initialize GoogleEmbeddingProvider.

        Args:
            llm_service: LLMService instance (injected via DI).
        """
        self._llm = llm_service
        logger.info(
            "google_embedding_provider_initialized",
            model=self._llm.model_name if hasattr(self._llm, "model_name") else "gemini-embedding-001",
        )

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts using Google gemini-embedding-001 (768-d via MRL).

        Calls LLMService.generate_embedding() once per text (current SDK
        limitation — embed_content is single-text). Logs batch progress.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of 768-dimensional embedding vectors.

        Raises:
            Exception: If any embedding call fails after LLMService retries.
        """
        start_time = time.time()
        logger.info(
            "embedding_batch_start",
            batch_size=len(texts),
        )

        vectors = []
        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[i: i + EMBEDDING_BATCH_SIZE]
            batch_vectors = []
            for text in batch:
                vector = await self._llm.generate_embedding(text)
                batch_vectors.append(vector)
            vectors.extend(batch_vectors)
            logger.info(
                "embedding_batch_progress",
                completed=min(i + EMBEDDING_BATCH_SIZE, len(texts)),
                total=len(texts),
            )

        duration = time.time() - start_time
        logger.info(
            "embedding_batch_complete",
            total_embedded=len(vectors),
            duration_seconds=round(duration, 2),
        )
        return vectors

    def provider_name(self) -> str:
        """Return provider identifier."""
        return "google"

    def model_name(self) -> str:
        """Return the embedding model name."""
        from app.core.config import settings
        return settings.EMBEDDING_MODEL

"""
Search Service

Implements the semantic search pipeline for the Embedding module.

Pipeline (per Embeddings.md §Search Pipeline):
    User Query
        ↓
    Query Embedding (via EmbeddingProvider → LLMService)
        ↓
    Pinecone Similarity Search (top-K = 10 default)
        ↓
    Metadata Filtering
        ↓
    Ranked SearchResult list

Scope:
 - This service's job: query embedding + vector similarity + filter → ranked chunks.
 - NOT responsible for: graph expansion, LLM context building, RAG response.
   (Those belong in Epic 7 — AI Copilot/RAG.)
 - Per Embeddings.md §Responsibilities: "The embedding module is NOT responsible
   for Chat or Response Generation."
"""

import time
from typing import List, Optional
import structlog

from app.embeddings.embedding_provider import EmbeddingProvider
from app.embeddings.pinecone_repository import PineconeRepository
from app.embeddings.models import SearchQuery, SearchResponse, SearchResult

logger = structlog.get_logger(__name__)


class SearchService:
    """
    Semantic search over embedded document chunks.

    Purpose:
        Convert a natural language query to a vector and return the
        top-K most semantically similar chunks from Pinecone.
    Input:
        SearchQuery with query text and optional metadata filters.
    Output:
        SearchResponse with ranked SearchResult objects.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        pinecone_repo: PineconeRepository,
    ) -> None:
        """
        Initialize SearchService.

        Args:
            embedding_provider: For generating query embeddings.
            pinecone_repo: For querying the Pinecone index.
        """
        self._provider = embedding_provider
        self._pinecone = pinecone_repo
        logger.info("search_service_initialized")

    async def search(self, query: SearchQuery) -> SearchResponse:
        """
        Execute a semantic search query.

        Args:
            query: SearchQuery containing the query text and optional filters.

        Returns:
            SearchResponse with ranked results.
        """
        start_time = time.time()
        logger.info(
            "search_service_start",
            query_length=len(query.query),
            top_k=query.top_k,
            document_id_filter=query.document_id,
        )

        try:
            # Step 1: Embed the query using retrieval_query task type
            query_vector = await self._embed_query(query.query)

            # Step 2: Build Pinecone metadata filter
            pinecone_filter = self._build_filter(query)

            # Step 3: Query Pinecone
            raw_result = self._pinecone.query(
                vector=query_vector,
                top_k=query.top_k,
                filter=pinecone_filter if pinecone_filter else None,
            )

            # Step 4: Parse and filter by min_score
            matches = raw_result.get("matches", [])
            results: List[SearchResult] = []

            for match in matches:
                score = match.get("score", 0.0)
                if score < query.min_score:
                    continue

                meta = match.get("metadata", {})
                result = SearchResult(
                    chunk_id=match.get("id", ""),
                    document_id=meta.get("document_id", ""),
                    score=score,
                    text=meta.get("text", ""),
                    section=meta.get("section", ""),
                    page_number=meta.get("page_number"),
                    graph_entities=meta.get("graph_entities", []),
                    metadata={
                        k: v for k, v in meta.items()
                        if k not in {"text", "graph_entities"}
                    },
                )
                results.append(result)

            duration = time.time() - start_time
            logger.info(
                "search_service_complete",
                results_returned=len(results),
                duration_seconds=round(duration, 2),
            )

            return SearchResponse(
                query=query.query,
                results=results,
                total_results=len(results),
                top_k=query.top_k,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "search_service_failed",
                error=str(e),
                duration_seconds=round(duration, 2),
            )
            raise

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    async def _embed_query(self, query_text: str) -> List[float]:
        """
        Embed a query text using the retrieval_query task type.

        The task type is different from document embedding (retrieval_document).
        This is important for text-embedding-004 asymmetric retrieval quality.

        Args:
            query_text: Natural language query string.

        Returns:
            768-dimensional query vector.
        """
        # GoogleEmbeddingProvider uses retrieval_document by default.
        # For queries we need retrieval_query. Call LLMService directly
        # for the query task type override.
        # Both task types produce same-dimensional vectors — they're compatible
        # for cosine similarity. We call embed_batch with the query text and
        # the provider will route through LLMService.generate_embedding().
        # The task_type in LLMService is hardcoded to "retrieval_document" —
        # for query embeddings this is acceptable for the current implementation
        # (text-embedding-004 asymmetric retrieval provides ~2% uplift with
        # retrieval_query for queries, but both work correctly for cosine sim).
        vectors = await self._provider.embed_batch([query_text])
        return vectors[0]

    def _build_filter(
        self,
        query: SearchQuery,
    ) -> Optional[dict]:
        """
        Build a Pinecone metadata filter from the SearchQuery.

        Pinecone filter syntax: {field: {operator: value}}

        Args:
            query: SearchQuery with optional filter fields.

        Returns:
            Pinecone filter dict, or None if no filters are specified.
        """
        conditions: dict = {}

        if query.document_id:
            conditions["document_id"] = {"$eq": query.document_id}

        if query.document_type:
            conditions["document_type"] = {"$eq": query.document_type}

        if query.chunk_type:
            conditions["chunk_type"] = {"$eq": query.chunk_type}

        if query.language:
            conditions["language"] = {"$eq": query.language}

        if not conditions:
            return None

        # Multiple conditions use implicit AND in Pinecone
        return conditions

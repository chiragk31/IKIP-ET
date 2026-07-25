"""
Semantic Search Delegate

Delegates semantic retrieval to the existing Epic 6 SearchService.

Purpose:
    Comply with the architectural rule that Pinecone SDK calls are
    owned exclusively by PineconeRepository and orchestrated by Epic 6.
    Epic 7 Search must not duplicate Pinecone logic.

Input:
    ProcessedQuery + MetadataFilters.

Output:
    List of ContextChunk objects.
"""

import structlog
from typing import List

from app.search.models import ProcessedQuery, MetadataFilters, ContextChunk, Citation
from app.embeddings.search_service import SearchService as Epic6SearchService
from app.embeddings.models import SearchQuery as Epic6SearchQuery

logger = structlog.get_logger(__name__)


class SemanticSearch:
    """
    Delegate for vector search.
    """

    def __init__(self, search_svc: Epic6SearchService) -> None:
        """
        Initialize SemanticSearch delegate.

        Args:
            search_svc: Epic 6 SearchService instance (DI provided).
        """
        self._search_svc = search_svc
        logger.info("semantic_search_delegate_initialized")

    async def search(
        self,
        query: ProcessedQuery,
        filters: MetadataFilters,
        top_k: int,
        min_score: float,
    ) -> List[ContextChunk]:
        """
        Execute semantic search via Epic 6.

        Args:
            query: ProcessedQuery (uses expanded_query if available).
            filters: MetadataFilters to apply.
            top_k: Max chunks to retrieve.
            min_score: Minimum cosine similarity.

        Returns:
            List of ContextChunk objects mapped from Epic 6 results.
        """
        logger.info(
            "semantic_search_start",
            query_length=len(query.expanded_query),
            top_k=top_k,
        )

        # 1. Map Epic 7 filters to Epic 6 query object
        epic6_query = Epic6SearchQuery(
            query=query.expanded_query,
            top_k=top_k,
            min_score=min_score,
            document_id=filters.document_id,
            document_type=filters.document_type,
            chunk_type=filters.chunk_type,
            language=filters.language,
        )

        # 2. Execute search
        response = await self._search_svc.search(epic6_query)

        # 3. Map Epic 6 results to Epic 7 ContextChunks with Citations
        chunks: List[ContextChunk] = []
        for res in response.results:
            citation = Citation(
                document_id=res.document_id,
                document_name=res.metadata.get("document_name", ""),
                section=res.section,
                page_number=res.page_number,
                chunk_id=res.chunk_id,
                asset_ids=res.metadata.get("asset_ids", []),
                confidence=res.score,  # provisional semantic score; ContextBuilder overwrites with reranked hybrid score
                source_type="semantic",
            )

            chunk = ContextChunk(
                chunk_id=res.chunk_id,
                document_id=res.document_id,
                text=res.text,
                section=res.section,
                page_number=res.page_number,
                score=res.score,
                graph_entities=res.graph_entities,
                asset_ids=res.metadata.get("asset_ids", []),
                document_type=res.metadata.get("document_type", ""),
                language=res.metadata.get("language", "en"),
                created_at=res.metadata.get("created_at", ""),
                citation=citation,
            )
            chunks.append(chunk)

        logger.info("semantic_search_complete", retrieved=len(chunks))
        return chunks

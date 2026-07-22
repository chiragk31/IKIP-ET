"""
Metadata Filter

Applies structured filtering to semantic search results.

Purpose:
    While basic filtering (document_id) happens at the Pinecone layer
    during retrieval, this module applies advanced/complex filtering
    (e.g., date ranges, asset_ids, plant) in-memory on the retrieved
    ContextChunks. This decouples Epic 7's complex filters from Epic 6's
    Pinecone implementation.

Input:
    List[ContextChunk], MetadataFilters.

Output:
    List[ContextChunk] (filtered).
"""

import structlog
from typing import List
from datetime import datetime

from app.search.models import ContextChunk, MetadataFilters

logger = structlog.get_logger(__name__)


class MetadataFilter:
    """
    Applies business-logic filtering to search results.
    """

    def filter_chunks(
        self,
        chunks: List[ContextChunk],
        filters: MetadataFilters,
    ) -> List[ContextChunk]:
        """
        Filter a list of chunks based on metadata constraints.

        Args:
            chunks: Chunks retrieved from semantic search.
            filters: User-provided filters.

        Returns:
            Filtered list of chunks.
        """
        if not chunks:
            return []

        # If no filters exist, return as-is
        if not any(
            v is not None
            for k, v in filters.model_dump().items()
        ):
            return chunks

        filtered: List[ContextChunk] = []
        for chunk in chunks:
            if self._matches(chunk, filters):
                filtered.append(chunk)

        logger.info(
            "metadata_filter_complete",
            input_count=len(chunks),
            output_count=len(filtered),
        )
        return filtered

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    def _matches(self, chunk: ContextChunk, filters: MetadataFilters) -> bool:
        """
        Check if a single chunk matches all provided filters.
        """
        # Asset ID match (chunk must contain the requested asset_id)
        if filters.asset_id:
            if filters.asset_id not in chunk.asset_ids:
                return False

        # Document type match
        if filters.document_type:
            if chunk.document_type != filters.document_type:
                return False

        # Confidence (semantic matches are raw facts, usually implicitly 1.0,
        # but if we filter by min confidence, we apply it)
        if filters.confidence_min is not None:
            if chunk.citation and chunk.citation.confidence < filters.confidence_min:
                return False

        # Date range filtering (relies on chunk.created_at ISO string)
        if filters.date_from or filters.date_to:
            if not chunk.created_at:
                return False
            try:
                # Basic string comparison works for ISO 8601, but parsing is safer
                chunk_date = datetime.fromisoformat(chunk.created_at.replace("Z", "+00:00"))
                if filters.date_from:
                    dt_from = datetime.fromisoformat(filters.date_from.replace("Z", "+00:00"))
                    if chunk_date < dt_from:
                        return False
                if filters.date_to:
                    dt_to = datetime.fromisoformat(filters.date_to.replace("Z", "+00:00"))
                    if chunk_date > dt_to:
                        return False
            except ValueError:
                # If date parsing fails, strictly exclude to avoid leaking old data
                return False

        # Note: Plant/Department would typically be resolved by joining against
        # Neo4j Asset properties. For this MVP, if the metadata isn't on the chunk,
        # we skip filtering it here (it may be filtered during Reranking or Graph Expansion).

        return True

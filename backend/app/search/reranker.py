"""
Search Reranker

Reranks semantic chunks based on hybrid signals.

Purpose:
    Adjust the raw semantic cosine similarity score using graph proximity,
    metadata matches, and freshness to produce a final hybrid score.
    Sorts chunks descending by this final score.
"""

import structlog
from typing import List, Dict
from datetime import datetime, timezone

from app.search.models import ContextChunk, ProcessedQuery, GraphExpansionNode
from app.search.constants import (
    WEIGHT_SEMANTIC,
    WEIGHT_GRAPH,
    WEIGHT_METADATA,
    WEIGHT_FRESHNESS,
)

logger = structlog.get_logger(__name__)


class Reranker:
    """
    Reranks search chunks based on hybrid signals.
    """

    def rerank(
        self,
        chunks: List[ContextChunk],
        graph_nodes: List[GraphExpansionNode],
        query: ProcessedQuery,
    ) -> List[ContextChunk]:
        """
        Adjust scores and re-sort chunks.

        Args:
            chunks: ContextChunks from Pinecone.
            graph_nodes: GraphExpansionNodes discovered.
            query: ProcessedQuery containing intent/entities.

        Returns:
            Sorted list of ContextChunks.
        """
        if not chunks:
            return []

        logger.info("reranker_start", num_chunks=len(chunks))

        # Build quick lookups for graph proximity
        graph_entities = {n.node_id for n in graph_nodes}

        now = datetime.now(timezone.utc)

        for chunk in chunks:
            raw_score = chunk.score

            # 1. Semantic component
            semantic_part = raw_score * WEIGHT_SEMANTIC

            # 2. Graph proximity component
            # If the chunk contains entities that are in the graph expansion set, boost it
            graph_part = 0.0
            overlap = set(chunk.graph_entities).intersection(graph_entities)
            if overlap:
                # 1.0 if there is any overlap (simplistic boost for MVP)
                graph_part = 1.0 * WEIGHT_GRAPH

            # 3. Metadata component
            # Boost if chunk document type matches intent (e.g. intent=failure, type=maintenance_report)
            meta_part = 0.0
            if query.detected_intent == "failure" and "maintenance" in chunk.document_type.lower():
                meta_part += 0.5
            if query.detected_intent == "procedure" and "procedure" in chunk.document_type.lower():
                meta_part += 0.5
            meta_part = min(meta_part, 1.0) * WEIGHT_METADATA

            # 4. Freshness component
            fresh_part = 0.0
            if chunk.created_at:
                try:
                    dt = datetime.fromisoformat(chunk.created_at.replace("Z", "+00:00"))
                    days_old = (now - dt).days
                    # Normalize decay: 0 days = 1.0, 365 days = 0.0
                    fresh_score = max(0.0, 1.0 - (days_old / 365.0))
                    fresh_part = fresh_score * WEIGHT_FRESHNESS
                except ValueError:
                    pass

            # Final hybrid score
            final_score = semantic_part + graph_part + meta_part + fresh_part
            chunk.score = round(final_score, 4)

        # Re-sort chunks by new hybrid score
        chunks.sort(key=lambda c: c.score, reverse=True)

        logger.info("reranker_complete")
        return chunks

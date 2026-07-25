"""
Context Builder

Assembles semantic chunks and graph nodes into a unified Context Package.

Purpose:
    Comply with the rule "Context Before LLM" (Search.md). The AI Copilot
    must never perform retrieval itself. This module packs all retrieved
    context into the `ContextPackage` schema.
"""

import structlog
from typing import List, Dict, Any

from app.search.models import (
    ContextPackage,
    ProcessedQuery,
    ContextChunk,
    GraphExpansionNode,
    Citation,
)
from app.search.constants import MAX_CONTEXT_CHUNKS, MAX_CONTEXT_GRAPH_NODES

logger = structlog.get_logger(__name__)


class ContextBuilder:
    """
    Builds the ContextPackage for AI Copilot consumption.
    """

    def build(
        self,
        query: str,
        processed_query: ProcessedQuery,
        chunks: List[ContextChunk],
        graph_nodes: List[GraphExpansionNode],
    ) -> ContextPackage:
        """
        Assemble the final context package.

        Args:
            query: Original user query.
            processed_query: Processed/rewritten query metadata.
            chunks: Ranked, filtered semantic chunks.
            graph_nodes: Ranked, filtered graph nodes.

        Returns:
            ContextPackage.
        """
        logger.info("context_builder_start")

        # Trim to max context sizes to fit LLM window constraints
        final_chunks = chunks[:MAX_CONTEXT_CHUNKS]
        final_nodes = graph_nodes[:MAX_CONTEXT_GRAPH_NODES]

        # Aggregate citations from chunks
        citations: List[Citation] = []
        for c in final_chunks:
            if c.citation:
                c.citation.confidence = c.score
                citations.append(c.citation)

        package = ContextPackage(
            query=query,
            processed_query=processed_query,
            chunks=final_chunks,
            graph_nodes=final_nodes,
            relationships=[],  # Minimal MVP: relationships are implicit in GraphExpansionNode
            metadata={"source": "hybrid_search_pipeline"},
            citations=citations,
        )

        logger.info(
            "context_builder_complete",
            chunks_packed=len(final_chunks),
            nodes_packed=len(final_nodes),
        )
        return package

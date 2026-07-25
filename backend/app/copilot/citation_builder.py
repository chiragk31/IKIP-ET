"""
Citation Builder

Combines raw LLM citations with the trusted ContextPackage citations.
Calculates the final confidence score based on the formula defined in constants.py.
"""

import structlog
from typing import Any, Dict, List, Tuple

from app.search.models import ContextPackage
from app.copilot.models import CopilotCitation
from app.copilot.constants import (
    CONFIDENCE_WEIGHT_SEARCH,
    CONFIDENCE_WEIGHT_GRAPH,
    CONFIDENCE_WEIGHT_META,
    CONFIDENCE_WEIGHT_LLM,
)

logger = structlog.get_logger(__name__)


class CitationBuilder:
    """
    Builds the final citations and confidence score.
    """

    def __init__(self) -> None:
        logger.info("citation_builder_initialized")

    def build(
        self,
        raw_response: Dict[str, Any],
        context_package: ContextPackage,
    ) -> Tuple[List[CopilotCitation], float]:
        """
        Build citations and hybrid confidence.

        Args:
            raw_response: Validated response from LLM.
            context_package: The retrieved ContextPackage.

        Returns:
            Tuple of (List of CopilotCitations, Final confidence score).
        """
        logger.debug("citation_builder_start")

        # 1. Match LLM citations back to trusted ContextPackage chunks
        # The LLM outputs "document_id" or "chunk_id" in its JSON, we map that
        # to the real, fully-populated Citation from Epic 7 to avoid LLM hallucinations.
        final_citations: List[CopilotCitation] = []
        llm_cites = raw_response.get("citations", [])
        
        # Build lookup from context package
        trusted_citations = {c.chunk_id: c for c in context_package.citations}
        # Also build by document_id as a fallback (if LLM is lazy)
        doc_citations = {c.document_id: c for c in context_package.citations}

        for llm_c in llm_cites:
            chunk_id = llm_c.get("chunk_id", "")
            doc_id = llm_c.get("document_id", "")
            excerpt = llm_c.get("excerpt", "")

            trusted = trusted_citations.get(chunk_id) or doc_citations.get(doc_id)
            if trusted:
                final_citations.append(
                    CopilotCitation(
                        document_id=trusted.document_id,
                        document_name=trusted.document_name,
                        section=trusted.section,
                        page_number=trusted.page_number,
                        chunk_id=trusted.chunk_id,
                        asset_ids=trusted.asset_ids,
                        confidence=trusted.confidence,  # Epic 7's hybrid reranked score
                        source_type=trusted.source_type,
                        excerpt=excerpt,
                    )
                )

        # Remove duplicates
        unique_citations = {c.chunk_id: c for c in final_citations}.values()
        final_citations = list(unique_citations)

        # 2. Compute final hybrid confidence
        confidence = self._compute_confidence(
            raw_response=raw_response,
            context_package=context_package,
            final_citations=final_citations,
        )

        logger.info(
            "citation_builder_complete",
            citations=len(final_citations),
            confidence=confidence,
        )
        return final_citations, confidence

    def _compute_confidence(
        self,
        raw_response: Dict[str, Any],
        context_package: ContextPackage,
        final_citations: List[CopilotCitation],
    ) -> float:
        """
        Compute final confidence blending Search + Graph + Meta + LLM signals.
        """
        if not final_citations:
            return 0.0

        # 1. Search Signal (Average of cited chunk scores)
        search_signal = sum(c.confidence for c in final_citations) / len(final_citations)

        # 2. Graph Signal (Fraction of query entities found in graph)
        graph_signal = 0.0
        query_entities = context_package.processed_query.detected_entities
        if query_entities and context_package.graph_nodes:
            found_entities = {n.seed_entity_id for n in context_package.graph_nodes}
            overlap = len(set(query_entities).intersection(found_entities))
            graph_signal = overlap / len(query_entities)

        # 3. Metadata Match Signal (Fraction of chunks matching intent)
        meta_signal = 0.0
        if context_package.chunks:
            intent = context_package.processed_query.detected_intent
            match_count = 0
            for chunk in context_package.chunks:
                dtype = chunk.document_type.lower()
                if intent == "failure" and "maintenance" in dtype:
                    match_count += 1
                elif intent == "procedure" and "procedure" in dtype:
                    match_count += 1
                elif intent == "general":
                    match_count += 1
            meta_signal = match_count / len(context_package.chunks)

        # 4. LLM Confidence
        llm_signal = float(raw_response.get("confidence", 0.0))

        # Blend
        final = (
            (search_signal * CONFIDENCE_WEIGHT_SEARCH)
            + (graph_signal * CONFIDENCE_WEIGHT_GRAPH)
            + (meta_signal * CONFIDENCE_WEIGHT_META)
            + (llm_signal * CONFIDENCE_WEIGHT_LLM)
        )

        return round(min(final, 1.0), 4)

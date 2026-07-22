"""
Query Processor

Normalizes and analyzes raw query text before embedding.

Purpose:
    Transform the raw user query into a ProcessedQuery that captures:
    - Normalized text (whitespace, case)
    - Detected language
    - Detected entities (asset names, procedure names, etc.)
    - Detected search intent (asset_inquiry | procedure | failure | general)
    - Detected filters that can be inferred from the query text

Input:
    Raw query string.

Output:
    ProcessedQuery with normalized_query and detected metadata.

Design:
    This is a lightweight, rule-based processor — no LLM call here.
    LLM-based query expansion is handled by QueryRewriter.
    The intent/entity detection is heuristic and sufficient for
    structured industrial documents.
"""

import re
import structlog
from typing import Dict, Any, List

from app.search.models import ProcessedQuery
from app.search.constants import MAX_ENTITIES_PER_QUERY

logger = structlog.get_logger(__name__)


# Common industrial entity patterns for heuristic detection
_ASSET_PATTERNS = [
    r"\bP[-\s]?\d{2,4}\b",          # Pump IDs: P-101, P101
    r"\bV[-\s]?\d{2,4}\b",          # Valve IDs: V-201
    r"\bC[-\s]?\d{2,4}\b",          # Compressor IDs
    r"\bT[-\s]?\d{2,4}\b",          # Tank IDs
    r"\bHE[-\s]?\d{2,4}\b",         # Heat Exchanger IDs
    r"\b[A-Z]{1,3}[-\s]\d{3,5}\b",  # Generic tag format
]

_INTENT_KEYWORDS = {
    "failure": [
        "fail", "failure", "fault", "breakdown", "malfunction",
        "error", "damage", "wear", "leak", "trip",
    ],
    "procedure": [
        "procedure", "maintenance", "inspection", "checklist",
        "how to", "steps", "process", "sop",
    ],
    "asset_inquiry": [
        "asset", "pump", "valve", "compressor", "motor", "tank",
        "equipment", "machine", "device",
    ],
    "compliance": [
        "regulation", "compliance", "standard", "iso", "osha",
        "requirement", "certificate", "audit",
    ],
}

_COMPILED_ASSET = [re.compile(p, re.IGNORECASE) for p in _ASSET_PATTERNS]


class QueryProcessor:
    """
    Normalize and analyze a raw search query.

    Purpose:
        Produce a ProcessedQuery that downstream pipeline steps
        (rewriter, filter extractor, context builder) can rely on.
    Input:
        Raw query string.
    Output:
        ProcessedQuery with normalized text and detected metadata.
    """

    def process(self, raw_query: str) -> ProcessedQuery:
        """
        Normalize and analyze a raw query string.

        Args:
            raw_query: Original query from the user.

        Returns:
            ProcessedQuery with normalized_query, detected_entities, intent.
        """
        logger.info("query_processor_start", query_length=len(raw_query))

        normalized = self._normalize(raw_query)
        entities = self._detect_entities(normalized)
        intent = self._detect_intent(normalized)
        filters = self._detect_filters(normalized, entities)
        language = self._detect_language(normalized)

        result = ProcessedQuery(
            original_query=raw_query,
            normalized_query=normalized,
            expanded_query=normalized,   # Rewriter will update this
            detected_language=language,
            detected_entities=entities[:MAX_ENTITIES_PER_QUERY],
            detected_intent=intent,
            detected_filters=filters,
        )

        logger.info(
            "query_processor_complete",
            intent=intent,
            entities_found=len(entities),
            language=language,
        )
        return result

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Normalize whitespace and strip leading/trailing space.

        Args:
            text: Raw query string.

        Returns:
            Normalized query string.
        """
        # Collapse multiple spaces/newlines to single space
        normalized = re.sub(r"\s+", " ", text).strip()
        return normalized

    @staticmethod
    def _detect_entities(text: str) -> List[str]:
        """
        Heuristically detect asset/entity identifiers in the query.

        Args:
            text: Normalized query string.

        Returns:
            List of detected entity strings.
        """
        entities: List[str] = []
        seen = set()
        for pattern in _COMPILED_ASSET:
            for match in pattern.finditer(text):
                val = match.group(0).upper().replace(" ", "-")
                if val not in seen:
                    seen.add(val)
                    entities.append(val)
        return entities

    @staticmethod
    def _detect_intent(text: str) -> str:
        """
        Classify the search intent from the query text.

        Args:
            text: Normalized query string.

        Returns:
            Intent string: one of failure | procedure | asset_inquiry |
            compliance | general.
        """
        lower = text.lower()
        scores: Dict[str, int] = {intent: 0 for intent in _INTENT_KEYWORDS}
        for intent, keywords in _INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    scores[intent] += 1

        best_intent = max(scores, key=lambda k: scores[k])
        if scores[best_intent] == 0:
            return "general"
        return best_intent

    @staticmethod
    def _detect_filters(text: str, entities: List[str]) -> Dict[str, Any]:
        """
        Infer filter hints from the query text (e.g., explicit asset IDs).

        Args:
            text: Normalized query string.
            entities: Already-detected entity identifiers.

        Returns:
            Dict of filter hints (keys match MetadataFilters fields).
        """
        filters: Dict[str, Any] = {}
        if entities:
            # Use the first detected entity as an asset_id hint
            filters["asset_id_hint"] = entities[0]
        return filters

    @staticmethod
    def _detect_language(text: str) -> str:
        """
        Heuristic language detection (en only for now; extensible).

        Args:
            text: Normalized query string.

        Returns:
            ISO 639-1 language code.
        """
        # Placeholder — full implementation would use langdetect
        return "en"

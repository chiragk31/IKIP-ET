"""
Response Validator

Validates raw LLM outputs to prevent hallucinations and enforce schema.
Rejects or overrides answers based on confidence thresholds and context constraints.
"""

import structlog
from typing import Any, Dict

from app.search.models import ContextPackage
from app.copilot.constants import (
    NO_EVIDENCE_RESPONSE,
    MIN_ACCEPTABLE_CONFIDENCE,
    MIN_CITATIONS_REQUIRED,
)

logger = structlog.get_logger(__name__)


class ResponseValidator:
    """
    Validates Copilot responses before final formatting.
    """

    def __init__(self) -> None:
        logger.info("response_validator_initialized")

    def validate(self, raw_response: Dict[str, Any], context_package: ContextPackage) -> Dict[str, Any]:
        """
        Validate and potentially override the raw LLM response.

        Args:
            raw_response: Raw dictionary from LLM Gateway.
            context_package: The retrieved context package.

        Returns:
            Validated response dictionary.
        """
        logger.debug("response_validation_start")

        # 1. Base constraints (schema presence)
        answer = raw_response.get("answer", "")
        llm_confidence = float(raw_response.get("confidence", 0.0))
        citations = raw_response.get("citations", [])

        # 2. Empty context constraint (Hallucination prevention)
        # If the search module returned NOTHING, the LLM must not invent an answer.
        if not context_package.chunks and not context_package.graph_nodes:
            logger.info("validation_override_empty_context")
            return self._build_no_evidence_response()

        # 3. Minimum Citation Constraint
        # If the LLM answered but failed to cite any documents when context WAS provided,
        # it is likely hallucinating outside the bounds of the provided text.
        if len(citations) < MIN_CITATIONS_REQUIRED:
            logger.info("validation_override_no_citations", actual=len(citations))
            return self._build_no_evidence_response()

        # 4. Minimum Confidence Constraint
        # If the LLM itself reports extremely low confidence, don't trust the answer.
        if llm_confidence < MIN_ACCEPTABLE_CONFIDENCE:
            logger.info("validation_override_low_confidence", conf=llm_confidence)
            return self._build_no_evidence_response()

        logger.info("response_validation_passed")
        return raw_response

    def _build_no_evidence_response(self) -> Dict[str, Any]:
        """Return the strict no-evidence fallback."""
        return {
            "answer": NO_EVIDENCE_RESPONSE,
            "citations": [],
            "confidence": 0.0,
            "followup_questions": [],
            "reasoning": "Context package was empty or constraints failed.",
            "related_assets": [],
        }

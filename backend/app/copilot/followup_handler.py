"""
Follow-up Handler

Resolves pronoun/reference ambiguity in follow-up questions using conversation context.

Examples:
  "When was it last inspected?"   → "When was Pump P-101 last inspected?"
  "What are the related risks?"   → "What are the risks related to Pump P-101's failure?"

Approach: Heuristic string substitution using active_asset and active_topic from
ConversationContext. No LLM call — this is deterministic and cheap.
If context is insufficient to resolve, the original question is returned unchanged
and SearchService will handle it as a fresh query.
"""

import re
import structlog
from typing import Optional

from app.copilot.models import ConversationContext

logger = structlog.get_logger(__name__)

# Pronouns that trigger reference resolution
_PRONOUN_PATTERNS = [
    re.compile(r"\b(it|this|that|the equipment|the asset|the pump|the valve|the unit)\b", re.IGNORECASE),
    re.compile(r"\b(its|this equipment'?s?|the above)\b", re.IGNORECASE),
]


class FollowupHandler:
    """
    Resolves follow-up question references using conversation context.

    Purpose:
        Replace vague pronouns/references with the specific asset or topic from memory.
    Input:
        User question + ConversationContext.
    Output:
        Enriched question string (may be identical if no resolution needed).
    """

    def resolve(self, question: str, context: ConversationContext) -> str:
        """
        Attempt to resolve references in a follow-up question.

        Args:
            question: Current user question (may contain pronouns).
            context: ConversationContext from current session.

        Returns:
            Enriched question string.
        """
        if not context.history:
            logger.debug("followup_resolve_no_history")
            return question

        if not context.active_asset and not context.active_topic:
            logger.debug("followup_resolve_no_context")
            return question

        enriched = question
        resolved = False

        if context.active_asset:
            for pattern in _PRONOUN_PATTERNS:
                if pattern.search(enriched):
                    enriched = pattern.sub(context.active_asset, enriched)
                    resolved = True

        # Append active topic context to help SearchService build better embeddings
        if context.active_topic and context.active_asset:
            if not re.search(r"\b" + re.escape(context.active_asset) + r"\b", enriched, re.IGNORECASE):
                enriched = f"{enriched} (context: {context.active_asset} {context.active_topic})"
                resolved = True

        if resolved:
            logger.info(
                "followup_resolved",
                original=question,
                enriched=enriched,
                active_asset=context.active_asset,
                active_topic=context.active_topic,
            )
        else:
            logger.debug("followup_no_resolution_needed")

        return enriched

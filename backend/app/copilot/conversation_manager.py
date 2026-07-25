"""
Conversation Manager

Builds ConversationContext for each turn using session memory.

Responsibilities:
  - Retrieve history from MemoryManager.
  - Extract active asset and topic from prior turns.
  - Detect new asset/topic from current question using simple heuristics
    (same pattern as QueryProcessor — no AI call, deterministic).
  - Save the completed turn back to MemoryManager after generation.
"""

import re
import structlog
from typing import List, Optional

from app.copilot.models import ConversationContext, ConversationTurn
from app.copilot.memory_manager import MemoryManager

logger = structlog.get_logger(__name__)

# Simple asset patterns (same heuristic as QueryProcessor in Epic 7)
_ASSET_PATTERN = re.compile(r"\b([A-Z]{1,4}-\d{2,4}[A-Z]?)\b")

# Intent-to-topic mapping
_TOPIC_KEYWORDS = {
    "failure": ["fail", "broke", "fault", "error", "alarm", "trip", "shutdown"],
    "maintenance": ["maintain", "service", "overhaul", "inspect", "lubricate", "repair"],
    "procedure": ["procedure", "startup", "shutdown procedure", "steps", "how to"],
    "measurement": ["temperature", "pressure", "flow", "rpm", "vibration", "reading"],
    "compliance": ["osha", "regulation", "standard", "compliance", "certificate", "permit"],
}


class ConversationManager:
    """
    Manages session context for the Copilot.

    Purpose:
        Build rich ConversationContext from session history + current question.
    Input:
        session_id, question string.
    Output:
        ConversationContext containing history, active asset, active topic.
    """

    def __init__(self, memory: MemoryManager) -> None:
        """
        Initialize with a MemoryManager.

        Args:
            memory: Session store.
        """
        self._memory = memory
        logger.info("conversation_manager_initialized")

    def get_context(self, session_id: str, question: str) -> ConversationContext:
        """
        Build ConversationContext for the current turn.

        Determines active_asset and active_topic from:
        1. Explicit mention in the current question (highest priority).
        2. Carried over from the most recent prior turn.

        Args:
            session_id: Unique session identifier.
            question: Current user question.

        Returns:
            ConversationContext.
        """
        history = self._memory.get_history(session_id)

        # Detect from current question
        detected_asset = self._detect_asset(question)
        detected_topic = self._detect_topic(question)

        # Fall back to history if not detected in current question
        active_asset = detected_asset or self._memory.get_active_asset(session_id)
        active_topic = detected_topic or self._memory.get_active_topic(session_id)

        context = ConversationContext(
            session_id=session_id,
            history=history,
            active_asset=active_asset,
            active_topic=active_topic,
        )

        logger.info(
            "conversation_context_built",
            session_id=session_id,
            history_turns=len(history),
            active_asset=active_asset,
            active_topic=active_topic,
        )
        return context

    def save_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        active_asset: Optional[str],
        active_topic: Optional[str],
    ) -> None:
        """
        Persist the completed Q&A turn to session memory.

        Args:
            session_id: Session to save to.
            question: User's question.
            answer: Copilot's answer.
            active_asset: Asset active during this turn.
            active_topic: Topic active during this turn.
        """
        turn = ConversationTurn(
            question=question,
            answer=answer,
            active_asset=active_asset,
            active_topic=active_topic,
        )
        self._memory.append_turn(session_id, turn)
        logger.debug("conversation_turn_saved", session_id=session_id)

    def format_history_for_prompt(self, history: List[ConversationTurn]) -> str:
        """
        Format conversation history into a text block for the LLM prompt.

        Args:
            history: List of prior ConversationTurns.

        Returns:
            Formatted string; empty string if no history.
        """
        if not history:
            return "(No prior conversation)"

        lines = []
        for turn in history:
            lines.append(f"User: {turn.question}")
            lines.append(f"Copilot: {turn.answer}")
        return "\n".join(lines)

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    def _detect_asset(self, question: str) -> Optional[str]:
        """Detect asset ID patterns (e.g., P-101, V-12) from a question."""
        match = _ASSET_PATTERN.search(question)
        if match:
            return match.group(1)
        return None

    def _detect_topic(self, question: str) -> Optional[str]:
        """Detect the primary topic from a question using keyword heuristics."""
        lower = question.lower()
        for topic, keywords in _TOPIC_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return topic
        return None

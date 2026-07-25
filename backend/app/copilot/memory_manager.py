"""
Memory Manager

In-memory session store for conversation history.

Design:
  - Session-scoped: each session_id has an isolated list of ConversationTurns.
  - Never mix contexts across sessions (Copilot.md explicit requirement).
  - Capped at MAX_SESSIONS to prevent unbounded memory growth.
  - Capped at MAX_HISTORY_TURNS per session (oldest turns evicted first).
  - Stateless across server restarts (acceptable for MVP — persistent memory is a future enhancement).

Per Copilot.md: "Memory is session scoped by default."
"""

import structlog
from collections import OrderedDict
from typing import Dict, List, Optional

from app.copilot.models import ConversationTurn
from app.copilot.constants import MAX_HISTORY_TURNS, MAX_SESSIONS

logger = structlog.get_logger(__name__)


class MemoryManager:
    """
    Stores and retrieves per-session conversation history.

    Purpose:
        Provide isolated, session-scoped conversation memory.
    Input:
        session_id (str), ConversationTurn objects.
    Output:
        List[ConversationTurn] for a given session.
    """

    def __init__(self) -> None:
        """
        Initialize with an ordered dict (oldest session evicted when at capacity).
        """
        self._store: OrderedDict[str, List[ConversationTurn]] = OrderedDict()
        logger.info("memory_manager_initialized", max_sessions=MAX_SESSIONS)

    def get_history(self, session_id: str) -> List[ConversationTurn]:
        """
        Return the conversation history for a session.

        Args:
            session_id: Unique session identifier.

        Returns:
            List of ConversationTurn ordered oldest-to-newest.
        """
        return self._store.get(session_id, [])

    def append_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """
        Append a new Q&A turn to a session's history.

        Args:
            session_id: Unique session identifier.
            turn: Completed ConversationTurn to persist.
        """
        if session_id not in self._store:
            if len(self._store) >= MAX_SESSIONS:
                # Evict oldest session
                oldest = next(iter(self._store))
                self._store.pop(oldest)
                logger.warning("memory_session_evicted", evicted_session=oldest)
            self._store[session_id] = []

        history = self._store[session_id]
        history.append(turn)

        # Trim to max turns (keep most recent)
        if len(history) > MAX_HISTORY_TURNS:
            self._store[session_id] = history[-MAX_HISTORY_TURNS:]

        logger.debug("memory_turn_appended", session_id=session_id, total_turns=len(self._store[session_id]))

    def clear_session(self, session_id: str) -> None:
        """
        Clear all history for a session.

        Args:
            session_id: Session to clear.
        """
        self._store.pop(session_id, None)
        logger.info("memory_session_cleared", session_id=session_id)

    def get_active_asset(self, session_id: str) -> Optional[str]:
        """
        Return the most recently referenced asset in this session.

        Args:
            session_id: Session to inspect.

        Returns:
            Asset identifier string if found, None otherwise.
        """
        history = self.get_history(session_id)
        for turn in reversed(history):
            if turn.active_asset:
                return turn.active_asset
        return None

    def get_active_topic(self, session_id: str) -> Optional[str]:
        """
        Return the most recently active topic in this session.

        Args:
            session_id: Session to inspect.

        Returns:
            Topic string ("failure", "procedure", etc.) if found, None otherwise.
        """
        history = self.get_history(session_id)
        for turn in reversed(history):
            if turn.active_topic:
                return turn.active_topic
        return None

"""
Copilot Pydantic Models

Internal data structures for the Epic 8 AI Copilot pipeline.

Pipeline:
    ChatRequest
        ↓ ConversationManager  → ConversationContext
        ↓ FollowupHandler      → enriched question string
        ↓ HybridSearchService  → ContextPackage
        ↓ ResponseGenerator    → raw LLM dict
        ↓ ResponseValidator    → validated
        ↓ CitationBuilder      → List[CopilotCitation]
        ↓ ConfidenceScorer     → float
        ↓                      → CopilotResponse

These are INTERNAL models — API schemas live in schemas.py.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationTurn(BaseModel):
    """A single Q&A pair stored in conversation memory."""
    question: str
    answer: str
    active_asset: Optional[str] = None   # e.g. "P-101"
    active_topic: Optional[str] = None   # e.g. "failure", "maintenance"
    timestamp: str = Field(default_factory=_utcnow)


class ConversationContext(BaseModel):
    """
    Resolved context for the current turn.

    Built by ConversationManager from session history.
    """
    session_id: str
    history: List[ConversationTurn] = Field(default_factory=list)
    active_asset: Optional[str] = None
    active_topic: Optional[str] = None
    active_filters: Dict[str, Any] = Field(default_factory=dict)


class CopilotCitation(BaseModel):
    """
    A citation in the final Copilot response.

    Per Copilot.md: must include Document Name, Section, Page, Asset, Confidence.
    Reuses the Search Citation shape for consistency.
    """
    document_id: str
    document_name: str = ""
    section: str = ""
    page_number: Optional[int] = None
    chunk_id: str = ""
    asset_ids: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    source_type: str = "semantic"
    excerpt: str = ""                    # short text snippet for UI display


class CopilotResponse(BaseModel):
    """
    Final output of the Copilot pipeline.

    Matches the required response format from Copilot.md exactly:
        {answer, citations, confidence, followup_questions}
    """
    answer: str
    citations: List[CopilotCitation] = Field(default_factory=list)
    confidence: float = 0.0
    followup_questions: List[str] = Field(default_factory=list)
    reasoning: str = ""                  # brief reasoning trace from LLM
    related_assets: List[str] = Field(default_factory=list)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)

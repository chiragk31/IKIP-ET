"""
Copilot API Schemas

API-facing request and response schemas for POST /api/v1/chat.
These are separate from internal models to decouple API contract from pipeline internals.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Request body for POST /api/v1/chat.

    session_id is required to enable conversation memory isolation per session.
    expand_graph defaults to False for chat to reduce latency (opt-in for richer context).
    """
    question: str = Field(..., min_length=2, max_length=2000, description="User question")
    session_id: str = Field(..., min_length=1, max_length=128, description="Session ID (caller-generated, unique per user/conversation)")
    top_k: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.30, ge=0.0, le=1.0)
    expand_graph: bool = Field(default=False, description="Enable graph expansion (adds latency)")
    filters: Optional[Dict[str, Any]] = Field(default=None)


class CitationOut(BaseModel):
    """Citation in the API response."""
    document_id: str
    document_name: str = ""
    section: str = ""
    page_number: Optional[int] = None
    asset_ids: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    excerpt: str = ""


class ChatResponse(BaseModel):
    """
    Response body for POST /api/v1/chat.

    Matches the required response format from Copilot.md:
        {answer, citations, confidence, followup_questions}
    """
    answer: str
    citations: List[CitationOut] = Field(default_factory=list)
    confidence: float = 0.0
    followup_questions: List[str] = Field(default_factory=list)
    reasoning: str = ""
    related_assets: List[str] = Field(default_factory=list)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)

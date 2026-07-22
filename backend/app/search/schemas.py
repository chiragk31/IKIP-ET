"""
Search API Schemas

API-facing Pydantic request/response schemas for POST /search.

These are the objects validated at the API boundary. Internal pipeline
models live in models.py and are only used between services.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.search.models import (
    MetadataFilters,
    Citation,
    ContextChunk,
    GraphExpansionNode,
)


class SearchRequest(BaseModel):
    """
    API request body for POST /api/v1/search.

    Purpose:
        Validated input from the client.
    """
    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="Natural language query",
        examples=["What are the failure modes of Pump P-101?"],
    )
    top_k: int = Field(default=10, ge=1, le=50, description="Max chunks to return")
    min_score: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Minimum cosine similarity score (0–1)",
    )
    graph_depth: int = Field(
        default=2, ge=0, le=3,
        description="Graph expansion depth (0=disable, max=3)",
    )
    expand_graph: bool = Field(default=True, description="Enable graph expansion")
    rerank: bool = Field(default=True, description="Enable result reranking")
    filters: MetadataFilters = Field(
        default_factory=MetadataFilters,
        description="Structured metadata filters",
    )


class SearchResponse(BaseModel):
    """
    API response body for POST /api/v1/search.

    Purpose:
        Serialized search results ready for the frontend / AI Copilot.
    """
    query: str
    total_results: int
    chunks: List[ContextChunk]
    graph_nodes: List[GraphExpansionNode]
    citations: List[Citation]
    diagnostics: Dict[str, Any] = Field(default_factory=dict)

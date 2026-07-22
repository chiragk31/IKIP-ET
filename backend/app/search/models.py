"""
Search Pydantic Models

Internal data structures that flow through the Epic 7 search pipeline.

Pipeline:
    HybridSearchQuery
        ↓ QueryProcessor      → ProcessedQuery
        ↓ QueryRewriter       → ProcessedQuery (expanded text)
        ↓ SemanticSearch      → List[ContextChunk]
        ↓ MetadataFilter      → List[ContextChunk]
        ↓ GraphSearch         → List[GraphExpansionNode]
        ↓ ContextBuilder      → ContextPackage
        ↓ Reranker            → HybridSearchResult

These are INTERNAL models — not directly exposed to the API layer.
API-facing schemas live in schemas.py.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------------------
# Input models
# -------------------------------------------------------------------

class MetadataFilters(BaseModel):
    """
    Optional structured filters applied to Pinecone metadata.

    All fields are optional — omitted fields are not applied.
    """
    asset_id: Optional[str] = None
    plant: Optional[str] = None
    department: Optional[str] = None
    date_from: Optional[str] = None       # ISO 8601
    date_to: Optional[str] = None         # ISO 8601
    document_type: Optional[str] = None
    confidence_min: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    language: Optional[str] = None
    chunk_type: Optional[str] = None
    document_id: Optional[str] = None


class HybridSearchQuery(BaseModel):
    """
    Full hybrid search request combining semantic + graph + metadata retrieval.

    Purpose:
        Carry all user-provided search intent through the pipeline.
    Input:
        API layer from POST /search.
    Output:
        Fed to SearchService.search().
    """
    query: str = Field(..., min_length=2, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=50)
    min_score: float = Field(default=0.3, ge=0.0, le=1.0)
    graph_depth: int = Field(default=2, ge=0, le=3)
    expand_graph: bool = Field(default=True)
    rerank: bool = Field(default=True)
    filters: MetadataFilters = Field(default_factory=MetadataFilters)


# -------------------------------------------------------------------
# Intermediate pipeline models
# -------------------------------------------------------------------

class ProcessedQuery(BaseModel):
    """
    Output from QueryProcessor + optional QueryRewriter expansion.

    Purpose:
        Normalized, expanded query ready for embedding.
    """
    original_query: str
    normalized_query: str
    expanded_query: str                   # after QueryRewriter; may equal normalized
    detected_language: str = "en"
    detected_entities: List[str] = Field(default_factory=list)
    detected_intent: str = "general"      # "asset_inquiry" | "procedure" | "failure" | "general"
    detected_filters: Dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    """
    Full citation for a search result (required by Epic 8 — AI Copilot).

    Per Search.md §Citations: every result must include document, section,
    page, chunk_id, asset, confidence.
    """
    document_id: str
    document_name: str = ""
    section: str = ""
    page_number: Optional[int] = None
    chunk_id: str
    asset_ids: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    source_type: str = "semantic"         # "semantic" | "graph" | "hybrid"


class ContextChunk(BaseModel):
    """
    A chunk retrieved from Pinecone, enriched for context assembly.
    """
    chunk_id: str
    document_id: str
    text: str
    section: str = ""
    page_number: Optional[int] = None
    score: float = 0.0
    graph_entities: List[str] = Field(default_factory=list)
    asset_ids: List[str] = Field(default_factory=list)
    document_type: str = ""
    language: str = "en"
    created_at: str = ""
    citation: Optional[Citation] = None


class GraphExpansionNode(BaseModel):
    """
    A node discovered during graph expansion via GraphRepository.get_neighbors().
    """
    node_id: str
    node_name: str = ""
    node_label: str = ""                  # Neo4j label: Asset, Person, etc.
    relationship: str = ""                # relationship type connecting to seed
    seed_entity_id: str = ""             # entity_id this was discovered from
    hop: int = 1                          # 1 = directly connected, 2 = two hops, etc.
    properties: Dict[str, Any] = Field(default_factory=dict)


class ContextPackage(BaseModel):
    """
    The assembled context package passed to the AI Copilot (Epic 8).

    Per Search.md §Context Package:
        {query, chunks, graph_nodes, relationships, metadata, citations}
    """
    query: str
    processed_query: ProcessedQuery
    chunks: List[ContextChunk] = Field(default_factory=list)
    graph_nodes: List[GraphExpansionNode] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    citations: List[Citation] = Field(default_factory=list)


# -------------------------------------------------------------------
# Final output model
# -------------------------------------------------------------------

class HybridSearchResult(BaseModel):
    """
    Final output of the full hybrid search pipeline.

    Purpose:
        Carry ranked results, context package, and diagnostics
        back to the API layer.
    Input:
        Produced by Reranker.
    Output:
        Serialized by the API endpoint.
    """
    query: str
    total_results: int
    chunks: List[ContextChunk] = Field(default_factory=list)
    graph_nodes: List[GraphExpansionNode] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    context_package: ContextPackage
    diagnostics: Dict[str, Any] = Field(default_factory=dict)

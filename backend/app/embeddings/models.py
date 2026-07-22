"""
Embeddings Pydantic Models

Defines the data structures that flow through the embedding pipeline:

    CanonicalDocument → ChunkGenerator → Chunk
    Chunk + vector    → EmbeddedChunk
    [EmbeddedChunk]   → EmbeddingService → EmbeddingResult

Design decisions:
 - chunk_id is deterministic: sha256(document_id + section + text[:100])
   truncated to 40 hex chars. This ensures idempotency — same document,
   same chunk always gets the same ID, so Pinecone upsert is idempotent.
 - chunk_hash is the full sha256 of the chunk text — used to detect if
   a chunk has already been embedded in the same pipeline version.
 - graph_entities carries entity_ids (strings) from the NKO, not full
   entity objects — keeping vector metadata lean per Pinecone best practice.
 - embedding_model reads from settings at instantiation time so no source
   file needs to be updated when the embedding model changes (AD-022).
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.config import settings


def _utcnow() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def make_chunk_id(document_id: str, section: str, text_prefix: str) -> str:
    """
    Generate a deterministic chunk ID.

    Args:
        document_id: Source document ID.
        section: Section heading the chunk belongs to.
        text_prefix: First 100 characters of the chunk text.

    Returns:
        40-character hex string (SHA-256 truncated).
    """
    key = f"{document_id}::{section}::{text_prefix}"
    return hashlib.sha256(key.encode()).hexdigest()[:40]


def make_chunk_hash(text: str) -> str:
    """
    Generate a content hash for a chunk text.

    Used for idempotency: if this hash is already in Pinecone at the
    same pipeline_version, skip re-embedding.

    Args:
        text: Chunk text to hash.

    Returns:
        64-character full SHA-256 hex string.
    """
    return hashlib.sha256(text.encode()).hexdigest()


class Chunk(BaseModel):
    """
    A semantic chunk ready for embedding.

    Matches the Canonical Chunk Model from Embeddings.md §Canonical Chunk Model.
    Every chunk carries full citation metadata so retrieval results can be
    traced to their source without a database lookup.
    """

    # Identity
    chunk_id: str = Field(..., description="Deterministic ID: sha256(doc+section+text_prefix)[:40]")
    chunk_hash: str = Field(..., description="sha256(text) — used for idempotency check")
    document_id: str = Field(..., description="Source document ID")
    chunk_index: int = Field(..., description="0-indexed position within the document")

    # Content
    text: str = Field(..., description="Chunk text to embed")
    section: str = Field(default="", description="Section heading this chunk belongs to")
    chunk_type: str = Field(default="text", description="text | table | procedure | maintenance_log | etc.")

    # Citation metadata
    page_number: Optional[int] = Field(default=None, description="Page where chunk starts")
    document_type: str = Field(default="", description="E.g. maintenance_report, procedure, etc.")
    language: str = Field(default="en")

    # Graph-aware enrichment (per Embeddings.md §Graph-Aware Chunks)
    graph_entities: List[str] = Field(
        default_factory=list,
        description="entity_ids from the NKO whose name/aliases appear in this chunk",
    )
    graph_relationships: List[str] = Field(
        default_factory=list,
        description="relationship types present in this chunk's entity pairs",
    )

    # Additional metadata for hybrid filtering
    asset_ids: List[str] = Field(default_factory=list, description="Asset entity IDs in this chunk")
    keywords: List[str] = Field(default_factory=list)

    # Versioning
    chunk_pipeline_version: str = Field(default="1.0")
    created_at: str = Field(default_factory=_utcnow)


class EmbeddedChunk(BaseModel):
    """
    A Chunk that has been embedded — carries the vector alongside the chunk.

    This is the object that flows into EmbeddingValidator and then
    PineconeRepository.
    """

    chunk: Chunk
    vector: List[float] = Field(..., description="Embedding vector")
    embedding_model: str = Field(default_factory=lambda: settings.EMBEDDING_MODEL)  # AD-022: reads from config
    embedding_pipeline_version: str = Field(default="1.0")
    embedded_at: str = Field(default_factory=_utcnow)


class EmbeddingResult(BaseModel):
    """
    Summary returned by EmbeddingService after a run.

    Parallels GraphBuildResult — same pattern for consistency.
    """

    document_id: str
    chunks_generated: int = 0
    chunks_embedded: int = 0
    chunks_skipped: int = 0           # already in Pinecone at same version
    chunks_failed: int = 0
    vectors_upserted: int = 0
    duration_seconds: float = 0.0
    status: str = "completed"         # "completed" | "failed" | "partial"
    error_message: Optional[str] = None


class SearchQuery(BaseModel):
    """
    Incoming search request from the API.
    """

    query: str = Field(..., description="Natural language query to embed and search")
    top_k: int = Field(default=10, ge=1, le=50)
    document_id: Optional[str] = Field(default=None, description="Filter to a specific document")
    document_type: Optional[str] = Field(default=None)
    chunk_type: Optional[str] = Field(default=None)
    language: Optional[str] = Field(default=None)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")


class SearchResult(BaseModel):
    """
    A single result from semantic search.
    """

    chunk_id: str
    document_id: str
    score: float
    text: str
    section: str
    page_number: Optional[int] = None
    graph_entities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """
    Full response from a semantic search query.
    """

    query: str
    results: List[SearchResult]
    total_results: int
    top_k: int

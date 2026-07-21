"""
Graph Pydantic Models

GraphNode and GraphRelationship are the internal transfer objects
that flow through the graph pipeline:

    NKO → NodeBuilder → GraphNode
    NKO → RelationshipBuilder → GraphRelationship
    [GraphNode] + [GraphRelationship] → GraphValidator
    Validated → GraphRepository → Neo4j

Design rules (from Graph.md):
 - Every element carries provenance: source_document, confidence,
   created_at, extraction_version.
 - entity_id is the stable Neo4j node key (deterministic from Epic 4).
 - Graph updates are idempotent: MERGE on entity_id for nodes,
   MERGE on (source_id, rel_type, target_id) for relationships.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def _utcnow() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


class GraphNode(BaseModel):
    """
    A validated, provenance-enriched graph node ready for Neo4j insertion.

    Maps 1-to-1 with a NormalizedEntity from Epic 4.
    The `entity_id` is the stable MERGE key for Neo4j.
    """

    # Identity
    entity_id: str = Field(..., description="Stable Neo4j MERGE key (from NKO)")
    label: str = Field(..., description="Neo4j node label (e.g., Asset, Person)")
    name: str = Field(..., description="Primary display name")

    # Semantic properties
    aliases: List[str] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)

    # Provenance (Graph.md §Provenance — mandatory on every node)
    source_document: str = Field(..., description="Document ID that originated this node")
    confidence: float = Field(..., ge=0.0, le=1.0)
    extraction_version: str = Field(default="1.0")
    created_at: str = Field(default_factory=_utcnow)


class GraphRelationship(BaseModel):
    """
    A validated, provenance-enriched graph relationship ready for Neo4j.

    Maps 1-to-1 with a NormalizedRelationship from Epic 4.
    Relationships are directional and reference node entity_ids.
    """

    # Identity (forms the MERGE key: source_id + rel_type + target_id)
    source_id: str = Field(..., description="entity_id of the source node")
    rel_type: str = Field(..., description="Relationship type in UPPER_SNAKE_CASE")
    target_id: str = Field(..., description="entity_id of the target node")

    # Semantic properties
    properties: Dict[str, Any] = Field(default_factory=dict)

    # Provenance (Graph.md §Provenance — mandatory on every relationship)
    source_document: str = Field(..., description="Document ID that originated this relationship")
    confidence: float = Field(..., ge=0.0, le=1.0)
    extraction_version: str = Field(default="1.0")
    created_at: str = Field(default_factory=_utcnow)


class GraphBuildResult(BaseModel):
    """
    Summary returned by GraphService after a build run.

    Includes counts so the caller (handler / API) can emit meaningful
    event payloads and log entries without re-querying Neo4j.
    """

    document_id: str
    nodes_written: int = 0
    relationships_written: int = 0
    nodes_skipped: int = 0        # failed validation
    relationships_skipped: int = 0
    duration_seconds: float = 0.0
    status: str = "completed"     # "completed" | "failed" | "partial"
    error_message: Optional[str] = None

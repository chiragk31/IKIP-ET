"""
Asset Intelligence Internal Models

Pydantic models used internally within the Asset module.

These are NOT the API-facing schemas (those live in schemas.py).
They carry provenance on every field per Assets.md's Explainability requirement:
    "Every field in the Asset 360 profile should be traceable."

All fields that originate from graph data carry:
  - source_document: which document produced this information
  - confidence: extraction confidence from the graph pipeline
  - relationship_type: which Neo4j relationship connected this node

Fields originating from semantic search carry:
  - source_document: document_id of the matching chunk
  - confidence: Pinecone similarity score
  - chunk_id: for direct chunk traceability
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Asset Node (extracted from graph)
# ---------------------------------------------------------------------------


class AssetNode(BaseModel):
    """
    Core asset identity and properties extracted from the Neo4j graph.

    Purpose:
        Represent a single asset node with all provenance fields intact.
    Input:
        Parsed from GraphRepository.get_asset_360() result dict.
    Output:
        Used as the 'asset' field in Asset360.
    """

    entity_id: str = Field(..., description="Stable entity_id (e.g. 'asset_p101')")
    name: str = Field(default="", description="Primary display name")
    entity_type: str = Field(default="Asset")
    label: str = Field(default="Asset", description="Neo4j node label")

    # Structured properties (best-effort from graph node properties dict)
    asset_tag: Optional[str] = None
    equipment_id: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    installation_date: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)

    # Provenance (mandatory per Assets.md §Explainability)
    source_document: str = Field(default="", description="Document that originated this node")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: str = Field(default="")

    # Raw properties bag — carries everything not explicitly mapped above
    raw_properties: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Asset Relationship (edges from graph)
# ---------------------------------------------------------------------------


class AssetRelationship(BaseModel):
    """
    A typed relationship between the asset and a connected node.

    Purpose:
        Expose graph relationships with full provenance so the
        UI can link back to source documents.
    Input:
        Produced by RelationshipBuilder from GraphRepository.get_neighbors() data.
    Output:
        Populates the 'relationships' list in Asset360.
    """

    relationship_type: str = Field(..., description="Neo4j relationship type (e.g. CONNECTED_TO)")
    relationship_category: str = Field(default="related", description="Human-readable category")
    direction: str = Field(default="outgoing", description="'outgoing' or 'incoming'")

    # Target node identity
    target_entity_id: str = Field(default="")
    target_name: str = Field(default="")
    target_label: str = Field(default="")

    # Provenance
    source_document: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Timeline Event (chronological history)
# ---------------------------------------------------------------------------


class TimelineEvent(BaseModel):
    """
    A single event in the asset's chronological history.

    Purpose:
        Provide a time-ordered narrative of the asset's lifecycle.
    Input:
        Produced by TimelineBuilder from graph neighbor data.
    Output:
        Populates the 'timeline' list in Asset360.

    Note: event_date may be None when the graph does not carry a date
          for this particular event — the event is still included for
          completeness with date=None rather than silently dropped.
    """

    event_type: str = Field(
        ...,
        description="Category: 'maintenance' | 'failure' | 'inspection' | 'compliance' | 'installation' | 'event' | 'measurement'",
    )
    event_label: str = Field(default="", description="Neo4j label of the event node")
    description: str = Field(default="")
    event_date: Optional[str] = Field(default=None, description="ISO 8601 date if available")
    relationship_type: str = Field(default="", description="Neo4j relationship that linked this event")

    # Identity
    entity_id: str = Field(default="")
    entity_name: str = Field(default="")

    # Provenance
    source_document: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Health Summary (descriptive only — no predictive fields)
# ---------------------------------------------------------------------------


class HealthSummary(BaseModel):
    """
    Descriptive health summary for an asset.

    Purpose:
        Surface a human-readable snapshot of asset health based on
        historical graph data. Strictly descriptive — no RUL, failure
        probability, or any predictive field (those are future scope
        per Assets.md §Future Enhancements).
    Input:
        Produced by HealthBuilder from graph neighbor data.
    Output:
        Populates the 'health_summary' field in Asset360.
    """

    # Counts (raw numbers for UI rendering)
    maintenance_event_count: int = Field(default=0)
    failure_count: int = Field(default=0)
    inspection_count: int = Field(default=0)
    compliance_event_count: int = Field(default=0)

    # Descriptive labels
    maintenance_frequency: str = Field(
        default="unknown",
        description="'high' | 'moderate' | 'low' | 'unknown' — descriptive only",
    )
    failure_severity: str = Field(
        default="none",
        description="'high' | 'moderate' | 'none' — descriptive only, based on count",
    )
    inspection_status: str = Field(
        default="unknown",
        description="'current' | 'overdue' | 'unknown' — derived from event presence",
    )
    compliance_status: str = Field(
        default="unknown",
        description="'compliant' | 'non_compliant' | 'unknown'",
    )

    # Recent alerts — list of entity names from the graph, no predictions
    recent_alerts: List[str] = Field(default_factory=list)

    # Provenance: which document contributed to this summary
    contributing_documents: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Related Document (from semantic search)
# ---------------------------------------------------------------------------


class RelatedDocument(BaseModel):
    """
    A document related to this asset, retrieved via HybridSearchService.

    Purpose:
        Link the asset to its supporting documentation with full
        traceability back to the chunk and page that matched.
    Input:
        Produced from HybridSearchService search results.
    Output:
        Populates the 'documents' list in Asset360.
    """

    document_id: str
    document_name: str = ""
    document_type: str = ""
    section: str = ""
    page_number: Optional[int] = None
    excerpt: str = ""

    # Provenance
    chunk_id: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_type: str = "semantic"   # "semantic" | "graph"


# ---------------------------------------------------------------------------
# Asset 360 (assembled profile)
# ---------------------------------------------------------------------------


class Asset360(BaseModel):
    """
    The complete Asset 360 profile — the final output of the asset pipeline.

    Purpose:
        Aggregate all available intelligence about a single asset into
        one coherent, fully-provenanced response.
    Input:
        Assembled by AssetBuilder from all sub-builder outputs.
    Output:
        Serialized to the Asset360Response API schema.

    Response shape matches Assets.md §Asset 360 Response exactly:
        {asset, timeline, relationships, documents, procedures,
         maintenance, inspections, compliance, health_summary}
    """

    asset: AssetNode
    timeline: List[TimelineEvent] = Field(default_factory=list)
    relationships: List[AssetRelationship] = Field(default_factory=list)
    documents: List[RelatedDocument] = Field(default_factory=list)
    procedures: List[TimelineEvent] = Field(default_factory=list)
    maintenance: List[TimelineEvent] = Field(default_factory=list)
    inspections: List[TimelineEvent] = Field(default_factory=list)
    compliance: List[TimelineEvent] = Field(default_factory=list)
    health_summary: HealthSummary = Field(default_factory=HealthSummary)

    # Diagnostics (not exposed in API response, used internally)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)

"""
Asset Intelligence API Schemas

Pydantic schemas for the Asset API endpoints:
  - GET /assets          → AssetListRequest / AssetListResponse
  - GET /assets/{id}     → Asset360Response

These are the API-facing types. Internal models live in models.py.

Per Assets.md §Security: internal graph identifiers (Neo4j internal node IDs)
are NEVER exposed. Only the stable entity_id scheme is returned.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Asset Search / List
# ---------------------------------------------------------------------------


class AssetSearchFilters(BaseModel):
    """
    Query parameters for GET /assets.

    Per Assets.md §Asset Search: users can filter by tag, name,
    equipment_id, location, department, and asset_type.

    All fields optional — omitting a field means 'no filter on that field'.
    """

    q: Optional[str] = Field(
        default=None,
        description="Free-text search across name and aliases",
    )
    asset_tag: Optional[str] = Field(default=None, description="Exact or partial asset tag")
    equipment_id: Optional[str] = Field(default=None, description="Equipment ID")
    location: Optional[str] = Field(default=None, description="Location name or code")
    department: Optional[str] = Field(default=None, description="Department name")
    asset_type: Optional[str] = Field(default=None, description="Asset type / category")
    page: int = Field(default=1, ge=1, description="1-indexed page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")


class AssetListItem(BaseModel):
    """
    Compact asset representation for list responses.

    Includes only identity and basic info — full details require GET /assets/{id}.
    """

    entity_id: str
    name: str = ""
    entity_type: str = "Asset"
    asset_tag: Optional[str] = None
    equipment_id: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    source_document: str = ""
    confidence: float = 0.0


class AssetListResponse(BaseModel):
    """
    Response for GET /assets.
    """

    items: List[AssetListItem]
    total: int
    page: int
    limit: int
    pages: int


# ---------------------------------------------------------------------------
# Asset 360 — full profile response
# ---------------------------------------------------------------------------


class TimelineEventResponse(BaseModel):
    """Serializable timeline event for API response."""

    event_type: str
    event_label: str = ""
    description: str = ""
    event_date: Optional[str] = None
    relationship_type: str = ""
    entity_id: str = ""
    entity_name: str = ""
    source_document: str = ""
    confidence: float = 0.0


class AssetRelationshipResponse(BaseModel):
    """Serializable relationship for API response."""

    relationship_type: str
    relationship_category: str = "related"
    direction: str = "outgoing"
    target_entity_id: str = ""
    target_name: str = ""
    target_label: str = ""
    source_document: str = ""
    confidence: float = 0.0


class RelatedDocumentResponse(BaseModel):
    """Serializable related document for API response."""

    document_id: str
    document_name: str = ""
    document_type: str = ""
    section: str = ""
    page_number: Optional[int] = None
    excerpt: str = ""
    chunk_id: str = ""
    confidence: float = 0.0
    source_type: str = "semantic"


class AssetNodeResponse(BaseModel):
    """Serializable asset node for API response."""

    entity_id: str
    name: str = ""
    entity_type: str = "Asset"
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
    source_document: str = ""
    confidence: float = 0.0
    created_at: str = ""


class HealthSummaryResponse(BaseModel):
    """Serializable health summary for API response."""

    maintenance_event_count: int = 0
    failure_count: int = 0
    inspection_count: int = 0
    compliance_event_count: int = 0
    maintenance_frequency: str = "unknown"
    failure_severity: str = "none"
    inspection_status: str = "unknown"
    compliance_status: str = "unknown"
    recent_alerts: List[str] = Field(default_factory=list)
    contributing_documents: List[str] = Field(default_factory=list)


class Asset360Response(BaseModel):
    """
    Full Asset 360 API response.

    Matches Assets.md §Asset 360 Response exactly:
        {asset, timeline, relationships, documents, procedures,
         maintenance, inspections, compliance, health_summary}
    """

    asset: AssetNodeResponse
    timeline: List[TimelineEventResponse] = Field(default_factory=list)
    relationships: List[AssetRelationshipResponse] = Field(default_factory=list)
    documents: List[RelatedDocumentResponse] = Field(default_factory=list)
    procedures: List[TimelineEventResponse] = Field(default_factory=list)
    maintenance: List[TimelineEventResponse] = Field(default_factory=list)
    inspections: List[TimelineEventResponse] = Field(default_factory=list)
    compliance: List[TimelineEventResponse] = Field(default_factory=list)
    health_summary: HealthSummaryResponse = Field(default_factory=HealthSummaryResponse)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)

"""
Knowledge Schemas

Pydantic models for the AI Knowledge Extraction pipeline output.

These schemas define:
  - Individual extraction results per pipeline stage
  - The Canonical Knowledge Object (CKO) — the authoritative output format
  - Persistence metadata for the KnowledgeRepository

Rules:
  - No downstream module consumes raw Gemini output.
  - All AI output is validated against these schemas before use.
  - Every CKO includes confidence score, model version, prompt version.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# -----------------------------------------------
# Entity Schema
# -----------------------------------------------

class ExtractedEntity(BaseModel):
    """
    A single entity extracted by the AI entity extraction stage.

    Conforms to the canonical entity format from Ontology.md.
    """
    entity_id: str = Field(..., description="Unique entity identifier (snake_case)")
    entity_type: str = Field(..., description="Ontology entity type (Asset, Person, etc.)")
    label: str = Field(..., description="Primary canonical name")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    page: Optional[int] = Field(default=None, description="Source page number")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity-specific properties")


class EntityExtractionResult(BaseModel):
    """Output of the entity extraction AI stage."""
    entities: List[ExtractedEntity] = Field(default_factory=list)


# -----------------------------------------------
# Relationship Schema
# -----------------------------------------------

class ExtractedRelationship(BaseModel):
    """
    A single relationship extracted by the AI relationship extraction stage.
    """
    source: str = Field(..., description="Source entity ID")
    relationship: str = Field(..., description="Relationship type (UPPER_SNAKE_CASE)")
    target: str = Field(..., description="Target entity ID")
    confidence: float = Field(..., ge=0.0, le=1.0)
    properties: Dict[str, Any] = Field(default_factory=dict)


class RelationshipExtractionResult(BaseModel):
    """Output of the relationship extraction AI stage."""
    relationships: List[ExtractedRelationship] = Field(default_factory=list)


# -----------------------------------------------
# Measurement Schema
# -----------------------------------------------

class ExtractedMeasurement(BaseModel):
    """
    A single measurement extracted by the AI measurement extraction stage.
    """
    measurement_id: str = Field(..., description="Unique measurement identifier")
    name: str = Field(..., description="Measurement parameter name")
    value: Optional[float] = Field(default=None, description="Scalar value")
    unit: str = Field(..., description="Unit of measurement")
    value_min: Optional[float] = Field(default=None, description="Range minimum")
    value_max: Optional[float] = Field(default=None, description="Range maximum")
    tolerance: Optional[float] = Field(default=None, description="±tolerance value")
    measurement_type: str = Field(default="actual", description="actual|limit|design|alarm")
    applies_to_entity: Optional[str] = Field(default=None, description="Entity ID this measurement belongs to")
    applies_to_label: Optional[str] = Field(default=None, description="Human-readable entity label")
    context: str = Field(default="", description="Surrounding context from document")
    page: Optional[int] = Field(default=None)
    confidence: float = Field(..., ge=0.0, le=1.0)


class MeasurementExtractionResult(BaseModel):
    """Output of the measurement extraction AI stage."""
    measurements: List[ExtractedMeasurement] = Field(default_factory=list)


# -----------------------------------------------
# Procedure Schema
# -----------------------------------------------

class ProcedureStep(BaseModel):
    """A single step within a procedure."""
    step_number: int
    description: str
    warning: Optional[str] = None
    tools: List[str] = Field(default_factory=list)


class ExtractedProcedure(BaseModel):
    """
    A complete procedure extracted by the AI procedure extraction stage.
    """
    procedure_id: str = Field(..., description="Unique procedure identifier")
    name: str = Field(..., description="Procedure name/title")
    procedure_type: str = Field(default="maintenance", description="maintenance|inspection|safety|startup|shutdown|calibration|emergency")
    applies_to_entity: Optional[str] = Field(default=None, description="Target entity ID")
    applies_to_label: Optional[str] = Field(default=None, description="Target entity label")
    steps: List[ProcedureStep] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    required_ppe: List[str] = Field(default_factory=list)
    applicable_standards: List[str] = Field(default_factory=list)
    estimated_duration_hours: Optional[float] = Field(default=None)
    page: Optional[int] = Field(default=None)
    confidence: float = Field(..., ge=0.0, le=1.0)


class ProcedureExtractionResult(BaseModel):
    """Output of the procedure extraction AI stage."""
    procedures: List[ExtractedProcedure] = Field(default_factory=list)


# -----------------------------------------------
# Risk Schema
# -----------------------------------------------

class ExtractedRisk(BaseModel):
    """
    A single risk or hazard extracted by the AI risk analysis stage.
    """
    risk_id: str = Field(..., description="Unique risk identifier")
    name: str = Field(..., description="Risk name/title")
    category: str = Field(default="operational", description="safety|operational|environmental|compliance|financial")
    severity: str = Field(default="medium", description="critical|high|medium|low")
    probability: Optional[str] = Field(default=None, description="high|medium|low")
    applies_to_entity: Optional[str] = Field(default=None)
    applies_to_label: Optional[str] = Field(default=None)
    description: str = Field(default="")
    consequences: List[str] = Field(default_factory=list)
    mitigations: List[str] = Field(default_factory=list)
    applicable_standards: List[str] = Field(default_factory=list)
    page: Optional[int] = Field(default=None)
    confidence: float = Field(..., ge=0.0, le=1.0)


class ExtractedWarning(BaseModel):
    """A safety warning or caution extracted from the document."""
    warning_id: str
    text: str
    severity: str = Field(default="medium", description="critical|high|medium|low")
    applies_to_entity: Optional[str] = None
    page: Optional[int] = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class ExtractedComplianceGap(BaseModel):
    """A compliance gap or regulatory violation found in the document."""
    gap_id: str
    description: str
    regulation: Optional[str] = None
    severity: str = Field(default="high")
    page: Optional[int] = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class RiskExtractionResult(BaseModel):
    """Output of the risk analysis AI stage."""
    risks: List[ExtractedRisk] = Field(default_factory=list)
    warnings: List[ExtractedWarning] = Field(default_factory=list)
    compliance_gaps: List[ExtractedComplianceGap] = Field(default_factory=list)


# -----------------------------------------------
# Summary Schema
# -----------------------------------------------

class DocumentSummaryResult(BaseModel):
    """Output of the document summary AI stage."""
    summary: str = Field(default="", description="Executive technical summary (150-300 words)")
    document_type: str = Field(default="unknown", description="maintenance_report|inspection|procedure|manual|etc.")
    language: str = Field(default="en")
    keywords: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    key_dates: List[str] = Field(default_factory=list)
    key_assets: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)


# -----------------------------------------------
# Ontology Discovery Schema
# -----------------------------------------------

class NewOntologyConcept(BaseModel):
    """A new ontology concept suggested by the AI discovery stage."""
    concept_name: str
    category: str = Field(description="Which existing category it is closest to")
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    justification: str
    related_to_existing: List[str] = Field(default_factory=list)


class OntologyDiscoveryResult(BaseModel):
    """Output of the ontology discovery AI stage."""
    new_concepts: List[NewOntologyConcept] = Field(default_factory=list)


# -----------------------------------------------
# Canonical Knowledge Object (CKO)
# -----------------------------------------------

class CanonicalKnowledgeObject(BaseModel):
    """
    The Canonical Knowledge Object (CKO) — the universal AI extraction output.

    Every processed document produces exactly one CKO.
    All downstream services (Ontology, Graph, Embeddings, Copilot) consume this.

    This object is stored in Supabase Storage and metadata in DB (via KnowledgeRepository).
    """
    # Document reference
    document_id: str = Field(..., description="Supabase document ID")
    document: Dict[str, Any] = Field(default_factory=dict, description="Document metadata from CanonicalDocument")

    # AI extraction output per stage
    summary: str = Field(default="", description="Executive summary")
    document_type: str = Field(default="unknown")
    language: str = Field(default="en")
    keywords: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    key_assets: List[str] = Field(default_factory=list)

    entities: List[ExtractedEntity] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)
    measurements: List[ExtractedMeasurement] = Field(default_factory=list)
    procedures: List[ExtractedProcedure] = Field(default_factory=list)
    risks: List[ExtractedRisk] = Field(default_factory=list)
    standards: List[str] = Field(default_factory=list, description="Referenced standards and regulations")
    warnings: List[ExtractedWarning] = Field(default_factory=list)
    compliance_gaps: List[ExtractedComplianceGap] = Field(default_factory=list)
    new_concepts: List[NewOntologyConcept] = Field(default_factory=list, description="Ontology discovery suggestions")

    # Pipeline quality
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall extraction confidence")
    flagged_entities: List[ExtractedEntity] = Field(default_factory=list, description="Low-confidence entities for review")
    flagged_relationships: List[ExtractedRelationship] = Field(default_factory=list)

    # Versioning and telemetry
    model_version: str = Field(default="", description="LLM model name used")
    prompt_version: str = Field(default="1.0", description="Prompt version used for extraction")
    extraction_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    extraction_time_seconds: float = Field(default=0.0)

    # Pipeline stage latencies (observability)
    stage_latencies: Dict[str, float] = Field(default_factory=dict, description="Per-stage latency in seconds")
    total_prompt_tokens: int = Field(default=0, description="Accumulated prompt tokens across all LLM stages")
    total_completion_tokens: int = Field(default=0, description="Accumulated completion tokens across all LLM stages")
    total_tokens_used: int = Field(default=0, description="Total tokens consumed (prompt + completion)")


# -----------------------------------------------
# Knowledge Record (DB persistence model)
# -----------------------------------------------

class KnowledgeRecord(BaseModel):
    """
    Metadata persisted to the `knowledge_extractions` table in Supabase.

    The full CKO JSON is stored in Supabase Storage.
    This record holds the reference and key metrics.
    """
    id: str = Field(..., description="UUID knowledge record ID")
    document_id: str
    storage_path: str = Field(..., description="Path to CKO JSON in Supabase Storage")
    model_version: str
    prompt_version: str
    confidence: float
    entity_count: int = Field(default=0)
    relationship_count: int = Field(default=0)
    measurement_count: int = Field(default=0)
    procedure_count: int = Field(default=0)
    risk_count: int = Field(default=0)
    extraction_time_seconds: float = Field(default=0.0)
    extraction_timestamp: str
    status: str = Field(default="completed", description="completed|failed|partial")
    error_message: Optional[str] = Field(default=None)
    created_at: Optional[str] = Field(default=None)

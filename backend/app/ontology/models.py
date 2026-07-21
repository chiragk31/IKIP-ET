"""
Ontology Models

Pydantic models for the normalized ontology structures.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NormalizedEntity(BaseModel):
    """
    A fully normalized entity ready for graph insertion.
    Duplicates are merged, synonyms are resolved, and names are canonicalized.
    """
    entity_id: str = Field(..., description="Unique canonical identifier")
    entity_type: str = Field(..., description="Ontology entity type (e.g., Asset, Person)")
    canonical_name: str = Field(..., description="Primary resolved name")
    aliases: List[str] = Field(default_factory=list, description="All known alternative names")
    confidence: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_document_ids: List[str] = Field(default_factory=list)


class NormalizedRelationship(BaseModel):
    """
    A validated relationship between two normalized entities.
    """
    source_id: str = Field(..., description="Source entity ID")
    relationship: str = Field(..., description="Validated relationship type")
    target_id: str = Field(..., description="Target entity ID")
    confidence: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DiscoveredConcept(BaseModel):
    """
    A new concept suggested by AI for ontology enrichment.
    """
    concept_name: str
    category: str
    description: str
    confidence: float
    justification: str
    source_document_id: str


class NormalizedKnowledgeObject(BaseModel):
    """
    The output of the Ontology Manager.
    
    Contains clean, deduplicated entities and validated relationships,
    ready for ingestion by the Graph Builder (Epic 5).
    """
    document_id: str
    entities: List[NormalizedEntity] = Field(default_factory=list)
    relationships: List[NormalizedRelationship] = Field(default_factory=list)
    discovered_concepts: List[DiscoveredConcept] = Field(default_factory=list)
    confidence: float

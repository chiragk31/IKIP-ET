"""
Shared Pydantic Schemas

Common request/response models used across multiple API endpoints.
Every API endpoint must use Pydantic models for type safety.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# -----------------------------------------------
# Base Response Models
# -----------------------------------------------

class APIResponse(BaseModel):
    """Standard API response wrapper."""
    status: str = Field(..., description="'success' or 'error'")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Dict[str, Any]] = Field(default=None)
    errors: Optional[Dict[str, Any]] = Field(default=None)


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    pages: int = Field(..., ge=0)


class PaginatedResponse(BaseModel):
    """Paginated list response."""
    status: str = "success"
    message: str = "Success"
    data: Dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------
# Health Check
# -----------------------------------------------

class ServiceHealth(BaseModel):
    """Health status for an individual service."""
    status: str = Field(..., description="'up' or 'down'")
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Comprehensive health check response."""
    status: str = Field(..., description="'healthy' or 'degraded'")
    services: Dict[str, str] = Field(..., description="Service name to status mapping")
    duration_ms: float = Field(..., description="Health check duration in milliseconds")


# -----------------------------------------------
# Entity Models (Canonical Knowledge Object)
# -----------------------------------------------

class CanonicalEntity(BaseModel):
    """
    Canonical entity format for all AI-extracted entities.

    Every entity extracted by AI must conform to this schema
    before being passed to the Ontology Manager.
    """
    entity_id: str = Field(..., description="Unique entity identifier")
    entity_type: str = Field(..., description="Core ontology entity type")
    label: str = Field(..., description="Primary display name")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    source_document: Optional[str] = Field(default=None)
    page: Optional[int] = Field(default=None)
    properties: Dict[str, Any] = Field(default_factory=dict)


class CanonicalRelationship(BaseModel):
    """
    Canonical relationship format for all AI-extracted relationships.

    Every relationship extracted by AI must conform to this schema.
    """
    source: str = Field(..., description="Source entity ID")
    relationship: str = Field(..., description="Relationship type (e.g., HAS_FAILURE)")
    target: str = Field(..., description="Target entity ID")
    confidence: float = Field(..., ge=0.0, le=1.0)
    properties: Dict[str, Any] = Field(default_factory=dict)


class CanonicalKnowledgeObject(BaseModel):
    """
    Canonical Knowledge Object — the universal data structure passed between pipeline stages.

    Every AI module produces and consumes this format.
    This object is never stored directly — it is transformed into Neo4j, Pinecone, and Supabase records.
    """
    document: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    entities: List[CanonicalEntity] = Field(default_factory=list)
    relationships: List[CanonicalRelationship] = Field(default_factory=list)
    measurements: List[Dict[str, Any]] = Field(default_factory=list)
    chunks: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    citations: List[Dict[str, Any]] = Field(default_factory=list)


# -----------------------------------------------
# Pagination Query Parameters
# -----------------------------------------------

class PaginationParams(BaseModel):
    """Query parameters for paginated list endpoints."""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

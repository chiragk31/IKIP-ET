"""
Ontology Module
"""

from app.ontology.models import (
    NormalizedEntity,
    NormalizedRelationship,
    DiscoveredConcept,
    NormalizedKnowledgeObject,
)
from app.ontology.ontology_manager import OntologyManager
from app.ontology.ontology_repository import OntologyRepository

__all__ = [
    "OntologyManager",
    "OntologyRepository",
    "NormalizedEntity",
    "NormalizedRelationship",
    "DiscoveredConcept",
    "NormalizedKnowledgeObject",
]

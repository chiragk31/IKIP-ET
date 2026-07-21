"""
Ontology Manager
"""

import structlog
from typing import Optional
from app.schemas.knowledge import CanonicalKnowledgeObject
from app.ontology.models import NormalizedKnowledgeObject
from app.ontology.entity_mapper import EntityMapper
from app.ontology.relationship_validator import RelationshipValidator
from app.ontology.ontology_discovery import OntologyDiscovery
from app.ontology.ontology_repository import OntologyRepository
from app.ontology.ontology_validator import OntologyValidator

logger = structlog.get_logger(__name__)


class OntologyManager:
    """
    Orchestrates the ontology normalization and validation pipeline.
    
    Transforms a CanonicalKnowledgeObject (from Epic 3) into a 
    NormalizedKnowledgeObject (for Epic 5), merging duplicates,
    resolving synonyms/aliases, and enforcing the ontology schema.
    """

    def __init__(self, ontology_repo: OntologyRepository) -> None:
        self._entity_mapper = EntityMapper()
        self._relationship_validator = RelationshipValidator()
        self._ontology_discovery = OntologyDiscovery()
        self._ontology_repo = ontology_repo
        self._ontology_validator = OntologyValidator()
        logger.info("ontology_manager_initialized")

    def process(self, cko: CanonicalKnowledgeObject) -> Optional[NormalizedKnowledgeObject]:
        """
        Process a CanonicalKnowledgeObject into a NormalizedKnowledgeObject.
        
        Args:
            cko: The extracted Canonical Knowledge Object
            
        Returns:
            NormalizedKnowledgeObject, or None if validation fails
        """
        logger.info("ontology_processing_start", document_id=cko.document_id)

        # 1. Normalize Entities (Synonyms, Aliases, Deduplication)
        normalized_entities = self._entity_mapper.normalize_entities(
            document_id=cko.document_id,
            raw_entities=cko.entities
        )

        # 2. Validate Relationships (Referential integrity, allowed types)
        validated_relationships = self._relationship_validator.validate(
            raw_relationships=cko.relationships,
            normalized_entities=normalized_entities
        )

        # 3. Process Discovered Concepts
        discovered_concepts = self._ontology_discovery.process(
            document_id=cko.document_id,
            new_concepts=cko.new_concepts
        )
        
        # 4. Persist Discovered Concepts for human review
        if discovered_concepts:
            self._ontology_repo.save_discovered_concepts(discovered_concepts)

        # 5. Assemble NormalizedKnowledgeObject
        nko = NormalizedKnowledgeObject(
            document_id=cko.document_id,
            entities=normalized_entities,
            relationships=validated_relationships,
            discovered_concepts=discovered_concepts,
            confidence=cko.confidence,
        )

        # 6. Final Validation
        if not self._ontology_validator.validate(nko):
            logger.error("ontology_processing_failed_validation", document_id=cko.document_id)
            return None

        storage_path = self._ontology_repo.save_nko(nko)

        logger.info(
            "ontology_processing_complete",
            document_id=nko.document_id,
            entities=len(nko.entities),
            relationships=len(nko.relationships),
            discovered_concepts=len(nko.discovered_concepts),
        )
        
        return nko

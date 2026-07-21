"""
Epic 4 — Ontology Management Tests

Unit tests for:
- SynonymResolver
- AliasResolver
- EntityMapper
- RelationshipValidator
- OntologyDiscovery
- OntologyManager
- OntologyHandler
"""

import pytest
from unittest.mock import MagicMock
from app.schemas.knowledge import (
    CanonicalKnowledgeObject,
    ExtractedEntity,
    ExtractedRelationship,
    NewOntologyConcept,
)
from app.ontology.synonym_resolver import SynonymResolver
from app.ontology.alias_resolver import AliasResolver
from app.ontology.entity_mapper import EntityMapper
from app.ontology.relationship_validator import RelationshipValidator
from app.ontology.ontology_discovery import OntologyDiscovery
from app.ontology.models import NormalizedEntity, NormalizedKnowledgeObject
from app.ontology.ontology_manager import OntologyManager
from app.ontology.constants import CORE_ENTITY_TYPES, VALID_RELATIONSHIP_TYPES


class TestSynonymResolver:
    def setup_method(self):
        self.resolver = SynonymResolver()

    def test_resolve_known_synonym(self):
        assert self.resolver.resolve_label("Water Pump") == "Pump"
        assert self.resolver.resolve_label("feed pump") == "Pump"
        assert self.resolver.resolve_label("Steam Generator") == "Boiler"
        
    def test_resolve_unknown_label_preserves_casing(self):
        assert self.resolver.resolve_label("heat exchanger") == "Heat Exchanger"
        # If it has numbers, it keeps original casing + strip
        assert self.resolver.resolve_label(" heat exchanger 101 ") == "heat exchanger 101"
        
    def test_resolve_type(self):
        assert self.resolver.resolve_type("asset") == "Asset"
        assert self.resolver.resolve_type(" person ") == "Person"


class TestAliasResolver:
    def setup_method(self):
        self.resolver = AliasResolver()

    def test_normalize_tag(self):
        assert self.resolver.normalize_tag("P101") == "P-101"
        assert self.resolver.normalize_tag("P 101") == "P-101"
        assert self.resolver.normalize_tag("p-101") == "P-101"
        assert self.resolver.normalize_tag("VALVE15") == "VALVE-15"
        # Non-tag patterns are left alone
        assert self.resolver.normalize_tag("Main Pump") == "Main Pump"

    def test_deduplicate_aliases(self):
        aliases = self.resolver.deduplicate_aliases(
            label="Pump P-101",
            aliases=["P101", "P-101", "Main Pump", "p 101"]
        )
        assert "P-101" in aliases
        assert "Main Pump" in aliases
        # P-101 should not be duplicated


class TestEntityMapper:
    def setup_method(self):
        self.mapper = EntityMapper()

    def test_normalize_entities_merges_duplicates(self):
        raw_entities = [
            ExtractedEntity(
                entity_id="asset_p101",
                entity_type="Asset",
                label="Water Pump",
                aliases=["P101"],
                confidence=0.8
            ),
            ExtractedEntity(
                entity_id="asset_p101",
                entity_type="Asset",
                label="Feed Pump P-101",
                aliases=["Main Pump"],
                confidence=0.9
            )
        ]
        
        normalized = self.mapper.normalize_entities("doc1", raw_entities)
        assert len(normalized) == 1
        
        entity = normalized[0]
        assert entity.entity_id == "asset_p101"
        assert entity.entity_type == "Asset"
        assert entity.confidence == 0.9
        assert "P-101" in entity.aliases
        assert "Main Pump" in entity.aliases
        assert "Water Pump" in entity.aliases

    def test_normalize_entities_standardizes_tags(self):
        raw_entities = [
            ExtractedEntity(
                entity_id="asset_p102",
                entity_type="Asset",
                label="Pump P102",
                confidence=0.9
            )
        ]
        normalized = self.mapper.normalize_entities("doc1", raw_entities)
        assert normalized[0].canonical_name == "Pump P-102"


class TestRelationshipValidator:
    def setup_method(self):
        self.validator = RelationshipValidator()
        self.entities = [
            NormalizedEntity(
                entity_id="a1", entity_type="Asset", canonical_name="A1", confidence=1.0
            ),
            NormalizedEntity(
                entity_id="a2", entity_type="Asset", canonical_name="A2", confidence=1.0
            )
        ]

    def test_validate_filters_invalid_relationships(self):
        raw_rels = [
            ExtractedRelationship(source="a1", relationship="USES", target="a2", confidence=0.9),
            ExtractedRelationship(source="a1", relationship="USES", target="a3", confidence=0.9), # target doesn't exist
            ExtractedRelationship(source="a3", relationship="USES", target="a2", confidence=0.9), # source doesn't exist
            ExtractedRelationship(source="a1", relationship="INVALID_REL", target="a2", confidence=0.9), # invalid type
            ExtractedRelationship(source="a1", relationship="USES", target="a1", confidence=0.9), # self link
        ]
        
        validated = self.validator.validate(raw_rels, self.entities)
        assert len(validated) == 1
        assert validated[0].source_id == "a1"
        assert validated[0].target_id == "a2"


class TestOntologyDiscovery:
    def setup_method(self):
        self.discovery = OntologyDiscovery()

    def test_process_filters_core_types(self):
        new_concepts = [
            NewOntologyConcept(
                concept_name="LOTO Permit",
                category="Procedure",
                description="desc",
                confidence=0.9,
                justification="just"
            ),
            NewOntologyConcept(
                concept_name="Asset", # Core type
                category="Category",
                description="desc",
                confidence=0.9,
                justification="just"
            )
        ]
        
        discovered = self.discovery.process("doc1", new_concepts)
        assert len(discovered) == 1
        assert discovered[0].concept_name == "LOTO Permit"


class TestOntologyManager:
    def test_process_success(self):
        repo_mock = MagicMock()
        manager = OntologyManager(ontology_repo=repo_mock)
        
        cko = CanonicalKnowledgeObject(
            document_id="doc1",
            entities=[
                ExtractedEntity(entity_id="a1", entity_type="Asset", label="Pump P101", confidence=0.9)
            ],
            relationships=[
                ExtractedRelationship(source="a1", relationship="HAS_FAILURE", target="a1", confidence=0.9) # Will be filtered (self link)
            ],
            new_concepts=[
                NewOntologyConcept(
                    concept_name="New Concept", category="Category", description="desc", confidence=0.9, justification="just"
                )
            ],
            confidence=0.9
        )
        
        nko = manager.process(cko)
        assert nko is not None
        assert nko.document_id == "doc1"
        assert len(nko.entities) == 1
        assert nko.entities[0].canonical_name == "Pump P-101"
        assert len(nko.relationships) == 0 # filtered
        assert len(nko.discovered_concepts) == 1
        
        repo_mock.save_discovered_concepts.assert_called_once()

    def test_process_empty_cko(self):
        repo_mock = MagicMock()
        manager = OntologyManager(ontology_repo=repo_mock)
        
        cko = CanonicalKnowledgeObject(document_id="doc1")
        nko = manager.process(cko)
        assert nko is not None
        assert len(nko.entities) == 0
        repo_mock.save_discovered_concepts.assert_not_called()

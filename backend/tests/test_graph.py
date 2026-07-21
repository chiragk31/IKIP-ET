"""
Test Suite — Graph Builder (Epic 5)

Covers:
 1. NodeBuilder  — entity_id stability, label mapping, missing-ID rejection
 2. RelationshipBuilder — referential integrity, self-link rejection, type validation
 3. GraphValidator — duplicate detection, invalid labels/types, confidence bounds
 4. Idempotency — building the same NKO twice yields the same node/rel objects
    (MERGE semantics guarantee no duplicates in Neo4j; this test verifies the
     pipeline itself is stable — same input → same output on every run)

Pattern:
 - Pure unit tests — no Neo4j driver, no Supabase, no LLM.
 - Mirrors test_ontology.py / test_extraction.py conventions.
 - Pytest classes, explicit fixtures, assertion messages.
"""

import pytest
from datetime import datetime, timezone
from typing import List

from app.ontology.models import (
    NormalizedEntity,
    NormalizedRelationship,
    NormalizedKnowledgeObject,
    DiscoveredConcept,
)
from app.graph.node_builder import NodeBuilder
from app.graph.relationship_builder import RelationshipBuilder
from app.graph.graph_validator import GraphValidator
from app.graph.models import GraphNode, GraphRelationship


# -------------------------------------------------------------------
# Shared fixtures
# -------------------------------------------------------------------

DOCUMENT_ID = "doc_test_001"


def _make_entity(
    entity_id: str,
    entity_type: str = "Asset",
    canonical_name: str = "Pump P-101",
    confidence: float = 0.95,
) -> NormalizedEntity:
    return NormalizedEntity(
        entity_id=entity_id,
        entity_type=entity_type,
        canonical_name=canonical_name,
        aliases=["P101", "Main Pump"],
        confidence=confidence,
        metadata={},
        source_document_ids=[DOCUMENT_ID],
    )


def _make_relationship(
    source_id: str,
    target_id: str,
    relationship: str = "CONNECTED_TO",
    confidence: float = 0.9,
) -> NormalizedRelationship:
    return NormalizedRelationship(
        source_id=source_id,
        relationship=relationship,
        target_id=target_id,
        confidence=confidence,
        metadata={},
    )


# -------------------------------------------------------------------
# 1. NodeBuilder Tests
# -------------------------------------------------------------------

class TestNodeBuilder:

    def setup_method(self):
        self.builder = NodeBuilder()

    def test_builds_node_from_entity(self):
        """NodeBuilder converts a NormalizedEntity into a GraphNode correctly."""
        entity = _make_entity("asset_p101", "Asset", "Pump P-101")
        nodes = self.builder.build([entity], DOCUMENT_ID)

        assert len(nodes) == 1, "Expected exactly one node"
        node = nodes[0]
        assert node.entity_id == "asset_p101"
        assert node.label == "Asset"
        assert node.name == "Pump P-101"
        assert node.source_document == DOCUMENT_ID
        assert node.confidence == 0.95
        assert node.extraction_version == "1.0"

    def test_entity_id_is_stable(self):
        """Running NodeBuilder twice on the same entity gives the same entity_id."""
        entity = _make_entity("asset_p101")
        first_run = self.builder.build([entity], DOCUMENT_ID)
        second_run = self.builder.build([entity], DOCUMENT_ID)

        assert first_run[0].entity_id == second_run[0].entity_id, (
            "entity_id must be deterministic across runs"
        )

    def test_skips_entity_with_missing_id(self):
        """An entity with an empty entity_id is skipped (not raised)."""
        bad_entity = _make_entity("")  # empty entity_id
        nodes = self.builder.build([bad_entity], DOCUMENT_ID)
        assert len(nodes) == 0, "Empty entity_id should be skipped"

    def test_skips_entity_with_whitespace_id(self):
        """An entity with a whitespace-only entity_id is skipped."""
        bad_entity = _make_entity("   ")
        nodes = self.builder.build([bad_entity], DOCUMENT_ID)
        assert len(nodes) == 0

    def test_unknown_entity_type_falls_back_to_concept(self):
        """An unknown entity_type is mapped to the Concept label, not raised."""
        entity = _make_entity("unknown_001", entity_type="WidgetThingamajig")
        nodes = self.builder.build([entity], DOCUMENT_ID)

        assert len(nodes) == 1, "Unknown type should not be skipped"
        assert nodes[0].label == "Concept", (
            "Unknown entity types must fall back to Concept"
        )

    def test_builds_multiple_entities(self):
        """NodeBuilder handles a list of entities."""
        entities = [
            _make_entity("asset_001", "Asset"),
            _make_entity("person_001", "Person"),
            _make_entity("risk_001", "Risk"),
        ]
        nodes = self.builder.build(entities, DOCUMENT_ID)
        assert len(nodes) == 3

    def test_known_entity_types_map_correctly(self):
        """All core EntityType values produce the right label."""
        type_map = {
            "Asset": "Asset",
            "Person": "Person",
            "Organization": "Organization",
            "Location": "Location",
            "Procedure": "Procedure",
            "Event": "Event",
            "Measurement": "Measurement",
            "Risk": "Risk",
            "Failure": "Failure",
            "Regulation": "Regulation",
            "Concept": "Concept",
            "Document": "Document",
        }
        for entity_type, expected_label in type_map.items():
            entity = _make_entity(f"test_{entity_type.lower()}", entity_type)
            nodes = self.builder.build([entity], DOCUMENT_ID)
            assert len(nodes) == 1
            assert nodes[0].label == expected_label, (
                f"Entity type '{entity_type}' should produce label '{expected_label}', "
                f"got '{nodes[0].label}'"
            )


# -------------------------------------------------------------------
# 2. RelationshipBuilder Tests
# -------------------------------------------------------------------

class TestRelationshipBuilder:

    def setup_method(self):
        self.builder = RelationshipBuilder()
        self.node_a = GraphNode(
            entity_id="asset_001",
            label="Asset",
            name="Pump A",
            source_document=DOCUMENT_ID,
            confidence=0.9,
        )
        self.node_b = GraphNode(
            entity_id="location_001",
            label="Location",
            name="Plant Floor 1",
            source_document=DOCUMENT_ID,
            confidence=0.85,
        )
        self.nodes = [self.node_a, self.node_b]

    def test_builds_valid_relationship(self):
        """RelationshipBuilder builds a GraphRelationship for a valid NKO rel."""
        rel = _make_relationship("asset_001", "location_001", "LOCATED_IN")
        rels = self.builder.build([rel], self.nodes, DOCUMENT_ID)

        assert len(rels) == 1
        graph_rel = rels[0]
        assert graph_rel.source_id == "asset_001"
        assert graph_rel.target_id == "location_001"
        assert graph_rel.rel_type == "LOCATED_IN"
        assert graph_rel.source_document == DOCUMENT_ID

    def test_rejects_self_link(self):
        """Self-links (source == target) are rejected."""
        rel = _make_relationship("asset_001", "asset_001", "CONNECTED_TO")
        rels = self.builder.build([rel], self.nodes, DOCUMENT_ID)
        assert len(rels) == 0, "Self-link should be rejected"

    def test_rejects_missing_source(self):
        """A relationship whose source_id is not in the node set is rejected."""
        rel = _make_relationship("nonexistent_id", "location_001", "LOCATED_IN")
        rels = self.builder.build([rel], self.nodes, DOCUMENT_ID)
        assert len(rels) == 0, "Missing source node should be rejected"

    def test_rejects_missing_target(self):
        """A relationship whose target_id is not in the node set is rejected."""
        rel = _make_relationship("asset_001", "nonexistent_id", "LOCATED_IN")
        rels = self.builder.build([rel], self.nodes, DOCUMENT_ID)
        assert len(rels) == 0, "Missing target node should be rejected"

    def test_rejects_invalid_relationship_type(self):
        """A relationship with an unrecognised type is rejected."""
        rel = _make_relationship("asset_001", "location_001", "DOES_MAGIC_THINGS")
        rels = self.builder.build([rel], self.nodes, DOCUMENT_ID)
        assert len(rels) == 0, "Invalid relationship type should be rejected"

    def test_normalizes_relationship_type_to_uppercase(self):
        """Relationship types are uppercased before validation."""
        rel = _make_relationship("asset_001", "location_001", "located_in")
        rels = self.builder.build([rel], self.nodes, DOCUMENT_ID)
        assert len(rels) == 1
        assert rels[0].rel_type == "LOCATED_IN"


# -------------------------------------------------------------------
# 3. GraphValidator Tests
# -------------------------------------------------------------------

class TestGraphValidator:

    def setup_method(self):
        self.validator = GraphValidator()

    def _make_graph_node(self, entity_id: str, label: str = "Asset") -> GraphNode:
        return GraphNode(
            entity_id=entity_id,
            label=label,
            name=f"Name {entity_id}",
            source_document=DOCUMENT_ID,
            confidence=0.9,
        )

    def _make_graph_rel(
        self,
        source_id: str,
        target_id: str,
        rel_type: str = "CONNECTED_TO",
    ) -> GraphRelationship:
        return GraphRelationship(
            source_id=source_id,
            rel_type=rel_type,
            target_id=target_id,
            source_document=DOCUMENT_ID,
            confidence=0.85,
        )

    def test_valid_graph_passes(self):
        """A clean graph with no issues passes validation."""
        nodes = [self._make_graph_node("n1"), self._make_graph_node("n2")]
        rels = [self._make_graph_rel("n1", "n2")]

        result = self.validator.validate(nodes, rels)
        assert result.is_valid
        assert len(result.valid_nodes) == 2
        assert len(result.valid_relationships) == 1

    def test_rejects_duplicate_nodes(self):
        """Two nodes with the same entity_id — second one is rejected."""
        nodes = [
            self._make_graph_node("dup_001"),
            self._make_graph_node("dup_001"),
        ]
        result = self.validator.validate(nodes, [])
        assert len(result.valid_nodes) == 1
        assert len(result.invalid_nodes) == 1
        assert "duplicate" in result.invalid_nodes[0][1]

    def test_rejects_invalid_node_label(self):
        """A node with a label not in VALID_NODE_LABELS is rejected."""
        node = self._make_graph_node("n1", label="Banana")
        result = self.validator.validate([node], [])
        assert len(result.invalid_nodes) == 1
        assert "invalid label" in result.invalid_nodes[0][1]

    def test_rejects_duplicate_relationships(self):
        """Two identical (source, type, target) relationships — second is rejected."""
        nodes = [self._make_graph_node("n1"), self._make_graph_node("n2")]
        rels = [
            self._make_graph_rel("n1", "n2"),
            self._make_graph_rel("n1", "n2"),
        ]
        result = self.validator.validate(nodes, rels)
        assert len(result.valid_relationships) == 1
        assert len(result.invalid_relationships) == 1

    def test_rejects_self_link(self):
        """A relationship where source == target is rejected."""
        nodes = [self._make_graph_node("n1")]
        rels = [self._make_graph_rel("n1", "n1")]
        result = self.validator.validate(nodes, rels)
        assert len(result.invalid_relationships) == 1
        assert "self-link" in result.invalid_relationships[0][1]

    def test_rejects_relationship_missing_source_node(self):
        """A relationship whose source node is not in the valid node set is rejected."""
        nodes = [self._make_graph_node("n2")]
        rels = [self._make_graph_rel("n1", "n2")]  # n1 not in nodes
        result = self.validator.validate(nodes, rels)
        assert len(result.invalid_relationships) == 1

    def test_rejects_relationship_missing_target_node(self):
        """A relationship whose target node is not in the valid node set is rejected."""
        nodes = [self._make_graph_node("n1")]
        rels = [self._make_graph_rel("n1", "n2")]  # n2 not in nodes
        result = self.validator.validate(nodes, rels)
        assert len(result.invalid_relationships) == 1

    def test_rejects_invalid_relationship_type(self):
        """A relationship with an invalid type is rejected."""
        nodes = [self._make_graph_node("n1"), self._make_graph_node("n2")]
        rel = GraphRelationship(
            source_id="n1",
            rel_type="DOES_MAGIC",
            target_id="n2",
            source_document=DOCUMENT_ID,
            confidence=0.9,
        )
        result = self.validator.validate(nodes, [rel])
        assert len(result.invalid_relationships) == 1


# -------------------------------------------------------------------
# 4. Idempotency Test
# -------------------------------------------------------------------

class TestIdempotency:
    """
    Verifies the pipeline is deterministic: running NodeBuilder and
    RelationshipBuilder on the same NKO twice produces identical outputs.

    This is the Python-level guarantee that Neo4j MERGE semantics will
    not create duplicates (same input → same entity_ids → same MERGE keys).
    """

    def test_same_nko_produces_same_nodes_twice(self):
        """Building the same NKO twice produces identical node entity_ids."""
        builder = NodeBuilder()
        entities = [
            _make_entity("asset_001", "Asset", "Pump P-101"),
            _make_entity("person_001", "Person", "Jane Doe"),
        ]

        first = builder.build(entities, DOCUMENT_ID)
        second = builder.build(entities, DOCUMENT_ID)

        first_ids = sorted(n.entity_id for n in first)
        second_ids = sorted(n.entity_id for n in second)

        assert first_ids == second_ids, (
            "Same NKO must produce the same node entity_ids on every run"
        )

    def test_same_nko_produces_same_relationships_twice(self):
        """Building the same NKO twice produces identical relationship keys."""
        node_builder = NodeBuilder()
        rel_builder = RelationshipBuilder()

        entities = [
            _make_entity("asset_001", "Asset"),
            _make_entity("location_001", "Location"),
        ]
        nko_rels = [_make_relationship("asset_001", "location_001", "LOCATED_IN")]

        nodes = node_builder.build(entities, DOCUMENT_ID)

        first = rel_builder.build(nko_rels, nodes, DOCUMENT_ID)
        second = rel_builder.build(nko_rels, nodes, DOCUMENT_ID)

        def rel_key(r: GraphRelationship):
            return (r.source_id, r.rel_type, r.target_id)

        first_keys = sorted(rel_key(r) for r in first)
        second_keys = sorted(rel_key(r) for r in second)

        assert first_keys == second_keys, (
            "Same NKO must produce the same relationship keys on every run"
        )

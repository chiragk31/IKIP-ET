"""
Graph Validator

Pre-insertion validation of the complete graph (nodes + relationships)
before any Neo4j write is attempted.

Checks (per Graph.md §Graph Validator):
 1. Duplicate nodes (same entity_id)
 2. Duplicate relationships (same source_id, rel_type, target_id)
 3. Invalid node labels (not in VALID_NODE_LABELS)
 4. Invalid relationship types (not in VALID_RELATIONSHIP_TYPES)
 5. Relationships referencing missing nodes
 6. Circular self-links (source_id == target_id)
 7. Invalid confidence values (outside [0.0, 1.0])

Design:
 - Returns a ValidationResult — callers decide whether to abort or proceed.
 - Invalid elements are LOGGED and collected, never silently dropped.
 - Does NOT modify the input lists — returns separate valid/invalid lists.
 - Does NOT call Neo4j.
"""

from dataclasses import dataclass, field
from typing import List, Set, Tuple
import structlog

from app.graph.models import GraphNode, GraphRelationship
from app.graph.constants import VALID_NODE_LABELS, VALID_RELATIONSHIP_TYPES

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """
    Result of a pre-insertion graph validation pass.

    Fields:
        valid_nodes: Nodes that passed all checks.
        valid_relationships: Relationships that passed all checks.
        invalid_nodes: (node, reason) pairs that failed.
        invalid_relationships: (rel, reason) pairs that failed.
        is_valid: True only when there are no invalid elements.
    """

    valid_nodes: List[GraphNode] = field(default_factory=list)
    valid_relationships: List[GraphRelationship] = field(default_factory=list)
    invalid_nodes: List[Tuple[GraphNode, str]] = field(default_factory=list)
    invalid_relationships: List[Tuple[GraphRelationship, str]] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True when both node and relationship invalid lists are empty."""
        return not self.invalid_nodes and not self.invalid_relationships


class GraphValidator:
    """
    Validates a complete graph (nodes + relationships) before Neo4j insertion.

    Purpose:
        Enforce graph.md quality guarantees before any write hits Neo4j.
    Input:
        List[GraphNode] + List[GraphRelationship] from the builders.
    Output:
        ValidationResult — valid/invalid splits with logged reasons.
    """

    def validate(
        self,
        nodes: List[GraphNode],
        relationships: List[GraphRelationship],
    ) -> ValidationResult:
        """
        Run all validation checks on the node + relationship sets.

        Args:
            nodes: GraphNode objects from NodeBuilder.
            relationships: GraphRelationship objects from RelationshipBuilder.

        Returns:
            ValidationResult with valid/invalid splits.
        """
        result = ValidationResult()

        valid_node_ids = self._validate_nodes(nodes, result)
        self._validate_relationships(relationships, valid_node_ids, result)

        logger.info(
            "graph_validator_complete",
            valid_nodes=len(result.valid_nodes),
            invalid_nodes=len(result.invalid_nodes),
            valid_relationships=len(result.valid_relationships),
            invalid_relationships=len(result.invalid_relationships),
        )
        return result

    # ------------------------------------------------------------------
    # Node validation
    # ------------------------------------------------------------------

    def _validate_nodes(
        self,
        nodes: List[GraphNode],
        result: ValidationResult,
    ) -> Set[str]:
        """
        Validate all nodes. Populates result.valid_nodes and result.invalid_nodes.

        Returns:
            Set of entity_ids that passed validation (used for rel checking).
        """
        seen_ids: Set[str] = set()
        valid_ids: Set[str] = set()

        for node in nodes:
            reason = self._check_node(node, seen_ids)
            if reason:
                logger.warning(
                    "graph_validator_node_rejected",
                    entity_id=node.entity_id,
                    label=node.label,
                    reason=reason,
                )
                result.invalid_nodes.append((node, reason))
            else:
                seen_ids.add(node.entity_id)
                valid_ids.add(node.entity_id)
                result.valid_nodes.append(node)

        return valid_ids

    @staticmethod
    def _check_node(node: GraphNode, seen_ids: Set[str]) -> str:
        """
        Return an error reason string if the node is invalid, else ''.
        """
        if not node.entity_id or not node.entity_id.strip():
            return "missing entity_id"
        if node.entity_id in seen_ids:
            return f"duplicate entity_id: {node.entity_id}"
        if node.label not in VALID_NODE_LABELS:
            return f"invalid label: {node.label}"
        if not (0.0 <= node.confidence <= 1.0):
            return f"invalid confidence: {node.confidence}"
        return ""

    # ------------------------------------------------------------------
    # Relationship validation
    # ------------------------------------------------------------------

    def _validate_relationships(
        self,
        relationships: List[GraphRelationship],
        valid_node_ids: Set[str],
        result: ValidationResult,
    ) -> None:
        """
        Validate all relationships. Populates result.valid/invalid_relationships.
        """
        seen_rels: Set[Tuple[str, str, str]] = set()

        for rel in relationships:
            reason = self._check_relationship(rel, valid_node_ids, seen_rels)
            if reason:
                logger.warning(
                    "graph_validator_rel_rejected",
                    source_id=rel.source_id,
                    rel_type=rel.rel_type,
                    target_id=rel.target_id,
                    reason=reason,
                )
                result.invalid_relationships.append((rel, reason))
            else:
                key = (rel.source_id, rel.rel_type, rel.target_id)
                seen_rels.add(key)
                result.valid_relationships.append(rel)

    @staticmethod
    def _check_relationship(
        rel: GraphRelationship,
        valid_node_ids: Set[str],
        seen_rels: Set[Tuple[str, str, str]],
    ) -> str:
        """
        Return an error reason string if the relationship is invalid, else ''.
        """
        if rel.source_id == rel.target_id:
            return "self-link"
        if rel.source_id not in valid_node_ids:
            return f"source_id not in valid nodes: {rel.source_id}"
        if rel.target_id not in valid_node_ids:
            return f"target_id not in valid nodes: {rel.target_id}"
        if rel.rel_type not in VALID_RELATIONSHIP_TYPES:
            return f"invalid relationship type: {rel.rel_type}"
        if not (0.0 <= rel.confidence <= 1.0):
            return f"invalid confidence: {rel.confidence}"
        key = (rel.source_id, rel.rel_type, rel.target_id)
        if key in seen_rels:
            return f"duplicate relationship: {key}"
        return ""

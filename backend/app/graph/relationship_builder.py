"""
Relationship Builder

Converts NormalizedRelationship objects (from NKO) into GraphRelationship
objects, enforcing referential integrity against the node set being built.

Design:
 - Both source_id and target_id must exist in the provided node set.
 - Relationship type must be in VALID_RELATIONSHIP_TYPES.
 - Self-links (source_id == target_id) are rejected.
 - Attaches provenance on every relationship.

This module does NOT call Neo4j.  It only builds Python objects.
"""

from typing import List, Optional, Set
import structlog

from app.ontology.models import NormalizedRelationship
from app.graph.models import GraphNode, GraphRelationship
from app.graph.constants import VALID_RELATIONSHIP_TYPES, GRAPH_PIPELINE_VERSION

logger = structlog.get_logger(__name__)


class RelationshipBuilder:
    """
    Converts NormalizedRelationship objects to GraphRelationship objects.

    Purpose:
        Transform Epic 4 output into graph-ready relationships with provenance.
    Input:
        List[NormalizedRelationship] + the nodes already built by NodeBuilder.
    Output:
        List[GraphRelationship] ready for GraphValidator then GraphRepository.
    """

    def build(
        self,
        relationships: List[NormalizedRelationship],
        nodes: List[GraphNode],
        document_id: str,
    ) -> List[GraphRelationship]:
        """
        Build GraphRelationship objects.

        Args:
            relationships: Normalized relationships from NKO.
            nodes: GraphNode objects already built by NodeBuilder — used for
                   referential integrity checking.
            document_id: Source document ID for provenance.

        Returns:
            List of validated GraphRelationship objects. Invalid ones are
            skipped with a warning log, not raised.
        """
        valid_entity_ids: Set[str] = {n.entity_id for n in nodes}
        graph_rels: List[GraphRelationship] = []

        for rel in relationships:
            graph_rel = self._build_single(rel, valid_entity_ids, document_id)
            if graph_rel is not None:
                graph_rels.append(graph_rel)

        logger.info(
            "relationship_builder_complete",
            document_id=document_id,
            total_input=len(relationships),
            relationships_built=len(graph_rels),
            relationships_skipped=len(relationships) - len(graph_rels),
        )
        return graph_rels

    def _build_single(
        self,
        rel: NormalizedRelationship,
        valid_entity_ids: Set[str],
        document_id: str,
    ) -> Optional[GraphRelationship]:
        """
        Build and validate a single GraphRelationship.

        Args:
            rel: NormalizedRelationship to convert.
            valid_entity_ids: Set of entity_ids from the current node set.
            document_id: Source document ID.

        Returns:
            GraphRelationship, or None if invalid.
        """
        # 1. Reject self-links
        if rel.source_id == rel.target_id:
            logger.warning(
                "relationship_builder_skip_self_link",
                source_id=rel.source_id,
                rel_type=rel.relationship,
            )
            return None

        # 2. Validate source exists in node set
        if rel.source_id not in valid_entity_ids:
            logger.warning(
                "relationship_builder_skip_missing_source",
                source_id=rel.source_id,
                target_id=rel.target_id,
                rel_type=rel.relationship,
            )
            return None

        # 3. Validate target exists in node set
        if rel.target_id not in valid_entity_ids:
            logger.warning(
                "relationship_builder_skip_missing_target",
                source_id=rel.source_id,
                target_id=rel.target_id,
                rel_type=rel.relationship,
            )
            return None

        # 4. Validate relationship type
        rel_type = rel.relationship.strip().upper()
        if rel_type not in VALID_RELATIONSHIP_TYPES:
            logger.warning(
                "relationship_builder_skip_invalid_type",
                source_id=rel.source_id,
                target_id=rel.target_id,
                rel_type=rel.relationship,
            )
            return None

        return GraphRelationship(
            source_id=rel.source_id,
            rel_type=rel_type,
            target_id=rel.target_id,
            properties=rel.metadata,
            source_document=document_id,
            confidence=rel.confidence,
            extraction_version=GRAPH_PIPELINE_VERSION,
        )

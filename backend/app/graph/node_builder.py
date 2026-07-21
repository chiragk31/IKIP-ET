"""
Node Builder

Converts NormalizedEntity objects (from the NKO produced by Epic 4)
into GraphNode objects ready for Neo4j insertion.

Design:
 - Uses entity_id as the stable node key (deterministic from Epic 4 —
   no new UUIDs are generated here).
 - Maps entity_type to a Neo4j node label.
 - Attaches provenance (source_document, confidence, extraction_version).
 - Unknown entity types are mapped to "Concept" (dynamic ontology node)
   and logged as warnings.

This module does NOT call Neo4j.  It only builds Python objects.
"""

from typing import List, Optional
import structlog

from app.ontology.models import NormalizedEntity
from app.graph.models import GraphNode
from app.graph.constants import VALID_NODE_LABELS, GRAPH_PIPELINE_VERSION

logger = structlog.get_logger(__name__)

# Fallback label when entity_type is not in the core ontology
_CONCEPT_LABEL = "Concept"


class NodeBuilder:
    """
    Converts NormalizedEntity objects to GraphNode objects.

    Purpose:
        Transform Epic 4 output into graph-ready objects with provenance.
    Input:
        List[NormalizedEntity] from a NormalizedKnowledgeObject.
    Output:
        List[GraphNode] ready for GraphValidator then GraphRepository.
    """

    def build(
        self,
        entities: List[NormalizedEntity],
        document_id: str,
    ) -> List[GraphNode]:
        """
        Build GraphNode objects from a list of NormalizedEntity objects.

        Args:
            entities: List of normalized entities from NKO.
            document_id: Source document ID for provenance.

        Returns:
            List of GraphNode objects (invalid ones are skipped with a log).
        """
        nodes: List[GraphNode] = []

        for entity in entities:
            node = self._build_single(entity, document_id)
            if node is not None:
                nodes.append(node)

        logger.info(
            "node_builder_complete",
            document_id=document_id,
            total_input=len(entities),
            nodes_built=len(nodes),
            nodes_skipped=len(entities) - len(nodes),
        )
        return nodes

    def _build_single(
        self,
        entity: NormalizedEntity,
        document_id: str,
    ) -> Optional[GraphNode]:
        """
        Build a single GraphNode from a NormalizedEntity.

        Args:
            entity: Normalized entity to convert.
            document_id: Source document ID.

        Returns:
            GraphNode, or None if the entity is invalid.
        """
        # Validate entity_id is present and non-empty
        if not entity.entity_id or not entity.entity_id.strip():
            logger.warning(
                "node_builder_skip_missing_entity_id",
                entity_type=entity.entity_type,
                canonical_name=entity.canonical_name,
            )
            return None

        # Map entity_type to Neo4j label
        label = self._resolve_label(entity.entity_type, entity.entity_id)

        # Build the GraphNode
        return GraphNode(
            entity_id=entity.entity_id.strip(),
            label=label,
            name=entity.canonical_name,
            aliases=entity.aliases,
            properties=entity.metadata,
            source_document=document_id,
            confidence=entity.confidence,
            extraction_version=GRAPH_PIPELINE_VERSION,
        )

    @staticmethod
    def _resolve_label(entity_type: str, entity_id: str) -> str:
        """
        Map an entity_type string to a valid Neo4j node label.

        If the type is not in VALID_NODE_LABELS, falls back to "Concept"
        (the dynamic ontology label) and emits a warning so operators
        can add missing types to the ontology.

        Args:
            entity_type: Entity type string from the NKO.
            entity_id: Entity ID for logging context.

        Returns:
            Valid Neo4j node label string.
        """
        # Normalize casing — ontology uses TitleCase labels
        resolved = entity_type.strip().title() if entity_type else _CONCEPT_LABEL

        if resolved in VALID_NODE_LABELS:
            return resolved

        logger.warning(
            "node_builder_unknown_entity_type",
            entity_type=entity_type,
            entity_id=entity_id,
            fallback_label=_CONCEPT_LABEL,
        )
        return _CONCEPT_LABEL

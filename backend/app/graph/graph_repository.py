"""
Graph Repository

The ONLY module that communicates with Neo4j.

Architecture (from Graph.md §Repository Layer):
    GraphService → GraphRepository → Neo4jClient → Neo4j

Critical rules:
 - Never accept AI-generated / raw Cypher strings.
 - All writes use MERGE semantics (idempotent by design).
 - All writes are batched (NODE_BATCH_SIZE / RELATIONSHIP_BATCH_SIZE).
 - Read queries come from graph_queries.py (parameterized only).

Write semantics:
  Node MERGE key    : entity_id (scoped per native label)
  Rel MERGE key     : (source_id, rel_type, target_id)

  ON CREATE SET  → sets creation-time provenance (source_document, created_at)
  ON MATCH SET   → updates confidence if the new value is higher (enrichment)

Label handling:
  Neo4j does not allow labels to be passed as query parameters. Since
  every label used here is drawn exclusively from VALID_NODE_LABELS
  (a closed, pre-validated set — never raw AI/user text), nodes are
  grouped by label in Python and one MERGE query per label group is
  executed with the label safely interpolated into the Cypher string.
  This is the standard, safe pattern for Neo4j's label-parameterization
  limitation and requires no APOC plugin.
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import structlog

from app.database.neo4j_client import Neo4jClient
from app.graph.models import GraphNode, GraphRelationship
from app.graph.constants import (
    NODE_BATCH_SIZE,
    RELATIONSHIP_BATCH_SIZE,
    VALID_NODE_LABELS,
    VALID_RELATIONSHIP_TYPES,
    GRAPH_PIPELINE_VERSION,
)
from app.graph import graph_queries as Q

logger = structlog.get_logger(__name__)

# -------------------------------------------------------------------
# Relationship MERGE template — rel_type is interpolated into the
# Cypher string because Neo4j does not support parameterized
# relationship types. Safe ONLY because rel_type is always drawn
# from VALID_RELATIONSHIP_TYPES (a closed, code-defined enum) before
# this template is ever formatted — never raw AI/user text.
# -------------------------------------------------------------------

_MERGE_RELATIONSHIP_TEMPLATE = """
UNWIND $rels AS r
MATCH (src {{entity_id: r.source_id}})
MATCH (tgt {{entity_id: r.target_id}})
MERGE (src)-[rel:{rel_type}]->(tgt)
ON CREATE SET
    rel.confidence          = r.confidence,
    rel.source_document     = r.source_document,
    rel.extraction_version  = r.extraction_version,
    rel.created_at          = r.created_at
ON MATCH SET
    rel.confidence = CASE
        WHEN r.confidence > rel.confidence THEN r.confidence
        ELSE rel.confidence
    END
RETURN count(rel) AS merged
"""

_MERGE_DOCUMENT_CYPHER = """
MERGE (d:Document {entity_id: $document_id})
ON CREATE SET
    d.name               = $document_id,
    d.entity_type        = 'Document',
    d.created_at          = $created_at,
    d.extraction_version = $extraction_version
RETURN d.entity_id AS entity_id
"""


class GraphRepository:
    """
    The ONLY writer to Neo4j in the entire IKIP platform.

    Purpose:
        Persist validated GraphNode and GraphRelationship objects via
        idempotent MERGE operations.
    Input:
        Validated lists from GraphValidator.
    Output:
        Integer counts of merged nodes/relationships (for reporting).
    """

    def __init__(self, neo4j: Neo4jClient) -> None:
        """
        Initialize GraphRepository.

        Args:
            neo4j: Configured Neo4j client wrapper.
        """
        self._neo4j = neo4j
        logger.info("graph_repository_initialized")

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def merge_document_node(self, document_id: str) -> None:
        """
        Ensure a :Document node exists for the given document_id.

        Called once per graph build, before entity nodes are written,
        so status/related-document queries (which MATCH on :Document)
        succeed instead of warning on a missing label.

        Args:
            document_id: The document's entity_id (its Supabase document ID).
        """
        params = {
            "document_id": document_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "extraction_version": GRAPH_PIPELINE_VERSION,
        }
        try:
            self._neo4j.execute_query(_MERGE_DOCUMENT_CYPHER, params)
            logger.info("document_node_merged", document_id=document_id)
        except Exception as e:
            logger.error(
                "document_node_merge_failed",
                document_id=document_id,
                error=str(e),
            )
            raise

    def merge_nodes(self, nodes: List[GraphNode]) -> int:
        """
        Batch-MERGE a list of GraphNode objects into Neo4j.

        Nodes are grouped by label (native Neo4j label, e.g. :Asset,
        :Person) since labels cannot be passed as query parameters.
        Each group is written with MERGE on entity_id — idempotent:
        re-running the same nodes does not create duplicates.

        Args:
            nodes: Validated GraphNode objects to persist.

        Returns:
            Number of nodes successfully merged.
        """
        if not nodes:
            return 0

        grouped: Dict[str, List[GraphNode]] = defaultdict(list)
        for n in nodes:
            grouped[n.label].append(n)

        total_merged = 0
        for label, label_nodes in grouped.items():
            if label not in VALID_NODE_LABELS:
                # Should never happen — GraphValidator rejects unknown
                # labels before this point — but never interpolate an
                # unvalidated string into Cypher, so hard-stop instead.
                logger.error(
                    "node_merge_rejected_invalid_label",
                    label=label,
                    count=len(label_nodes),
                )
                continue

            cypher = self._build_node_merge_cypher(label)

            for batch in self._batch(label_nodes, NODE_BATCH_SIZE):
                params = {"nodes": [self._node_to_params(n) for n in batch]}
                try:
                    results = self._neo4j.execute_query(cypher, params)
                    merged = results[0].get("merged", 0) if results else len(batch)
                    total_merged += merged
                    logger.debug(
                        "node_batch_merged",
                        label=label,
                        batch_size=len(batch),
                        merged=merged,
                    )
                except Exception as e:
                    logger.error(
                        "node_batch_merge_failed",
                        label=label,
                        batch_size=len(batch),
                        error=str(e),
                    )
                    raise

        logger.info("nodes_merged_total", total_merged=total_merged, total_input=len(nodes))
        return total_merged

    def merge_relationships(self, relationships: List[GraphRelationship]) -> int:
        """
        Batch-MERGE a list of GraphRelationship objects into Neo4j.

        Relationships are grouped by rel_type (native Neo4j relationship
        type, e.g. :CAUSED_BY, :REQUIRES) since relationship types cannot
        be passed as query parameters — the same constraint and pattern
        as node label handling (see _build_node_merge_cypher / AD-021).

        MERGE key: (source_id, rel_type, target_id) via the native type
        plus matched src/tgt entity_ids — idempotent.

        Args:
            relationships: Validated GraphRelationship objects to persist.

        Returns:
            Number of relationships successfully merged.
        """
        if not relationships:
            return 0

        grouped: Dict[str, List[GraphRelationship]] = defaultdict(list)
        for r in relationships:
            grouped[r.rel_type].append(r)

        total_merged = 0
        for rel_type, rel_group in grouped.items():
            if rel_type not in VALID_RELATIONSHIP_TYPES:
                # Should never happen — RelationshipBuilder/GraphValidator
                # reject unknown types before this point — but never
                # interpolate an unvalidated string into Cypher, so
                # hard-stop instead.
                logger.error(
                    "rel_merge_rejected_invalid_type",
                    rel_type=rel_type,
                    count=len(rel_group),
                )
                continue

            cypher = self._build_relationship_merge_cypher(rel_type)

            for batch in self._batch(rel_group, RELATIONSHIP_BATCH_SIZE):
                params = {"rels": [self._rel_to_params(r) for r in batch]}
                try:
                    results = self._neo4j.execute_query(cypher, params)
                    merged = results[0].get("merged", 0) if results else len(batch)
                    total_merged += merged
                    logger.debug(
                        "rel_batch_merged",
                        rel_type=rel_type,
                        batch_size=len(batch),
                        merged=merged,
                    )
                except Exception as e:
                    logger.error(
                        "rel_batch_merge_failed",
                        rel_type=rel_type,
                        batch_size=len(batch),
                        error=str(e),
                    )
                    raise

        logger.info(
            "relationships_merged_total",
            total_merged=total_merged,
            total_input=len(relationships),
        )
        return total_merged

    # ------------------------------------------------------------------
    # Read operations (delegate to graph_queries.py)
    # ------------------------------------------------------------------

    def get_asset_360(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Return all connected nodes and relationships for an asset.

        Args:
            entity_id: Stable entity ID of the target asset.

        Returns:
            List of result records from Neo4j.
        """
        return self._neo4j.execute_query(
            Q.ASSET_360_QUERY,
            Q.asset_360_params(entity_id),
        )

    def get_neighbors(self, entity_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Return first-degree neighbours of a node.

        Args:
            entity_id: Node to explore.
            limit: Max neighbours to return.

        Returns:
            List of neighbor records.
        """
        return self._neo4j.execute_query(
            Q.NEIGHBOR_DISCOVERY_QUERY,
            Q.neighbor_discovery_params(entity_id, limit),
        )

    def get_related_documents(
        self, document_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Return documents sharing entities with the given document.

        Args:
            document_id: Document entity_id.
            limit: Max results.

        Returns:
            List of related document records.
        """
        return self._neo4j.execute_query(
            Q.RELATED_DOCUMENTS_QUERY,
            Q.related_documents_params(document_id, limit),
        )

    def get_node_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single node by its stable entity_id.

        Args:
            entity_id: Stable entity ID.

        Returns:
            Node dict, or None if not found.
        """
        results = self._neo4j.execute_query(
            Q.NODE_BY_ID_QUERY,
            Q.node_by_id_params(entity_id),
        )
        return results[0] if results else None

    def list_nodes(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """
        Return a paginated list of all graph nodes.

        Args:
            page: 1-indexed page number.
            limit: Items per page.

        Returns:
            Dict with 'items' (list of node dicts) and 'total' count.
        """
        items = self._neo4j.execute_query(
            Q.LIST_NODES_QUERY,
            Q.list_nodes_params(page, limit),
        )
        total_result = self._neo4j.execute_query(Q.COUNT_NODES_QUERY, {})
        total = total_result[0].get("total", 0) if total_result else 0
        return {"items": items, "total": total}

    def get_document_graph_status(
        self, document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check whether a document's nodes have been written to Neo4j.

        Args:
            document_id: Document entity_id to check.

        Returns:
            Dict with 'document_id' and 'graphed_at', or None if not yet graphed.
        """
        results = self._neo4j.execute_query(
            Q.DOCUMENT_GRAPH_STATUS_QUERY,
            Q.document_graph_status_params(document_id),
        )
        return results[0] if results else None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_node_merge_cypher(label: str) -> str:
        """
        Build a MERGE query for a single, pre-validated node label.

        `label` MUST already be checked against VALID_NODE_LABELS by the
        caller before this is invoked — it is interpolated directly into
        the Cypher string because Neo4j does not support parameterized
        labels. This is safe only because the value space is a closed,
        code-defined enum, never raw AI or user text.
        """
        return f"""
UNWIND $nodes AS n
MERGE (node:{label} {{entity_id: n.entity_id}})
ON CREATE SET
    node.name               = n.name,
    node.entity_type        = n.label,
    node.confidence         = n.confidence,
    node.source_document    = n.source_document,
    node.extraction_version = n.extraction_version,
    node.created_at         = n.created_at,
    node.aliases            = n.aliases,
    node.properties         = n.properties
ON MATCH SET
    node.confidence = CASE
        WHEN n.confidence > node.confidence THEN n.confidence
        ELSE node.confidence
    END
RETURN count(node) AS merged
"""

    @staticmethod
    def _build_relationship_merge_cypher(rel_type: str) -> str:
        """
        Build a MERGE query for a single, pre-validated relationship type.

        `rel_type` MUST already be checked against VALID_RELATIONSHIP_TYPES
        by the caller before this is invoked — it is interpolated directly
        into the Cypher string because Neo4j does not support parameterized
        relationship types. This is safe only because the value space is a
        closed, code-defined enum, never raw AI or user text.
        """
        return _MERGE_RELATIONSHIP_TEMPLATE.format(rel_type=rel_type)

    @staticmethod
    def _batch(items: list, size: int):
        """Yield successive fixed-size chunks from items."""
        for i in range(0, len(items), size):
            yield items[i : i + size]

    @staticmethod
    def _node_to_params(node: GraphNode) -> Dict[str, Any]:
        """Convert a GraphNode to a Neo4j parameter dict."""
        return {
            "entity_id": node.entity_id,
            "label": node.label,
            "name": node.name,
            "aliases": node.aliases,
            "properties": str(node.properties),  # store as string; enrich later
            "confidence": node.confidence,
            "source_document": node.source_document,
            "extraction_version": node.extraction_version,
            "created_at": node.created_at,
        }

    @staticmethod
    def _rel_to_params(rel: GraphRelationship) -> Dict[str, Any]:
        """Convert a GraphRelationship to a Neo4j parameter dict."""
        return {
            "source_id": rel.source_id,
            "rel_type": rel.rel_type,
            "target_id": rel.target_id,
            "confidence": rel.confidence,
            "source_document": rel.source_document,
            "extraction_version": rel.extraction_version,
            "created_at": rel.created_at,
        }
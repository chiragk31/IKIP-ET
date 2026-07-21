"""
Graph Service

Orchestrates the complete graph build pipeline for a single document:

    1. Load NKO from OntologyRepository (the persisted artifact from Epic 4)
    2. NodeBuilder   → List[GraphNode]
    3. RelationshipBuilder → List[GraphRelationship]
    4. GraphValidator → ValidationResult (valid/invalid splits)
    5. GraphRepository.merge_nodes()  (batch MERGE)
    6. GraphRepository.merge_relationships()  (batch MERGE)
    7. Return GraphBuildResult (counts + status)

Rules:
 - Never calls LLMService or any AI service.
 - Never calls Neo4j directly — only via GraphRepository.
 - Loads NKO via OntologyRepository.load_nko() — not from the raw CKO.
 - Logs start / complete / failure / duration on every run.
"""

import time
from typing import Optional
import structlog

from app.ontology.ontology_repository import OntologyRepository
from app.graph.node_builder import NodeBuilder
from app.graph.relationship_builder import RelationshipBuilder
from app.graph.graph_validator import GraphValidator
from app.graph.graph_repository import GraphRepository
from app.graph.models import GraphBuildResult

logger = structlog.get_logger(__name__)


class GraphService:
    """
    Orchestrates the NKO → Neo4j graph build pipeline.

    Purpose:
        Convert a persisted NKO into Neo4j nodes and relationships.
    Input:
        document_id — the ID of the document whose NKO to consume.
    Output:
        GraphBuildResult with node/relationship counts and status.
    """

    def __init__(
        self,
        ontology_repo: OntologyRepository,
        graph_repo: GraphRepository,
    ) -> None:
        """
        Initialize GraphService.

        Args:
            ontology_repo: Repository to load the NKO artifact from Supabase Storage.
            graph_repo: Repository to write validated nodes/relationships to Neo4j.
        """
        self._ontology_repo = ontology_repo
        self._graph_repo = graph_repo
        self._node_builder = NodeBuilder()
        self._rel_builder = RelationshipBuilder()
        self._validator = GraphValidator()
        logger.info("graph_service_initialized")

    def build(self, document_id: str) -> GraphBuildResult:
        """
        Run the full graph build pipeline for a document.

        This is the single entry point called by graph_handler.py and the
        manual trigger API.

        Args:
            document_id: ID of the document whose NKO to consume.

        Returns:
            GraphBuildResult with counts and status.
        """
        start_time = time.time()
        logger.info("graph_build_start", document_id=document_id)

        # 1. Load NKO from Supabase Storage
        nko = self._ontology_repo.load_nko(document_id)
        if not nko:
            duration = time.time() - start_time
            logger.error(
                "graph_build_failed_no_nko",
                document_id=document_id,
                duration_seconds=round(duration, 2),
            )
            return GraphBuildResult(
                document_id=document_id,
                status="failed",
                error_message=f"NKO not found for document {document_id}. "
                              "Run ontology normalization first.",
                duration_seconds=round(duration, 2),
            )

        logger.info(
            "graph_build_nko_loaded",
            document_id=document_id,
            entity_count=len(nko.entities),
            relationship_count=len(nko.relationships),
        )

        try:
            # 2. Build nodes
            nodes = self._node_builder.build(
                entities=nko.entities,
                document_id=document_id,
            )

            # 3. Build relationships (uses nodes for referential integrity)
            relationships = self._rel_builder.build(
                relationships=nko.relationships,
                nodes=nodes,
                document_id=document_id,
            )

            # 4. Validate entire graph (pre-insertion)
            validation = self._validator.validate(nodes, relationships)

            nodes_skipped = len(validation.invalid_nodes)
            rels_skipped = len(validation.invalid_relationships)

            if nodes_skipped or rels_skipped:
                logger.warning(
                    "graph_build_validation_rejections",
                    document_id=document_id,
                    nodes_skipped=nodes_skipped,
                    rels_skipped=rels_skipped,
                )

            # 5. Write valid nodes to Neo4j (batch MERGE)
            nodes_written = self._graph_repo.merge_nodes(validation.valid_nodes)

            # 6. Write valid relationships to Neo4j (batch MERGE)
            rels_written = self._graph_repo.merge_relationships(
                validation.valid_relationships
            )

            duration = time.time() - start_time
            logger.info(
                "graph_build_complete",
                document_id=document_id,
                nodes_written=nodes_written,
                rels_written=rels_written,
                nodes_skipped=nodes_skipped,
                rels_skipped=rels_skipped,
                duration_seconds=round(duration, 2),
            )

            return GraphBuildResult(
                document_id=document_id,
                nodes_written=nodes_written,
                relationships_written=rels_written,
                nodes_skipped=nodes_skipped,
                relationships_skipped=rels_skipped,
                duration_seconds=round(duration, 2),
                status="completed",
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "graph_build_failed",
                document_id=document_id,
                error=str(e),
                duration_seconds=round(duration, 2),
            )
            return GraphBuildResult(
                document_id=document_id,
                status="failed",
                error_message=str(e),
                duration_seconds=round(duration, 2),
            )

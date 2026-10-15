"""
Graph Event Handler

Listens for `ontology.updated` events (emitted by OntologyHandler / Epic 4)
and runs the Graph Builder pipeline.

Event flow:
    ontology.updated
        ↓
    handle_ontology_updated()
        ↓
    GraphService.build(document_id)
        ↓
    InngestClient.send_graph_updated_event()
        ↓
    graph.updated

Design:
 - Loads NKO via OntologyRepository.load_nko(document_id) as the primary
   path.  The nko_storage_path from the event payload is used for logging
   only — the repository already knows the path pattern.
 - Falls back gracefully: if nko_storage_path is missing from the payload,
   load_nko() is called anyway (it computes the path internally).
 - No AI calls in this handler.
"""

import time
import structlog

from app.core.dependencies import (
    get_inngest_client,
    create_graph_service_for_inngest,
)

logger = structlog.get_logger(__name__)


async def handle_ontology_updated(
    document_id: str,
    nko_storage_path: str = None,
    entity_count: int = 0,
    relationship_count: int = 0,
    user_id: str = None,
) -> dict:
    """
    Process an `ontology.updated` event.

    Triggers the Graph Builder pipeline (Epic 5), converting the persisted
    NKO into Neo4j nodes and relationships, then emits `graph.updated`.

    Args:
        document_id: Document whose NKO to consume.
        nko_storage_path: Storage path for logging context (optional).
        entity_count: Entity count from the event payload (informational).
        relationship_count: Relationship count from the event payload (informational).
        user_id: Optional user context for the downstream event.

    Returns:
        Dict with build result summary.
    """
    start_time = time.time()

    logger.info(
        "graph_handler_start",
        document_id=document_id,
        nko_storage_path=nko_storage_path,
        entity_count=entity_count,
        relationship_count=relationship_count,
    )

    try:
        # NOTE: create_graph_service_for_inngest() is used instead of
        # get_graph_service() because this handler runs outside FastAPI
        # request handling — FastAPI's Depends() resolver is not active.
        graph_svc = create_graph_service_for_inngest()
        inngest = get_inngest_client()

        # Run the graph build pipeline
        result = graph_svc.build(document_id)

        if result.status == "failed":
            raise ValueError(result.error_message or "Graph build failed")

        duration = time.time() - start_time

        # Emit graph.updated event for downstream modules (Epic 6 — Embeddings)
        inngest.send_graph_updated_event(
            document_id=document_id,
            nodes_written=result.nodes_written,
            relationships_written=result.relationships_written,
            user_id=user_id,
        )

        logger.info(
            "graph_handler_complete",
            document_id=document_id,
            nodes_written=result.nodes_written,
            relationships_written=result.relationships_written,
            duration_seconds=round(duration, 2),
        )

        return {
            "document_id": document_id,
            "status": "completed",
            "nodes_written": result.nodes_written,
            "relationships_written": result.relationships_written,
            "nodes_skipped": result.nodes_skipped,
            "relationships_skipped": result.relationships_skipped,
            "duration_seconds": round(duration, 2),
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "graph_handler_failed",
            document_id=document_id,
            error=str(e),
            duration_seconds=round(duration, 2),
        )
        raise

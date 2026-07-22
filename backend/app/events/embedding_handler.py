"""
Embedding Event Handler

Listens for `graph.updated` events (emitted by GraphHandler / Epic 5)
and runs the Embedding pipeline.

Event flow:
    graph.updated
        ↓
    handle_graph_updated()
        ↓
    EmbeddingService.embed(document_id)
        ↓
    InngestClient.send_embeddings_created_event()
        ↓
    embeddings.created

Design:
 - Receives the same graph.updated payload as emitted by graph_handler.py:
   {document_id, nodes_written, relationships_written, user_id}
 - No AI calls in this handler.
 - Follows the same pattern as graph_handler.py exactly.
"""

import time
import structlog

from app.core.dependencies import (
    get_embedding_service,
    get_inngest_client,
)

logger = structlog.get_logger(__name__)


async def handle_graph_updated(
    document_id: str,
    nodes_written: int = 0,
    relationships_written: int = 0,
    user_id: str = None,
) -> dict:
    """
    Process a `graph.updated` event.

    Triggers the Embedding pipeline (Epic 6), converting the CanonicalDocument
    into Pinecone vectors enriched with NKO graph entity references.

    Args:
        document_id: Document whose CanonicalDocument + NKO to embed.
        nodes_written: Node count from the event payload (informational).
        relationships_written: Relationship count from the event payload (informational).
        user_id: Optional user context for the downstream event.

    Returns:
        Dict with embedding result summary.
    """
    start_time = time.time()

    logger.info(
        "embedding_handler_start",
        document_id=document_id,
        nodes_written=nodes_written,
        relationships_written=relationships_written,
    )

    try:
        # Resolve dependencies (same pattern as graph_handler.py)
        embedding_svc = get_embedding_service()
        inngest = get_inngest_client()

        # Run the embedding pipeline
        result = await embedding_svc.embed(document_id)

        if result.status == "failed":
            raise ValueError(result.error_message or "Embedding pipeline failed")

        duration = time.time() - start_time

        # Emit embeddings.created event for downstream modules (Epic 7 — Copilot/RAG)
        inngest.send_embeddings_created_event(
            document_id=document_id,
            chunks_generated=result.chunks_generated,
            vectors_upserted=result.vectors_upserted,
            user_id=user_id,
        )

        logger.info(
            "embedding_handler_complete",
            document_id=document_id,
            chunks_generated=result.chunks_generated,
            vectors_upserted=result.vectors_upserted,
            chunks_skipped=result.chunks_skipped,
            duration_seconds=round(duration, 2),
        )

        return {
            "document_id": document_id,
            "status": "completed",
            "chunks_generated": result.chunks_generated,
            "chunks_embedded": result.chunks_embedded,
            "chunks_skipped": result.chunks_skipped,
            "vectors_upserted": result.vectors_upserted,
            "duration_seconds": round(duration, 2),
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "embedding_handler_failed",
            document_id=document_id,
            error=str(e),
            duration_seconds=round(duration, 2),
        )
        raise

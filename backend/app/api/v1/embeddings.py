"""
Embeddings API Router

Manual trigger endpoints for the embedding pipeline and semantic search.

Endpoints:
    POST /{document_id}/embed — Manually trigger embedding for a document
    GET  /{document_id}/status — Check whether a document has been embedded
    POST /search — Run a semantic search query

Design:
 - Follows graph.py pattern: manual trigger uses BackgroundTasks so the
   API returns 202 immediately; embedding happens asynchronously.
 - GET /{document_id}/status is included from day one — lessons learned
   from Epic 4/5: never ship a pipeline step without a way to verify it ran.
 - POST /search is synchronous (queries are fast, < 1s typical).
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.core.dependencies import (
    get_embedding_service,
    get_search_service,
    get_pinecone_repository,
)
from app.embeddings.models import SearchQuery, SearchResponse, EmbeddingResult
from app.utils.response import success_response, error_response

router = APIRouter()


# -------------------------------------------------------------------
# Request schemas (simple enough to define inline)
# -------------------------------------------------------------------

class EmbedRequest(BaseModel):
    """Optional request body for the embed endpoint."""
    force: bool = False  # If True, re-embed even if vectors already exist


# -------------------------------------------------------------------
# Background task wrapper
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# Background task wrapper
# -------------------------------------------------------------------

async def _run_embed(document_id: str, canonical_storage_path: str, embedding_svc) -> None:
    """
    Background task: run the embedding pipeline without blocking the API.

    Args:
        document_id: ID of the document to embed.
        canonical_storage_path: Storage path of the canonical.json for this document.
        embedding_svc: EmbeddingService instance.
    """
    import structlog
    logger = structlog.get_logger(__name__)
    try:
        result = await embedding_svc.embed(document_id, canonical_storage_path)
        logger.info(
            "background_embed_complete",
            document_id=document_id,
            status=result.status,
            vectors_upserted=result.vectors_upserted,
        )
    except Exception as e:
        logger.error(
            "background_embed_failed",
            document_id=document_id,
            error=str(e),
        )


# -------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------

@router.post("/{document_id}/embed", status_code=202)
async def trigger_embedding(
    document_id: str,
    canonical_storage_path: str,
    background_tasks: BackgroundTasks,
    embedding_svc=Depends(get_embedding_service),
):
    """
    Manually trigger the embedding pipeline for a document.

    Returns 202 immediately. Embedding runs in the background.
    Use GET /{document_id}/status to check completion.

    Args:
        document_id: ID of the document to embed.
        canonical_storage_path: Storage path of the canonical.json for this document
            (e.g. "processed/{document_id}/canonical.json", or wherever Epic 2
            actually wrote it — check Supabase Storage if unsure).

    Returns:
        202 Accepted with document_id confirmation.
    """
    background_tasks.add_task(_run_embed, document_id, canonical_storage_path, embedding_svc)
    return success_response(
        data={"document_id": document_id},
        message="Embedding pipeline triggered. Use GET /status to track progress.",
    )

@router.get("/{document_id}/status")
async def get_embedding_status(
    document_id: str,
    pinecone_repo=Depends(get_pinecone_repository),
):
    """
    Check whether a document has been embedded in Pinecone.

    Queries the Pinecone index to count vectors with this document_id.
    This confirms the pipeline actually completed, not just that it was triggered.

    Args:
        document_id: Document ID to check.

    Returns:
        Status dict with vector_count and embedded flag.
    """
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("embedding_status_check", document_id=document_id)

    try:
        # Query Pinecone with a zero vector to count matches for this document
        # (filter-only query — we use a dummy vector and filter by document_id)
        dummy_vector = [0.0] * 768
        result = pinecone_repo.query(
            vector=dummy_vector,
            top_k=1,
            filter={"document_id": {"$eq": document_id}},
        )
        matches = result.get("matches", [])
        vector_count = len(matches)
        has_embeddings = vector_count > 0

        # For a more accurate count, check index stats if available
        # (Pinecone's describe_index_stats is namespace-level, not per-document)

        return success_response(
            data={
                "document_id": document_id,
                "embedded": has_embeddings,
                "sample_vector_count": vector_count,
                "note": "sample_vector_count is top_k=1 — use Pinecone console for exact count",
            },
            message="Embedding status retrieved",
        )

    except Exception as e:
        logger.error("embedding_status_failed", document_id=document_id, error=str(e))
        return error_response(
            message="Failed to retrieve embedding status",
            errors={"error": str(e)},
        )


@router.post("/search", response_model=None)
async def semantic_search(
    query: SearchQuery,
    search_svc=Depends(get_search_service),
):
    """
    Execute a semantic search over embedded document chunks.

    Embeds the query, queries Pinecone, and returns the top-K most
    semantically similar chunks with metadata.

    Note: Graph expansion is NOT performed here — that is Epic 7 (Copilot/RAG).

    Args:
        query: SearchQuery with text and optional metadata filters.

    Returns:
        SearchResponse with ranked results.
    """
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("search_request", query_length=len(query.query), top_k=query.top_k)

    try:
        response = await search_svc.search(query)
        return success_response(
            data=response.model_dump(),
            message=f"Found {response.total_results} results",
        )
    except Exception as e:
        logger.error("search_failed", error=str(e))
        return error_response(
            message="Search failed",
            errors={"error": str(e)},
        )

"""
Knowledge Extraction API

Provides endpoints for triggering and querying AI knowledge extraction.

Endpoints:
    POST /knowledge/{document_id}/extract    — Trigger extraction pipeline
    GET  /knowledge/{document_id}            — Get extraction status and metadata
    GET  /knowledge/{document_id}/cko        — Get full CKO JSON

These endpoints mirror the reprocess pattern from the documents router.
They allow manual trigger in development and status polling in production.
"""

from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
import structlog

from app.core.dependencies import get_extraction_service, get_knowledge_repository
from app.services.extraction_service import ExtractionService
from app.repositories.knowledge_repository import KnowledgeRepository
from app.utils.response import success_response, error_response

logger = structlog.get_logger(__name__)

router = APIRouter()


# -----------------------------------------------
# Trigger Knowledge Extraction
# -----------------------------------------------

@router.post(
    "/{document_id}/extract",
    summary="Trigger AI knowledge extraction for a document",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_extraction(
    document_id: str,
    canonical_storage_path: str,
    background_tasks: BackgroundTasks,
    original_filename: str = "",
    user_id: Optional[str] = None,
    extraction_service: ExtractionService = Depends(get_extraction_service),
):
    """
    Trigger the AI knowledge extraction pipeline for a processed document.

    This endpoint is the primary way to start Epic 3 during development.
    In production, the pipeline is triggered automatically by the
    `document.processed` Inngest event.

    The extraction runs asynchronously. Poll `GET /knowledge/{document_id}`
    to check status.

    Args:
        document_id: Supabase document UUID
        canonical_storage_path: Storage path of the canonical JSON (from Epic 2)
        original_filename: Original document filename (for context)
        user_id: Optional user ID for attribution

    Returns:
        202 Accepted with tracking info
    """
    logger.info(
        "knowledge_extraction_trigger",
        document_id=document_id,
        canonical_path=canonical_storage_path,
    )

    async def run_extraction():
        try:
            await extraction_service.extract(
                document_id=document_id,
                canonical_storage_path=canonical_storage_path,
                original_filename=original_filename,
                user_id=user_id,
            )
        except Exception as e:
            logger.error(
                "background_extraction_failed",
                document_id=document_id,
                error=str(e),
            )

    background_tasks.add_task(run_extraction)

    return success_response(
        message="Knowledge extraction started",
        data={
            "document_id": document_id,
            "status": "extracting",
            "note": "Poll GET /knowledge/{document_id} to check status",
        },
        status_code=202,
    )


# -----------------------------------------------
# Get Extraction Status
# -----------------------------------------------

@router.get(
    "/{document_id}",
    summary="Get knowledge extraction status and metadata",
)
async def get_knowledge_status(
    document_id: str,
    knowledge_repo: KnowledgeRepository = Depends(get_knowledge_repository),
):
    """
    Get the knowledge extraction metadata record for a document.

    Returns extraction status, confidence, entity/relationship counts,
    timing information, and the storage path to the full CKO JSON.

    Args:
        document_id: Supabase document UUID

    Returns:
        200 with KnowledgeRecord metadata, or 404 if not extracted yet
    """
    logger.info("knowledge_status_get", document_id=document_id)

    record = knowledge_repo.get_record(document_id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No knowledge extraction record found for document {document_id}. "
                   "The document may not have been extracted yet.",
        )

    return success_response(
        message="Knowledge extraction record retrieved",
        data={
            "knowledge_id": record.id,
            "document_id": record.document_id,
            "status": record.status,
            "confidence": record.confidence,
            "entity_count": record.entity_count,
            "relationship_count": record.relationship_count,
            "measurement_count": record.measurement_count,
            "procedure_count": record.procedure_count,
            "risk_count": record.risk_count,
            "model_version": record.model_version,
            "prompt_version": record.prompt_version,
            "extraction_time_seconds": record.extraction_time_seconds,
            "extraction_timestamp": record.extraction_timestamp,
            "storage_path": record.storage_path,
            "error_message": record.error_message,
            "created_at": record.created_at,
        },
    )


# -----------------------------------------------
# Get Full CKO
# -----------------------------------------------

@router.get(
    "/{document_id}/cko",
    summary="Get the full Canonical Knowledge Object for a document",
)
async def get_canonical_knowledge_object(
    document_id: str,
    knowledge_repo: KnowledgeRepository = Depends(get_knowledge_repository),
):
    """
    Return the complete Canonical Knowledge Object (CKO) for a document.

    The CKO contains all extracted entities, relationships, measurements,
    procedures, risks, summary, keywords, and ontology discoveries.

    This is the primary data consumed by Epic 4 (Ontology), Epic 5 (Graph),
    Epic 6 (Embeddings), and Epic 8 (AI Copilot).

    Args:
        document_id: Supabase document UUID

    Returns:
        200 with full CKO JSON, or 404 if not extracted yet
    """
    logger.info("knowledge_cko_get", document_id=document_id)

    cko = knowledge_repo.load(document_id)

    if not cko:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No CKO found for document {document_id}. "
                   "Run extraction first via POST /knowledge/{document_id}/extract.",
        )

    return success_response(
        message="Canonical Knowledge Object retrieved",
        data=cko.model_dump(),
    )

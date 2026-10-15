"""
Knowledge Extraction Handler

Event handler that listens on `document.processed` events and triggers
the full AI knowledge extraction pipeline.

Architecture:
    document.processed (Inngest or BackgroundTask)
        ↓
    handle_document_processed()
        ↓
    ExtractionService.extract()
        ↓
    knowledge.extracted (event)

For production: Inngest subscribes to `document.processed` and calls
the POST /api/v1/knowledge/extract endpoint, which invokes this handler.

For development/testing: The handler can be called directly via
POST /api/v1/documents/{id}/extract-knowledge.

Retry Policy:
    3 retries with exponential backoff
    Non-recoverable: corrupted canonical JSON, invalid document ID
    Recoverable: Gemini API timeouts, rate limits, storage errors
"""

import asyncio
import time
from typing import Optional
import structlog

from app.services.extraction_service import ExtractionService
from app.core.dependencies import (
    get_supabase_client,
    get_storage_repository,
    get_document_repository,
    get_inngest_client,
    create_llm_service_for_inngest,
    get_knowledge_repository,
)

logger = structlog.get_logger(__name__)

# Non-recoverable error types — Inngest should NOT retry these
NON_RECOVERABLE_ERRORS = (
    ValueError,       # Bad document ID, invalid canonical format
    UnicodeDecodeError,  # Corrupted JSON encoding
)


async def handle_document_processed(
    document_id: str,
    canonical_storage_path: str,
    original_filename: str = "",
    user_id: Optional[str] = None,
) -> dict:
    """
    Process a `document.processed` event through the AI extraction pipeline.

    This is the main entry point for Epic 3. It is called:
      - By the POST /api/v1/documents/{id}/extract-knowledge API endpoint
      - By the Inngest SDK function handler (when wired up)
      - By test code directly

    Args:
        document_id: Supabase document UUID
        canonical_storage_path: Path to canonical JSON in Supabase Storage
        original_filename: Original document filename
        user_id: Optional uploader user ID

    Returns:
        Dict with extraction result summary

    Raises:
        Exception: On failure (Inngest will retry unless non-recoverable)
    """
    start_time = time.time()

    logger.info(
        "knowledge_handler_start",
        document_id=document_id,
        canonical_path=canonical_storage_path,
        filename=original_filename,
    )

    try:
        # Build ExtractionService with production dependencies.
        # NOTE: create_llm_service_for_inngest() is used instead of
        # get_llm_service() because this handler runs outside FastAPI
        # request handling — FastAPI's Depends() resolver is not active
        # here, so calling get_llm_service() directly would pass the raw
        # Depends(get_prompt_manager) marker object as prompt_manager.
        supabase = get_supabase_client()
        storage_repo = get_storage_repository(supabase=supabase)
        document_repo = get_document_repository(supabase=supabase)
        inngest = get_inngest_client()
        llm_service = create_llm_service_for_inngest()
        knowledge_repo = get_knowledge_repository(supabase=supabase)

        service = ExtractionService(
            llm_service=llm_service,
            knowledge_repo=knowledge_repo,
            storage_repo=storage_repo,
            document_repo=document_repo,
            inngest=inngest,
        )

        # Run the extraction pipeline
        cko = await service.extract(
            document_id=document_id,
            canonical_storage_path=canonical_storage_path,
            original_filename=original_filename,
            user_id=user_id,
        )

        duration = time.time() - start_time

        logger.info(
            "knowledge_handler_complete",
            document_id=document_id,
            duration_seconds=round(duration, 2),
            entity_count=len(cko.entities),
            relationship_count=len(cko.relationships),
            measurement_count=len(cko.measurements),
            procedure_count=len(cko.procedures),
            risk_count=len(cko.risks),
            confidence=cko.confidence,
        )

        return {
            "document_id": document_id,
            "status": "completed",
            "entity_count": len(cko.entities),
            "relationship_count": len(cko.relationships),
            "measurement_count": len(cko.measurements),
            "procedure_count": len(cko.procedures),
            "risk_count": len(cko.risks),
            "confidence": cko.confidence,
            "duration_seconds": round(duration, 2),
        }

    except NON_RECOVERABLE_ERRORS as e:
        duration = time.time() - start_time
        logger.error(
            "knowledge_handler_non_recoverable",
            document_id=document_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=round(duration, 2),
        )
        return {
            "document_id": document_id,
            "status": "failed",
            "error": str(e),
            "recoverable": False,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "knowledge_handler_failed",
            document_id=document_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=round(duration, 2),
        )
        # Re-raise so Inngest retries (recoverable error)
        raise

"""
Document Processing Handler

Background event handler that listens on `document.uploaded` and triggers
the full document processing pipeline.

Since we are running FastAPI without the official Inngest Python SDK installed
as a function server, this handler implements the processing as a direct
background task triggered by a dedicated HTTP endpoint.

Architecture:
    Inngest (or test client) → POST /api/v1/documents/{id}/process
    → processing_handler.handle_document_uploaded()
    → ProcessingService.process_document()

For production: This module can be adapted to the official Inngest Python SDK
when it becomes available. The handler signature matches what Inngest expects.

Retry Policy:
    3 retries with exponential backoff (configured in main.py / Inngest dashboard)
    Non-recoverable errors: corrupted file, unsupported type (no retry)
    Recoverable errors: storage timeouts, temporary OCR failures (auto-retry)

Note on Inngest integration:
    The Inngest HTTP event API is used to SEND events (via InngestClient).
    Receiving/handling events uses the Inngest SDK's serve() endpoint.
    Since we call process_document directly in tests/development, the handler
    is written as a plain async function that can be invoked by either:
      - FastAPI background tasks
      - Inngest function handler (when SDK is wired up)
      - Direct test invocation
"""

import asyncio
import time
from typing import Optional
import structlog

from app.services.processing_service import ProcessingService
from app.core.dependencies import (
    get_supabase_client,
    get_storage_repository,
    get_document_repository,
    get_inngest_client,
)

logger = structlog.get_logger(__name__)

# Non-recoverable error types — Inngest should not retry these
NON_RECOVERABLE_ERRORS = (
    ValueError,       # Unsupported doc type, bad detection
    UnicodeDecodeError,  # Corrupted/invalid encoding
)


async def handle_document_uploaded(
    document_id: str,
    storage_path: str,
    mime_type: str,
    file_size: int,
    original_filename: str,
    user_id: Optional[str] = None,
) -> dict:
    """
    Process a document triggered by the `document.uploaded` event.

    This is the main entry point for Epic 2. It's called:
      - By the POST /documents/{id}/process API endpoint
      - By the Inngest SDK function handler (when wired up)
      - By test code directly

    Args:
        document_id: Supabase document ID
        storage_path: Path in Supabase Storage bucket
        mime_type: MIME type from upload
        file_size: File size in bytes
        original_filename: Original filename
        user_id: Optional user ID

    Returns:
        Dict with processing result summary

    Raises:
        Exception: On failure (Inngest will retry unless non-recoverable)
    """
    start_time = time.time()

    logger.info(
        "processing_handler_start",
        document_id=document_id,
        filename=original_filename,
        mime_type=mime_type,
    )

    try:
        # Build ProcessingService with production dependencies
        supabase = get_supabase_client()
        storage_repo = get_storage_repository(supabase=supabase)
        document_repo = get_document_repository(supabase=supabase)
        inngest = get_inngest_client()

        service = ProcessingService(
            document_repo=document_repo,
            storage_repo=storage_repo,
            inngest=inngest,
        )

        # Run the pipeline (synchronous — Docling is CPU-bound)
        # We run it in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        canonical = await loop.run_in_executor(
            None,
            lambda: service.process_document(
                document_id=document_id,
                storage_path=storage_path,
                mime_type=mime_type,
                file_size=file_size,
                original_filename=original_filename,
                user_id=user_id,
            )
        )

        duration = time.time() - start_time

        logger.info(
            "processing_handler_complete",
            document_id=document_id,
            duration_seconds=round(duration, 2),
            pages=canonical.metadata.page_count,
            words=canonical.metadata.word_count,
            ocr_applied=canonical.ocr_applied,
        )

        return {
            "document_id": document_id,
            "status": "completed",
            "pages": canonical.metadata.page_count,
            "words": canonical.metadata.word_count,
            "ocr_applied": canonical.ocr_applied,
            "duration_seconds": round(duration, 2),
        }

    except NON_RECOVERABLE_ERRORS as e:
        duration = time.time() - start_time
        logger.error(
            "processing_handler_non_recoverable",
            document_id=document_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=round(duration, 2),
        )
        # Return failure info — Inngest should NOT retry non-recoverable errors
        return {
            "document_id": document_id,
            "status": "failed",
            "error": str(e),
            "recoverable": False,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "processing_handler_failed",
            document_id=document_id,
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=round(duration, 2),
        )
        # Re-raise so Inngest retries (recoverable error)
        raise

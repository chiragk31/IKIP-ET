"""
Documents API

Endpoints for document upload, listing, retrieval, status, deletion,
and manual reprocessing trigger.

All endpoints follow the standard response format:
    Success: {"status": "success", "message": "...", "data": {...}}
    Error:   {"status": "error",   "message": "...", "errors": {...}}

Upload endpoint returns HTTP 202 Accepted — never blocks for processing.
"""

import time
from typing import Any, Dict, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
import structlog

from app.core.dependencies import (
    get_upload_service,
    get_document_service,
    get_document_repository,
)
from app.services.upload_service import UploadService, FileValidationError
from app.services.document_service import DocumentService
from app.utils.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Documents"])


# -----------------------------------------------
# Upload
# -----------------------------------------------

@router.post(
    "/upload",
    summary="Upload Document",
    description=(
        "Upload a document for AI processing. "
        "Returns 202 Accepted immediately. "
        "Processing happens asynchronously in the background."
    ),
    status_code=202,
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    upload_svc: UploadService = Depends(get_upload_service),
) -> JSONResponse:
    """
    Upload a document.

    Accepts: multipart/form-data with `file` field.

    Supported types: PDF, DOCX, PPTX, XLSX, TXT, CSV, PNG, JPG, JPEG, TIFF
    Maximum size: 50 MB

    Returns 202 Accepted with document_id and queued status.
    Processing (OCR, parsing, AI extraction) runs asynchronously.
    """
    start_time = time.time()
    filename = file.filename or "unnamed_file"

    logger.info(
        "upload_request_received",
        filename=filename,
        content_type=file.content_type,
    )

    try:
        file_content = await file.read()

        result = await upload_svc.upload(
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
            file_content=file_content,
            user_id=None,  # Auth deferred to Phase 10
        )

        duration = time.time() - start_time
        logger.info(
            "upload_request_success",
            document_id=result.document_id,
            duration_ms=round(duration * 1000, 2),
        )

        return JSONResponse(
            status_code=202,
            content={
                "status": "success",
                "message": result.message,
                "data": {
                    "document_id": result.document_id,
                    "status": result.status,
                    "filename": result.original_filename,
                    "file_size": result.file_size,
                    "file_type": result.file_type,
                    "upload_time": result.upload_time.isoformat(),
                },
            },
        )

    except FileValidationError as e:
        logger.warning(
            "upload_validation_rejected",
            filename=filename,
            reason=str(e),
        )
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "message": str(e),
                "errors": {"file": str(e)},
            },
        )

    except Exception as e:
        logger.error(
            "upload_request_failed",
            filename=filename,
            error=str(e),
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Upload failed due to a server error. Please try again.",
                "errors": {},
            },
        )


# -----------------------------------------------
# List Documents
# -----------------------------------------------

@router.get(
    "/",
    summary="List Documents",
    description="List all uploaded documents with pagination.",
)
async def list_documents(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    document_svc: DocumentService = Depends(get_document_service),
) -> JSONResponse:
    """
    List all documents with pagination.

    Returns documents ordered by upload_time descending (newest first).
    """
    try:
        result = await document_svc.list_documents(page=page, limit=limit)

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Documents retrieved successfully",
                "data": {
                    "documents": [
                        {
                            "id": doc.id,
                            "filename": doc.original_filename,
                            "file_type": doc.file_type,
                            "file_size": doc.file_size,
                            "status": doc.status,
                            "processing_stage": doc.processing_stage,
                            "upload_time": doc.upload_time.isoformat(),
                            "document_type": doc.document_type,
                            "language": doc.language,
                        }
                        for doc in result.documents
                    ],
                    "pagination": {
                        "page": result.page,
                        "limit": result.limit,
                        "total": result.total,
                        "pages": result.pages,
                    },
                },
            },
        )

    except Exception as e:
        logger.error("document_list_failed", error=str(e))
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Failed to retrieve documents",
                "errors": {},
            },
        )


# -----------------------------------------------
# Get Document Detail
# -----------------------------------------------

@router.get(
    "/{document_id}",
    summary="Get Document",
    description="Retrieve full details for a specific document.",
)
async def get_document(
    document_id: str,
    document_svc: DocumentService = Depends(get_document_service),
) -> JSONResponse:
    """Retrieve a single document by ID."""
    try:
        doc = await document_svc.get_document(document_id)

        if doc is None:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Document '{document_id}' not found",
                    "errors": {},
                },
            )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Document retrieved successfully",
                "data": {
                    "id": doc.id,
                    "filename": doc.original_filename,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "storage_path": doc.storage_path,
                    "status": doc.status,
                    "processing_stage": doc.processing_stage,
                    "summary": doc.summary,
                    "document_type": doc.document_type,
                    "language": doc.language,
                    "upload_time": doc.upload_time.isoformat(),
                    "created_at": doc.created_at.isoformat(),
                    "updated_at": doc.updated_at.isoformat(),
                },
            },
        )

    except Exception as e:
        logger.error("document_get_failed", document_id=document_id, error=str(e))
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Failed to retrieve document", "errors": {}},
        )


# -----------------------------------------------
# Get Document Status
# -----------------------------------------------

@router.get(
    "/{document_id}/status",
    summary="Document Status",
    description="Get the current processing status of a document. Poll this endpoint for updates.",
)
async def get_document_status(
    document_id: str,
    document_svc: DocumentService = Depends(get_document_service),
) -> JSONResponse:
    """
    Get processing status for a document.

    Frontend polls this endpoint every 3-5 seconds to track pipeline progress.
    """
    try:
        status = await document_svc.get_document_status(document_id)

        if status is None:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Document '{document_id}' not found",
                    "errors": {},
                },
            )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Status retrieved",
                "data": {
                    "document_id": status.document_id,
                    "status": status.status,
                    "processing_stage": status.processing_stage,
                    "updated_at": status.updated_at.isoformat(),
                },
            },
        )

    except Exception as e:
        logger.error("document_status_failed", document_id=document_id, error=str(e))
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Failed to retrieve status", "errors": {}},
        )


# -----------------------------------------------
# Delete Document
# -----------------------------------------------

@router.delete(
    "/{document_id}",
    summary="Delete Document",
    description="Delete a document and its file from storage.",
)
async def delete_document(
    document_id: str,
    document_svc: DocumentService = Depends(get_document_service),
) -> JSONResponse:
    """Delete a document and its associated file."""
    try:
        deleted = await document_svc.delete_document(document_id)

        if not deleted:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Document '{document_id}' not found",
                    "errors": {},
                },
            )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Document deleted successfully",
                "data": {"document_id": document_id},
            },
        )

    except Exception as e:
        logger.error("document_delete_failed", document_id=document_id, error=str(e))
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Failed to delete document", "errors": {}},
        )


# -----------------------------------------------
# Reprocess Document (Manual Trigger)
# -----------------------------------------------

@router.post(
    "/{document_id}/reprocess",
    summary="Reprocess Document",
    description=(
        "Manually trigger document processing pipeline. "
        "Useful when Inngest is not available or for re-running after a failure. "
        "Returns 202 Accepted; processing runs in the background."
    ),
    status_code=202,
)
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    document_svc: DocumentService = Depends(get_document_service),
) -> JSONResponse:
    """
    Manually trigger the processing pipeline for an existing document.

    This endpoint is useful in development when Inngest Dev Server is not
    running, or when a document needs to be reprocessed after a failure.

    The processing job runs asynchronously via FastAPI BackgroundTasks.
    Poll GET /documents/{id}/status for progress.
    """
    try:
        # Fetch document to get storage info
        doc = await document_svc.get_document(document_id)

        if doc is None:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Document '{document_id}' not found",
                    "errors": {},
                },
            )

        # Import handler here to avoid circular imports at module level
        from app.events.processing_handler import handle_document_uploaded

        async def run_processing():
            try:
                await handle_document_uploaded(
                    document_id=doc.id,
                    storage_path=doc.storage_path,
                    mime_type=f"application/{doc.file_type}",  # Best guess
                    file_size=doc.file_size,
                    original_filename=doc.filename,
                    user_id=doc.user_id,
                )
            except Exception as e:
                logger.error(
                    "reprocess_background_failed",
                    document_id=document_id,
                    error=str(e),
                )

        background_tasks.add_task(run_processing)

        logger.info("reprocess_triggered", document_id=document_id)

        return JSONResponse(
            status_code=202,
            content={
                "status": "success",
                "message": "Processing started. Poll /status for updates.",
                "data": {"document_id": document_id},
            },
        )

    except Exception as e:
        logger.error("reprocess_trigger_failed", document_id=document_id, error=str(e))
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Failed to trigger reprocessing", "errors": {}},
        )

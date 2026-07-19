"""
Document Service

Business logic for document management operations.

Architecture:
    API Route → DocumentService → DocumentRepository

Responsibilities:
    - List documents with pagination
    - Retrieve document details
    - Get processing status
    - Trigger reprocessing
    - Delete documents (with storage cleanup)

Rules:
    - No AI logic
    - Always call DocumentRepository (never Supabase directly)
    - For deletion: delete file from storage AND metadata from DB
"""

import time
from typing import Optional
import structlog

from app.repositories.document_repository import DocumentRepository
from app.repositories.storage_repository import StorageRepository
from app.schemas.upload import (
    DocumentSchema,
    DocumentListResponse,
    DocumentStatusResponse,
    ProcessingJobSchema,
)
from app.models.document import DocumentModel, _parse_dt

logger = structlog.get_logger(__name__)


class DocumentService:
    """
    Service for document listing, retrieval, and management.

    Used by the documents API router for all non-upload operations.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        storage_repo: StorageRepository,
    ) -> None:
        """
        Initialize the DocumentService.

        Args:
            document_repo: DocumentRepository for metadata operations
            storage_repo: StorageRepository for file cleanup on deletion
        """
        self._documents = document_repo
        self._storage = storage_repo
        logger.info("document_service_initialized")

    async def list_documents(
        self,
        page: int = 1,
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> DocumentListResponse:
        """
        List documents with pagination.

        Args:
            page: Page number (1-indexed)
            limit: Items per page (max 100)
            user_id: Filter by owner (None = all)

        Returns:
            DocumentListResponse with paginated document list
        """
        start_time = time.time()
        logger.info("document_list_start", page=page, limit=limit)

        documents, total = self._documents.list_all(
            page=page, limit=limit, user_id=user_id
        )

        pages = (total + limit - 1) // limit if limit > 0 else 0

        result = DocumentListResponse(
            documents=[self._to_schema(doc) for doc in documents],
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

        duration = time.time() - start_time
        logger.info(
            "document_list_success",
            count=len(documents),
            total=total,
            duration_ms=round(duration * 1000, 2),
        )
        return result

    async def get_document(self, document_id: str) -> Optional[DocumentSchema]:
        """
        Get a single document by ID.

        Args:
            document_id: UUID of the document

        Returns:
            DocumentSchema if found, None if not found
        """
        logger.info("document_get_start", document_id=document_id)

        doc = self._documents.get_by_id(document_id)
        if doc is None:
            logger.info("document_get_not_found", document_id=document_id)
            return None

        return self._to_schema(doc)

    async def get_document_status(self, document_id: str) -> Optional[DocumentStatusResponse]:
        """
        Get the current processing status of a document.

        Used by the frontend to poll for upload processing progress.

        Args:
            document_id: UUID of the document

        Returns:
            DocumentStatusResponse if found, None if not found
        """
        doc = self._documents.get_by_id(document_id)
        if doc is None:
            return None

        return DocumentStatusResponse(
            document_id=doc.id,
            status=doc.status,
            processing_stage=doc.processing_stage,
            updated_at=doc.updated_at,
        )

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document — removes both the file from storage and the metadata.

        Steps:
            1. Look up document metadata
            2. Delete file from Supabase Storage
            3. Delete metadata from Supabase DB

        Args:
            document_id: UUID of the document

        Returns:
            True if deleted, False if document not found
        """
        logger.info("document_delete_start", document_id=document_id)

        doc = self._documents.get_by_id(document_id)
        if doc is None:
            logger.info("document_delete_not_found", document_id=document_id)
            return False

        # Delete from storage first
        try:
            self._storage.delete_file(doc.storage_path)
        except Exception as e:
            logger.warning(
                "document_delete_storage_failed",
                document_id=document_id,
                storage_path=doc.storage_path,
                error=str(e),
            )
            # Continue with DB deletion even if storage delete fails

        # Delete metadata
        self._documents.delete(document_id)

        logger.info("document_delete_success", document_id=document_id)
        return True

    def _to_schema(self, doc: DocumentModel) -> DocumentSchema:
        """
        Convert DocumentModel to DocumentSchema for API response.

        Args:
            doc: Internal domain model

        Returns:
            Pydantic schema ready for JSON serialization
        """
        return DocumentSchema(
            id=doc.id,
            user_id=doc.user_id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            storage_path=doc.storage_path,
            file_type=doc.file_type,
            file_size=doc.file_size,
            upload_time=doc.upload_time,
            status=doc.status,
            processing_stage=doc.processing_stage,
            summary=doc.summary,
            language=doc.language,
            document_type=doc.document_type,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

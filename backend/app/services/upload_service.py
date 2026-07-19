"""
Upload Service

Coordinates the complete file upload workflow.

Architecture:
    API Route → UploadService → StorageRepository + DocumentRepository → InngestClient

Responsibilities:
    1. Validate file (type, size, extension, MIME type)
    2. Upload file to Supabase Storage via StorageRepository
    3. Save document metadata to Supabase DB via DocumentRepository
    4. Emit `document.uploaded` event via InngestClient
    5. Return UploadResponse immediately (never wait for processing)

Rules:
    - No AI logic
    - No OCR
    - No parsing
    - No Gemini calls
    - Return 202 immediately after event emission
    - Upload failure must attempt storage rollback
"""

import time
import mimetypes
from pathlib import Path
from typing import Optional
import structlog

from app.repositories.storage_repository import StorageRepository
from app.repositories.document_repository import DocumentRepository
from app.events.inngest_client import InngestClient
from app.models.document import DocumentModel
from app.schemas.upload import UploadResponse
from app.utils.constants import (
    SUPPORTED_MIME_TYPES,
    SUPPORTED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    DocumentStatus,
)

logger = structlog.get_logger(__name__)


class FileValidationError(Exception):
    """Raised when a file fails validation checks."""
    pass


class UploadService:
    """
    Service coordinating the document upload workflow.

    Validates, stores, persists metadata, and triggers the AI pipeline.
    Returns immediately after emitting the event — never waits for processing.
    """

    def __init__(
        self,
        storage_repo: StorageRepository,
        document_repo: DocumentRepository,
        inngest: InngestClient,
    ) -> None:
        """
        Initialize the UploadService.

        Args:
            storage_repo: StorageRepository for file operations
            document_repo: DocumentRepository for metadata operations
            inngest: InngestClient for event emission
        """
        self._storage = storage_repo
        self._documents = document_repo
        self._inngest = inngest
        logger.info("upload_service_initialized")

    def validate_file(
        self,
        filename: str,
        content_type: str,
        file_size: int,
        file_content: bytes,
    ) -> str:
        """
        Validate the uploaded file against all rules.

        Checks performed (in order):
            1. Filename not empty
            2. File size <= 50 MB
            3. File extension is supported
            4. MIME type is supported
            5. MIME type matches extension (consistency check)

        Args:
            filename: Original filename from upload
            content_type: MIME type from Content-Type header
            file_size: File size in bytes
            file_content: Raw file bytes (used to sniff MIME if needed)

        Returns:
            Detected file type string (e.g., "pdf", "docx")

        Raises:
            FileValidationError: If any validation check fails
        """
        if not filename or not filename.strip():
            raise FileValidationError("Filename cannot be empty")

        if file_size > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise FileValidationError(
                f"File size {file_size // (1024*1024)} MB exceeds maximum {max_mb} MB"
            )

        if file_size == 0:
            raise FileValidationError("File is empty (0 bytes)")

        # Validate extension
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(SUPPORTED_EXTENSIONS.keys())
            raise FileValidationError(
                f"Unsupported file extension '{suffix}'. Supported: {supported}"
            )

        # Validate MIME type
        # Normalize content_type (strip parameters like "; charset=utf-8")
        normalized_mime = content_type.split(";")[0].strip().lower()

        if normalized_mime not in SUPPORTED_MIME_TYPES:
            # Try to detect from extension as fallback
            guessed_mime, _ = mimetypes.guess_type(filename)
            if guessed_mime and guessed_mime in SUPPORTED_MIME_TYPES:
                normalized_mime = guessed_mime
            else:
                supported = ", ".join(SUPPORTED_MIME_TYPES.keys())
                raise FileValidationError(
                    f"Unsupported MIME type '{normalized_mime}'. Supported: {supported}"
                )

        file_type = SUPPORTED_MIME_TYPES[normalized_mime]
        return file_type.value

    async def upload(
        self,
        filename: str,
        content_type: str,
        file_content: bytes,
        user_id: Optional[str] = None,
    ) -> UploadResponse:
        """
        Execute the complete upload workflow.

        Steps:
            1. Validate file
            2. Upload to Supabase Storage
            3. Save metadata to Supabase DB
            4. Emit `document.uploaded` event to Inngest
            5. Return UploadResponse (202)

        Args:
            filename: Original filename from the upload request
            content_type: MIME type from Content-Type header
            file_content: Raw file bytes
            user_id: Authenticated user ID (None until auth is implemented)

        Returns:
            UploadResponse with document_id and initial status

        Raises:
            FileValidationError: If the file fails validation
            Exception: If storage or database operations fail (with rollback)
        """
        start_time = time.time()
        file_size = len(file_content)
        storage_path: Optional[str] = None

        logger.info(
            "upload_start",
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            user_id=user_id,
        )

        # Step 1: Validate
        file_type = self.validate_file(
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            file_content=file_content,
        )
        logger.info("upload_validation_passed", filename=filename, file_type=file_type)

        # Step 2: Upload to storage
        storage_result = self._storage.upload_file(
            file_content=file_content,
            original_filename=filename,
            mime_type=content_type.split(";")[0].strip(),
        )
        storage_path = storage_result["storage_path"]

        # Step 3: Save metadata
        try:
            document = DocumentModel(
                filename=Path(storage_path).name,
                original_filename=filename,
                storage_path=storage_path,
                file_type=file_type,
                file_size=file_size,
                status=DocumentStatus.QUEUED.value,
                user_id=user_id,
            )

            saved_document = self._documents.create(document)

        except Exception as db_error:
            # Rollback: delete file from storage if metadata save fails
            logger.error(
                "upload_metadata_failed_rolling_back",
                error=str(db_error),
                storage_path=storage_path,
            )
            try:
                self._storage.delete_file(storage_path)
            except Exception as rollback_error:
                logger.error(
                    "upload_rollback_failed",
                    error=str(rollback_error),
                    storage_path=storage_path,
                )
            raise

        # Step 4: Emit event (non-blocking — failure does not fail the upload)
        event_sent = self._inngest.send_document_uploaded_event(
            document_id=saved_document.id,
            storage_path=storage_path,
            mime_type=content_type.split(";")[0].strip(),
            file_size=file_size,
            original_filename=filename,
            user_id=user_id,
        )

        if not event_sent:
            logger.warning(
                "upload_event_not_sent",
                document_id=saved_document.id,
                note="Document saved but processing pipeline not triggered. Reprocess manually.",
            )

        duration = time.time() - start_time
        logger.info(
            "upload_success",
            document_id=saved_document.id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            duration_ms=round(duration * 1000, 2),
            event_sent=event_sent,
        )

        return UploadResponse(
            document_id=saved_document.id,
            status=DocumentStatus.QUEUED.value,
            filename=saved_document.filename,
            original_filename=saved_document.original_filename,
            file_size=saved_document.file_size,
            file_type=saved_document.file_type,
            upload_time=saved_document.upload_time,
        )

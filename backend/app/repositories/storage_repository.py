"""
Storage Repository

Wraps Supabase Storage SDK for all file operations.

Architecture:
    UploadService → StorageRepository → SupabaseClient → Supabase Storage

Rules:
    - Services NEVER call Supabase SDK directly.
    - All file I/O goes through this repository.
    - Storage path pattern: documents/{year}/{month}/{uuid}_{filename}

Storage bucket: `documents` (must be created in Supabase dashboard)
"""

import uuid
from datetime import datetime
from typing import Optional
import structlog

from app.database.supabase import SupabaseClient
from app.utils.constants import STORAGE_BUCKET_DOCUMENTS

logger = structlog.get_logger(__name__)


class StorageRepository:
    """
    Repository for Supabase Storage file operations.

    Handles upload, download, delete, and URL generation.
    All methods are synchronous (Supabase Python SDK is sync).
    """

    def __init__(self, supabase: SupabaseClient) -> None:
        """
        Initialize the StorageRepository.

        Args:
            supabase: Supabase client wrapper (injected)
        """
        self._supabase = supabase
        logger.info("storage_repository_initialized", bucket=STORAGE_BUCKET_DOCUMENTS)

    def _build_storage_path(self, original_filename: str) -> str:
        """
        Build a unique storage path for a file.

        Pattern: documents/{year}/{month}/{uuid}_{sanitized_filename}

        Args:
            original_filename: Original file name from the upload

        Returns:
            Unique storage path string
        """
        now = datetime.utcnow()
        file_id = str(uuid.uuid4())[:8]
        # Sanitize filename: remove spaces, limit length
        sanitized = original_filename.replace(" ", "_")[:100]
        return f"documents/{now.year}/{now.month:02d}/{file_id}_{sanitized}"

    def upload_file(
        self,
        file_content: bytes,
        original_filename: str,
        mime_type: str,
    ) -> dict:
        """
        Upload a file to Supabase Storage.

        Generates a unique storage path automatically.

        Args:
            file_content: Raw file bytes
            original_filename: Original filename (used to build the path)
            mime_type: MIME type for Content-Type header

        Returns:
            Dict with storage_path and public metadata

        Raises:
            Exception: If upload fails (network error, bucket missing, etc.)
        """
        storage_path = self._build_storage_path(original_filename)
        logger.info(
            "storage_upload_start",
            path=storage_path,
            size=len(file_content),
            mime_type=mime_type,
        )

        try:
            response = self._supabase.storage.from_(STORAGE_BUCKET_DOCUMENTS).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": mime_type, "upsert": "false"},
            )

            logger.info(
                "storage_upload_success",
                path=storage_path,
                size=len(file_content),
            )

            return {
                "storage_path": storage_path,
                "bucket": STORAGE_BUCKET_DOCUMENTS,
            }

        except Exception as e:
            logger.error(
                "storage_upload_failed",
                path=storage_path,
                error=str(e),
            )
            raise

    def delete_file(self, storage_path: str) -> None:
        """
        Delete a file from Supabase Storage.

        Called on document deletion or upload rollback.

        Args:
            storage_path: Full path in storage bucket

        Raises:
            Exception: If deletion fails
        """
        logger.info("storage_delete_start", path=storage_path)

        try:
            self._supabase.storage.from_(STORAGE_BUCKET_DOCUMENTS).remove([storage_path])
            logger.info("storage_delete_success", path=storage_path)
        except Exception as e:
            logger.error("storage_delete_failed", path=storage_path, error=str(e))
            raise

    def get_signed_url(
        self,
        storage_path: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a time-limited signed URL for file download.

        Args:
            storage_path: Full path in storage bucket
            expires_in: URL expiry in seconds (default: 1 hour)

        Returns:
            Signed URL string

        Raises:
            Exception: If URL generation fails
        """
        logger.info("storage_signed_url_start", path=storage_path)

        try:
            response = self._supabase.storage.from_(STORAGE_BUCKET_DOCUMENTS).create_signed_url(
                path=storage_path,
                expires_in=expires_in,
            )
            signed_url = response.get("signedURL") or response.get("signed_url", "")
            logger.info("storage_signed_url_success", path=storage_path)
            return signed_url
        except Exception as e:
            logger.error("storage_signed_url_failed", path=storage_path, error=str(e))
            raise

    def download_file(self, storage_path: str) -> bytes:
        """
        Download a file from Supabase Storage.

        Used by the document processing pipeline (Epic 2) to read files.

        Args:
            storage_path: Full path in storage bucket

        Returns:
            Raw file bytes

        Raises:
            Exception: If download fails
        """
        logger.info("storage_download_start", path=storage_path)

        try:
            content = self._supabase.storage.from_(STORAGE_BUCKET_DOCUMENTS).download(storage_path)
            logger.info(
                "storage_download_success",
                path=storage_path,
                size=len(content),
            )
            return content
        except Exception as e:
            logger.error("storage_download_failed", path=storage_path, error=str(e))
            raise

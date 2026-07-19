"""
Document Loader

Downloads a document from Supabase Storage into a temporary local file
that parsers can operate on.

Architecture:
    ProcessingService → DocumentLoader → StorageRepository → Supabase

Rules:
    - Always clean up temp files in a finally block.
    - Never expose temp path to services; use context manager.
    - Never hold large file content in memory longer than needed.
"""

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import structlog

from app.repositories.storage_repository import StorageRepository

logger = structlog.get_logger(__name__)


class DocumentLoader:
    """
    Downloads documents from Supabase Storage to a local temp file.

    Provides a context manager so the temp file is always cleaned up,
    even if parsing fails.
    """

    def __init__(self, storage_repo: StorageRepository) -> None:
        """
        Initialize the DocumentLoader.

        Args:
            storage_repo: StorageRepository (injected)
        """
        self._storage = storage_repo
        logger.info("document_loader_initialized")

    @contextmanager
    def load(
        self,
        storage_path: str,
        original_filename: str,
    ) -> Generator[str, None, None]:
        """
        Download a file from Supabase Storage and yield the local temp path.

        Usage:
            with loader.load(storage_path, filename) as local_path:
                # parse the file at local_path
                ...
            # temp file is deleted here automatically

        Args:
            storage_path: Full path in Supabase Storage bucket
            original_filename: Original filename (used to preserve extension)

        Yields:
            Absolute path to the downloaded temp file

        Raises:
            Exception: If download fails
        """
        # Preserve the original extension so parsers can detect the format
        suffix = Path(original_filename).suffix or ".bin"
        tmp_file = None

        logger.info(
            "document_load_start",
            storage_path=storage_path,
            filename=original_filename,
        )

        try:
            # Download bytes from Supabase Storage
            file_bytes = self._storage.download_file(storage_path)

            # Write to a named temp file with the correct extension
            with tempfile.NamedTemporaryFile(
                suffix=suffix,
                delete=False,
                prefix="ikip_doc_",
            ) as tmp:
                tmp.write(file_bytes)
                tmp_file = tmp.name

            file_size = len(file_bytes)
            logger.info(
                "document_load_success",
                temp_path=tmp_file,
                size_bytes=file_size,
            )

            yield tmp_file

        except Exception as e:
            logger.error(
                "document_load_failed",
                storage_path=storage_path,
                error=str(e),
            )
            raise

        finally:
            # Always clean up temp file
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.unlink(tmp_file)
                    logger.info("document_temp_cleanup", temp_path=tmp_file)
                except OSError as cleanup_err:
                    logger.warning(
                        "document_temp_cleanup_failed",
                        temp_path=tmp_file,
                        error=str(cleanup_err),
                    )

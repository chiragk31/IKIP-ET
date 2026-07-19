"""
Upload Service Tests

Unit tests for the UploadService validation and workflow logic.
All external dependencies (storage, database, Inngest) are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.services.upload_service import UploadService, FileValidationError
from app.models.document import DocumentModel
from app.schemas.upload import UploadResponse


# -----------------------------------------------
# Fixtures
# -----------------------------------------------

def make_upload_service():
    """Create UploadService with fully mocked dependencies."""
    storage_repo = MagicMock()
    document_repo = MagicMock()
    inngest = MagicMock()

    # Default successful mocks
    storage_repo.upload_file.return_value = {
        "storage_path": "documents/2026/07/abc12345_test.pdf",
        "bucket": "documents",
    }

    document_repo.create.return_value = DocumentModel(
        id="test-doc-id-123",
        filename="abc12345_test.pdf",
        original_filename="test.pdf",
        storage_path="documents/2026/07/abc12345_test.pdf",
        file_type="pdf",
        file_size=1024,
        status="queued",
        upload_time=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    inngest.send_document_uploaded_event.return_value = True

    return UploadService(
        storage_repo=storage_repo,
        document_repo=document_repo,
        inngest=inngest,
    )


# -----------------------------------------------
# Validation Tests
# -----------------------------------------------

class TestFileValidation:
    """Tests for UploadService.validate_file()"""

    def setup_method(self):
        self.svc = make_upload_service()

    def test_valid_pdf_accepted(self):
        result = self.svc.validate_file(
            filename="report.pdf",
            content_type="application/pdf",
            file_size=1024,
            file_content=b"%PDF-1.4",
        )
        assert result == "pdf"

    def test_valid_docx_accepted(self):
        result = self.svc.validate_file(
            filename="report.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=2048,
            file_content=b"PK",
        )
        assert result == "docx"

    def test_empty_filename_rejected(self):
        with pytest.raises(FileValidationError, match="Filename cannot be empty"):
            self.svc.validate_file(
                filename="",
                content_type="application/pdf",
                file_size=1024,
                file_content=b"data",
            )

    def test_zero_byte_file_rejected(self):
        with pytest.raises(FileValidationError, match="empty"):
            self.svc.validate_file(
                filename="empty.pdf",
                content_type="application/pdf",
                file_size=0,
                file_content=b"",
            )

    def test_oversized_file_rejected(self):
        max_size = 50 * 1024 * 1024  # 50 MB
        with pytest.raises(FileValidationError, match="exceeds maximum"):
            self.svc.validate_file(
                filename="huge.pdf",
                content_type="application/pdf",
                file_size=max_size + 1,
                file_content=b"data",
            )

    def test_unsupported_extension_rejected(self):
        with pytest.raises(FileValidationError, match="Unsupported file extension"):
            self.svc.validate_file(
                filename="file.exe",
                content_type="application/octet-stream",
                file_size=1024,
                file_content=b"data",
            )

    def test_unsupported_mime_type_rejected(self):
        with pytest.raises(FileValidationError):
            self.svc.validate_file(
                filename="video.mp4",
                content_type="video/mp4",
                file_size=1024,
                file_content=b"data",
            )

    def test_mime_type_with_charset_accepted(self):
        """MIME types with parameters (e.g. charset) should still be accepted."""
        result = self.svc.validate_file(
            filename="report.txt",
            content_type="text/plain; charset=utf-8",
            file_size=512,
            file_content=b"hello world",
        )
        assert result == "txt"

    def test_jpeg_extension_accepted(self):
        result = self.svc.validate_file(
            filename="photo.jpg",
            content_type="image/jpeg",
            file_size=10240,
            file_content=b"\xff\xd8\xff",
        )
        assert result == "jpg"

    def test_png_accepted(self):
        result = self.svc.validate_file(
            filename="diagram.png",
            content_type="image/png",
            file_size=5120,
            file_content=b"\x89PNG",
        )
        assert result == "png"


# -----------------------------------------------
# Upload Workflow Tests
# -----------------------------------------------

class TestUploadWorkflow:
    """Tests for UploadService.upload()"""

    @pytest.mark.asyncio
    async def test_successful_upload_returns_response(self):
        svc = make_upload_service()

        result = await svc.upload(
            filename="report.pdf",
            content_type="application/pdf",
            file_content=b"%PDF-1.4 content here",
        )

        assert isinstance(result, UploadResponse)
        assert result.document_id == "test-doc-id-123"
        assert result.status == "queued"
        assert result.file_type == "pdf"

    @pytest.mark.asyncio
    async def test_upload_calls_storage(self):
        svc = make_upload_service()

        await svc.upload(
            filename="report.pdf",
            content_type="application/pdf",
            file_content=b"%PDF-1.4 content here",
        )

        svc._storage.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_calls_document_repo(self):
        svc = make_upload_service()

        await svc.upload(
            filename="report.pdf",
            content_type="application/pdf",
            file_content=b"%PDF-1.4 content here",
        )

        svc._documents.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_emits_inngest_event(self):
        svc = make_upload_service()

        await svc.upload(
            filename="report.pdf",
            content_type="application/pdf",
            file_content=b"%PDF-1.4 content here",
        )

        svc._inngest.send_document_uploaded_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_validation_error_rejects_early(self):
        svc = make_upload_service()

        with pytest.raises(FileValidationError):
            await svc.upload(
                filename="malware.exe",
                content_type="application/octet-stream",
                file_content=b"data",
            )

        # Storage should NOT be called if validation fails
        svc._storage.upload_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_storage_failure_rolls_back(self):
        """If DB save fails after storage upload, the file should be deleted."""
        svc = make_upload_service()
        svc._storage.upload_file.return_value = {
            "storage_path": "documents/2026/07/abc_report.pdf",
            "bucket": "documents",
        }
        svc._documents.create.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError):
            await svc.upload(
                filename="report.pdf",
                content_type="application/pdf",
                file_content=b"%PDF-1.4 content",
            )

        # Verify rollback was attempted
        svc._storage.delete_file.assert_called_once_with("documents/2026/07/abc_report.pdf")

    @pytest.mark.asyncio
    async def test_inngest_failure_does_not_fail_upload(self):
        """If Inngest is unreachable, the upload should still succeed."""
        svc = make_upload_service()
        svc._inngest.send_document_uploaded_event.return_value = False

        result = await svc.upload(
            filename="report.pdf",
            content_type="application/pdf",
            file_content=b"%PDF-1.4 content",
        )

        # Upload still succeeds even if Inngest event fails
        assert result.document_id == "test-doc-id-123"
        assert result.status == "queued"

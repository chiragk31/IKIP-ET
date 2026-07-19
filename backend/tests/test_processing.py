"""
Processing Service Tests (Unit)

Tests for the full document processing pipeline.
All external dependencies are mocked.

Tests cover:
    - Canonical model serialization
    - CanonicalBuilder merge and normalization
    - DocumentDetector type selection and OCR decision
    - ProcessingService orchestration with mocks
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.canonical.canonical_models import (
    CanonicalDocument,
    CanonicalPage,
    CanonicalSection,
    CanonicalTable,
    CanonicalImage,
    DocumentMetadata,
)
from app.canonical.canonical_builder import CanonicalBuilder
from app.parser.document_detector import DocumentDetector, ParserStrategy
from app.ocr.ocr_service import OCRPageResult
from app.utils.constants import DocumentType


# -----------------------------------------------
# CanonicalDocument Tests
# -----------------------------------------------

class TestCanonicalModels:
    """Tests for CanonicalDocument and related dataclasses."""

    def test_canonical_document_creation(self):
        doc = CanonicalDocument(
            document_id="test-id",
            original_filename="report.pdf",
            storage_path="documents/2026/07/test.pdf",
        )
        assert doc.document_id == "test-id"
        assert doc.original_filename == "report.pdf"
        assert doc.full_text == ""
        assert doc.ocr_applied is False
        assert doc.warnings == []
        assert doc.pages == []

    def test_canonical_document_to_dict(self):
        doc = CanonicalDocument(
            document_id="doc-123",
            original_filename="manual.pdf",
            storage_path="documents/2026/07/manual.pdf",
            full_text="Test content",
            language="en",
        )
        d = doc.to_dict()

        assert d["document_id"] == "doc-123"
        assert d["full_text"] == "Test content"
        assert d["language"] == "en"
        assert "metadata" in d
        assert "pages" in d
        assert "tables" in d
        assert "images" in d

    def test_canonical_document_to_dict_json_serializable(self):
        """to_dict output must be JSON-serializable."""
        doc = CanonicalDocument(
            document_id="doc-456",
            original_filename="report.docx",
            storage_path="documents/2026/07/report.docx",
            pages=[CanonicalPage(page_number=1, text="Page one text")],
            tables=[CanonicalTable(
                page_number=1,
                headers=["Col A", "Col B"],
                rows=[["val1", "val2"]],
                markdown="| Col A | Col B |\n|---|---|\n| val1 | val2 |",
            )],
        )
        # Should not raise
        json_str = json.dumps(doc.to_dict())
        assert "doc-456" in json_str

    def test_metadata_defaults(self):
        meta = DocumentMetadata()
        assert meta.title == ""
        assert meta.language == "en"
        assert meta.page_count == 0
        assert meta.pipeline_version == "1.0.0"


# -----------------------------------------------
# CanonicalBuilder Tests
# -----------------------------------------------

class TestCanonicalBuilder:
    """Tests for the CanonicalBuilder merge and normalization logic."""

    def setup_method(self):
        self.builder = CanonicalBuilder()

    def _make_doc(self, pages=None, full_text="") -> CanonicalDocument:
        return CanonicalDocument(
            document_id="test",
            original_filename="test.pdf",
            storage_path="path/test.pdf",
            pages=pages or [],
            full_text=full_text,
        )

    def test_merge_ocr_empty_results_returns_original(self):
        doc = self._make_doc(
            pages=[CanonicalPage(page_number=1, text="Original text")],
            full_text="Original text",
        )
        result = self.builder.merge_ocr(doc, [])
        assert result.full_text == "Original text"
        assert not result.ocr_applied

    def test_merge_ocr_replaces_sparse_page_text(self):
        doc = self._make_doc(
            pages=[CanonicalPage(page_number=1, text="x")],
        )
        ocr_results = [OCRPageResult(page_number=1, text="This is much longer OCR text from the page.")]
        result = self.builder.merge_ocr(doc, ocr_results)
        assert result.pages[0].text == "This is much longer OCR text from the page."
        assert result.pages[0].ocr_applied is True
        assert result.ocr_applied is True

    def test_merge_ocr_keeps_parser_text_if_better(self):
        long_parser_text = "A" * 500
        doc = self._make_doc(
            pages=[CanonicalPage(page_number=1, text=long_parser_text)],
        )
        ocr_results = [OCRPageResult(page_number=1, text="Short OCR")]
        result = self.builder.merge_ocr(doc, ocr_results)
        # Parser text is longer — should be kept
        assert result.pages[0].text == long_parser_text

    def test_merge_ocr_adds_missing_page(self):
        doc = self._make_doc(
            pages=[CanonicalPage(page_number=1, text="Page 1")],
        )
        ocr_results = [
            OCRPageResult(page_number=1, text="OCR Page 1"),
            OCRPageResult(page_number=2, text="OCR Page 2"),
        ]
        result = self.builder.merge_ocr(doc, ocr_results)
        assert len(result.pages) == 2

    def test_merge_ocr_rebuilds_full_text(self):
        doc = self._make_doc(
            pages=[
                CanonicalPage(page_number=1, text="A"),
                CanonicalPage(page_number=2, text="B"),
            ],
        )
        ocr_results = [OCRPageResult(page_number=1, text="Long OCR text for page one content.")]
        result = self.builder.merge_ocr(doc, ocr_results)
        assert "Long OCR text for page one content." in result.full_text

    def test_finalize_updates_metadata_counts(self):
        from app.canonical.canonical_models import CanonicalTable, CanonicalImage
        doc = self._make_doc(
            pages=[CanonicalPage(page_number=1, text="Hello world")],
            full_text="Hello world",
        )
        doc.tables = [CanonicalTable(page_number=1)]
        doc.images = [CanonicalImage(page_number=1), CanonicalImage(page_number=2)]

        result = self.builder.finalize(doc)
        assert result.metadata.word_count == 2
        assert result.metadata.table_count == 1
        assert result.metadata.image_count == 2

    def test_normalize_text_collapses_whitespace(self):
        result = self.builder._normalize_text("Hello   world\n\n\n\nEnd")
        assert "   " not in result
        assert "\n\n\n" not in result

    def test_normalize_text_handles_empty(self):
        assert self.builder._normalize_text("") == ""
        assert self.builder._normalize_text(None) == ""


# -----------------------------------------------
# DocumentDetector Tests
# -----------------------------------------------

class TestDocumentDetector:
    """Tests for document type detection and parser selection."""

    def setup_method(self):
        self.detector = DocumentDetector()

    def test_pdf_detected_correctly(self):
        result = self.detector.detect("application/pdf", "report.pdf")
        assert result.file_type == DocumentType.PDF
        assert result.parser == ParserStrategy.DOCLING
        assert result.needs_ocr is False

    def test_docx_detected_correctly(self):
        result = self.detector.detect(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "manual.docx",
        )
        assert result.file_type == DocumentType.DOCX
        assert result.parser == ParserStrategy.DOCLING
        assert result.needs_ocr is False

    def test_png_needs_ocr(self):
        result = self.detector.detect("image/png", "scan.png")
        assert result.file_type == DocumentType.PNG
        assert result.parser == ParserStrategy.IMAGE
        assert result.needs_ocr is True

    def test_jpeg_needs_ocr(self):
        result = self.detector.detect("image/jpeg", "photo.jpg")
        assert result.parser == ParserStrategy.IMAGE
        assert result.needs_ocr is True

    def test_tiff_needs_ocr(self):
        result = self.detector.detect("image/tiff", "scan.tiff")
        assert result.parser == ParserStrategy.IMAGE
        assert result.needs_ocr is True

    def test_xlsx_uses_spreadsheet_parser(self):
        result = self.detector.detect(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "data.xlsx",
        )
        assert result.parser == ParserStrategy.SPREADSHEET
        assert result.needs_ocr is False

    def test_csv_uses_spreadsheet_parser(self):
        result = self.detector.detect("text/csv", "data.csv")
        assert result.parser == ParserStrategy.SPREADSHEET

    def test_txt_uses_text_parser(self):
        result = self.detector.detect("text/plain", "notes.txt")
        assert result.parser == ParserStrategy.TEXT
        assert result.needs_ocr is False

    def test_extension_fallback_for_unknown_mime(self):
        result = self.detector.detect("application/octet-stream", "report.pdf")
        assert result.file_type == DocumentType.PDF

    def test_unsupported_type_raises(self):
        with pytest.raises(ValueError):
            self.detector.detect("video/mp4", "movie.mp4")

    def test_mime_with_charset_param_normalized(self):
        result = self.detector.detect("text/plain; charset=utf-8", "file.txt")
        assert result.parser == ParserStrategy.TEXT


# -----------------------------------------------
# ProcessingService Tests (Mocked)
# -----------------------------------------------

class TestProcessingService:
    """Tests for ProcessingService orchestration with all dependencies mocked."""

    def _make_service(self):
        from app.services.processing_service import ProcessingService

        document_repo = MagicMock()
        storage_repo = MagicMock()
        inngest = MagicMock()

        # Mock download_file to return a minimal PDF header
        storage_repo.download_file.return_value = b"%PDF-1.4 fake content"
        storage_repo.upload_file.return_value = {"storage_path": "processed/test/canonical.json"}
        document_repo.update_status.return_value = None
        document_repo.create_processing_job.return_value = MagicMock()
        inngest.send_event.return_value = True

        svc = ProcessingService(
            document_repo=document_repo,
            storage_repo=storage_repo,
            inngest=inngest,
        )

        return svc, document_repo, storage_repo, inngest

    def test_rows_to_markdown_basic(self):
        from app.services.processing_service import ProcessingService
        md = ProcessingService._rows_to_markdown(["A", "B"], [["1", "2"], ["3", "4"]])
        assert "| A | B |" in md
        assert "| 1 | 2 |" in md

    def test_rows_to_markdown_empty_headers(self):
        from app.services.processing_service import ProcessingService
        assert ProcessingService._rows_to_markdown([], []) == ""

    def test_update_status_non_fatal(self):
        """Status update failure should be logged but not raise."""
        svc, doc_repo, _, _ = self._make_service()
        doc_repo.update_status.side_effect = RuntimeError("DB error")
        # Should not raise
        svc._update_status("doc-id", "processing", "parsing")

    def test_create_job_non_fatal(self):
        """Job creation failure should be logged but not raise."""
        svc, doc_repo, _, _ = self._make_service()
        doc_repo.create_processing_job.side_effect = RuntimeError("DB error")
        # Should not raise
        svc._create_job("doc-id", "parsing")

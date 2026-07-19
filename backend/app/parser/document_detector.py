"""
Document Type Detector

Determines the document type from MIME type and extension, selects
the appropriate parser, and decides whether OCR is required.

Architecture:
    ProcessingService → DocumentDetector → ParserStrategy

Rules:
    - Detection is based on MIME type first, extension as fallback.
    - OCR is decided by document type:
        Images always need OCR.
        PDFs need OCR only if they are scanned (detected during parsing).
        Office docs (DOCX, PPTX, XLSX) and text files never need OCR.
"""

from enum import Enum
from pathlib import Path
from typing import NamedTuple
import structlog

from app.utils.constants import SUPPORTED_MIME_TYPES, SUPPORTED_EXTENSIONS, DocumentType

logger = structlog.get_logger(__name__)


class ParserStrategy(str, Enum):
    """Which parser to use for a given document type."""
    DOCLING = "docling"       # PDF, DOCX, PPTX — rich structured extraction
    SPREADSHEET = "spreadsheet"  # XLSX, CSV — tabular extraction
    TEXT = "text"             # TXT — plain text passthrough
    IMAGE = "image"           # PNG, JPG, JPEG, TIFF — OCR only


class DetectionResult(NamedTuple):
    """
    Result of document type detection.

    Attributes:
        file_type: Detected DocumentType enum value
        parser: ParserStrategy to use
        needs_ocr: Whether to run OCR
        mime_type: Resolved MIME type string
    """
    file_type: DocumentType
    parser: ParserStrategy
    needs_ocr: bool
    mime_type: str


# Maps DocumentType → (ParserStrategy, needs_ocr_by_default)
DOCUMENT_TYPE_MAP: dict = {
    DocumentType.PDF:  (ParserStrategy.DOCLING,     False),  # Scanned detection during parse
    DocumentType.DOCX: (ParserStrategy.DOCLING,     False),
    DocumentType.PPTX: (ParserStrategy.DOCLING,     False),
    DocumentType.XLSX: (ParserStrategy.SPREADSHEET, False),
    DocumentType.CSV:  (ParserStrategy.SPREADSHEET, False),
    DocumentType.TXT:  (ParserStrategy.TEXT,        False),
    DocumentType.PNG:  (ParserStrategy.IMAGE,       True),
    DocumentType.JPG:  (ParserStrategy.IMAGE,       True),
    DocumentType.JPEG: (ParserStrategy.IMAGE,       True),
    DocumentType.TIFF: (ParserStrategy.IMAGE,       True),
}


class DocumentDetector:
    """
    Detects document type and selects the appropriate processing strategy.

    Resolution order:
        1. MIME type from upload headers
        2. File extension from original filename
    """

    def detect(
        self,
        mime_type: str,
        original_filename: str,
    ) -> DetectionResult:
        """
        Detect document type and select parser strategy.

        Args:
            mime_type: MIME type from the upload request
            original_filename: Original filename (used for extension fallback)

        Returns:
            DetectionResult with file type, parser, OCR flag, and resolved MIME

        Raises:
            ValueError: If the document type cannot be determined
        """
        logger.info(
            "document_detection_start",
            mime_type=mime_type,
            filename=original_filename,
        )

        # Normalize MIME (strip parameters like "; charset=utf-8")
        normalized_mime = mime_type.split(";")[0].strip().lower()

        # Try MIME lookup first
        file_type: DocumentType | None = SUPPORTED_MIME_TYPES.get(normalized_mime)

        # Fallback to extension
        if file_type is None:
            suffix = Path(original_filename).suffix.lower()
            file_type = SUPPORTED_EXTENSIONS.get(suffix)

        if file_type is None:
            raise ValueError(
                f"Cannot detect document type for MIME '{normalized_mime}' "
                f"and filename '{original_filename}'"
            )

        parser, needs_ocr = DOCUMENT_TYPE_MAP.get(
            file_type,
            (ParserStrategy.TEXT, False),
        )

        result = DetectionResult(
            file_type=file_type,
            parser=parser,
            needs_ocr=needs_ocr,
            mime_type=normalized_mime,
        )

        logger.info(
            "document_detection_success",
            file_type=file_type.value,
            parser=parser.value,
            needs_ocr=needs_ocr,
        )

        return result

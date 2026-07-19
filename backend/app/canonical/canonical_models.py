"""
Canonical Document Models

The universal intermediate representation produced by every parser and
consumed by every downstream AI module.

Rules:
    - No parser-specific types leak beyond this layer.
    - Epic 3 (AI Extraction), Epic 4 (Ontology), Epic 5 (Graph), and
      Epic 6 (Embeddings) ALL consume CanonicalDocument.
    - Never expose Docling or PaddleOCR objects to services.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


# -----------------------------------------------------------
# Sub-structures
# -----------------------------------------------------------

@dataclass
class CanonicalPage:
    """
    Single page extracted from a document.

    Args:
        page_number: 1-indexed page number
        text: Full plain text of the page
        width: Page width in points/pixels (if known)
        height: Page height in points/pixels (if known)
        ocr_applied: Whether OCR was applied to this page
    """
    page_number: int
    text: str = ""
    width: Optional[float] = None
    height: Optional[float] = None
    ocr_applied: bool = False


@dataclass
class CanonicalSection:
    """
    Logical section (heading + body text).

    Args:
        heading: Section heading text
        level: Heading level (1=H1, 2=H2, etc.)
        text: Section body text
        page_number: Page where section starts
    """
    heading: str
    level: int = 1
    text: str = ""
    page_number: Optional[int] = None


@dataclass
class CanonicalTable:
    """
    Table extracted from a document.

    Args:
        page_number: Page where the table appears
        caption: Table caption or title if available
        headers: Column headers
        rows: List of rows; each row is a list of cell strings
        markdown: Markdown representation for LLM consumption
    """
    page_number: Optional[int]
    caption: str = ""
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    markdown: str = ""


@dataclass
class CanonicalImage:
    """
    Image reference extracted from a document.

    Args:
        page_number: Page where the image appears
        caption: Image caption if available
        ocr_text: Text extracted from the image via OCR (if applicable)
        width: Image width in pixels
        height: Image height in pixels
    """
    page_number: Optional[int] = None
    caption: str = ""
    ocr_text: str = ""
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class DocumentMetadata:
    """
    Document-level metadata extracted from file properties or content.

    Args:
        title: Document title
        author: Author name(s)
        created_at: Document creation date
        modified_at: Last modification date
        page_count: Total number of pages
        word_count: Approximate word count of full text
        language: Detected/declared language (ISO code)
        file_type: Source file type (pdf, docx, etc.)
        file_size: File size in bytes
        image_count: Number of images in the document
        table_count: Number of tables in the document
        parser_version: Docling version string
        ocr_version: PaddleOCR version string (or None if OCR not used)
        pipeline_version: Processing pipeline version
    """
    title: str = ""
    author: str = ""
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    page_count: int = 0
    word_count: int = 0
    language: str = "en"
    file_type: str = ""
    file_size: int = 0
    image_count: int = 0
    table_count: int = 0
    parser_version: str = ""
    ocr_version: Optional[str] = None
    pipeline_version: str = "1.0.0"


# -----------------------------------------------------------
# Root Canonical Document
# -----------------------------------------------------------

@dataclass
class CanonicalDocument:
    """
    The universal document representation produced by the processing pipeline.

    Every parser (Docling for structured docs, OCR for images) produces
    a CanonicalDocument. All downstream modules (AI Extraction, Graph Builder,
    Embedding Generator) consume ONLY this format.

    This enables swapping parsers (e.g. replace Docling with another library)
    without touching any AI or graph code.

    Args:
        document_id: Supabase document ID
        original_filename: Original upload filename
        storage_path: Path in Supabase Storage bucket
        metadata: Extracted document metadata
        pages: Per-page text content
        sections: Hierarchical sections (heading + body)
        tables: Extracted tables
        images: Image references
        full_text: Complete concatenated plain text (for chunking)
        language: Primary language detected
        warnings: Non-fatal issues encountered during parsing
        ocr_applied: True if OCR was used for any page
        processing_time_seconds: Total processing duration
        processed_at: ISO timestamp of processing completion
    """
    # Required
    document_id: str
    original_filename: str
    storage_path: str

    # Extracted content
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    pages: List[CanonicalPage] = field(default_factory=list)
    sections: List[CanonicalSection] = field(default_factory=list)
    tables: List[CanonicalTable] = field(default_factory=list)
    images: List[CanonicalImage] = field(default_factory=list)
    full_text: str = ""

    # Language and warnings
    language: str = "en"
    warnings: List[str] = field(default_factory=list)

    # Processing telemetry
    ocr_applied: bool = False
    processing_time_seconds: float = 0.0
    processed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to a plain dictionary for storage (Supabase Storage as JSON).

        Returns:
            JSON-serializable dictionary
        """
        return {
            "document_id": self.document_id,
            "original_filename": self.original_filename,
            "storage_path": self.storage_path,
            "metadata": {
                "title": self.metadata.title,
                "author": self.metadata.author,
                "created_at": self.metadata.created_at,
                "modified_at": self.metadata.modified_at,
                "page_count": self.metadata.page_count,
                "word_count": self.metadata.word_count,
                "language": self.metadata.language,
                "file_type": self.metadata.file_type,
                "file_size": self.metadata.file_size,
                "image_count": self.metadata.image_count,
                "table_count": self.metadata.table_count,
                "parser_version": self.metadata.parser_version,
                "ocr_version": self.metadata.ocr_version,
                "pipeline_version": self.metadata.pipeline_version,
            },
            "pages": [
                {
                    "page_number": p.page_number,
                    "text": p.text,
                    "ocr_applied": p.ocr_applied,
                }
                for p in self.pages
            ],
            "sections": [
                {
                    "heading": s.heading,
                    "level": s.level,
                    "text": s.text,
                    "page_number": s.page_number,
                }
                for s in self.sections
            ],
            "tables": [
                {
                    "page_number": t.page_number,
                    "caption": t.caption,
                    "headers": t.headers,
                    "rows": t.rows,
                    "markdown": t.markdown,
                }
                for t in self.tables
            ],
            "images": [
                {
                    "page_number": i.page_number,
                    "caption": i.caption,
                    "ocr_text": i.ocr_text,
                }
                for i in self.images
            ],
            "full_text": self.full_text,
            "language": self.language,
            "warnings": self.warnings,
            "ocr_applied": self.ocr_applied,
            "processing_time_seconds": self.processing_time_seconds,
            "processed_at": self.processed_at,
        }

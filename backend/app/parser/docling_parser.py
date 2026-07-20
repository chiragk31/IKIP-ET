"""
Docling Parser

Extracts structured content from PDF, DOCX, and PPTX files using Docling.

Architecture:
    ProcessingService → DoclingParser → CanonicalDocument

Rules:
    - NEVER return Docling-specific objects to the service layer.
    - ALWAYS return CanonicalDocument.
    - Never call Gemini or any AI service here.
    - This module is purely text/structure extraction.

Docling capabilities used:
    - Text extraction (preserving reading order)
    - Table detection and extraction
    - Section/heading detection
    - Page segmentation
    - Document metadata extraction

Note on scanned PDFs:
    Docling automatically applies an internal OCR pipeline for scanned PDFs.
    If Docling's text confidence is low (very little text extracted vs page count),
    ProcessingService will additionally run PaddleOCR on the pages.
"""
import torch  # noqa: F401

import time
from pathlib import Path
from typing import List, Optional
import structlog

from app.canonical.canonical_models import (
    CanonicalDocument,
    CanonicalPage,
    CanonicalSection,
    CanonicalTable,
    CanonicalImage,
    DocumentMetadata,
)

logger = structlog.get_logger(__name__)

# Minimum average characters per page to consider a PDF "text-based" (not scanned)
SCANNED_PDF_THRESHOLD = 100


class DoclingParser:
    """
    Extracts structured content from documents using Docling.

    Supports: PDF, DOCX, PPTX
    Returns: CanonicalDocument (parser-agnostic format)
    """

    def __init__(self) -> None:
        logger.info("docling_parser_initialized")

    def parse(
        self,
        local_path: str,
        document_id: str,
        original_filename: str,
        storage_path: str,
        file_size: int = 0,
        file_type: str = "",
    ) -> CanonicalDocument:
        """
        Parse a document file using Docling.

        Args:
            local_path: Absolute path to the downloaded temp file
            document_id: Supabase document ID
            original_filename: Original filename for metadata
            storage_path: Supabase storage path
            file_size: File size in bytes
            file_type: Detected file type string

        Returns:
            CanonicalDocument with all extracted content

        Raises:
            Exception: If Docling cannot parse the file
        """
        start_time = time.time()
        logger.info(
            "docling_parse_start",
            document_id=document_id,
            filename=original_filename,
            path=local_path,
        )

        try:
            from docling.document_converter import DocumentConverter
            from docling.datamodel.base_models import InputFormat

            # Initialize converter — Docling auto-selects backend based on extension
            converter = DocumentConverter()
            result = converter.convert(local_path)
            doc = result.document

            # --- Extract text per page ---
            pages = self._extract_pages(doc)

            # --- Detect if scanned (low text density) ---
            is_scanned = self._detect_scanned(pages)

            # --- Extract sections ---
            sections = self._extract_sections(doc)

            # --- Extract tables ---
            tables = self._extract_tables(doc)

            # --- Extract images ---
            images = self._extract_images(doc)

            # --- Full text ---
            full_text = self._build_full_text(pages, sections)

            # --- Metadata ---
            metadata = self._extract_metadata(
                doc=doc,
                original_filename=original_filename,
                file_size=file_size,
                file_type=file_type,
                page_count=len(pages),
                image_count=len(images),
                table_count=len(tables),
                full_text=full_text,
            )

            # Warnings
            warnings: List[str] = []
            if is_scanned:
                warnings.append(
                    "Document appears to be scanned (low text density). "
                    "OCR will be applied for better text quality."
                )

            duration = time.time() - start_time
            logger.info(
                "docling_parse_success",
                document_id=document_id,
                pages=len(pages),
                sections=len(sections),
                tables=len(tables),
                images=len(images),
                is_scanned=is_scanned,
                duration_seconds=round(duration, 2),
            )

            canonical = CanonicalDocument(
                document_id=document_id,
                original_filename=original_filename,
                storage_path=storage_path,
                metadata=metadata,
                pages=pages,
                sections=sections,
                tables=tables,
                images=images,
                full_text=full_text,
                language=metadata.language,
                warnings=warnings,
                ocr_applied=False,  # Will be set to True by OCR service if needed
                processing_time_seconds=round(duration, 2),
            )

            # Tag scanned pages so OCR service knows which to process
            if is_scanned:
                for page in canonical.pages:
                    page.ocr_applied = False  # Will flip to True after OCR

            return canonical

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "docling_parse_failed",
                document_id=document_id,
                error=str(e),
                duration_seconds=round(duration, 2),
            )
            raise

    # -----------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------

    def _extract_pages(self, doc) -> List[CanonicalPage]:
        """Extract per-page text from Docling document."""
        pages: List[CanonicalPage] = []
        try:
            # Docling uses pages property
            for page in doc.pages.values():
                page_num = getattr(page, "page_no", 0)
                # Get text for this page from exported markdown split by page
                pages.append(CanonicalPage(
                    page_number=page_num + 1 if isinstance(page_num, int) else 1,
                    text="",  # We'll populate from full text export
                    ocr_applied=False,
                ))
        except AttributeError:
            pass

        # If no pages extracted, create one synthetic page
        if not pages:
            # Export full text and treat as single page
            try:
                full = doc.export_to_markdown()
                pages = [CanonicalPage(page_number=1, text=full)]
            except Exception:
                pages = [CanonicalPage(page_number=1, text="")]

        # Populate page text from Docling text items
        try:
            page_texts: dict = {}
            for item, _ in doc.iterate_items():
                prov = getattr(item, "prov", [])
                for p in (prov or []):
                    pno = getattr(p, "page_no", None)
                    if pno is not None:
                        text_chunk = getattr(item, "text", "")
                        page_texts[pno + 1] = page_texts.get(pno + 1, "") + text_chunk + "\n"

            for page in pages:
                if page.page_number in page_texts:
                    page.text = page_texts[page.page_number].strip()

        except Exception as e:
            logger.warning("docling_page_text_extraction_warning", error=str(e))

        return pages

    def _detect_scanned(self, pages: List[CanonicalPage]) -> bool:
        """
        Heuristic: if average chars per page is below threshold, the doc is likely scanned.
        """
        if not pages:
            return False
        avg_chars = sum(len(p.text) for p in pages) / len(pages)
        return avg_chars < SCANNED_PDF_THRESHOLD

    def _extract_sections(self, doc) -> List[CanonicalSection]:
        """Extract section headings and body text from Docling document."""
        sections: List[CanonicalSection] = []
        try:
            from docling.datamodel.document import SectionHeaderItem, TextItem
            current_section: Optional[CanonicalSection] = None

            for item, _ in doc.iterate_items():
                label = getattr(item, "label", None)
                label_str = str(label) if label is not None else ""

                # Detect headings
                if "section_header" in label_str.lower() or "heading" in label_str.lower():
                    level = 1
                    try:
                        level = int(getattr(item, "level", 1))
                    except (TypeError, ValueError):
                        pass
                    text = getattr(item, "text", "").strip()
                    page_num = None
                    try:
                        provs = getattr(item, "prov", [])
                        if provs:
                            page_num = getattr(provs[0], "page_no", None)
                            if page_num is not None:
                                page_num += 1
                    except Exception:
                        pass

                    current_section = CanonicalSection(
                        heading=text,
                        level=level,
                        text="",
                        page_number=page_num,
                    )
                    sections.append(current_section)

                elif current_section is not None:
                    # Append body text to current section
                    text = getattr(item, "text", "").strip()
                    if text:
                        current_section.text += text + "\n"

        except Exception as e:
            logger.warning("docling_section_extraction_warning", error=str(e))

        return sections

    def _extract_tables(self, doc) -> List[CanonicalTable]:
        """Extract tables from Docling document."""
        tables: List[CanonicalTable] = []
        try:
            for item, _ in doc.iterate_items():
                label = str(getattr(item, "label", ""))
                if "table" not in label.lower():
                    continue

                page_num = None
                try:
                    provs = getattr(item, "prov", [])
                    if provs:
                        page_num = getattr(provs[0], "page_no", None)
                        if page_num is not None:
                            page_num += 1
                except Exception:
                    pass

                # Try to export table as markdown
                markdown = ""
                headers: List[str] = []
                rows: List[List[str]] = []
                try:
                    markdown = item.export_to_markdown() if hasattr(item, "export_to_markdown") else ""
                except Exception:
                    pass

                try:
                    tbl_data = item.data if hasattr(item, "data") else None
                    if tbl_data and hasattr(tbl_data, "grid"):
                        grid = tbl_data.grid
                        if grid:
                            headers = [str(cell.text) for cell in grid[0]]
                            rows = [[str(cell.text) for cell in row] for row in grid[1:]]
                except Exception:
                    pass

                tables.append(CanonicalTable(
                    page_number=page_num,
                    headers=headers,
                    rows=rows,
                    markdown=markdown,
                ))

        except Exception as e:
            logger.warning("docling_table_extraction_warning", error=str(e))

        return tables

    def _extract_images(self, doc) -> List[CanonicalImage]:
        """Extract image references from Docling document."""
        images: List[CanonicalImage] = []
        try:
            for item, _ in doc.iterate_items():
                label = str(getattr(item, "label", ""))
                if "picture" not in label.lower() and "figure" not in label.lower():
                    continue

                page_num = None
                try:
                    provs = getattr(item, "prov", [])
                    if provs:
                        page_num = getattr(provs[0], "page_no", None)
                        if page_num is not None:
                            page_num += 1
                except Exception:
                    pass

                caption = getattr(item, "caption", "") or ""
                images.append(CanonicalImage(page_number=page_num, caption=str(caption)))

        except Exception as e:
            logger.warning("docling_image_extraction_warning", error=str(e))

        return images

    def _build_full_text(
        self,
        pages: List[CanonicalPage],
        sections: List[CanonicalSection],
    ) -> str:
        """
        Build the complete plain text from pages.
        Falls back to concatenating section text if pages are empty.
        """
        page_text = "\n\n".join(p.text for p in pages if p.text).strip()
        if page_text:
            return page_text
        # Fallback: concatenate section headings + bodies
        parts = []
        for s in sections:
            if s.heading:
                parts.append(s.heading)
            if s.text:
                parts.append(s.text)
        return "\n\n".join(parts).strip()

    def _extract_metadata(
        self,
        doc,
        original_filename: str,
        file_size: int,
        file_type: str,
        page_count: int,
        image_count: int,
        table_count: int,
        full_text: str,
    ) -> DocumentMetadata:
        """Extract document-level metadata from Docling doc properties."""
        title = ""
        author = ""
        created_at = None
        modified_at = None
        language = "en"

        try:
            props = getattr(doc, "properties", None) or getattr(doc, "metadata", None)
            if props:
                title = str(getattr(props, "title", "") or "")
                author = str(getattr(props, "author", "") or "")
                created_at = str(getattr(props, "created", "") or "") or None
                modified_at = str(getattr(props, "modified", "") or "") or None

        except Exception as e:
            logger.warning("docling_metadata_extraction_warning", error=str(e))

        if not title:
            title = Path(original_filename).stem.replace("_", " ").replace("-", " ").title()

        word_count = len(full_text.split()) if full_text else 0

        # Try to detect Docling version
        try:
            import docling
            parser_version = getattr(docling, "__version__", "unknown")
        except Exception:
            parser_version = "unknown"

        return DocumentMetadata(
            title=title,
            author=author,
            created_at=created_at,
            modified_at=modified_at,
            page_count=page_count,
            word_count=word_count,
            language=language,
            file_type=file_type,
            file_size=file_size,
            image_count=image_count,
            table_count=table_count,
            parser_version=parser_version,
        )

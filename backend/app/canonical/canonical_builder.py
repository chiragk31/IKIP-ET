"""
Canonical Builder

Normalizes and merges parser output and OCR output into the final
CanonicalDocument.

Architecture:
    ProcessingService → CanonicalBuilder.merge_ocr() → CanonicalDocument

Responsibilities:
    - Merge OCR page text into pages that had low text density
    - Normalize whitespace and encoding across all text fields
    - Remove duplicate OCR blocks
    - Rebuild full_text from merged pages
    - Set final language, metadata counts, and OCR flags

Rules:
    - The builder NEVER calls parsers or OCR directly.
    - It only merges data structures already produced by parsers and OCR.
    - Output must be a complete, self-consistent CanonicalDocument.
"""

import re
import unicodedata
from typing import List
import structlog

from app.canonical.canonical_models import CanonicalDocument, CanonicalPage
from app.ocr.ocr_service import OCRPageResult

logger = structlog.get_logger(__name__)


class CanonicalBuilder:
    """
    Merges parser output with OCR results and normalizes the final document.
    """

    def merge_ocr(
        self,
        canonical: CanonicalDocument,
        ocr_results: List[OCRPageResult],
    ) -> CanonicalDocument:
        """
        Merge OCR text into the CanonicalDocument's pages.

        Strategy:
            - For each OCR result page, if the existing page text is
              shorter than the OCR text, replace it (OCR won).
            - If OCR found nothing, keep the original parser text.
            - Rebuild full_text after merging.

        Args:
            canonical: CanonicalDocument from the parser (may have sparse text)
            ocr_results: List of OCRPageResult from OCRService

        Returns:
            Updated CanonicalDocument with merged text and updated flags
        """
        if not ocr_results:
            return canonical

        # Build a page lookup for fast access
        page_map = {p.page_number: p for p in canonical.pages}

        # Merge page-by-page
        for ocr_result in ocr_results:
            ocr_text = self._normalize_text(ocr_result.text)
            page_num = ocr_result.page_number

            if page_num in page_map:
                existing_page = page_map[page_num]
                existing_text = self._normalize_text(existing_page.text)

                # Use OCR text if it's longer (any improvement wins)
                if len(ocr_text) > len(existing_text):
                    existing_page.text = ocr_text
                    existing_page.ocr_applied = True
                    logger.debug(
                        "canonical_ocr_merge_override",
                        page=page_num,
                        ocr_chars=len(ocr_text),
                        parser_chars=len(existing_text),
                    )
                else:
                    existing_page.ocr_applied = (ocr_result.engine != "none")
            else:
                # OCR found a page the parser didn't — add it
                canonical.pages.append(CanonicalPage(
                    page_number=page_num,
                    text=ocr_text,
                    ocr_applied=True,
                ))
                page_map[page_num] = canonical.pages[-1]

        # Sort pages by page number
        canonical.pages.sort(key=lambda p: p.page_number)

        # Mark canonical as OCR-processed
        canonical.ocr_applied = any(p.ocr_applied for p in canonical.pages)

        # Set OCR version in metadata
        if ocr_results and ocr_results[0].engine not in ("none", ""):
            canonical.metadata.ocr_version = ocr_results[0].engine

        # Rebuild full text
        canonical.full_text = self._rebuild_full_text(canonical)

        # Normalize all text fields
        canonical = self._normalize_document(canonical)

        # Update derived counts
        canonical.metadata.page_count = len(canonical.pages)
        canonical.metadata.word_count = len(canonical.full_text.split())
        canonical.metadata.table_count = len(canonical.tables)
        canonical.metadata.image_count = len(canonical.images)

        logger.info(
            "canonical_builder_merge_complete",
            document_id=canonical.document_id,
            pages=len(canonical.pages),
            ocr_applied=canonical.ocr_applied,
            full_text_chars=len(canonical.full_text),
            word_count=canonical.metadata.word_count,
        )

        return canonical

    def finalize(self, canonical: CanonicalDocument) -> CanonicalDocument:
        """
        Finalize a CanonicalDocument that did NOT need OCR (text-based docs).

        Applies normalization and updates derived counts.

        Args:
            canonical: CanonicalDocument from parser

        Returns:
            Finalized CanonicalDocument
        """
        canonical = self._normalize_document(canonical)
        canonical.metadata.page_count = len(canonical.pages)
        canonical.metadata.word_count = len(canonical.full_text.split()) if canonical.full_text else 0
        canonical.metadata.table_count = len(canonical.tables)
        canonical.metadata.image_count = len(canonical.images)

        logger.info(
            "canonical_builder_finalize_complete",
            document_id=canonical.document_id,
            pages=canonical.metadata.page_count,
            words=canonical.metadata.word_count,
        )
        return canonical

    # -----------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text: unicode NFC, collapse whitespace, strip.
        """
        if not text:
            return ""
        # Unicode normalization (NFC)
        text = unicodedata.normalize("NFC", text)
        # Replace multiple spaces/tabs with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Collapse more than 2 consecutive newlines into 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _normalize_document(self, canonical: CanonicalDocument) -> CanonicalDocument:
        """Apply normalization to all text fields in the document."""
        canonical.full_text = self._normalize_text(canonical.full_text)

        for page in canonical.pages:
            page.text = self._normalize_text(page.text)

        for section in canonical.sections:
            section.heading = self._normalize_text(section.heading)
            section.text = self._normalize_text(section.text)

        for table in canonical.tables:
            table.caption = self._normalize_text(table.caption)
            table.headers = [self._normalize_text(h) for h in table.headers]
            table.rows = [
                [self._normalize_text(cell) for cell in row]
                for row in table.rows
            ]
            table.markdown = self._normalize_text(table.markdown)

        return canonical

    def _rebuild_full_text(self, canonical: CanonicalDocument) -> str:
        """Rebuild full_text by concatenating all pages in order."""
        parts = [p.text for p in canonical.pages if p.text]
        return "\n\n".join(parts).strip()

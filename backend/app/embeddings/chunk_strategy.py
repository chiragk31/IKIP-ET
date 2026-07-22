"""
Chunk Strategy

Implements the semantic chunking algorithm for CanonicalDocument objects.

Design (per Embeddings.md §Chunking Strategy):
 - NEVER split by character count alone.
 - Preferred hierarchy: Document → Section → Paragraph → Chunk
 - Tables are ALWAYS kept as a single chunk (never split across chunks).
 - Sections whose heading matches NEVER_SPLIT_HEADING_KEYWORDS are kept
   whole if they fit within CHUNK_MAX_TOKENS; if they exceed it, they
   are split at paragraph boundaries (blank lines), not mid-sentence.
 - Overlap is achieved by repeating CHUNK_OVERLAP_TOKENS worth of text
   from the end of the previous chunk at the start of the next.

Token counting:
 - Uses a 4-char/token approximation (tiktoken not in project deps).
 - All thresholds have sufficient margin that approximation error
   (typically ±10%) does not cause retrieval-quality problems.

This module does NOT call any external service — pure Python logic.
"""

from typing import List, Optional, Tuple
import structlog

from app.canonical.canonical_models import CanonicalDocument, CanonicalSection, CanonicalTable
from app.embeddings.constants import (
    CHUNK_MAX_TOKENS,
    CHUNK_MIN_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_TARGET_TOKENS,
    NEVER_SPLIT_HEADING_KEYWORDS,
    estimate_tokens,
)

logger = structlog.get_logger(__name__)


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------

def _is_never_split_section(heading: str) -> bool:
    """
    Return True if this section heading indicates content that must
    not be split mid-way (procedures, safety instructions, etc.).

    Args:
        heading: Section heading text.

    Returns:
        True if the section should be kept whole or split only at paragraphs.
    """
    lower = heading.lower()
    return any(keyword in lower for keyword in NEVER_SPLIT_HEADING_KEYWORDS)


def _split_into_paragraphs(text: str) -> List[str]:
    """
    Split text at blank lines to get paragraph-level fragments.

    Args:
        text: Multi-paragraph text to split.

    Returns:
        List of non-empty paragraph strings.
    """
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _apply_overlap(prev_text: str, overlap_tokens: int) -> str:
    """
    Extract the trailing overlap_tokens worth of text from prev_text
    to prepend to the next chunk.

    Args:
        prev_text: The text of the previous chunk.
        overlap_tokens: Approximate number of tokens to retain.

    Returns:
        Overlap prefix string (may be empty if prev_text is too short).
    """
    if not prev_text:
        return ""
    overlap_chars = overlap_tokens * 4  # ~4 chars/token
    if len(prev_text) <= overlap_chars:
        return prev_text
    # Find a sentence boundary near the start of the overlap window
    start = max(0, len(prev_text) - overlap_chars)
    # Try to snap to a period/newline boundary
    snap = prev_text.rfind(".", 0, start + overlap_chars // 2)
    if snap != -1 and snap > start:
        return prev_text[snap + 1:].strip()
    return prev_text[start:].strip()


# -------------------------------------------------------------------
# Public interface
# -------------------------------------------------------------------

class ChunkStrategy:
    """
    Converts a CanonicalDocument into a list of (text, section, page_number, chunk_type)
    tuples for the ChunkGenerator to wrap into Chunk objects.

    Purpose:
        Semantic chunking respecting section structure and never-split rules.
    Input:
        CanonicalDocument from Epic 2.
    Output:
        List of raw chunk tuples (text, section_heading, page_number, chunk_type).
    """

    def chunk(
        self,
        doc: CanonicalDocument,
    ) -> List[Tuple[str, str, Optional[int], str]]:
        """
        Produce a list of raw chunk tuples from a CanonicalDocument.

        Strategy (in priority order):
         1. Tables → one chunk per table (type="table"), never split.
         2. Sections → walk sections; apply never-split and token-size rules.
         3. Bare pages (if no sections) → fallback to page-level chunking.
         4. Full text fallback (if no pages and no sections).

        Args:
            doc: CanonicalDocument to chunk.

        Returns:
            List of (text, section_heading, page_number, chunk_type) tuples.
        """
        raw_chunks: List[Tuple[str, str, Optional[int], str]] = []

        # Step 1: Tables (each table = 1 chunk, never split)
        for table in doc.tables:
            if table.markdown.strip():
                table_text = table.markdown.strip()
                caption = table.caption or "Table"
                raw_chunks.append((
                    table_text,
                    caption,
                    table.page_number,
                    "table",
                ))

        # Step 2: Sections
        if doc.sections:
            raw_chunks.extend(self._chunk_sections(doc.sections))
        elif doc.pages:
            # Fallback: page-level chunks
            raw_chunks.extend(self._chunk_pages(doc))
        else:
            # Last resort: chunk full_text
            raw_chunks.extend(self._chunk_full_text(doc.full_text))

        # Filter out any chunks that are too small (but keep all tables)
        filtered = [
            c for c in raw_chunks
            if c[3] == "table" or estimate_tokens(c[0]) >= CHUNK_MIN_TOKENS
        ]

        logger.info(
            "chunk_strategy_complete",
            total_raw=len(raw_chunks),
            after_min_filter=len(filtered),
            tables=len(doc.tables),
            sections=len(doc.sections),
        )
        return filtered

    def _chunk_sections(
        self,
        sections: List[CanonicalSection],
    ) -> List[Tuple[str, str, Optional[int], str]]:
        """
        Process a list of CanonicalSections into chunk tuples.

        Sections within CHUNK_MAX_TOKENS: kept whole.
        Large non-critical sections: split by paragraph then by token window.
        Never-split sections above max: split by paragraph only (not mid-sentence).

        Args:
            sections: List of CanonicalSection objects.

        Returns:
            List of raw chunk tuples.
        """
        results: List[Tuple[str, str, Optional[int], str]] = []
        prev_text = ""

        for section in sections:
            text = section.text.strip()
            if not text:
                continue

            heading = section.heading or ""
            page = section.page_number
            chunk_type = "procedure" if _is_never_split_section(heading) else "text"

            # Determine chunk type for this content
            tok = estimate_tokens(text)

            if tok <= CHUNK_MAX_TOKENS:
                # Fits in one chunk — add overlap prefix
                overlap = _apply_overlap(prev_text, CHUNK_OVERLAP_TOKENS)
                chunk_text = (overlap + " " + text).strip() if overlap else text
                results.append((chunk_text, heading, page, chunk_type))
                prev_text = text
            elif chunk_type == "procedure":
                # Never-split: break only at paragraph boundaries
                parts = _split_into_paragraphs(text)
                for part in parts:
                    overlap = _apply_overlap(prev_text, CHUNK_OVERLAP_TOKENS)
                    chunk_text = (overlap + " " + part).strip() if overlap else part
                    results.append((chunk_text, heading, page, chunk_type))
                    prev_text = part
            else:
                # Regular large section: sliding window by token count
                window_chunks = self._sliding_window(text, heading, page, "text")
                for i, wc in enumerate(window_chunks):
                    if i == 0:
                        overlap = _apply_overlap(prev_text, CHUNK_OVERLAP_TOKENS)
                        chunk_text = (overlap + " " + wc[0]).strip() if overlap else wc[0]
                        results.append((chunk_text, wc[1], wc[2], wc[3]))
                    else:
                        results.append(wc)
                if window_chunks:
                    prev_text = window_chunks[-1][0]

        return results

    def _sliding_window(
        self,
        text: str,
        heading: str,
        page: Optional[int],
        chunk_type: str,
    ) -> List[Tuple[str, str, Optional[int], str]]:
        """
        Split a large text block using a token-count sliding window.

        Uses CHUNK_TARGET_TOKENS as the target size with CHUNK_OVERLAP_TOKENS
        overlap between adjacent chunks.

        Args:
            text: Text to split.
            heading: Section heading for attribution.
            page: Page number for citation.
            chunk_type: Chunk type label.

        Returns:
            List of (text, heading, page, chunk_type) tuples.
        """
        results = []
        words = text.split()
        words_per_chunk = CHUNK_TARGET_TOKENS * 4 // 5  # ~words at ~5 chars/word
        overlap_words = CHUNK_OVERLAP_TOKENS * 4 // 5

        start = 0
        while start < len(words):
            end = min(start + words_per_chunk, len(words))
            chunk_text = " ".join(words[start:end])
            results.append((chunk_text, heading, page, chunk_type))
            if end >= len(words):
                break
            start = end - overlap_words

        return results

    def _chunk_pages(
        self,
        doc: CanonicalDocument,
    ) -> List[Tuple[str, str, Optional[int], str]]:
        """
        Fallback: chunk at the page level when no sections are present.

        Args:
            doc: CanonicalDocument with pages.

        Returns:
            List of raw chunk tuples.
        """
        results = []
        prev_text = ""
        for page in doc.pages:
            text = page.text.strip()
            if not text:
                continue
            heading = f"Page {page.page_number}"
            overlap = _apply_overlap(prev_text, CHUNK_OVERLAP_TOKENS)
            chunk_text = (overlap + " " + text).strip() if overlap else text
            results.append((chunk_text, heading, page.page_number, "text"))
            prev_text = text
        return results

    def _chunk_full_text(
        self,
        full_text: str,
    ) -> List[Tuple[str, str, Optional[int], str]]:
        """
        Last-resort fallback: chunk the full_text string using a sliding window.

        Args:
            full_text: Complete document text.

        Returns:
            List of raw chunk tuples.
        """
        if not full_text.strip():
            return []
        return self._sliding_window(full_text, "Document", None, "text")

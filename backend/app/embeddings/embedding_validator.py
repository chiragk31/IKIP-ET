"""
Embedding Validator

Validates EmbeddedChunks before they are upserted into Pinecone.

Checks (all must pass):
 1. Vector dimension matches the configured EMBEDDING_DIMENSION (768).
 2. No NaN or None values anywhere in the vector.
 3. No infinite values in the vector.
 4. Required metadata fields are present (chunk_id, document_id).
 5. chunk_id and document_id are non-empty strings.

Design:
 - Invalid chunks are collected and returned (never silently dropped).
 - Callers can log invalid chunks before proceeding with valid ones.
 - Pure Python — no external service calls.
"""

import math
from typing import List, Tuple
import structlog

from app.embeddings.models import EmbeddedChunk
from app.embeddings.constants import EMBEDDING_DIMENSION

logger = structlog.get_logger(__name__)


class ValidationResult:
    """
    Container for validation output.

    Attributes:
        valid_chunks: EmbeddedChunks that passed all checks.
        invalid_chunks: List of (EmbeddedChunk, reason) for failures.
        is_valid: True if ALL chunks passed (no invalid entries).
    """

    def __init__(self) -> None:
        self.valid_chunks: List[EmbeddedChunk] = []
        self.invalid_chunks: List[Tuple[EmbeddedChunk, str]] = []

    @property
    def is_valid(self) -> bool:
        """Return True only if every chunk is valid."""
        return len(self.invalid_chunks) == 0


class EmbeddingValidator:
    """
    Pre-upsert validator for EmbeddedChunks.

    Purpose:
        Catch dimension mismatches, NaN/null vectors, and missing metadata
        before they corrupt the Pinecone index.
    Input:
        List of EmbeddedChunk objects.
    Output:
        ValidationResult with valid/invalid splits.
    """

    def validate(
        self,
        embedded_chunks: List[EmbeddedChunk],
        expected_dimension: int = EMBEDDING_DIMENSION,
    ) -> ValidationResult:
        """
        Validate a list of EmbeddedChunks.

        Args:
            embedded_chunks: Chunks with vectors to validate.
            expected_dimension: Expected vector length (default: 768 for text-embedding-004).

        Returns:
            ValidationResult with valid and invalid splits.
        """
        result = ValidationResult()

        for ec in embedded_chunks:
            reason = self._check(ec, expected_dimension)
            if reason:
                result.invalid_chunks.append((ec, reason))
                logger.warning(
                    "embedding_validation_rejected",
                    chunk_id=ec.chunk.chunk_id,
                    document_id=ec.chunk.document_id,
                    reason=reason,
                )
            else:
                result.valid_chunks.append(ec)

        logger.info(
            "embedding_validation_complete",
            total=len(embedded_chunks),
            valid=len(result.valid_chunks),
            invalid=len(result.invalid_chunks),
        )
        return result

    def _check(
        self,
        ec: EmbeddedChunk,
        expected_dimension: int,
    ) -> str:
        """
        Run all checks on a single EmbeddedChunk.

        Args:
            ec: EmbeddedChunk to check.
            expected_dimension: Expected vector length.

        Returns:
            Reason string if invalid, empty string if valid.
        """
        # 1. Required metadata
        if not ec.chunk.chunk_id or not ec.chunk.chunk_id.strip():
            return "missing chunk_id"
        if not ec.chunk.document_id or not ec.chunk.document_id.strip():
            return "missing document_id"

        # 2. Vector must exist and be a list
        if not ec.vector or not isinstance(ec.vector, list):
            return "vector is empty or not a list"

        # 3. Dimension check
        if len(ec.vector) != expected_dimension:
            return (
                f"wrong dimension: expected {expected_dimension}, "
                f"got {len(ec.vector)}"
            )

        # 4. NaN / None / Inf check
        for val in ec.vector:
            if val is None:
                return "vector contains None values"
            if math.isnan(val):
                return "vector contains NaN values"
            if math.isinf(val):
                return "vector contains infinite values"

        return ""

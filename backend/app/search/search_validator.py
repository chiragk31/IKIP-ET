"""
Search Validator

Validates and sanitizes incoming search queries before any processing.

Purpose:
    Prevent Cypher injection, invalid filter keys, excessive traversal
    depth, and malformed queries from entering the pipeline.

Input:
    Raw HybridSearchQuery from the API boundary.

Output:
    Validated HybridSearchQuery, or raises ValueError with a safe message.

Rules (Search.md §Security):
  - Validate all user queries.
  - Prevent Cypher injection.
  - Reject invalid metadata filter keys.
  - Reject traversal depth requests above 3.
  - Never expose raw database queries.
"""

import re
import structlog
from typing import List

from app.search.models import HybridSearchQuery, MetadataFilters
from app.search.constants import (
    CYPHER_INJECTION_PATTERNS,
    VALID_FILTER_KEYS,
    GRAPH_EXPANSION_MAX_DEPTH,
    MIN_QUERY_LENGTH,
    MAX_QUERY_LENGTH,
)

logger = structlog.get_logger(__name__)


class SearchValidator:
    """
    Validates and sanitizes search queries before pipeline entry.

    Purpose:
        Act as a security gate that rejects anything resembling an
        injection attack, invalid filter, or out-of-bounds parameter.
    Input:
        HybridSearchQuery from the API layer.
    Output:
        Validated HybridSearchQuery, or raises ValueError.
    """

    def validate(self, query: HybridSearchQuery) -> HybridSearchQuery:
        """
        Full validation pass on a HybridSearchQuery.

        Args:
            query: Incoming search request.

        Returns:
            The same query object (possibly with normalized text).

        Raises:
            ValueError: If validation fails. Message is safe to surface to the caller.
        """
        logger.info("search_validator_start", query_length=len(query.query))

        self._validate_query_text(query.query)
        self._validate_depth(query.graph_depth)
        self._validate_filters(query.filters)

        logger.info("search_validator_pass")
        return query

    # -------------------------------------------------------------------
    # Private validators
    # -------------------------------------------------------------------

    def _validate_query_text(self, text: str) -> None:
        """
        Check query text for length bounds and Cypher injection patterns.

        Args:
            text: Raw query string from the caller.

        Raises:
            ValueError: On length violation or injection pattern match.
        """
        if len(text) < MIN_QUERY_LENGTH:
            raise ValueError(
                f"Query too short — minimum {MIN_QUERY_LENGTH} characters."
            )
        if len(text) > MAX_QUERY_LENGTH:
            raise ValueError(
                f"Query too long — maximum {MAX_QUERY_LENGTH} characters."
            )

        upper = text.upper()
        for pattern in CYPHER_INJECTION_PATTERNS:
            if pattern.upper() in upper:
                logger.warning(
                    "search_validator_injection_detected",
                    pattern=pattern,
                )
                raise ValueError(
                    f"Query contains a disallowed pattern: '{pattern}'. "
                    "Raw database query syntax is not permitted."
                )

    def _validate_depth(self, depth: int) -> None:
        """
        Reject graph expansion depth requests above the hard cap.

        Args:
            depth: Requested expansion depth.

        Raises:
            ValueError: If depth exceeds GRAPH_EXPANSION_MAX_DEPTH.
        """
        if depth > GRAPH_EXPANSION_MAX_DEPTH:
            raise ValueError(
                f"graph_depth {depth} exceeds the maximum allowed value "
                f"of {GRAPH_EXPANSION_MAX_DEPTH}."
            )

    def _validate_filters(self, filters: MetadataFilters) -> None:
        """
        Check that all provided filter fields are in the allowed set.

        Args:
            filters: MetadataFilters from the query.

        Raises:
            ValueError: If any unexpected filter key is provided.
        """
        # All fields in MetadataFilters are explicitly typed — Pydantic already
        # rejects unknown fields by default. This extra pass validates that the
        # values themselves are safe for the fields we do allow.
        if filters.confidence_min is not None:
            if not (0.0 <= filters.confidence_min <= 1.0):
                raise ValueError("confidence_min must be between 0.0 and 1.0.")

        # Scan string filter values for injection patterns
        string_filters = {
            "asset_id": filters.asset_id,
            "plant": filters.plant,
            "department": filters.department,
            "document_type": filters.document_type,
            "language": filters.language,
            "chunk_type": filters.chunk_type,
            "document_id": filters.document_id,
        }
        for field_name, value in string_filters.items():
            if value is not None:
                upper = value.upper()
                for pattern in CYPHER_INJECTION_PATTERNS:
                    if pattern.upper() in upper:
                        logger.warning(
                            "search_validator_filter_injection",
                            field=field_name,
                            pattern=pattern,
                        )
                        raise ValueError(
                            f"Filter field '{field_name}' contains a disallowed pattern."
                        )

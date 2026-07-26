"""
Asset Validator

Validates asset IDs and query parameters before any downstream call.

Per Assets.md §Security:
    "Validate Asset IDs, Query Parameters, User Permissions.
     Never expose internal graph identifiers."

Per Memory.md §Critical Rules:
    "Never trust raw user input into any downstream query."

This module is called at the API boundary — before AssetService, before
AssetRepository, and before any graph or search call is made.
"""

import re
import structlog

from app.assets.constants import (
    ASSET_ID_MAX_LENGTH,
    ASSET_ID_PATTERN,
    ASSET_ENTITY_ID_PREFIX,
)

logger = structlog.get_logger(__name__)

# Compiled pattern for fast repeated validation
_ENTITY_ID_RE = re.compile(ASSET_ID_PATTERN)


class AssetValidator:
    """
    Validates asset identifiers and search query parameters.

    Purpose:
        Act as the security boundary for all asset module inputs.
        Reject malformed or potentially dangerous inputs before they
        reach GraphRepository or HybridSearchService.
    Input:
        Raw user-supplied strings from API routes.
    Output:
        Normalised, validated strings ready for downstream use;
        raises ValueError with a user-safe message on failure.
    """

    def validate_asset_id(self, raw_id: str) -> str:
        """
        Validate and normalise an asset entity_id.

        Normalisation: strips whitespace, lowercases.
        Validation: must match ASSET_ID_PATTERN, must be within length limit.

        The method does NOT require the 'asset_' prefix — callers may pass
        either 'asset_p101' or 'p101' (in which case the prefix is added
        automatically).  This supports the identity priority chain:
            Asset Tag → Equipment ID → UUID
        as described in Assets.md §Asset Identity.

        Args:
            raw_id: Raw asset_id string from the API route.

        Returns:
            Validated, normalised entity_id string.

        Raises:
            ValueError: If the id is empty, too long, or contains
                        invalid characters.
        """
        if not raw_id or not raw_id.strip():
            raise ValueError("Asset ID must not be empty")

        normalised = raw_id.strip().lower()

        if len(normalised) > ASSET_ID_MAX_LENGTH:
            raise ValueError(
                f"Asset ID exceeds maximum length ({ASSET_ID_MAX_LENGTH})"
            )

        # Auto-prefix if missing — makes the API friendly to callers that
        # supply "p101" instead of "asset_p101"
        if not normalised.startswith(ASSET_ENTITY_ID_PREFIX):
            normalised = f"{ASSET_ENTITY_ID_PREFIX}{normalised}"

        if not _ENTITY_ID_RE.match(normalised):
            raise ValueError(
                "Asset ID contains invalid characters. "
                "Only lowercase letters, digits, underscores, and hyphens are allowed."
            )

        logger.debug("asset_id_validated", original=raw_id, normalised=normalised)
        return normalised

    def validate_search_params(
        self,
        q: str | None,
        asset_tag: str | None,
        equipment_id: str | None,
        location: str | None,
        department: str | None,
        asset_type: str | None,
        page: int,
        limit: int,
    ) -> dict:
        """
        Validate and sanitise search query parameters.

        Args:
            q: Free-text search query (optional).
            asset_tag: Asset tag filter (optional).
            equipment_id: Equipment ID filter (optional).
            location: Location filter (optional).
            department: Department filter (optional).
            asset_type: Asset type filter (optional).
            page: Page number (must be ≥ 1).
            limit: Items per page (must be 1–100).

        Returns:
            Dict of validated, sanitised parameters.

        Raises:
            ValueError: On invalid pagination or excessively long strings.
        """
        MAX_FILTER_LENGTH = 256

        validated: dict = {}

        # Sanitise text filters — strip whitespace, enforce length
        text_fields = {
            "q": q,
            "asset_tag": asset_tag,
            "equipment_id": equipment_id,
            "location": location,
            "department": department,
            "asset_type": asset_type,
        }
        for field_name, value in text_fields.items():
            if value is not None:
                sanitised = value.strip()
                if len(sanitised) > MAX_FILTER_LENGTH:
                    raise ValueError(
                        f"Filter '{field_name}' exceeds maximum length ({MAX_FILTER_LENGTH})"
                    )
                validated[field_name] = sanitised if sanitised else None
            else:
                validated[field_name] = None

        # Pagination
        if page < 1:
            raise ValueError("Page number must be at least 1")
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")

        validated["page"] = page
        validated["limit"] = limit

        logger.debug("asset_search_params_validated", params=validated)
        return validated

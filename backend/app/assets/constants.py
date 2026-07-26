"""
Asset Intelligence Constants

Shared constants and enums for the Asset Intelligence module.

These constants drive classification logic in the builders and
ensure the module never depends on hardcoded strings scattered
across files.
"""

from typing import FrozenSet

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

# Time-to-live for in-memory Asset 360 cache entries (seconds)
ASSET_CACHE_TTL_SECONDS: int = 300

# Maximum number of cached asset profiles (LRU eviction when exceeded)
ASSET_CACHE_MAX_SIZE: int = 200

# ---------------------------------------------------------------------------
# Asset Identity
# ---------------------------------------------------------------------------

# The Neo4j node label for asset nodes
ASSET_NODE_LABEL: str = "Asset"

# entity_id prefix scheme (matches Epic 4 AliasResolver convention)
ASSET_ENTITY_ID_PREFIX: str = "asset_"

# Maximum length of a validated asset_id
ASSET_ID_MAX_LENGTH: int = 128

# Characters allowed in asset_ids (lowercase, digits, underscores, hyphens)
ASSET_ID_PATTERN: str = r"^[a-z0-9_\-]+$"

# ---------------------------------------------------------------------------
# Search Integration
# ---------------------------------------------------------------------------

# Query sent to HybridSearchService when fetching related documents for an asset
# The actual asset name/tag is substituted at call time
ASSET_DOCUMENT_SEARCH_TOP_K: int = 10
ASSET_DOCUMENT_SEARCH_MIN_SCORE: float = 0.25

# Graph depth for document search expansion (kept shallow to stay fast)
ASSET_DOCUMENT_SEARCH_DEPTH: int = 1

# ---------------------------------------------------------------------------
# Timeline Classification
# ---------------------------------------------------------------------------

# Neo4j node labels that represent timeline events
TIMELINE_EVENT_LABELS: FrozenSet[str] = frozenset(
    {
        "Event",
        "Failure",
        "Measurement",
        "Procedure",
        "Risk",
        "Regulation",
    }
)

# Relationship types that indicate a maintenance event
# MAINTENANCE_RELATIONSHIP_TYPES: FrozenSet[str] = frozenset(
#     {
#         "PERFORMED",
#         "HAS_MEASUREMENT",
#         "RECORDED_FOR",
#     }
# )
MAINTENANCE_RELATIONSHIP_TYPES: FrozenSet[str] = frozenset(
    {
        "PERFORMED",
    }
)

# Relationship types that indicate a failure/incident event
FAILURE_RELATIONSHIP_TYPES: FrozenSet[str] = frozenset(
    {
        "HAS_FAILURE",
        "CAUSED_BY",
    }
)

# Relationship types that indicate an inspection event
INSPECTION_RELATIONSHIP_TYPES: FrozenSet[str] = frozenset(
    {
        "INVOLVES",
        "PERFORMED",
    }
)

# Relationship types that indicate a compliance event
COMPLIANCE_RELATIONSHIP_TYPES: FrozenSet[str] = frozenset(
    {
        "REQUIRES",
        "MITIGATED_BY",
    }
)

# ---------------------------------------------------------------------------
# Relationship Classification (for Asset Relationships builder)
# ---------------------------------------------------------------------------

# Maps Neo4j relationship types → Asset 360 relationship categories
# Only relationship types defined here are surfaced in the response;
# others are included under "related".
RELATIONSHIP_TYPE_MAP: dict = {
    "PART_OF": "part_of",
    "CONNECTED_TO": "connected_to",
    "USES": "uses",
    "RELATED_TO": "related_to",
    "HAS_FAILURE": "has_failure",
    "CAUSED_BY": "caused_by",
    "REQUIRES": "requires",
    "MITIGATED_BY": "mitigated_by",
    "INVOLVES": "involves",
    "PERFORMED": "performed",
    "LOCATED_IN": "located_in",
    "OWNS": "owns",
    "GENERATED_FROM": "generated_from",
    "REFERENCES": "references",
    "MENTIONS": "mentions",
    "HAS_MEASUREMENT": "has_measurement",
    "RECORDED_FOR": "recorded_for",
}

# Relationships that represent "connected asset" (peer assets)
CONNECTED_ASSET_RELATIONSHIP_TYPES: FrozenSet[str] = frozenset(
    {
        "CONNECTED_TO",
        "PART_OF",
        "USES",
    }
)

# ---------------------------------------------------------------------------
# Health Summary
# ---------------------------------------------------------------------------

# Thresholds for descriptive maintenance frequency labels
MAINTENANCE_FREQ_HIGH_THRESHOLD: int = 5   # > 5 events → "high"
MAINTENANCE_FREQ_MED_THRESHOLD: int = 2    # 2-5 events  → "moderate"
# < 2 events → "low"

# Thresholds for failure severity labels
FAILURE_COUNT_HIGH_THRESHOLD: int = 3      # > 3 failures → "high"
FAILURE_COUNT_MED_THRESHOLD: int = 1       # 1-3 failures → "moderate"
# 0 failures → "none"

# Labels
MAINTENANCE_FREQ_HIGH: str = "high"
MAINTENANCE_FREQ_MED: str = "moderate"
MAINTENANCE_FREQ_LOW: str = "low"

FAILURE_SEVERITY_HIGH: str = "high"
FAILURE_SEVERITY_MED: str = "moderate"
FAILURE_SEVERITY_NONE: str = "none"

# ---------------------------------------------------------------------------
# Neighbour Discovery
# ---------------------------------------------------------------------------

# Maximum neighbours fetched per asset (limits graph query result size)
NEIGHBOR_FETCH_LIMIT: int = 100

# ---------------------------------------------------------------------------
# Search Query Template
# ---------------------------------------------------------------------------

# Template for the HybridSearchService query when fetching related documents.
# {name} is substituted with the asset's canonical name.
ASSET_SEARCH_QUERY_TEMPLATE: str = "maintenance inspection procedures for {name}"

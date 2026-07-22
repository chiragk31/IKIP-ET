"""
Search Constants

Centralizes all tunable parameters and sentinel values for the
Epic 7 search pipeline.
"""

from typing import FrozenSet

# -------------------------------------------------------------------
# Graph expansion depth limits (Search.md §Graph Expansion)
# -------------------------------------------------------------------

GRAPH_EXPANSION_DEFAULT_DEPTH: int = 2   # recommended
GRAPH_EXPANSION_MAX_DEPTH: int = 3       # hard cap — reject requests above this
GRAPH_NEIGHBORS_LIMIT: int = 50          # per-hop neighbor query limit

# -------------------------------------------------------------------
# Ranking weights (Search.md §Reranking)
# -------------------------------------------------------------------

WEIGHT_SEMANTIC: float = 0.60     # cosine similarity from Pinecone
WEIGHT_GRAPH: float = 0.20        # graph proximity bonus
WEIGHT_METADATA: float = 0.10     # metadata match bonus
WEIGHT_FRESHNESS: float = 0.10    # recency bonus

# -------------------------------------------------------------------
# Valid metadata filter keys (Search.md §Metadata Filtering)
# -------------------------------------------------------------------

VALID_FILTER_KEYS: FrozenSet[str] = frozenset(
    {
        "asset_id",
        "plant",
        "department",
        "date_from",
        "date_to",
        "document_type",
        "confidence_min",
        "language",
        "chunk_type",
        "document_id",
    }
)

# -------------------------------------------------------------------
# Cypher injection detection patterns
# -------------------------------------------------------------------

CYPHER_INJECTION_PATTERNS: tuple = (
    "MATCH",
    "MERGE",
    "CREATE",
    "DELETE",
    "DETACH",
    "RETURN",
    "UNION",
    "CALL",
    "WITH ",
    "WHERE ",
    "//",
    "/*",
    "*/",
    "--",
    ";",
)

# -------------------------------------------------------------------
# Query processing
# -------------------------------------------------------------------

MIN_QUERY_LENGTH: int = 2          # characters
MAX_QUERY_LENGTH: int = 1000       # characters
MAX_ENTITIES_PER_QUERY: int = 10

# -------------------------------------------------------------------
# Context package
# -------------------------------------------------------------------

MAX_CONTEXT_CHUNKS: int = 10
MAX_CONTEXT_GRAPH_NODES: int = 20

# -------------------------------------------------------------------
# Default search parameters
# -------------------------------------------------------------------

DEFAULT_TOP_K: int = 10
DEFAULT_MIN_SCORE: float = 0.3     # lower than Epic 6 default (0.0) — filter noise

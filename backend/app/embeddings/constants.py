"""
Embeddings Module Constants

Defines chunk sizes, batch sizes, dimensions, and pipeline version
for the Semantic Embeddings module (Epic 6).

Source of truth for tuning parameters — never hardcode these elsewhere.

Token estimation:
    text-embedding-004 accepts up to 2048 tokens.
    We use a 4 char/token approximation (standard rough estimate).
    tiktoken is not in the project's dependency set; add it if higher
    precision becomes a requirement.
"""


# -------------------------------------------------------------------
# Tokenization
# -------------------------------------------------------------------

# Characters per token estimate (4 chars ≈ 1 token, widely used approximation)
CHARS_PER_TOKEN: float = 4.0


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for a text string.

    Uses a 4-char/token approximation. Accurate enough for 400-800 token
    target ranges — the margin is larger than any approximation error.

    Args:
        text: Text to estimate tokens for.

    Returns:
        Estimated token count (integer).
    """
    return max(1, int(len(text) / CHARS_PER_TOKEN))


# -------------------------------------------------------------------
# Chunk Configuration (per Embeddings.md §Chunk Size Strategy)
# -------------------------------------------------------------------

# Target range: 400–800 tokens (Embeddings.md spec)
CHUNK_TARGET_TOKENS: int = 600         # midpoint target
CHUNK_MIN_TOKENS: int = 50             # drop chunks smaller than this
CHUNK_MAX_TOKENS: int = 800            # hard ceiling before splitting
CHUNK_OVERLAP_TOKENS: int = 100        # overlap between consecutive chunks (midpoint of 80-120)

# Safety: never split content whose heading matches these patterns
# (all lowercase for case-insensitive matching)
NEVER_SPLIT_HEADING_KEYWORDS = [
    "procedure",
    "step",
    "safety",
    "warning",
    "caution",
    "instructions",
    "checklist",
    "maintenance procedure",
    "operating procedure",
    "emergency procedure",
]

# -------------------------------------------------------------------
# Embedding Configuration
# -------------------------------------------------------------------

# Google text-embedding-004 outputs 768-dimensional vectors
# Confirmed: https://ai.google.dev/gemini-api/docs/models/gemini#text-embedding
EMBEDDING_DIMENSION: int = 768

# Embedding model task type for document indexing
EMBEDDING_TASK_TYPE_DOCUMENT: str = "retrieval_document"

# Embedding model task type for queries
EMBEDDING_TASK_TYPE_QUERY: str = "retrieval_query"

# -------------------------------------------------------------------
# Batch Configuration
# -------------------------------------------------------------------

# Google Embedding API batch size (embed_content is single; we loop in batches)
# Google's embed_content endpoint accepts one text at a time in the current SDK.
# Batch here means: number of chunks to process before reporting progress.
EMBEDDING_BATCH_SIZE: int = 20         # chunks per embedding batch

# Pinecone upsert batch size (Pinecone recommends ≤100 vectors/upsert)
PINECONE_UPSERT_BATCH_SIZE: int = 100

# -------------------------------------------------------------------
# Search Configuration
# -------------------------------------------------------------------

# Default top-K for similarity search (per Embeddings.md spec)
DEFAULT_SEARCH_TOP_K: int = 10

# -------------------------------------------------------------------
# Versioning (for re-embedding support)
# -------------------------------------------------------------------

EMBEDDING_PIPELINE_VERSION: str = "1.0"
CHUNK_PIPELINE_VERSION: str = "1.0"

# Pinecone metadata key storing the pipeline version
VERSION_METADATA_KEY: str = "pipeline_version"

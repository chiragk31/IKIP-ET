"""
Copilot Constants

Defines shared constants for the Epic 8 AI Copilot module.
"""

# Confidence combination weights (must sum to 1.0)
# Formula: confidence = search * W_SEARCH + graph * W_GRAPH + meta * W_META + llm * W_LLM
CONFIDENCE_WEIGHT_SEARCH = 0.40   # Avg reranked chunk score (real hybrid signal from Epic 7)
CONFIDENCE_WEIGHT_GRAPH = 0.20    # Fraction of query entities found in graph nodes (0–1)
CONFIDENCE_WEIGHT_META = 0.20     # Fraction of chunks matching query intent doc_type (0–1)
CONFIDENCE_WEIGHT_LLM = 0.20      # LLM self-reported confidence from JSON response

# Response that must be returned when context package is empty or insufficient
NO_EVIDENCE_RESPONSE = (
    "I could not find supporting evidence in the available knowledge base."
)

# Conversation memory limits
MAX_HISTORY_TURNS = 10            # How many prior turns to include in the prompt
MAX_SESSIONS = 1000               # Max simultaneous in-memory sessions

# Default search parameters for copilot (faster than full search)
COPILOT_DEFAULT_TOP_K = 5
COPILOT_DEFAULT_MIN_SCORE = 0.30

# Minimum confidence below which the response_validator will flag the answer
MIN_ACCEPTABLE_CONFIDENCE = 0.10

# Minimum number of citations required in a valid response
MIN_CITATIONS_REQUIRED = 1

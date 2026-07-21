"""
Graph Module Constants

Defines the valid set of Neo4j node labels and relationship types
for the Knowledge Graph Builder.

These values derive from:
 - EntityType in app/utils/constants.py  (the master enum)
 - RelationshipType in app/utils/constants.py

The graph layer mirrors the ontology layer — we do NOT invent new
types here.  If a new entity/relationship type is needed it must
first be added to constants.py.

Rule:
    LLM NEVER generates Cypher.
    Only GraphRepository writes to Neo4j.
    All Cypher is predefined here or in graph_queries.py.
"""

from app.utils.constants import EntityType, RelationshipType

# -------------------------------------------------------------------
# Valid Neo4j node labels (derived from EntityType enum)
# -------------------------------------------------------------------

VALID_NODE_LABELS: set[str] = {e.value for e in EntityType}

# -------------------------------------------------------------------
# Valid Neo4j relationship types (derived from RelationshipType enum)
# -------------------------------------------------------------------

VALID_RELATIONSHIP_TYPES: set[str] = {r.value for r in RelationshipType}

# -------------------------------------------------------------------
# Graph write configuration
# -------------------------------------------------------------------

# Number of nodes to write per Neo4j transaction
NODE_BATCH_SIZE: int = 100

# Number of relationships to write per Neo4j transaction
RELATIONSHIP_BATCH_SIZE: int = 200

# Minimum confidence required for a node to be written to the graph
# (low-confidence entities were already flagged / split in Epic 3)
MIN_NODE_CONFIDENCE: float = 0.0  # no floor here — Epic 3 validator handles filtering

# Pipeline version stored as provenance on every node and relationship
GRAPH_PIPELINE_VERSION: str = "1.0"

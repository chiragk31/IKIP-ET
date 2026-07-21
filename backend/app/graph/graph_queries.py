"""
Graph Queries

Pre-defined, parameterized Cypher queries for reading the Knowledge Graph.

Rules (Graph.md §Cypher Guidelines):
 - All queries are parameterized — NEVER concatenate strings.
 - NEVER execute AI-generated Cypher.
 - All queries are read-only (no MERGE/CREATE/DELETE).

Implemented queries:
 ✓ Asset 360           — all facts around a named asset
 ✓ Neighbor Discovery  — first-degree neighbours of any node
 ✓ Related Documents   — documents that mention the same entities

Stubbed (TODO for Epic 7 / GraphRAG integration):
 □ Shortest Path       — shortest path between two entities
 □ Subgraph Retrieval  — subgraph around an entity up to N hops
 □ Compliance Mapping  — regulations linked to an asset/procedure

GraphRepository uses these by passing them to Neo4jClient.execute_query().
This module contains ONLY Cypher strings and parameter builders — no Neo4j
driver calls.
"""

from typing import Any, Dict, Optional


# -------------------------------------------------------------------
# Asset 360
# -------------------------------------------------------------------

ASSET_360_QUERY = """
MATCH (a {entity_id: $entity_id})
OPTIONAL MATCH (a)-[r1]->(n1)
OPTIONAL MATCH (n2)-[r2]->(a)
RETURN
    a,
    collect(DISTINCT {rel: type(r1), node: n1}) AS outgoing,
    collect(DISTINCT {rel: type(r2), node: n2}) AS incoming
LIMIT 1
"""


def asset_360_params(entity_id: str) -> Dict[str, Any]:
    """
    Build parameters for the Asset 360 query.

    Args:
        entity_id: Stable entity ID of the asset node to query.

    Returns:
        Parameter dict for ASSET_360_QUERY.
    """
    return {"entity_id": entity_id}


# -------------------------------------------------------------------
# Neighbor Discovery
# -------------------------------------------------------------------

NEIGHBOR_DISCOVERY_QUERY = """
MATCH (n {entity_id: $entity_id})-[r]-(neighbor)
RETURN
    n.entity_id    AS node_id,
    n.name         AS node_name,
    type(r)        AS relationship,
    neighbor.entity_id AS neighbor_id,
    neighbor.name       AS neighbor_name,
    labels(neighbor)[0] AS neighbor_label
LIMIT $limit
"""


def neighbor_discovery_params(entity_id: str, limit: int = 50) -> Dict[str, Any]:
    """
    Build parameters for the Neighbor Discovery query.

    Args:
        entity_id: Entity ID of the node to explore.
        limit: Maximum number of neighbours to return.

    Returns:
        Parameter dict for NEIGHBOR_DISCOVERY_QUERY.
    """
    return {"entity_id": entity_id, "limit": limit}


# -------------------------------------------------------------------
# Related Documents
# -------------------------------------------------------------------

RELATED_DOCUMENTS_QUERY = """
MATCH (d1:Document {entity_id: $document_id})-[:MENTIONS]->(e)<-[:MENTIONS]-(d2:Document)
WHERE d2.entity_id <> $document_id
RETURN
    d2.entity_id AS related_document_id,
    d2.name      AS related_document_name,
    collect(DISTINCT e.name) AS shared_entities,
    count(DISTINCT e)        AS shared_count
ORDER BY shared_count DESC
LIMIT $limit
"""


def related_documents_params(document_id: str, limit: int = 20) -> Dict[str, Any]:
    """
    Build parameters for the Related Documents query.

    Args:
        document_id: Document entity_id to find related documents for.
        limit: Maximum number of related documents to return.

    Returns:
        Parameter dict for RELATED_DOCUMENTS_QUERY.
    """
    return {"document_id": document_id, "limit": limit}


# -------------------------------------------------------------------
# Node lookup by entity_id
# -------------------------------------------------------------------

NODE_BY_ID_QUERY = """
MATCH (n {entity_id: $entity_id})
RETURN n
LIMIT 1
"""


def node_by_id_params(entity_id: str) -> Dict[str, Any]:
    """
    Args:
        entity_id: Stable entity ID to retrieve.

    Returns:
        Parameter dict for NODE_BY_ID_QUERY.
    """
    return {"entity_id": entity_id}


# -------------------------------------------------------------------
# List nodes (paginated)
# -------------------------------------------------------------------

LIST_NODES_QUERY = """
MATCH (n)
RETURN
    n.entity_id AS entity_id,
    n.name      AS name,
    labels(n)[0] AS label,
    n.confidence AS confidence,
    n.source_document AS source_document,
    n.created_at AS created_at
ORDER BY n.created_at DESC
SKIP $skip
LIMIT $limit
"""

COUNT_NODES_QUERY = "MATCH (n) RETURN count(n) AS total"


def list_nodes_params(page: int = 1, limit: int = 20) -> Dict[str, Any]:
    """
    Args:
        page: 1-indexed page number.
        limit: Items per page.

    Returns:
        Parameter dict for LIST_NODES_QUERY.
    """
    return {"skip": (page - 1) * limit, "limit": limit}


# -------------------------------------------------------------------
# Document graph status check
# -------------------------------------------------------------------

# DOCUMENT_GRAPH_STATUS_QUERY = """
# MATCH (d:Document {entity_id: $document_id})
# RETURN d.entity_id AS document_id, d.created_at AS graphed_at
# LIMIT 1
# """

DOCUMENT_GRAPH_STATUS_QUERY = """
MATCH (n {source_document: $document_id})
RETURN n.source_document AS document_id, max(n.created_at) AS graphed_at
LIMIT 1
"""


def document_graph_status_params(document_id: str) -> Dict[str, Any]:
    """
    Args:
        document_id: Document entity_id to check.

    Returns:
        Parameter dict for DOCUMENT_GRAPH_STATUS_QUERY.
    """
    return {"document_id": document_id}


# -------------------------------------------------------------------
# Stubs — to be implemented in Epic 7 / GraphRAG
# -------------------------------------------------------------------

def shortest_path_params(source_id: str, target_id: str) -> Dict[str, Any]:
    """
    TODO: Implement shortest-path query for GraphRAG (Epic 7).

    Args:
        source_id: Source entity_id.
        target_id: Target entity_id.

    Returns:
        Parameter dict (stub — not yet executable).
    """
    raise NotImplementedError(
        "shortest_path_params is not yet implemented. "
        "Implement in Epic 7 (GraphRAG) using allShortestPaths() Cypher."
    )


def subgraph_retrieval_params(entity_id: str, hops: int = 2) -> Dict[str, Any]:
    """
    TODO: Implement subgraph retrieval for GraphRAG (Epic 7).

    Args:
        entity_id: Root entity_id for the subgraph.
        hops: Maximum number of hops to traverse.

    Returns:
        Parameter dict (stub — not yet executable).
    """
    raise NotImplementedError(
        "subgraph_retrieval_params is not yet implemented. "
        "Implement in Epic 7 (GraphRAG) using variable-length MATCH."
    )


def compliance_mapping_params(asset_id: str) -> Dict[str, Any]:
    """
    TODO: Implement compliance mapping for Epic 8 (Compliance Intelligence).

    Args:
        asset_id: Asset entity_id to find compliance requirements for.

    Returns:
        Parameter dict (stub — not yet executable).
    """
    raise NotImplementedError(
        "compliance_mapping_params is not yet implemented. "
        "Implement in Epic 8 (Compliance) traversing Asset→Procedure→Regulation."
    )

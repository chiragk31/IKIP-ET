"""
Graph Search / Expansion

Expands semantic results using the Knowledge Graph.

Purpose:
    Given seed entities (from the query or from the top semantic chunks),
    traverse the graph to find connected assets, procedures, failures, etc.

Input:
    List of seed entity_ids, depth.
Output:
    List of GraphExpansionNode objects.
"""

import structlog
from typing import List, Set, Dict, Any

from app.search.models import GraphExpansionNode
from app.graph.graph_repository import GraphRepository
from app.search.constants import GRAPH_EXPANSION_MAX_DEPTH

logger = structlog.get_logger(__name__)


class GraphSearch:
    """
    Expands search context using Neo4j graph traversal.
    """

    def __init__(self, graph_repo: GraphRepository) -> None:
        """
        Initialize GraphSearch.

        Args:
            graph_repo: DI provided GraphRepository (the ONLY Neo4j caller).
        """
        self._graph = graph_repo
        logger.info("graph_search_initialized")

    def expand(
        self,
        seed_entities: List[str],
        depth: int,
    ) -> List[GraphExpansionNode]:
        """
        Traverse the graph from seed entities up to `depth` hops.

        Args:
            seed_entities: List of starting entity_ids.
            depth: Hops to traverse (0 = disable).

        Returns:
            List of discovered GraphExpansionNode objects.
        """
        if depth <= 0 or not seed_entities:
            return []

        # Enforce max depth (search validator already checks this, but defense in depth)
        actual_depth = min(depth, GRAPH_EXPANSION_MAX_DEPTH)

        logger.info(
            "graph_search_start",
            seeds=len(seed_entities),
            depth=actual_depth,
        )

        discovered_nodes: Dict[str, GraphExpansionNode] = {}
        visited: Set[str] = set()

        # We do Breadth-First Expansion up to `actual_depth` hops.
        current_frontier = set(seed_entities)
        
        for current_hop in range(1, actual_depth + 1):
            next_frontier = set()
            for seed in current_frontier:
                if seed in visited:
                    continue
                visited.add(seed)

                # Use Epic 5's existing parameterized query via GraphRepository
                try:
                    neighbors = self._graph.get_neighbors(seed, limit=50)
                except Exception as e:
                    logger.warning(
                        "graph_search_neighbor_failed",
                        seed=seed,
                        error=str(e),
                    )
                    continue

                for record in neighbors:
                    n_id = record.get("neighbor_id")
                    if not n_id or n_id in discovered_nodes:
                        continue

                    node = GraphExpansionNode(
                        node_id=n_id,
                        node_name=record.get("neighbor_name", ""),
                        node_label=record.get("neighbor_label", ""),
                        relationship=record.get("relationship", ""),
                        seed_entity_id=seed,
                        hop=current_hop,
                    )
                    discovered_nodes[n_id] = node
                    next_frontier.add(n_id)

            current_frontier = next_frontier
            if not current_frontier:
                break  # Exhausted the graph component

        results = list(discovered_nodes.values())
        logger.info(
            "graph_search_complete",
            discovered=len(results),
            hops_completed=current_hop,
        )
        return results

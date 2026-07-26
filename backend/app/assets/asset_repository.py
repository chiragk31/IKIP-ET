"""
Asset Repository

Thin wrapper that coordinates GraphRepository (Epic 5) and
HybridSearchService (Epic 7) calls on behalf of the Asset module.

Per Assets.md §Design Philosophy and §Repository Layer:
    "Business logic never communicates directly with Neo4j or Supabase."
    "The Asset module never performs vector search directly."

This module is the ONLY caller of GraphRepository and HybridSearchService
within the assets/ package. It does NOT call:
  - Neo4jClient directly
  - PineconeRepository directly
  - Any embedding provider

It wraps the existing read methods from GraphRepository:
  - get_asset_360(entity_id)   — all connected nodes and relationships
  - get_neighbors(entity_id)   — first-degree neighbours
  - list_nodes()               — for asset list (filtered in Python)

And HybridSearchService:
  - search(HybridSearchQuery)  — related documents via semantic search
"""

import asyncio
import structlog
from typing import Any, Dict, List, Optional, Tuple

from app.graph.graph_repository import GraphRepository
from app.search.search_service import SearchService as HybridSearchService
from app.search.models import HybridSearchQuery, MetadataFilters, ContextChunk
from app.assets.constants import (
    ASSET_NODE_LABEL,
    ASSET_DOCUMENT_SEARCH_TOP_K,
    ASSET_DOCUMENT_SEARCH_MIN_SCORE,
    ASSET_DOCUMENT_SEARCH_DEPTH,
    NEIGHBOR_FETCH_LIMIT,
    ASSET_SEARCH_QUERY_TEMPLATE,
)

logger = structlog.get_logger(__name__)


class AssetRepository:
    """
    Coordinates GraphRepository and HybridSearchService for asset data retrieval.

    Purpose:
        Abstract the data access layer for the Asset module. Orchestrates
        parallel fetches where possible (graph + search are independent).
    Input:
        Validated asset entity_ids and search parameters.
    Output:
        Raw graph dicts and search chunks for the builder layer to assemble.
    """

    def __init__(
        self,
        graph_repo: GraphRepository,
        search_svc: HybridSearchService,
    ) -> None:
        """
        Initialize AssetRepository.

        Args:
            graph_repo: GraphRepository — the ONLY Neo4j caller.
            search_svc: HybridSearchService — the ONLY vector search caller.
        """
        self._graph = graph_repo
        self._search = search_svc
        logger.info("asset_repository_initialized")

    # ------------------------------------------------------------------
    # Parallel fetch — used by AssetService for Asset 360
    # ------------------------------------------------------------------

    async def fetch_asset_360_parallel(
        self,
        entity_id: str,
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[ContextChunk]]:
        """
        Fetch graph data and related documents in parallel.

        graph_data and neighbors are independent of the search call, so
        all three are launched concurrently via asyncio.gather() — this
        avoids the sequential latency pattern documented in Epic 7/8's
        Known Gaps section.

        Args:
            entity_id: Validated asset entity_id.

        Returns:
            Tuple of:
              - asset_360_data: Dict from GraphRepository.get_asset_360()
                                (None if no node found)
              - neighbors: List of dicts from GraphRepository.get_neighbors()
              - related_chunks: List of ContextChunk from HybridSearchService

        Raises:
            Exception: Propagates any graph or search failure to AssetService.
        """
        logger.info("asset_repository_fetch_start", entity_id=entity_id)

        # All three calls are independent — run concurrently
        graph_360_coro = asyncio.to_thread(self._get_asset_360_sync, entity_id)
        neighbors_coro = asyncio.to_thread(self._get_neighbors_sync, entity_id)
        search_coro = self._search_related_documents(entity_id, entity_id)

        graph_result, neighbors_result, search_result = await asyncio.gather(
            graph_360_coro,
            neighbors_coro,
            search_coro,
            return_exceptions=True,
        )

        # Handle partial failures gracefully — missing search results are
        # non-fatal; missing graph data signals a true 404
        asset_360_data: Optional[Dict[str, Any]] = None
        neighbors: List[Dict[str, Any]] = []
        related_chunks: List[ContextChunk] = []

        if isinstance(graph_result, Exception):
            logger.error(
                "asset_graph_360_failed",
                entity_id=entity_id,
                error=str(graph_result),
            )
            raise graph_result
        else:
            asset_360_data = graph_result

        if isinstance(neighbors_result, Exception):
            logger.warning(
                "asset_neighbors_failed",
                entity_id=entity_id,
                error=str(neighbors_result),
            )
            # Non-fatal: continue with empty neighbors
        else:
            neighbors = neighbors_result or []

        if isinstance(search_result, Exception):
            logger.warning(
                "asset_search_failed",
                entity_id=entity_id,
                error=str(search_result),
            )
            # Non-fatal: continue without related documents
        else:
            related_chunks = search_result or []

        logger.info(
            "asset_repository_fetch_complete",
            entity_id=entity_id,
            has_asset=asset_360_data is not None,
            neighbor_count=len(neighbors),
            related_chunk_count=len(related_chunks),
        )

        return asset_360_data, neighbors, related_chunks

    # ------------------------------------------------------------------
    # Asset list (for GET /assets)
    # ------------------------------------------------------------------

    async def list_assets(
        self,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Return a paginated list of asset nodes from the graph.

        Uses GraphRepository.list_nodes() then filters to :Asset label
        in Python — no new Cypher required (AD-037).

        Args:
            page: 1-indexed page number.
            limit: Items per page.

        Returns:
            Dict with 'items' (list of asset node dicts) and 'total' count.
        """
        logger.info("asset_repository_list_start", page=page, limit=limit)

        # Over-fetch to filter; list_nodes supports pagination but doesn't
        # support label filter — we fetch a wider page and filter in Python.
        # For a real production system this would be a targeted query; here
        # we stay within the "no new Cypher in assets/" constraint (AD-037).
        raw_result = await asyncio.to_thread(
            self._graph.list_nodes,
            page=page,
            limit=limit * 5,  # over-fetch to account for non-asset nodes
        )

        all_items: List[Dict[str, Any]] = raw_result.get("items", [])
        total_all: int = raw_result.get("total", 0)

        # Filter to Asset label only
        asset_items = [
            item for item in all_items
            if item.get("label") == ASSET_NODE_LABEL
        ]

        # Re-paginate the filtered results
        start = (page - 1) * limit
        end = start + limit
        paginated = asset_items[start:end]
        asset_total = len(asset_items)

        logger.info(
            "asset_repository_list_complete",
            asset_count=asset_total,
            returned=len(paginated),
        )

        return {"items": paginated, "total": asset_total}

    # ------------------------------------------------------------------
    # Sync helpers (for asyncio.to_thread wrapping)
    # ------------------------------------------------------------------

    def _get_asset_360_sync(
        self, entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call GraphRepository.get_asset_360() synchronously.

        Args:
            entity_id: Asset entity_id.

        Returns:
            First record dict, or None if not found.
        """
        results = self._graph.get_asset_360(entity_id)
        return results[0] if results else None

    def _get_neighbors_sync(
        self, entity_id: str
    ) -> List[Dict[str, Any]]:
        """
        Call GraphRepository.get_neighbors() synchronously.

        Args:
            entity_id: Asset entity_id.

        Returns:
            List of neighbor record dicts.
        """
        return self._graph.get_neighbors(entity_id, limit=NEIGHBOR_FETCH_LIMIT)

    async def _search_related_documents(
        self,
        entity_id: str,
        asset_name: str,
    ) -> List[ContextChunk]:
        """
        Search for related documents via HybridSearchService.

        Per Assets.md §Search Integration:
            "The Asset module never performs vector search directly."

        Uses the asset's entity_id as the search query seed plus a
        structured template that targets maintenance/inspection context.

        Args:
            entity_id: Asset entity_id (used in metadata filter).
            asset_name: Asset name for the search query text.

        Returns:
            List of ContextChunk objects from the search result.
        """
        query_text = ASSET_SEARCH_QUERY_TEMPLATE.format(name=asset_name)

        search_query = HybridSearchQuery(
            query=query_text,
            top_k=ASSET_DOCUMENT_SEARCH_TOP_K,
            min_score=ASSET_DOCUMENT_SEARCH_MIN_SCORE,
            graph_depth=ASSET_DOCUMENT_SEARCH_DEPTH,
            expand_graph=False,   # disable graph expansion here — we do it separately
            rerank=True,
            filters=MetadataFilters(asset_id=entity_id),
        )

        try:
            result = await self._search.search(search_query)
            return result.chunks
        except Exception as e:
            logger.warning(
                "asset_document_search_failed",
                entity_id=entity_id,
                error=str(e),
            )
            return []

"""
Search Service Orchestrator

Top-level service for Epic 7 (Search).

Orchestrates the entire hybrid retrieval pipeline per Search.md:
    Normalize → Rewrite → Embed → Semantic Search → Metadata Filter →
    Graph Expansion → Context Builder → Rerank → Return.
"""

import time
import structlog
from typing import Any, Dict

from app.search.models import HybridSearchQuery, HybridSearchResult
from app.search.search_validator import SearchValidator
from app.search.query_processor import QueryProcessor
from app.search.query_rewriter import QueryRewriter
from app.search.semantic_search import SemanticSearch
from app.search.metadata_filter import MetadataFilter
from app.search.graph_search import GraphSearch
from app.search.context_builder import ContextBuilder
from app.search.reranker import Reranker

logger = structlog.get_logger(__name__)


class SearchService:
    """
    Top-level orchestrator for the Hybrid Search pipeline.
    """

    def __init__(
        self,
        validator: SearchValidator,
        processor: QueryProcessor,
        rewriter: QueryRewriter,
        semantic: SemanticSearch,
        meta_filter: MetadataFilter,
        graph_search: GraphSearch,
        context_builder: ContextBuilder,
        reranker: Reranker,
    ) -> None:
        """
        Initialize the SearchService with all pipeline dependencies.
        """
        self._validator = validator
        self._processor = processor
        self._rewriter = rewriter
        self._semantic = semantic
        self._meta_filter = meta_filter
        self._graph_search = graph_search
        self._context_builder = context_builder
        self._reranker = reranker
        logger.info("search_orchestrator_initialized")

    async def search(self, query: HybridSearchQuery) -> HybridSearchResult:
        """
        Execute the full hybrid search pipeline.

        Args:
            query: HybridSearchQuery from the API.

        Returns:
            HybridSearchResult containing the context package and citations.
        """
        start_time = time.time()
        logger.info(
            "hybrid_search_start",
            query_length=len(query.query),
            top_k=query.top_k,
            depth=query.graph_depth,
        )

        try:
            # 1. Validation (raises ValueError on injection/invalid filters)
            valid_query = self._validator.validate(query)

            # 2. Query Processing (Normalization, Intent/Entity detection)
            processed_query = self._processor.process(valid_query.query)

            # 3. Query Rewriting (LLM-based expansion)
            processed_query = await self._rewriter.rewrite(processed_query)

            # 4. Semantic Search (Epic 6 delegation)
            raw_chunks = await self._semantic.search(
                query=processed_query,
                filters=valid_query.filters,
                top_k=valid_query.top_k,
                min_score=valid_query.min_score,
            )

            # 5. Metadata Filtering (In-memory strict filtering)
            filtered_chunks = self._meta_filter.filter_chunks(
                chunks=raw_chunks,
                filters=valid_query.filters,
            )

            # 6. Graph Expansion (Epic 5 delegation)
            graph_nodes = []
            if valid_query.expand_graph and valid_query.graph_depth > 0:
                # Seed with entities found in the query AND entities found in the top chunks
                seed_entities = set(processed_query.detected_entities)
                for c in filtered_chunks:
                    seed_entities.update(c.graph_entities)
                
                graph_nodes = self._graph_search.expand(
                    seed_entities=list(seed_entities),
                    depth=valid_query.graph_depth,
                )

            # 7. Reranking (Adjust scores using graph & meta signals)
            if valid_query.rerank:
                final_chunks = self._reranker.rerank(
                    chunks=filtered_chunks,
                    graph_nodes=graph_nodes,
                    query=processed_query,
                )
            else:
                final_chunks = filtered_chunks

            # 8. Context Builder (Assemble final package)
            context_package = self._context_builder.build(
                query=valid_query.query,
                processed_query=processed_query,
                chunks=final_chunks,
                graph_nodes=graph_nodes,
            )

            duration = time.time() - start_time
            diagnostics: Dict[str, Any] = {
                "duration_seconds": round(duration, 3),
                "semantic_chunks": len(raw_chunks),
                "filtered_chunks": len(final_chunks),
                "graph_nodes_discovered": len(graph_nodes),
                "expanded_query": processed_query.expanded_query,
            }

            logger.info(
                "hybrid_search_complete",
                total_results=len(final_chunks),
                duration=diagnostics["duration_seconds"],
            )

            return HybridSearchResult(
                query=valid_query.query,
                total_results=len(final_chunks),
                chunks=final_chunks,
                graph_nodes=graph_nodes,
                citations=context_package.citations,
                context_package=context_package,
                diagnostics=diagnostics,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "hybrid_search_failed",
                error=str(e),
                duration=round(duration, 3),
            )
            raise

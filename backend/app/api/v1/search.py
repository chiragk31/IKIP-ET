"""
Search API Router

Endpoints for Epic 7 (Hybrid Search).
"""

import structlog
from fastapi import APIRouter, Depends

from app.core.dependencies import get_hybrid_search_service
from app.search.schemas import SearchRequest, SearchResponse
from app.search.models import HybridSearchQuery
from app.utils.response import success_response, error_response

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("", response_model=None)
async def hybrid_search(
    request: SearchRequest,
    search_svc=Depends(get_hybrid_search_service),
):
    """
    Execute a hybrid search combining semantic retrieval and graph expansion.

    This is a synchronous endpoint. It validates the query, processes it,
    retrieves context from Pinecone and Neo4j, and returns a unified context package.

    Args:
        request: SearchRequest containing query text and optional filters.

    Returns:
        SearchResponse with ranked chunks, graph nodes, and citations.
    """
    try:
        # Map API schema to internal model
        internal_query = HybridSearchQuery(
            query=request.query,
            top_k=request.top_k,
            min_score=request.min_score,
            graph_depth=request.graph_depth,
            expand_graph=request.expand_graph,
            rerank=request.rerank,
            filters=request.filters,
        )

        # Execute
        result = await search_svc.search(internal_query)

        # Map internal result to API schema
        response = SearchResponse(
            query=result.query,
            total_results=result.total_results,
            chunks=result.chunks,
            graph_nodes=result.graph_nodes,
            citations=result.citations,
            diagnostics=result.diagnostics,
        )

        return success_response(
            data=response.model_dump(),
            message=f"Found {result.total_results} results",
        )

    except ValueError as e:
        # Validation failures (e.g. Cypher injection detected)
        logger.warning("search_validation_error", error=str(e))
        return error_response(
            message=str(e),
            status_code=400,
        )
    except Exception as e:
        # System failures
        logger.error("search_endpoint_failed", error=str(e))
        return error_response(
            message="Search failed due to an internal error",
            status_code=500,
        )

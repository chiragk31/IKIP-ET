"""
Graph API Endpoints

Provides:
 - POST /{document_id}/build  — Manual trigger (mirrors /ontology/{id}/normalize)
 - GET  /nodes                — Paginated list of all graph nodes
 - GET  /node/{entity_id}     — Single node with neighbours
 - GET  /{document_id}/status — Whether this document has been graphed yet

Design:
 - BackgroundTasks pattern (identical to ontology.py /normalize route).
 - success_response / error_response for all responses (per utils/response.py).
 - No direct Neo4j access — all reads go through GraphService → GraphRepository.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
import structlog

from app.core.dependencies import get_graph_service, get_graph_repository
from app.graph.graph_service import GraphService
from app.graph.graph_repository import GraphRepository
from app.utils.response import success_response, error_response

logger = structlog.get_logger(__name__)

router = APIRouter()


# -------------------------------------------------------------------
# Manual trigger — build graph for a document
# -------------------------------------------------------------------

@router.post(
    "/{document_id}/build",
    summary="Manually trigger graph build for a document",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_graph_build(
    document_id: str,
    background_tasks: BackgroundTasks,
    graph_service: GraphService = Depends(get_graph_service),
):
    """
    Manually trigger the graph build pipeline for a document.

    Requires the ontology normalization (Epic 4) to have completed —
    the NKO must be persisted at normalized/{document_id}/nko.json.

    In production, this is triggered automatically by the `ontology.updated`
    event.  This endpoint exists for development / retry flows.
    """
    logger.info("graph_build_trigger", document_id=document_id)

    async def run_build():
        try:
            result = graph_service.build(document_id)
            if result.status == "failed":
                logger.error(
                    "background_graph_build_failed",
                    document_id=document_id,
                    error=result.error_message,
                )
            else:
                logger.info(
                    "background_graph_build_complete",
                    document_id=document_id,
                    nodes_written=result.nodes_written,
                    relationships_written=result.relationships_written,
                )
        except Exception as e:
            logger.error(
                "background_graph_build_exception",
                document_id=document_id,
                error=str(e),
            )

    background_tasks.add_task(run_build)

    return success_response(
        message="Graph build started",
        data={"document_id": document_id, "status": "building"},
        status_code=status.HTTP_202_ACCEPTED,
    )


# -------------------------------------------------------------------
# GET /graph/nodes — paginated node list
# -------------------------------------------------------------------

@router.get(
    "/nodes",
    summary="List all graph nodes (paginated)",
)
async def list_graph_nodes(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    graph_repo: GraphRepository = Depends(get_graph_repository),
):
    """
    Return a paginated list of all nodes in the Knowledge Graph.

    Each node includes entity_id, name, label, confidence, source_document,
    and created_at.
    """
    try:
        result = graph_repo.list_nodes(page=page, limit=limit)
        return success_response(
            message="Graph nodes retrieved",
            data={
                "items": result["items"],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": result["total"],
                },
            },
        )
    except Exception as e:
        logger.error("list_graph_nodes_failed", error=str(e))
        return error_response(
            message="Failed to retrieve graph nodes",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# -------------------------------------------------------------------
# GET /graph/node/{entity_id} — single node with neighbours
# -------------------------------------------------------------------

@router.get(
    "/node/{entity_id}",
    summary="Get a single graph node with its neighbours",
)
async def get_graph_node(
    entity_id: str,
    graph_repo: GraphRepository = Depends(get_graph_repository),
):
    """
    Return a single node by its stable entity_id, plus its Asset 360 data
    (all connected nodes and relationships).
    """
    try:
        node = graph_repo.get_node_by_id(entity_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node not found: {entity_id}",
            )

        neighbors = graph_repo.get_neighbors(entity_id)

        return success_response(
            message="Node retrieved",
            data={"node": node, "neighbors": neighbors},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_graph_node_failed", entity_id=entity_id, error=str(e))
        return error_response(
            message="Failed to retrieve node",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# -------------------------------------------------------------------
# GET /graph/{document_id}/status — has this document been graphed?
# -------------------------------------------------------------------

@router.get(
    "/{document_id}/status",
    summary="Check whether a document has been written to the graph",
)
async def get_graph_status(
    document_id: str,
    graph_repo: GraphRepository = Depends(get_graph_repository),
):
    """
    Check whether the graph build pipeline has been run for this document.

    Returns the Document node's created_at timestamp if it has been graphed,
    or indicates that the document is not yet in the graph.
    """
    try:
        status_record = graph_repo.get_document_graph_status(document_id)

        if status_record:
            return success_response(
                message="Document has been graphed",
                data={
                    "document_id": document_id,
                    "graphed": True,
                    "graphed_at": status_record.get("graphed_at"),
                },
            )
        else:
            return success_response(
                message="Document has not been graphed yet",
                data={"document_id": document_id, "graphed": False},
            )
    except Exception as e:
        logger.error("get_graph_status_failed", document_id=document_id, error=str(e))
        return error_response(
            message="Failed to check graph status",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

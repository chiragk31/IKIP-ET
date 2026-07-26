"""
Dashboard API

Thin aggregation layer for the IKIP Dashboard frontend.

This router ONLY delegates to existing services already built in Epics 1-9.
It introduces NO new queries, NO new database access, NO AI calls.

Endpoints:
    GET /dashboard/overview    — Aggregate: document counts + asset count + graph stats
    GET /dashboard/documents   — Recent documents from DocumentService
    GET /dashboard/assets      — Asset list from AssetService
    GET /dashboard/system      — Service health check from health module
    GET /dashboard/graph       — Graph node/edge summary from GraphRepository
    GET /dashboard/activity    — Recent activity events from documents table
    GET /dashboard/search      — Search analytics placeholder (no analytics store yet)

Architecture:
    Dashboard API → existing Services → existing Repositories → existing DBs
    NO new business logic lives here.
"""

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
import structlog

from app.core.dependencies import (
    get_document_service,
    get_asset_service,
    get_graph_repository,
    get_supabase_client,
    get_neo4j_client,
    get_pinecone_client,
    get_llm_service,
)
from app.services.document_service import DocumentService
from app.assets.asset_service import AssetService
from app.graph.graph_repository import GraphRepository
from app.database.supabase import SupabaseClient
from app.database.neo4j_client import Neo4jClient
from app.database.pinecone_client import PineconeClient
from app.ai.llm_service import LLMService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Dashboard"])


# -----------------------------------------------
# Overview — aggregate platform-wide KPIs
# -----------------------------------------------

@router.get("/overview", summary="Dashboard overview metrics")
async def get_overview(
    document_svc: DocumentService = Depends(get_document_service),
    asset_svc: AssetService = Depends(get_asset_service),
    graph_repo: GraphRepository = Depends(get_graph_repository),
) -> JSONResponse:
    """
    Aggregate platform KPIs for the dashboard overview cards.

    Returns:
        documents: total, completed, failed, processing, queued
        assets: total count
        graph: node_count, relationship_count
        embeddings: approximate vector count (via Pinecone)
    """
    start = time.time()
    logger.info("dashboard_overview_start")

    result: Dict[str, Any] = {}

    # --- Documents ---
    try:
        doc_list = await document_svc.list_documents(page=1, limit=1)
        total_docs = doc_list.total

        # Fetch a larger page to count by status (up to 200 — sufficient for hackathon)
        all_docs = await document_svc.list_documents(page=1, limit=200)
        docs_by_status: Dict[str, int] = {}
        for doc in all_docs.documents:
            docs_by_status[doc.status] = docs_by_status.get(doc.status, 0) + 1

        result["documents"] = {
            "total": total_docs,
            "completed": docs_by_status.get("completed", 0),
            "failed": docs_by_status.get("failed", 0),
            "processing": docs_by_status.get("processing", 0),
            "queued": docs_by_status.get("queued", 0),
        }
    except Exception as e:
        logger.warning("dashboard_overview_docs_failed", error=str(e))
        result["documents"] = {"total": 0, "completed": 0, "failed": 0, "processing": 0, "queued": 0, "error": str(e)}

    # --- Assets ---
    try:
        asset_list = await asset_svc.list_assets(page=1, limit=1)
        result["assets"] = {"total": asset_list.total}
    except Exception as e:
        logger.warning("dashboard_overview_assets_failed", error=str(e))
        result["assets"] = {"total": 0, "error": str(e)}

    # --- Graph Stats ---
    try:
        graph_data = graph_repo.list_nodes(page=1, limit=1)
        node_count = graph_data.get("total", 0) if isinstance(graph_data, dict) else 0
        result["graph"] = {"node_count": node_count, "relationship_count": 0}
    except Exception as e:
        logger.warning("dashboard_overview_graph_failed", error=str(e))
        result["graph"] = {"node_count": 0, "relationship_count": 0, "error": str(e)}

    # --- Embeddings placeholder (Pinecone stats not directly available via our SDK wrapper) ---
    result["embeddings"] = {"total_vectors": 0, "note": "Pinecone stats not cached"}

    duration = round((time.time() - start) * 1000, 2)
    logger.info("dashboard_overview_complete", duration_ms=duration)

    return JSONResponse(status_code=200, content={
        "status": "success",
        "message": "Overview metrics retrieved",
        "data": result,
        "meta": {"duration_ms": duration},
    })


# -----------------------------------------------
# Recent Documents
# -----------------------------------------------

@router.get("/documents", summary="Recent documents for dashboard")
async def get_dashboard_documents(
    document_svc: DocumentService = Depends(get_document_service),
) -> JSONResponse:
    """
    Return the 20 most recent documents for the dashboard Documents widget.

    Delegates entirely to DocumentService.list_documents.
    """
    try:
        result = await document_svc.list_documents(page=1, limit=20)
        docs = [
            {
                "id": doc.id,
                "filename": doc.original_filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "status": doc.status,
                "processing_stage": doc.processing_stage,
                "upload_time": doc.upload_time.isoformat(),
                "document_type": doc.document_type,
                "language": doc.language,
            }
            for doc in result.documents
        ]
        return JSONResponse(status_code=200, content={
            "status": "success",
            "message": "Documents retrieved",
            "data": {
                "documents": docs,
                "total": result.total,
            },
        })
    except Exception as e:
        logger.error("dashboard_documents_failed", error=str(e))
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": "Failed to retrieve documents",
            "errors": {},
        })


# -----------------------------------------------
# Asset Summary
# -----------------------------------------------

@router.get("/assets", summary="Asset summary for dashboard")
async def get_dashboard_assets(
    asset_svc: AssetService = Depends(get_asset_service),
) -> JSONResponse:
    """
    Return top 20 assets for the dashboard Asset Intelligence widget.

    Delegates entirely to AssetService.list_assets.
    """
    try:
        result = await asset_svc.list_assets(page=1, limit=20)
        assets = [
            item.model_dump() if hasattr(item, "model_dump") else dict(item)
            for item in result.items
        ]
        return JSONResponse(status_code=200, content={
            "status": "success",
            "message": "Assets retrieved",
            "data": {
                "assets": assets,
                "total": result.total,
            },
        })
    except Exception as e:
        logger.error("dashboard_assets_failed", error=str(e))
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": "Failed to retrieve assets",
            "errors": {},
        })


# -----------------------------------------------
# System Health
# -----------------------------------------------

@router.get("/system", summary="System health for dashboard")
async def get_dashboard_system(
    supabase: SupabaseClient = Depends(get_supabase_client),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
    pinecone: PineconeClient = Depends(get_pinecone_client),
    llm: LLMService = Depends(get_llm_service),
) -> JSONResponse:
    """
    Aggregate service health status for the dashboard System Health widget.

    Reuses the same health check logic as GET /health.
    """
    start = time.time()
    services = {}

    try:
        result = supabase.health_check()
        services["supabase"] = {"status": result["status"], "latency_ms": result.get("latency_ms", 0)}
    except Exception as e:
        services["supabase"] = {"status": "down", "latency_ms": 0, "error": str(e)}

    try:
        result = neo4j.health_check()
        services["neo4j"] = {"status": result["status"], "latency_ms": result.get("latency_ms", 0)}
    except Exception as e:
        services["neo4j"] = {"status": "down", "latency_ms": 0, "error": str(e)}

    try:
        result = pinecone.health_check()
        services["pinecone"] = {"status": result["status"], "latency_ms": result.get("latency_ms", 0)}
    except Exception as e:
        services["pinecone"] = {"status": "down", "latency_ms": 0, "error": str(e)}

    try:
        result = await llm.health_check()
        services["gemini"] = {"status": result["status"], "latency_ms": result.get("latency_ms", 0)}
    except Exception as e:
        services["gemini"] = {"status": "down", "latency_ms": 0, "error": str(e)}

    # Backend self
    services["api"] = {"status": "up", "latency_ms": 0}

    overall = "healthy" if all(s["status"] in ("up", "healthy") for s in services.values()) else "degraded"
    duration = round((time.time() - start) * 1000, 2)

    return JSONResponse(status_code=200, content={
        "status": "success",
        "message": "System health retrieved",
        "data": {
            "overall": overall,
            "services": services,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_ms": duration,
        },
    })


# -----------------------------------------------
# Knowledge Graph Summary
# -----------------------------------------------

@router.get("/graph", summary="Knowledge Graph summary for dashboard")
async def get_dashboard_graph(
    graph_repo: GraphRepository = Depends(get_graph_repository),
) -> JSONResponse:
    """
    Return a sample of graph nodes for the dashboard Knowledge Graph widget.

    Delegates to GraphRepository.list_nodes — the ONLY Neo4j read path.
    """
    try:
        raw = graph_repo.list_nodes(page=1, limit=50)
        nodes = raw.get("items", []) if isinstance(raw, dict) else []
        total = raw.get("total", len(nodes)) if isinstance(raw, dict) else len(nodes)

        return JSONResponse(status_code=200, content={
            "status": "success",
            "message": "Graph data retrieved",
            "data": {
                "nodes": nodes,
                "total_nodes": total,
                "note": "Showing up to 50 nodes for dashboard preview",
            },
        })
    except Exception as e:
        logger.error("dashboard_graph_failed", error=str(e))
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": "Failed to retrieve graph data",
            "errors": {},
        })


# -----------------------------------------------
# Activity Timeline
# -----------------------------------------------

@router.get("/activity", summary="Recent activity timeline for dashboard")
async def get_dashboard_activity(
    document_svc: DocumentService = Depends(get_document_service),
) -> JSONResponse:
    """
    Return recent platform activity for the dashboard Activity Timeline widget.

    Derives activity from recent documents (uploads, status changes).
    No dedicated event log exists yet — uses document records as a proxy.
    """
    try:
        result = await document_svc.list_documents(page=1, limit=30)
        events = []
        for doc in result.documents:
            events.append({
                "event_type": "document_uploaded",
                "timestamp": doc.upload_time.isoformat(),
                "document_id": doc.id,
                "document_name": doc.original_filename,
                "status": doc.status,
                "detail": f"Document '{doc.original_filename}' uploaded ({doc.file_type.upper()})",
            })
            if doc.status == "completed":
                events.append({
                    "event_type": "processing_completed",
                    "timestamp": doc.upload_time.isoformat(),  # Best proxy — no updated_at in list
                    "document_id": doc.id,
                    "document_name": doc.original_filename,
                    "status": "completed",
                    "detail": f"Processing complete for '{doc.original_filename}'",
                })

        # Sort newest first
        events.sort(key=lambda x: x["timestamp"], reverse=True)

        return JSONResponse(status_code=200, content={
            "status": "success",
            "message": "Activity timeline retrieved",
            "data": {
                "events": events[:30],
                "total": len(events),
            },
        })
    except Exception as e:
        logger.error("dashboard_activity_failed", error=str(e))
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": "Failed to retrieve activity",
            "errors": {},
        })


# -----------------------------------------------
# Search Analytics (Placeholder)
# -----------------------------------------------

@router.get("/search", summary="Search analytics for dashboard")
async def get_dashboard_search() -> JSONResponse:
    """
    Return search analytics for the dashboard Search Analytics widget.

    NOTE: No persistent search analytics store exists in the current backend.
    This endpoint returns a structured placeholder response.
    When a search analytics service is added, this endpoint will delegate to it.
    """
    return JSONResponse(status_code=200, content={
        "status": "success",
        "message": "Search analytics retrieved",
        "data": {
            "total_searches": 0,
            "avg_response_ms": 0,
            "top_queries": [],
            "note": "Search analytics logging not yet implemented in backend",
        },
    })

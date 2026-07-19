"""
Health Check API

GET /api/v1/health

Checks connectivity to all external services:
- Backend (self)
- Supabase
- Neo4j
- Pinecone
- Gemini

Returns a comprehensive health report for monitoring.
"""

import time
from typing import Any, Dict
from fastapi import APIRouter, Depends
import structlog

from app.core.dependencies import get_supabase_client, get_neo4j_client, get_pinecone_client, get_llm_service
from app.database.supabase import SupabaseClient
from app.database.neo4j_client import Neo4jClient
from app.database.pinecone_client import PineconeClient
from app.ai.llm_service import LLMService
from app.utils.response import success_response, error_response

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health Check", description="Check connectivity to all external services")
async def health_check(
    supabase: SupabaseClient = Depends(get_supabase_client),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
    pinecone: PineconeClient = Depends(get_pinecone_client),
    llm: LLMService = Depends(get_llm_service),
) -> Dict[str, Any]:
    """
    Comprehensive health check for all platform services.

    Returns:
        Health status for each service
    """
    start_time = time.time()
    logger.info("health_check_start")

    services = {}
    overall_healthy = True

    # Check Supabase
    try:
        supabase_result = supabase.health_check()
        services["supabase"] = supabase_result["status"]
    except Exception as e:
        services["supabase"] = "down"
        overall_healthy = False
        logger.error("supabase_health_check_failed", error=str(e))

    # Check Neo4j
    try:
        neo4j_result = neo4j.health_check()
        services["neo4j"] = neo4j_result["status"]
    except Exception as e:
        services["neo4j"] = "down"
        overall_healthy = False
        logger.error("neo4j_health_check_failed", error=str(e))

    # Check Pinecone
    try:
        pinecone_result = pinecone.health_check()
        services["pinecone"] = pinecone_result["status"]
    except Exception as e:
        services["pinecone"] = "down"
        overall_healthy = False
        logger.error("pinecone_health_check_failed", error=str(e))

    # Check Gemini
    try:
        gemini_result = await llm.health_check()
        services["gemini"] = gemini_result["status"]
    except Exception as e:
        services["gemini"] = "down"
        overall_healthy = False
        logger.error("gemini_health_check_failed", error=str(e))

    duration = time.time() - start_time
    status = "healthy" if overall_healthy else "degraded"

    logger.info(
        "health_check_complete",
        status=status,
        services=services,
        duration_ms=round(duration * 1000, 2),
    )

    return {
        "status": status,
        "services": services,
        "duration_ms": round(duration * 1000, 2),
    }

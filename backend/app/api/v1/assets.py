"""
Assets API Router

Endpoints for Epic 9 — Asset Intelligence.

Routes:
    GET /assets          — Search/list assets (filterable)
    GET /assets/{id}     — Full Asset 360 profile

Per Memory.md §APIs: these endpoints were listed as planned
with no implementation — this file builds them for the first time.

Per Assets.md §Security:
    Internal graph identifiers are never exposed.
    Asset IDs in responses use the stable entity_id scheme.
"""

import structlog
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.core.dependencies import get_asset_service
from app.utils.response import success_response, error_response

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("", response_model=None)
async def list_assets(
    q: Optional[str] = Query(default=None, description="Free-text search across asset name"),
    asset_tag: Optional[str] = Query(default=None, description="Filter by asset tag"),
    equipment_id: Optional[str] = Query(default=None, description="Filter by equipment ID"),
    location: Optional[str] = Query(default=None, description="Filter by location"),
    department: Optional[str] = Query(default=None, description="Filter by department"),
    asset_type: Optional[str] = Query(default=None, description="Filter by asset type"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    asset_svc=Depends(get_asset_service),
):
    """
    List and search assets from the knowledge graph.

    Supports filtering by:
      - Asset Tag
      - Asset Name (q)
      - Equipment ID
      - Location
      - Department
      - Asset Type

    Returns a paginated list of AssetListItem objects.
    """
    try:
        result = await asset_svc.list_assets(
            q=q,
            asset_tag=asset_tag,
            equipment_id=equipment_id,
            location=location,
            department=department,
            asset_type=asset_type,
            page=page,
            limit=limit,
        )
        return success_response(
            data=result.model_dump(),
            message=f"Found {result.total} asset(s)",
        )

    except ValueError as e:
        logger.warning("assets_list_validation_error", error=str(e))
        return error_response(message=str(e), status_code=400)

    except Exception as e:
        logger.error("assets_list_failed", error=str(e))
        return error_response(
            message="Failed to retrieve asset list",
            status_code=500,
        )


@router.get("/{asset_id}", response_model=None)
async def get_asset_360(
    asset_id: str,
    asset_svc=Depends(get_asset_service),
):
    """
    Retrieve the full Asset 360 profile for a single asset.

    Returns:
        Structured Asset 360 profile containing:
          - asset: Core identity and properties
          - timeline: Chronological event history
          - relationships: Graph connections to other entities
          - documents: Related documents (via semantic search)
          - procedures: Active procedures
          - maintenance: Maintenance history
          - inspections: Inspection history
          - compliance: Compliance events
          - health_summary: Descriptive health snapshot

    Every field in the response carries source_document and confidence
    for full explainability traceability per Assets.md §Explainability.

    Returns 404 if the asset_id does not exist in the knowledge graph.
    """
    try:
        result = await asset_svc.get_asset_360(asset_id)
        return success_response(
            data=result.model_dump(),
            message=f"Asset 360 profile for {result.asset.entity_id}",
        )

    except ValueError as e:
        err_str = str(e)
        logger.warning("asset_360_not_found_or_invalid", asset_id=asset_id, error=err_str)

        # Distinguish between validation errors (400) and not-found (404)
        if "not found" in err_str.lower():
            return error_response(message=err_str, status_code=404)
        return error_response(message=err_str, status_code=400)

    except Exception as e:
        logger.error("asset_360_failed", asset_id=asset_id, error=str(e))
        return error_response(
            message="Failed to build Asset 360 profile",
            status_code=500,
        )

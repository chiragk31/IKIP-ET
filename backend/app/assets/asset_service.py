"""
Asset Service

Top-level orchestrator for the Asset Intelligence module.

Per Assets.md §Asset Pipeline:
    Asset Request → Graph Query → Metadata Lookup → Related Documents
    → Timeline Builder → Health Summary → Asset 360

Per Memory.md §Critical Rules:
    "This module is a pure aggregator. No new Neo4j Cypher, no new Pinecone
     calls, no new Supabase queries beyond metadata lookups explicitly described
     in Assets.md's Repository Layer diagram."

Per Memory.md §Notes for Future Agents:
    Structured logging (start/success/failure/duration) on every service method.

Caching:
    Simple in-memory TTL cache (AD-038). Cache key = entity_id.
    TTL = ASSET_CACHE_TTL_SECONDS (300s default).
    No Redis dependency — eviction is time-based only.
"""

import time
import asyncio
import structlog
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.assets.models import Asset360
from app.assets.schemas import (
    Asset360Response,
    AssetListResponse,
    AssetListItem,
    AssetNodeResponse,
    TimelineEventResponse,
    AssetRelationshipResponse,
    RelatedDocumentResponse,
    HealthSummaryResponse,
)
from app.assets.asset_builder import AssetBuilder
from app.assets.asset_repository import AssetRepository
from app.assets.asset_validator import AssetValidator
from app.assets.constants import ASSET_CACHE_TTL_SECONDS, ASSET_CACHE_MAX_SIZE

logger = structlog.get_logger(__name__)


class AssetService:
    """
    Top-level orchestrator for the Asset Intelligence pipeline.

    Purpose:
        Coordinate validation, parallel data fetching, profile assembly,
        caching, and API schema serialisation for all asset endpoints.
    Input:
        Raw user-supplied asset identifiers and search parameters.
    Output:
        Asset360Response or AssetListResponse Pydantic models.
    """

    def __init__(
        self,
        repository: AssetRepository,
        builder: AssetBuilder,
        validator: AssetValidator,
    ) -> None:
        """
        Initialize AssetService.

        Args:
            repository: Coordinates GraphRepository + HybridSearchService.
            builder: Assembles the Asset 360 profile from sub-builder outputs.
            validator: Validates and normalises all user-supplied input.
        """
        self._repo = repository
        self._builder = builder
        self._validator = validator

        # In-memory TTL cache: entity_id → (Asset360, cached_at_timestamp)
        # AD-038: simple dict-based TTL cache, evicted per request.
        self._cache: Dict[str, Tuple[Asset360, float]] = {}

        logger.info("asset_service_initialized")

    # ------------------------------------------------------------------
    # GET /assets/{id}  — Asset 360 profile
    # ------------------------------------------------------------------

    async def get_asset_360(self, raw_id: str) -> Asset360Response:
        """
        Build and return a full Asset 360 profile for the given asset ID.

        Pipeline:
          1. Validate + normalise the raw_id.
          2. Check in-memory TTL cache.
          3. Parallel fetch: GraphRepository (360 + neighbors) + HybridSearch.
          4. If graph returns no data → raise ValueError (404).
          5. AssetBuilder assembles the profile.
          6. Cache the result.
          7. Serialise to Asset360Response.

        Args:
            raw_id: Raw asset_id from the API route (may need normalisation).

        Returns:
            Asset360Response ready for the API endpoint.

        Raises:
            ValueError: If the asset_id is invalid or the asset is not found.
            Exception: For unexpected graph/search failures.
        """
        start_time = time.time()
        logger.info("asset_service_get_360_start", raw_id=raw_id)

        try:
            # Step 1: Validate and normalise
            entity_id = self._validator.validate_asset_id(raw_id)

            # Step 2: Cache check

            cached = self._get_from_cache(entity_id)
            if cached is not None:
                duration = time.time() - start_time
                cached.diagnostics["duration_seconds"] = round(duration, 3)
                logger.info(
                    "asset_service_cache_hit",
                    entity_id=entity_id,
                    duration=round(duration, 3),
                )
                return self._to_response(cached)

            # Step 3: Parallel fetch (graph + search concurrently)
            asset_360_data, neighbors, search_chunks = (
                await self._repo.fetch_asset_360_parallel(entity_id)
            )

            # Step 4: 404 guard — if no graph node exists, raise ValueError
            # This triggers a clean 404 at the API layer, not a silent
            # empty-but-200 response (same bug class as Epic 5 /status fix).
            if asset_360_data is None:
                logger.warning("asset_service_not_found", entity_id=entity_id)
                raise ValueError(f"Asset not found: {entity_id}")

            # Step 5: Build the profile
            profile = self._builder.build(
                entity_id=entity_id,
                asset_360_data=asset_360_data,
                neighbors=neighbors,
                search_chunks=search_chunks,
            )

            # Step 6: Cache
            duration = time.time() - start_time

            # Inject total pipeline duration into diagnostics now that we
            # know it — AssetBuilder.build() runs before this duration is
            # available, so diagnostics is patched here rather than there.
            profile.diagnostics["duration_seconds"] = round(duration, 3)

            # Step 6: Cache (cache the profile with duration already attached,
            # so cache hits also return a populated duration_seconds field —
            # see _get_from_cache path below for the cache-hit case)
            self._put_in_cache(entity_id, profile)

            logger.info(
                "asset_service_get_360_success",
                entity_id=entity_id,
                timeline_events=len(profile.timeline),
                relationships=len(profile.relationships),
                documents=len(profile.documents),
                duration=round(duration, 3),
            )

            # Step 7: Serialise
            return self._to_response(profile)

        except ValueError:
            # Re-raise validation errors and not-found errors as-is
            duration = time.time() - start_time
            logger.warning(
                "asset_service_get_360_not_found",
                raw_id=raw_id,
                duration=round(duration, 3),
            )
            raise
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "asset_service_get_360_failed",
                raw_id=raw_id,
                error=str(e),
                duration=round(duration, 3),
            )
            raise

    # ------------------------------------------------------------------
    # GET /assets  — asset list
    # ------------------------------------------------------------------

    async def list_assets(
        self,
        q: Optional[str] = None,
        asset_tag: Optional[str] = None,
        equipment_id: Optional[str] = None,
        location: Optional[str] = None,
        department: Optional[str] = None,
        asset_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> AssetListResponse:
        """
        Return a paginated, optionally filtered list of assets.

        Args:
            q: Free-text search (matched against name + aliases).
            asset_tag: Asset tag filter.
            equipment_id: Equipment ID filter.
            location: Location filter.
            department: Department filter.
            asset_type: Asset type filter.
            page: 1-indexed page number.
            limit: Items per page.

        Returns:
            AssetListResponse with paginated asset items.
        """
        start_time = time.time()
        logger.info(
            "asset_service_list_start",
            q=q,
            page=page,
            limit=limit,
        )

        try:
            # Validate search params
            params = self._validator.validate_search_params(
                q=q,
                asset_tag=asset_tag,
                equipment_id=equipment_id,
                location=location,
                department=department,
                asset_type=asset_type,
                page=page,
                limit=limit,
            )

            # Fetch from graph
            result = await self._repo.list_assets(
                page=params["page"],
                limit=params["limit"],
            )

            raw_items = result.get("items", [])
            total = result.get("total", 0)

            # Apply in-memory text filters (all optional)
            filtered = self._apply_list_filters(raw_items, params)

            # Serialise to list items
            items = [self._to_list_item(item) for item in filtered]

            pages = (total + limit - 1) // limit if limit > 0 else 0

            duration = time.time() - start_time
            logger.info(
                "asset_service_list_success",
                returned=len(items),
                total=total,
                duration=round(duration, 3),
            )

            return AssetListResponse(
                items=items,
                total=total,
                page=page,
                limit=limit,
                pages=pages,
            )

        except ValueError:
            raise
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "asset_service_list_failed",
                error=str(e),
                duration=round(duration, 3),
            )
            raise

    # ------------------------------------------------------------------
    # Cache helpers (AD-038)
    # ------------------------------------------------------------------

    def _get_from_cache(self, entity_id: str) -> Optional[Asset360]:
        """
        Retrieve an Asset360 from the in-memory TTL cache.

        Evicts the entry if it is expired (age > ASSET_CACHE_TTL_SECONDS).

        Args:
            entity_id: Asset entity_id.

        Returns:
            Cached Asset360, or None if not present / expired.
        """
        entry = self._cache.get(entity_id)
        if entry is None:
            return None

        profile, cached_at = entry
        age = time.time() - cached_at
        if age > ASSET_CACHE_TTL_SECONDS:
            del self._cache[entity_id]
            logger.debug("asset_cache_expired", entity_id=entity_id, age=round(age, 1))
            return None

        return profile

    def _put_in_cache(self, entity_id: str, profile: Asset360) -> None:
        """
        Store an Asset360 in the in-memory cache.

        Evicts the oldest entry if the cache is at capacity.

        Args:
            entity_id: Cache key.
            profile: Asset360 profile to cache.
        """
        if len(self._cache) >= ASSET_CACHE_MAX_SIZE:
            # Evict oldest entry
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
            logger.debug("asset_cache_evicted", evicted=oldest_key)

        self._cache[entity_id] = (profile, time.time())
        logger.debug("asset_cache_set", entity_id=entity_id)

    # ------------------------------------------------------------------
    # Schema serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_response(profile: Asset360) -> Asset360Response:
        """
        Serialise an Asset360 model to an Asset360Response API schema.

        Args:
            profile: Assembled Asset360 model.

        Returns:
            Asset360Response for API output.
        """
        asset = AssetNodeResponse(
            entity_id=profile.asset.entity_id,
            name=profile.asset.name,
            entity_type=profile.asset.entity_type,
            asset_tag=profile.asset.asset_tag,
            equipment_id=profile.asset.equipment_id,
            manufacturer=profile.asset.manufacturer,
            model=profile.asset.model,
            serial_number=profile.asset.serial_number,
            installation_date=profile.asset.installation_date,
            location=profile.asset.location,
            department=profile.asset.department,
            status=profile.asset.status,
            aliases=profile.asset.aliases,
            source_document=profile.asset.source_document,
            confidence=profile.asset.confidence,
            created_at=profile.asset.created_at,
        )

        timeline = [
            TimelineEventResponse(
                event_type=e.event_type,
                event_label=e.event_label,
                description=e.description,
                event_date=e.event_date,
                relationship_type=e.relationship_type,
                entity_id=e.entity_id,
                entity_name=e.entity_name,
                source_document=e.source_document,
                confidence=e.confidence,
            )
            for e in profile.timeline
        ]

        relationships = [
            AssetRelationshipResponse(
                relationship_type=r.relationship_type,
                relationship_category=r.relationship_category,
                direction=r.direction,
                target_entity_id=r.target_entity_id,
                target_name=r.target_name,
                target_label=r.target_label,
                source_document=r.source_document,
                confidence=r.confidence,
            )
            for r in profile.relationships
        ]

        documents = [
            RelatedDocumentResponse(
                document_id=d.document_id,
                document_name=d.document_name,
                document_type=d.document_type,
                section=d.section,
                page_number=d.page_number,
                excerpt=d.excerpt,
                chunk_id=d.chunk_id,
                confidence=d.confidence,
                source_type=d.source_type,
            )
            for d in profile.documents
        ]

        def _timeline_list(events):
            return [
                TimelineEventResponse(
                    event_type=e.event_type,
                    event_label=e.event_label,
                    description=e.description,
                    event_date=e.event_date,
                    relationship_type=e.relationship_type,
                    entity_id=e.entity_id,
                    entity_name=e.entity_name,
                    source_document=e.source_document,
                    confidence=e.confidence,
                )
                for e in events
            ]

        health = HealthSummaryResponse(
            maintenance_event_count=profile.health_summary.maintenance_event_count,
            failure_count=profile.health_summary.failure_count,
            inspection_count=profile.health_summary.inspection_count,
            compliance_event_count=profile.health_summary.compliance_event_count,
            maintenance_frequency=profile.health_summary.maintenance_frequency,
            failure_severity=profile.health_summary.failure_severity,
            inspection_status=profile.health_summary.inspection_status,
            compliance_status=profile.health_summary.compliance_status,
            recent_alerts=profile.health_summary.recent_alerts,
            contributing_documents=profile.health_summary.contributing_documents,
        )

        return Asset360Response(
            asset=asset,
            timeline=timeline,
            relationships=relationships,
            documents=documents,
            procedures=_timeline_list(profile.procedures),
            maintenance=_timeline_list(profile.maintenance),
            inspections=_timeline_list(profile.inspections),
            compliance=_timeline_list(profile.compliance),
            health_summary=health,
            diagnostics=profile.diagnostics,
        )

    @staticmethod
    def _to_list_item(raw_item: Dict[str, Any]) -> AssetListItem:
        """
        Convert a raw graph node dict to an AssetListItem.

        Args:
            raw_item: Dict from GraphRepository.list_nodes().

        Returns:
            AssetListItem for the paginated list response.
        """
        return AssetListItem(
            entity_id=raw_item.get("entity_id", ""),
            name=raw_item.get("name", ""),
            entity_type=raw_item.get("label", "Asset"),
            asset_tag=raw_item.get("asset_tag"),
            equipment_id=raw_item.get("equipment_id"),
            location=raw_item.get("location"),
            department=raw_item.get("department"),
            source_document=raw_item.get("source_document", ""),
            confidence=float(raw_item.get("confidence", 0.0) or 0.0),
        )

    @staticmethod
    def _apply_list_filters(
        items: list,
        params: Dict[str, Any],
    ) -> list:
        """
        Apply in-memory filters to the asset list.

        Args:
            items: List of raw node dicts.
            params: Validated search params from AssetValidator.

        Returns:
            Filtered list.
        """
        q = params.get("q")
        asset_tag = params.get("asset_tag")
        equipment_id = params.get("equipment_id")
        location = params.get("location")
        department = params.get("department")

        def _matches(item: Dict[str, Any]) -> bool:
            if q:
                name = (item.get("name") or "").lower()
                if q.lower() not in name:
                    return False
            if asset_tag:
                tag = (item.get("asset_tag") or "").lower()
                if asset_tag.lower() not in tag:
                    return False
            if equipment_id:
                eq = (item.get("equipment_id") or "").lower()
                if equipment_id.lower() not in eq:
                    return False
            if location:
                loc = (item.get("location") or "").lower()
                if location.lower() not in loc:
                    return False
            if department:
                dept = (item.get("department") or "").lower()
                if department.lower() not in dept:
                    return False
            return True

        return [item for item in items if _matches(item)]

"""
Asset Builder

Assembles the final Asset 360 profile from all sub-builder outputs.

Per Assets.md §Recommended Architecture Improvements (Mandatory):
    "Asset Builder Pattern — separate profile construction.
     Each builder should have one responsibility."

    Asset Service
        ↓
    Asset Builder
        ↓
    Timeline Builder
        ↓
    Relationship Builder
        ↓
    Health Builder
        ↓
    Asset Profile

This module is the assembly point — it calls each sub-builder in the
right order and collects their outputs into a single Asset360 model.
It performs NO data fetching of its own.
"""

import structlog
from typing import Any, Dict, List, Optional

from app.assets.models import Asset360, AssetNode, HealthSummary
from app.assets.asset_summary import SummaryBuilder
from app.assets.asset_relationships import RelationshipBuilder
from app.assets.asset_history import TimelineBuilder
from app.assets.asset_health import HealthBuilder
from app.search.models import ContextChunk

logger = structlog.get_logger(__name__)


class AssetBuilder:
    """
    Assembles the complete Asset 360 profile.

    Purpose:
        Coordinate all sub-builders (Summary, Relationships, Timeline, Health)
        and assemble their outputs into a single Asset360 model.
    Input:
        - entity_id: Validated asset entity_id.
        - asset_360_data: Raw dict from GraphRepository.get_asset_360().
        - neighbors: List of dicts from GraphRepository.get_neighbors().
        - search_chunks: ContextChunk list from HybridSearchService.
    Output:
        Asset360 model ready for API serialisation.
    """

    def __init__(self) -> None:
        """
        Initialize AssetBuilder with all sub-builders.

        Each sub-builder has exactly one responsibility per
        Assets.md's mandatory architecture pattern.
        """
        self._summary = SummaryBuilder()
        self._relationships = RelationshipBuilder()
        self._timeline = TimelineBuilder()
        self._health = HealthBuilder()
        logger.info("asset_builder_initialized")

    def build(
        self,
        entity_id: str,
        asset_360_data: Optional[Dict[str, Any]],
        neighbors: List[Dict[str, Any]],
        search_chunks: List[ContextChunk],
    ) -> Asset360:
        """
        Build the complete Asset 360 profile.

        Builder execution order:
          1. SummaryBuilder   → AssetNode + RelatedDocuments
          2. RelationshipBuilder → AssetRelationships
          3. TimelineBuilder  → TimelineEvents (chronologically sorted)
          4. HealthBuilder    → HealthSummary (descriptive only)

        The sub-builders run sequentially because 3 and 4 consume
        the output of 3 (timeline events) — they cannot be parallelised
        at this layer. The expensive I/O (graph + search fetches) was
        already parallelised upstream in AssetRepository.

        Args:
            entity_id: Validated asset entity_id.
            asset_360_data: Raw graph dict from GraphRepository.get_asset_360().
            neighbors: Neighbor dicts from GraphRepository.get_neighbors().
            search_chunks: ContextChunk list from HybridSearchService.

        Returns:
            Fully assembled Asset360 model.
        """
        logger.info(
            "asset_builder_start",
            entity_id=entity_id,
            neighbor_count=len(neighbors),
            chunk_count=len(search_chunks),
        )

        # 1. Build the core asset node (identity, properties, provenance)
        asset_node: AssetNode = self._summary.build_asset_node(
            entity_id=entity_id,
            asset_360_data=asset_360_data,
        )

        # 2. Build relationships from graph data
        relationships = self._relationships.build(
            asset_360_data=asset_360_data,
            neighbors=neighbors,
        )

        # 3. Build full chronological timeline
        #    Pass the raw asset node dict for the installation event
        raw_asset_dict = {}
        if asset_360_data:
            raw_a = asset_360_data.get("a")
            if isinstance(raw_a, dict):
                raw_asset_dict = raw_a
            elif raw_a is not None:
                try:
                    raw_asset_dict = dict(raw_a)
                except Exception:
                    raw_asset_dict = {}

        timeline = self._timeline.build(
            neighbors=neighbors,
            asset_360_data=asset_360_data,
            asset_node=raw_asset_dict,
        )

        # 4. Build health summary from timeline
        health: HealthSummary = self._health.build(
            timeline=timeline,
            neighbors=neighbors,
        )

        # 5. Build related documents from search results
        related_documents = self._summary.build_related_documents(search_chunks)

        # 6. Partition timeline into sub-categories for structured response
        maintenance_events = self._timeline.get_by_type(timeline, "maintenance")
        inspection_events = self._timeline.get_by_type(timeline, "inspection")
        compliance_events = self._timeline.get_by_type(timeline, "compliance")
        procedure_events = self._timeline.get_by_type(timeline, "procedure")

        profile = Asset360(
            asset=asset_node,
            timeline=timeline,
            relationships=relationships,
            documents=related_documents,
            procedures=procedure_events,
            maintenance=maintenance_events,
            inspections=inspection_events,
            compliance=compliance_events,
            health_summary=health,
            diagnostics={
                "neighbor_count": len(neighbors),
                "related_chunk_count": len(search_chunks),
                "relationship_count": len(relationships),
                "timeline_event_count": len(timeline),
                "entity_id": entity_id,
            },
        )

        logger.info(
            "asset_builder_complete",
            entity_id=entity_id,
            timeline_events=len(timeline),
            relationships=len(relationships),
            documents=len(related_documents),
        )
        return profile

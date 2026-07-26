"""
Asset Relationships Builder

Extracts and classifies graph relationships from neighbor node data.

Per Assets.md §Asset Relationships:
    Supported: Part Of, Connected To, Uses, Powered By, Controlled By,
               Monitored By, Maintained By, Inspected By.
    "These relationships are retrieved from Neo4j."

This builder operates purely on data already returned by
GraphRepository.get_neighbors() — it performs no additional queries.

Per Assets.md §Explainability:
    Every relationship carries source_document, confidence,
    and relationship_type so users can trace back to the originating document.
"""

import structlog
from typing import Any, Dict, List, Optional

from app.assets.models import AssetRelationship
from app.assets.constants import (
    RELATIONSHIP_TYPE_MAP,
    CONNECTED_ASSET_RELATIONSHIP_TYPES,
)

logger = structlog.get_logger(__name__)


class RelationshipBuilder:
    """
    Extracts typed relationships from graph neighbor data.

    Purpose:
        Classify raw Neo4j neighbor records into structured
        AssetRelationship objects with full provenance.
    Input:
        - asset_360_data: Dict from GraphRepository.get_asset_360()
          containing 'outgoing' and 'incoming' relationship lists.
        - neighbors: List of dicts from GraphRepository.get_neighbors().
    Output:
        List[AssetRelationship] for the Asset 360 profile.
    """

    def build(
        self,
        asset_360_data: Optional[Dict[str, Any]],
        neighbors: List[Dict[str, Any]],
    ) -> List[AssetRelationship]:
        """
        Build a list of AssetRelationship objects.

        asset_360_data (from get_asset_360) is the primary source: it carries
        real provenance (source_document, confidence) on every node. The
        neighbors list (from get_neighbors) carries accurate native Neo4j
        labels that asset_360_data's raw node dicts do not reliably expose,
        so it is used ONLY to backfill target_label, never to build
        relationship entries of its own — get_neighbors() returns no
        provenance fields at all (see NEIGHBOR_DISCOVERY_QUERY), so any
        relationship built from it alone would be permanently confidence=0.

        Deduplication is keyed by (target_entity_id, relationship_type) only
        — not direction. If the same target+type appears via both outgoing
        and incoming traversal (a genuine bidirectional edge in the graph),
        the entries are merged into one, preferring whichever side carries
        real provenance.

        Args:
            asset_360_data: Raw result from GraphRepository.get_asset_360().
            neighbors: Raw results from GraphRepository.get_neighbors().

        Returns:
            Deduplicated list of AssetRelationship objects, sorted by
            relationship_type for deterministic ordering.
        """
        logger.info(
            "relationship_builder_start",
            neighbor_count=len(neighbors),
        )

        # Label lookup: neighbor_id -> accurate native label (get_neighbors
        # returns this correctly via labels(neighbor)[0]; asset_360_data's
        # raw node dicts do not reliably carry a usable label field).
        label_lookup: Dict[str, str] = {
            r.get("neighbor_id", ""): r.get("neighbor_label", "")
            for r in neighbors
            if r.get("neighbor_id")
        }

        # Merge outgoing + incoming from asset_360_data, deduped by
        # (target_entity_id, relationship_type) — direction-agnostic.
        merged: Dict[tuple, AssetRelationship] = {}

        if asset_360_data:
            outgoing = asset_360_data.get("outgoing") or []
            incoming = asset_360_data.get("incoming") or []

            for direction, rel_list in (("outgoing", outgoing), ("incoming", incoming)):
                for item in rel_list:
                    rel = self._build_from_directional_item(item, direction, label_lookup)
                    if rel is None:
                        continue
                    key = (rel.target_entity_id, rel.relationship_type)
                    existing = merged.get(key)
                    # Prefer whichever entry carries real provenance
                    if existing is None or (existing.confidence == 0 and rel.confidence > 0):
                        merged[key] = rel

        relationships = list(merged.values())
        relationships.sort(key=lambda r: (r.relationship_type, r.target_name))

        logger.info(
            "relationship_builder_complete",
            relationships_built=len(relationships),
        )
        return relationships

    def get_connected_assets(
        self,
        relationships: List[AssetRelationship],
    ) -> List[AssetRelationship]:
        """
        Filter relationships to only those connecting peer assets.
        """
        return [
            r for r in relationships
            if r.relationship_type in CONNECTED_ASSET_RELATIONSHIP_TYPES
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_from_directional_item(
        self,
        item: Any,
        direction: str,
        label_lookup: Dict[str, str],
    ) -> Optional[AssetRelationship]:
        """
        Build a single AssetRelationship from one {rel, node} entry in
        asset_360_data's outgoing/incoming list.

        Args:
            item: Dict with keys 'rel' (rel_type) and 'node'.
            direction: 'outgoing' or 'incoming'.
            label_lookup: neighbor_id -> accurate native label, from
                get_neighbors(), used to backfill target_label since
                asset_360_data's node dicts don't reliably carry one.

        Returns:
            AssetRelationship, or None if the item is malformed.
        """
        if not isinstance(item, dict):
            return None

        rel_type = item.get("rel", "")
        node = item.get("node")

        if not rel_type or node is None:
            return None

        if isinstance(node, dict):
            props = node
        else:
            try:
                props = dict(node)
            except Exception:
                return None

        target_id = props.get("entity_id", "")
        if not target_id:
            return None

        target_name = props.get("name", "")
        # Prefer the accurate label from get_neighbors(); fall back to the
        # entity_type property (AD-021 defense-in-depth field) if present.
        target_label = label_lookup.get(target_id) or props.get("entity_type", "")
        source_doc = props.get("source_document", "")
        confidence = self._safe_float(props.get("confidence", 0.0))

        category = RELATIONSHIP_TYPE_MAP.get(rel_type, "related")

        return AssetRelationship(
            relationship_type=rel_type,
            relationship_category=category,
            direction=direction,
            target_entity_id=target_id,
            target_name=target_name,
            target_label=target_label,
            source_document=source_doc,
            confidence=confidence,
        )

    @staticmethod
    def _safe_float(val: Any) -> float:
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0
    @staticmethod
    def _extract_source_doc(record: Dict[str, Any]) -> str:
        """Extract source_document from a neighbor record (best-effort)."""
        return record.get("source_document", "")

    @staticmethod
    def _extract_confidence(record: Dict[str, Any]) -> float:
        """Extract confidence from a neighbor record (best-effort)."""
        val = record.get("confidence", 0.0)
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

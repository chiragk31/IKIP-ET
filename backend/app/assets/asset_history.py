"""
Asset History / Timeline Builder

Extracts chronological events from graph data.

Per Assets.md §Asset Timeline:
    "Timeline includes: Installation, Inspections, Maintenance, Failures,
     Repairs, Replacements, Compliance Audits.
     Timeline should be displayed chronologically."

Per Assets.md §Explainability:
    Every event carries source_document, confidence, and relationship_type.

PROVENANCE FIX (see RelationshipBuilder docstring for the same issue):
    NEIGHBOR_DISCOVERY_QUERY (used to build `neighbors`) never selects
    source_document/confidence — it structurally cannot carry provenance.
    This builder now sources events primarily from `asset_360_data`
    (ASSET_360_QUERY's outgoing/incoming lists, which return full node
    property maps including source_document/confidence), mirroring the
    fix already applied to RelationshipBuilder. `neighbors` is used ONLY
    to backfill accurate native Neo4j labels via label_lookup, since
    asset_360_data's raw node dicts don't reliably expose one.
"""

import structlog
from typing import Any, Dict, List, Optional

from app.assets.models import TimelineEvent
from app.assets.constants import (
    TIMELINE_EVENT_LABELS,
    MAINTENANCE_RELATIONSHIP_TYPES,
    FAILURE_RELATIONSHIP_TYPES,
    INSPECTION_RELATIONSHIP_TYPES,
    COMPLIANCE_RELATIONSHIP_TYPES,
)

logger = structlog.get_logger(__name__)


class TimelineBuilder:
    """
    Builds a chronological event timeline from graph data.

    Purpose:
        Transform asset_360_data (primary, carries provenance) and
        neighbors (label backfill only) into a sorted list of
        TimelineEvent objects for display and partitioning.
    Input:
        - asset_360_data: Dict from GraphRepository.get_asset_360()
          containing 'outgoing' and 'incoming' relationship lists with
          full node property maps (source_document, confidence, etc.)
        - neighbors: List of dicts from GraphRepository.get_neighbors()
          — used ONLY for accurate neighbor_label backfill.
        - asset_node: The raw asset node dict (for installation event).
    Output:
        Chronologically sorted List[TimelineEvent].
    """

    def build(
        self,
        neighbors: List[Dict[str, Any]],
        asset_360_data: Optional[Dict[str, Any]] = None,
        asset_node: Optional[Dict[str, Any]] = None,
    ) -> List[TimelineEvent]:
        """
        Build a chronological timeline from graph data.

        Includes an 'installation' event if the asset node itself has
        an installation_date or created_at property.

        Args:
            neighbors: List of dicts from GraphRepository.get_neighbors().
                Used only to backfill accurate neighbor_label.
            asset_360_data: Raw result from GraphRepository.get_asset_360().
                Primary source of events — carries real provenance.
            asset_node: The raw asset node dict (for installation event).

        Returns:
            Chronologically sorted List[TimelineEvent] (None dates last).
        """
        logger.info(
            "timeline_builder_start",
            neighbor_count=len(neighbors),
            has_asset_360=asset_360_data is not None,
        )

        events: List[TimelineEvent] = []

        # --- Installation event from the asset node itself ---
        if asset_node:
            install_event = self._build_installation_event(asset_node)
            if install_event:
                events.append(install_event)

        # --- Label lookup: neighbor_id -> accurate native label ---
        # (get_neighbors() returns this correctly via labels(neighbor)[0];
        #  asset_360_data's raw node dicts do not reliably carry one.)
        label_lookup: Dict[str, str] = {
            r.get("neighbor_id", ""): r.get("neighbor_label", "")
            for r in neighbors
            if r.get("neighbor_id")
        }

        # --- Events from asset_360_data (primary source — has provenance) ---
        seen_entity_ids: set = set()

        if asset_360_data:
            outgoing = asset_360_data.get("outgoing") or []
            incoming = asset_360_data.get("incoming") or []

            for direction, rel_list in (("outgoing", outgoing), ("incoming", incoming)):
                for item in rel_list:
                    event = self._build_from_directional_item(
                        item, direction, label_lookup, seen_entity_ids
                    )
                    if event is not None:
                        events.append(event)

        # Sort chronologically — events with dates first (ascending),
        # events without dates last
        events.sort(key=self._sort_key)

        logger.info(
            "timeline_builder_complete",
            event_count=len(events),
        )
        return events

    def get_by_type(
        self,
        events: List[TimelineEvent],
        event_type: str,
    ) -> List[TimelineEvent]:
        """
        Filter timeline events by their event_type category.

        Used by AssetBuilder to partition events into maintenance,
        inspections, compliance, and procedures sub-lists.

        Args:
            events: Full timeline event list.
            event_type: Category to filter by (e.g. 'maintenance').

        Returns:
            Filtered list of matching TimelineEvent objects.
        """
        return [e for e in events if e.event_type == event_type]

    # ------------------------------------------------------------------
    # Private classification helpers
    # ------------------------------------------------------------------

    def _build_from_directional_item(
        self,
        item: Any,
        direction: str,
        label_lookup: Dict[str, str],
        seen_entity_ids: set,
    ) -> Optional[TimelineEvent]:
        """
        Build a single TimelineEvent from one {rel, node} entry in
        asset_360_data's outgoing/incoming list.

        Args:
            item: Dict with keys 'rel' (rel_type) and 'node' (full props).
            direction: 'outgoing' or 'incoming' (unused for classification,
                kept for symmetry with RelationshipBuilder / future use).
            label_lookup: neighbor_id -> accurate native label.
            seen_entity_ids: Mutated in place to dedupe across both
                outgoing and incoming passes (same node reached via two
                relationship types must only produce one timeline entry).

        Returns:
            TimelineEvent, or None if malformed / not a timeline-relevant
            label / already seen.
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

        entity_id = props.get("entity_id", "")
        if not entity_id or entity_id in seen_entity_ids:
            return None

        neighbor_label = label_lookup.get(entity_id) or props.get("entity_type", "")
        if neighbor_label not in TIMELINE_EVENT_LABELS:
            return None

        seen_entity_ids.add(entity_id)

        event_type = self._resolve_event_type(neighbor_label, rel_type)

        return TimelineEvent(
            event_type=event_type,
            event_label=neighbor_label,
            description=props.get("name", ""),
            event_date=self._extract_date(props),
            relationship_type=rel_type,
            entity_id=entity_id,
            entity_name=props.get("name", ""),
            source_document=props.get("source_document", ""),
            confidence=self._safe_float(props.get("confidence", 0.0)),
        )

    @staticmethod
    def _resolve_event_type(neighbor_label: str, rel_type: str) -> str:
        """
        Resolve event_type from label and relationship.

        Args:
            neighbor_label: Neo4j node label.
            rel_type: Neo4j relationship type.

        Returns:
            Event type string.
        """
        if neighbor_label == "Measurement":
            return "measurement"
        if neighbor_label == "Failure" or rel_type in FAILURE_RELATIONSHIP_TYPES:
            return "failure"
        if rel_type in MAINTENANCE_RELATIONSHIP_TYPES:
            return "maintenance"
        if rel_type in INSPECTION_RELATIONSHIP_TYPES and neighbor_label == "Event":
            return "inspection"
        if rel_type in COMPLIANCE_RELATIONSHIP_TYPES:
            return "compliance"
        if neighbor_label == "Procedure":
            return "procedure"
        
        return "event"

    def _build_installation_event(
        self,
        asset_node: Dict[str, Any],
    ) -> Optional[TimelineEvent]:
        """
        Build an 'installation' TimelineEvent from the asset node itself.

        Args:
            asset_node: Raw asset node dict.

        Returns:
            TimelineEvent for installation, or None if no date available.
        """
        install_date = (
            asset_node.get("installation_date")
            or asset_node.get("created_at")
        )

        if not install_date:
            return None

        return TimelineEvent(
            event_type="installation",
            event_label="Asset",
            description=f"Asset {asset_node.get('name', '')} installed / first recorded",
            event_date=str(install_date)[:10] if install_date else None,
            relationship_type="",
            entity_id=asset_node.get("entity_id", ""),
            entity_name=asset_node.get("name", ""),
            source_document=asset_node.get("source_document", ""),
            confidence=self._safe_float(asset_node.get("confidence", 0.0)),
        )

    @staticmethod
    def _extract_date(record: Dict[str, Any]) -> Optional[str]:
        """
        Attempt to extract an ISO date from a node property dict.

        Args:
            record: Raw node properties dict.

        Returns:
            ISO 8601 date string (first 10 chars), or None.
        """
        for key in ("event_date", "date", "created_at", "occurred_at"):
            val = record.get(key)
            if val and isinstance(val, str) and len(val) >= 10:
                return val[:10]
        return None

    @staticmethod
    def _sort_key(event: TimelineEvent):
        """
        Sort key: dated events ascending, None-dated events last.

        Args:
            event: TimelineEvent to sort.

        Returns:
            Tuple for comparison: (has_no_date, date_str).
        """
        return (event.event_date is None, event.event_date or "")

    @staticmethod
    def _safe_float(val: Any) -> float:
        """Safely convert a value to float, returning 0.0 on failure."""
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0
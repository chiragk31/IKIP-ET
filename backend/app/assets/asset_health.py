"""
Asset Health Builder

Produces a descriptive health summary from graph event data.

Per Assets.md §Asset Health Summary:
    "Health summary combines: Maintenance Frequency, Failure Count,
     Inspection Status, Compliance Status, Recent Alerts.
     This is descriptive only.
     Predictive analytics belongs to future versions."

Per Assets.md §Future Enhancements:
    RUL, Failure Probability, Sensor Integration → future scope.
    NONE of those fields appear here.

This builder operates purely on already-fetched data — no graph queries.
"""

import structlog
from typing import Any, Dict, List, Optional

from app.assets.models import HealthSummary, TimelineEvent
from app.assets.constants import (
    MAINTENANCE_FREQ_HIGH_THRESHOLD,
    MAINTENANCE_FREQ_MED_THRESHOLD,
    FAILURE_COUNT_HIGH_THRESHOLD,
    FAILURE_COUNT_MED_THRESHOLD,
    MAINTENANCE_FREQ_HIGH,
    MAINTENANCE_FREQ_MED,
    MAINTENANCE_FREQ_LOW,
    FAILURE_SEVERITY_HIGH,
    FAILURE_SEVERITY_MED,
    FAILURE_SEVERITY_NONE,
)

logger = structlog.get_logger(__name__)


class HealthBuilder:
    """
    Builds a descriptive-only health summary from timeline event data.

    Purpose:
        Derive a human-readable health snapshot from historical graph events.
        Strictly descriptive — no predictions, no sensor data, no ML output.
    Input:
        - timeline: Full list of TimelineEvent objects (from TimelineBuilder).
        - neighbors: Raw neighbor dicts (for recent alert extraction).
    Output:
        HealthSummary model — the 'health_summary' field in Asset360.
    """

    def build(
        self,
        timeline: List[TimelineEvent],
        neighbors: List[Dict[str, Any]],
    ) -> HealthSummary:
        """
        Build a descriptive health summary.

        Args:
            timeline: Full chronological event list from TimelineBuilder.
            neighbors: Raw neighbor dicts from GraphRepository.get_neighbors().

        Returns:
            HealthSummary with descriptive fields only.
        """
        logger.info(
            "health_builder_start",
            event_count=len(timeline),
            neighbor_count=len(neighbors),
        )

        # Count events by type
        maintenance_count = sum(1 for e in timeline if e.event_type == "maintenance")
        failure_count = sum(1 for e in timeline if e.event_type == "failure")
        inspection_count = sum(1 for e in timeline if e.event_type == "inspection")
        compliance_count = sum(1 for e in timeline if e.event_type == "compliance")

        # Collect contributing documents (provenance)
        contributing_docs: List[str] = list(
            {e.source_document for e in timeline if e.source_document}
        )

        # Descriptive labels
        maintenance_frequency = self._classify_maintenance_frequency(maintenance_count)
        failure_severity = self._classify_failure_severity(failure_count)
        inspection_status = self._classify_inspection_status(inspection_count)
        compliance_status = self._classify_compliance_status(compliance_count)

        # Recent alerts: Risk and Failure neighbor node names (last 5)
        recent_alerts = self._extract_recent_alerts(neighbors)

        health = HealthSummary(
            maintenance_event_count=maintenance_count,
            failure_count=failure_count,
            inspection_count=inspection_count,
            compliance_event_count=compliance_count,
            maintenance_frequency=maintenance_frequency,
            failure_severity=failure_severity,
            inspection_status=inspection_status,
            compliance_status=compliance_status,
            recent_alerts=recent_alerts,
            contributing_documents=contributing_docs,
        )

        logger.info(
            "health_builder_complete",
            maintenance_frequency=maintenance_frequency,
            failure_severity=failure_severity,
            inspection_status=inspection_status,
            compliance_status=compliance_status,
            alert_count=len(recent_alerts),
        )
        return health

    # ------------------------------------------------------------------
    # Descriptive classifiers (NO predictive logic)
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_maintenance_frequency(count: int) -> str:
        """
        Classify maintenance frequency from event count.

        This is a descriptive label based on historical count —
        it is NOT a prediction of future maintenance needs.

        Args:
            count: Number of maintenance events in the timeline.

        Returns:
            'high' | 'moderate' | 'low'
        """
        if count > MAINTENANCE_FREQ_HIGH_THRESHOLD:
            return MAINTENANCE_FREQ_HIGH
        if count >= MAINTENANCE_FREQ_MED_THRESHOLD:
            return MAINTENANCE_FREQ_MED
        return MAINTENANCE_FREQ_LOW

    @staticmethod
    def _classify_failure_severity(count: int) -> str:
        """
        Classify failure severity from failure count.

        Descriptive only — based on recorded historical failures
        in the graph, not a forward-looking failure probability.

        Args:
            count: Number of failure events in the timeline.

        Returns:
            'high' | 'moderate' | 'none'
        """
        if count > FAILURE_COUNT_HIGH_THRESHOLD:
            return FAILURE_SEVERITY_HIGH
        if count >= FAILURE_COUNT_MED_THRESHOLD:
            return FAILURE_SEVERITY_MED
        return FAILURE_SEVERITY_NONE

    @staticmethod
    def _classify_inspection_status(inspection_count: int) -> str:
        """
        Classify inspection status from the presence of inspection events.

        'current' = at least one inspection event exists in the graph.
        'unknown' = no inspection data available.

        Note: 'overdue' would require a date comparison against an
        inspection schedule — that data is not currently in the graph,
        so we degrade gracefully to 'unknown' rather than guessing.

        Args:
            inspection_count: Number of inspection events in the timeline.

        Returns:
            'current' | 'unknown'
        """
        if inspection_count > 0:
            return "current"
        return "unknown"

    @staticmethod
    def _classify_compliance_status(compliance_count: int) -> str:
        """
        Classify compliance status from the presence of compliance events.

        'compliant' = compliance events (requirements/mitigations) exist in graph.
        'unknown' = no compliance data in the graph.

        Note: True compliance determination requires auditing compliance
        event outcomes — that detail is not currently surfaced by the graph
        queries used here. We degrade gracefully.

        Args:
            compliance_count: Number of compliance events in the timeline.

        Returns:
            'compliant' | 'unknown'
        """
        if compliance_count > 0:
            return "compliant"
        return "unknown"

    @staticmethod
    def _extract_recent_alerts(
        neighbors: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Extract recent alert names from Risk and Failure neighbor nodes.

        Per Assets.md §Asset Health Summary: "Recent Alerts" — these
        are the names of Risk and Failure nodes connected to the asset,
        representing documented concerns in the knowledge graph.

        Args:
            neighbors: Raw neighbor dicts from GraphRepository.get_neighbors().

        Returns:
            List of up to 5 alert names (node names), most recent first
            if ordering information is available.
        """
        alert_labels = {"Risk", "Failure"}
        alerts: List[str] = []

        for record in neighbors:
            if record.get("neighbor_label") in alert_labels:
                name = record.get("neighbor_name", "")
                if name and name not in alerts:
                    alerts.append(name)

        return alerts[:5]

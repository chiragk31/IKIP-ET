"""
Asset Intelligence Tests

Unit tests for Epic 9 — Asset Intelligence module.

Per Memory.md §Notes for Future Agents:
    "Do not trust 'all tests pass' alone as proof a live-integration
     module actually works."
    These tests confirm correctness of logic in isolation using mocks.
    Live verification is performed separately against the real Neo4j
    and Pinecone instances.

Coverage:
  - Asset identity resolution (tag/equipment ID/UUID priority)
  - Timeline chronological ordering
  - Health summary is descriptive-only (no predictive fields)
  - Relationship retrieval and classification
  - Response shape validation (must match Assets.md §Asset 360 Response)
  - AssetValidator: valid IDs, bad IDs, auto-prefix
  - 404 guard: AssetService raises ValueError for unknown assets
  - Cache: second call returns cached result
"""

import asyncio
import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from app.assets.asset_validator import AssetValidator
from app.assets.asset_relationships import RelationshipBuilder
from app.assets.asset_history import TimelineBuilder
from app.assets.asset_health import HealthBuilder
from app.assets.asset_summary import SummaryBuilder
from app.assets.asset_builder import AssetBuilder
from app.assets.asset_service import AssetService
from app.assets.asset_repository import AssetRepository
from app.assets.models import (
    AssetNode,
    AssetRelationship,
    TimelineEvent,
    HealthSummary,
    RelatedDocument,
    Asset360,
)
from app.assets.schemas import Asset360Response
from app.assets.constants import (
    ASSET_ENTITY_ID_PREFIX,
    ASSET_CACHE_TTL_SECONDS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_neighbor(
    neighbor_id: str,
    neighbor_name: str,
    neighbor_label: str,
    relationship: str,
    source_document: str = "doc1.pdf",
    confidence: float = 0.9,
) -> Dict[str, Any]:
    """Helper: build a neighbor record dict matching get_neighbors() output."""
    return {
        "node_id": "asset_p101",
        "node_name": "Pump P101",
        "relationship": relationship,
        "neighbor_id": neighbor_id,
        "neighbor_name": neighbor_name,
        "neighbor_label": neighbor_label,
        "source_document": source_document,
        "confidence": confidence,
    }


def _make_asset_360_data(entity_id: str = "asset_p101") -> Dict[str, Any]:
    """Helper: build an asset_360_data dict matching get_asset_360() output."""
    return {
        "a": {
            "entity_id": entity_id,
            "name": "Pump P101",
            "entity_type": "Asset",
            "asset_tag": "P-101",
            "equipment_id": "EQ-2024-001",
            "location": "Pump House A",
            "department": "Operations",
            "source_document": "maintenance_report_12.pdf",
            "confidence": 0.97,
            "created_at": "2024-01-01T00:00:00Z",
        },
        "outgoing": [],
        "incoming": [],
    }


# ---------------------------------------------------------------------------
# AssetValidator
# ---------------------------------------------------------------------------

class TestAssetValidator:
    """Tests for AssetValidator input validation."""

    def setup_method(self):
        self.validator = AssetValidator()

    def test_valid_entity_id_passes(self):
        """A well-formed entity_id passes through unchanged."""
        result = self.validator.validate_asset_id("asset_p101")
        assert result == "asset_p101"

    def test_auto_prefix_added(self):
        """ID without 'asset_' prefix gets the prefix added automatically."""
        result = self.validator.validate_asset_id("p101")
        assert result == "asset_p101"

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped before validation."""
        result = self.validator.validate_asset_id("  asset_p101  ")
        assert result == "asset_p101"

    def test_uppercase_lowercased(self):
        """Input is normalised to lowercase."""
        result = self.validator.validate_asset_id("ASSET_P101")
        assert result == "asset_p101"

    def test_empty_id_raises(self):
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            self.validator.validate_asset_id("")

    def test_whitespace_only_raises(self):
        """Whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            self.validator.validate_asset_id("   ")

    def test_too_long_raises(self):
        """ID exceeding max length raises ValueError."""
        long_id = "x" * 200
        with pytest.raises(ValueError, match="maximum length"):
            self.validator.validate_asset_id(long_id)

    def test_invalid_characters_raise(self):
        """Special characters raise ValueError."""
        with pytest.raises(ValueError, match="invalid characters"):
            self.validator.validate_asset_id("asset_p101; DROP TABLE assets")

    def test_hyphen_and_underscore_allowed(self):
        """Hyphens and underscores are valid in entity_ids."""
        result = self.validator.validate_asset_id("asset_pump-101_a")
        assert result == "asset_pump-101_a"

    def test_search_params_validated(self):
        """Valid search params return a validated dict."""
        params = self.validator.validate_search_params(
            q="pump",
            asset_tag="P-101",
            equipment_id=None,
            location=None,
            department=None,
            asset_type=None,
            page=1,
            limit=20,
        )
        assert params["q"] == "pump"
        assert params["asset_tag"] == "P-101"
        assert params["page"] == 1
        assert params["limit"] == 20

    def test_invalid_page_raises(self):
        """page < 1 raises ValueError."""
        with pytest.raises(ValueError, match="Page"):
            self.validator.validate_search_params(
                q=None, asset_tag=None, equipment_id=None,
                location=None, department=None, asset_type=None,
                page=0, limit=20,
            )


# ---------------------------------------------------------------------------
# RelationshipBuilder
# ---------------------------------------------------------------------------

class TestRelationshipBuilder:
    """Tests for relationship extraction and classification."""

    def setup_method(self):
        self.builder = RelationshipBuilder()

    def test_relationships_extracted_from_neighbors(self):
        """Relationships are built from neighbor records."""
        neighbors = [
            _make_neighbor("asset_p102", "Pump P102", "Asset", "CONNECTED_TO"),
            _make_neighbor("loc_001", "Pump House A", "Location", "LOCATED_IN"),
        ]
        relationships = self.builder.build(asset_360_data=None, neighbors=neighbors)
        assert len(relationships) == 2

    def test_relationship_provenance_preserved(self):
        """source_document and confidence are carried through from graph data."""
        neighbors = [
            _make_neighbor(
                "asset_p102", "Pump P102", "Asset", "CONNECTED_TO",
                source_document="pipe_diagram.pdf", confidence=0.85,
            )
        ]
        relationships = self.builder.build(asset_360_data=None, neighbors=neighbors)
        rel = relationships[0]
        assert rel.source_document == "pipe_diagram.pdf"
        assert rel.confidence == pytest.approx(0.85)

    def test_relationship_type_preserved(self):
        """relationship_type matches the Neo4j relationship type."""
        neighbors = [_make_neighbor("fail_001", "Bearing Failure", "Failure", "HAS_FAILURE")]
        relationships = self.builder.build(asset_360_data=None, neighbors=neighbors)
        assert relationships[0].relationship_type == "HAS_FAILURE"

    def test_duplicate_neighbors_deduplicated(self):
        """Same (target_id, rel_type) pair appears only once."""
        neighbor = _make_neighbor("asset_p102", "Pump P102", "Asset", "CONNECTED_TO")
        relationships = self.builder.build(
            asset_360_data=None,
            neighbors=[neighbor, neighbor],   # duplicate
        )
        assert len(relationships) == 1

    def test_connected_assets_filter(self):
        """get_connected_assets() filters to peer-asset relationship types only."""
        neighbors = [
            _make_neighbor("asset_p102", "Pump P102", "Asset", "CONNECTED_TO"),
            _make_neighbor("loc_001", "Pump House A", "Location", "LOCATED_IN"),
            _make_neighbor("asset_p103", "Pump P103", "Asset", "PART_OF"),
        ]
        relationships = self.builder.build(asset_360_data=None, neighbors=neighbors)
        connected = self.builder.get_connected_assets(relationships)
        assert all(r.relationship_type in {"CONNECTED_TO", "PART_OF", "USES"} for r in connected)


# ---------------------------------------------------------------------------
# TimelineBuilder
# ---------------------------------------------------------------------------

class TestTimelineBuilder:
    """Tests for timeline event extraction and chronological ordering."""

    def setup_method(self):
        self.builder = TimelineBuilder()

    def test_failure_events_classified_correctly(self):
        """Failure-labeled neighbors are classified as 'failure' events."""
        neighbors = [
            _make_neighbor("fail_001", "Bearing Failure 2024", "Failure", "HAS_FAILURE")
        ]
        timeline = self.builder.build(neighbors=neighbors)
        assert len(timeline) == 1
        assert timeline[0].event_type == "failure"

    def test_procedure_events_classified_correctly(self):
        """Procedure-labeled neighbors are classified as 'procedure' events."""
        neighbors = [
            _make_neighbor("proc_001", "PM-001 Procedure", "Procedure", "REQUIRES")
        ]
        timeline = self.builder.build(neighbors=neighbors)
        assert len(timeline) == 1
        assert timeline[0].event_type in ("procedure", "compliance")

    def test_non_event_labels_excluded(self):
        """Asset and Location neighbors are not timeline events."""
        neighbors = [
            _make_neighbor("asset_p102", "Pump P102", "Asset", "CONNECTED_TO"),
            _make_neighbor("loc_001", "Pump House", "Location", "LOCATED_IN"),
        ]
        timeline = self.builder.build(neighbors=neighbors)
        assert len(timeline) == 0

    def test_timeline_chronologically_ordered(self):
        """Events with dates are sorted in ascending chronological order."""
        neighbors = [
            {**_make_neighbor("evt_003", "Event 3", "Event", "INVOLVES"), "event_date": "2024-03-01"},
            {**_make_neighbor("evt_001", "Event 1", "Event", "INVOLVES"), "event_date": "2024-01-01"},
            {**_make_neighbor("evt_002", "Event 2", "Event", "INVOLVES"), "event_date": "2024-02-01"},
        ]
        timeline = self.builder.build(neighbors=neighbors)
        dates = [e.event_date for e in timeline if e.event_date]
        assert dates == sorted(dates)

    def test_events_without_dates_sorted_last(self):
        """Events without dates appear after dated events."""
        neighbors = [
            {**_make_neighbor("evt_001", "Dated Event", "Event", "INVOLVES"), "event_date": "2024-01-01"},
            _make_neighbor("evt_002", "Undated Event", "Failure", "HAS_FAILURE"),  # no date key
        ]
        timeline = self.builder.build(neighbors=neighbors)
        # Find position of None-date event
        none_date_positions = [i for i, e in enumerate(timeline) if e.event_date is None]
        dated_positions = [i for i, e in enumerate(timeline) if e.event_date is not None]
        if none_date_positions and dated_positions:
            assert min(none_date_positions) > max(dated_positions)

    def test_event_provenance_preserved(self):
        """source_document and confidence are carried through."""
        neighbors = [
            {
                **_make_neighbor(
                    "fail_001", "Pump Failure", "Failure", "HAS_FAILURE",
                    source_document="incident_report.pdf", confidence=0.92,
                ),
                "event_date": "2024-06-15",
            }
        ]
        timeline = self.builder.build(neighbors=neighbors)
        evt = timeline[0]
        assert evt.source_document == "incident_report.pdf"
        assert evt.confidence == pytest.approx(0.92)

    def test_get_by_type_filters_correctly(self):
        """get_by_type() returns only matching events."""
        timeline = [
            TimelineEvent(event_type="maintenance", event_label="Event", entity_id="e1"),
            TimelineEvent(event_type="failure", event_label="Failure", entity_id="e2"),
            TimelineEvent(event_type="maintenance", event_label="Event", entity_id="e3"),
        ]
        maintenance = self.builder.get_by_type(timeline, "maintenance")
        assert len(maintenance) == 2
        assert all(e.event_type == "maintenance" for e in maintenance)


# ---------------------------------------------------------------------------
# HealthBuilder
# ---------------------------------------------------------------------------

class TestHealthBuilder:
    """Tests for descriptive health summary generation."""

    def setup_method(self):
        self.builder = HealthBuilder()

    def test_health_summary_has_no_predictive_fields(self):
        """HealthSummary must NOT contain RUL, failure_probability, or similar."""
        health_fields = set(HealthSummary.model_fields.keys())
        forbidden_predictive_fields = {
            "remaining_useful_life",
            "rul",
            "failure_probability",
            "predicted_failure_date",
            "mtbf",
            "mttr",
            "health_score",
            "risk_score",
        }
        intersection = health_fields & forbidden_predictive_fields
        assert intersection == set(), (
            f"HealthSummary must not contain predictive fields: {intersection}"
        )

    def test_high_maintenance_frequency_classified(self):
        """More than MAINTENANCE_FREQ_HIGH_THRESHOLD events → 'high'."""
        timeline = [
            TimelineEvent(event_type="maintenance", event_label="Event", entity_id=f"e{i}")
            for i in range(8)   # 8 > threshold of 5
        ]
        health = self.builder.build(timeline=timeline, neighbors=[])
        assert health.maintenance_frequency == "high"

    def test_low_maintenance_frequency_classified(self):
        """Fewer than 2 events → 'low'."""
        timeline = [
            TimelineEvent(event_type="maintenance", event_label="Event", entity_id="e1")
        ]
        health = self.builder.build(timeline=timeline, neighbors=[])
        assert health.maintenance_frequency == "low"

    def test_failure_count_tracked(self):
        """failure_count reflects actual failure events in timeline."""
        timeline = [
            TimelineEvent(event_type="failure", event_label="Failure", entity_id="f1"),
            TimelineEvent(event_type="failure", event_label="Failure", entity_id="f2"),
        ]
        health = self.builder.build(timeline=timeline, neighbors=[])
        assert health.failure_count == 2

    def test_failure_severity_none_when_no_failures(self):
        """Zero failures → failure_severity = 'none'."""
        health = self.builder.build(timeline=[], neighbors=[])
        assert health.failure_severity == "none"

    def test_recent_alerts_from_risk_nodes(self):
        """Risk neighbor node names appear in recent_alerts."""
        neighbors = [
            _make_neighbor("risk_001", "High Vibration Alert", "Risk", "MITIGATED_BY"),
            _make_neighbor("risk_002", "High Temperature", "Risk", "MITIGATED_BY"),
        ]
        health = self.builder.build(timeline=[], neighbors=neighbors)
        assert "High Vibration Alert" in health.recent_alerts
        assert "High Temperature" in health.recent_alerts

    def test_alerts_capped_at_five(self):
        """recent_alerts is capped at 5 entries."""
        neighbors = [
            _make_neighbor(f"risk_00{i}", f"Alert {i}", "Risk", "MITIGATED_BY")
            for i in range(10)
        ]
        health = self.builder.build(timeline=[], neighbors=neighbors)
        assert len(health.recent_alerts) <= 5

    def test_contributing_documents_collected(self):
        """contributing_documents contains source docs from timeline events."""
        timeline = [
            TimelineEvent(
                event_type="maintenance", event_label="Event", entity_id="e1",
                source_document="doc_a.pdf",
            ),
            TimelineEvent(
                event_type="failure", event_label="Failure", entity_id="e2",
                source_document="doc_b.pdf",
            ),
        ]
        health = self.builder.build(timeline=timeline, neighbors=[])
        assert "doc_a.pdf" in health.contributing_documents
        assert "doc_b.pdf" in health.contributing_documents

    def test_inspection_status_current_when_events_exist(self):
        """Inspection events present → inspection_status = 'current'."""
        timeline = [
            TimelineEvent(event_type="inspection", event_label="Event", entity_id="insp1")
        ]
        health = self.builder.build(timeline=timeline, neighbors=[])
        assert health.inspection_status == "current"

    def test_inspection_status_unknown_when_no_events(self):
        """No inspection events → inspection_status = 'unknown'."""
        health = self.builder.build(timeline=[], neighbors=[])
        assert health.inspection_status == "unknown"


# ---------------------------------------------------------------------------
# Asset360 Response Shape Validation
# ---------------------------------------------------------------------------

class TestAsset360ResponseShape:
    """
    Validate that Asset360Response matches Assets.md §Asset 360 Response exactly.

    Per Assets.md:
        {asset, timeline, relationships, documents, procedures,
         maintenance, inspections, compliance, health_summary}
    """

    def test_response_has_all_required_top_level_keys(self):
        """Asset360Response must have all nine fields from the spec."""
        required_keys = {
            "asset",
            "timeline",
            "relationships",
            "documents",
            "procedures",
            "maintenance",
            "inspections",
            "compliance",
            "health_summary",
        }
        response_fields = set(Asset360Response.model_fields.keys())
        missing = required_keys - response_fields
        assert missing == set(), f"Asset360Response is missing fields: {missing}"

    def test_response_serialises_to_dict_with_correct_structure(self):
        """A built Asset360Response serialises to the correct dict shape."""
        from app.assets.schemas import (
            AssetNodeResponse,
            HealthSummaryResponse,
        )

        response = Asset360Response(
            asset=AssetNodeResponse(entity_id="asset_p101", name="Pump P101"),
            health_summary=HealthSummaryResponse(),
        )
        data = response.model_dump()

        assert "asset" in data
        assert "timeline" in data
        assert "relationships" in data
        assert "documents" in data
        assert "procedures" in data
        assert "maintenance" in data
        assert "inspections" in data
        assert "compliance" in data
        assert "health_summary" in data
        assert isinstance(data["timeline"], list)
        assert isinstance(data["relationships"], list)

    def test_asset_node_never_exposes_internal_neo4j_id(self):
        """AssetNodeResponse must NOT have a field named 'id' (Neo4j internal id)."""
        from app.assets.schemas import AssetNodeResponse
        field_names = set(AssetNodeResponse.model_fields.keys())
        assert "id" not in field_names, (
            "AssetNodeResponse must not expose internal Neo4j 'id' — use entity_id"
        )


# ---------------------------------------------------------------------------
# AssetService — 404 guard
# ---------------------------------------------------------------------------

class TestAssetService404Guard:
    """Ensure AssetService raises ValueError (not a silent 200 empty) on 404."""

    def _make_service(self, graph_returns_none=True):
        mock_repo = MagicMock(spec=AssetRepository)
        if graph_returns_none:
            # Simulates asset not found in graph
            mock_repo.fetch_asset_360_parallel = AsyncMock(
                return_value=(None, [], [])
            )
        mock_repo.list_assets = AsyncMock(return_value={"items": [], "total": 0})

        svc = AssetService(
            repository=mock_repo,
            builder=AssetBuilder(),
            validator=AssetValidator(),
        )
        return svc

    def test_missing_asset_raises_value_error(self):
        """get_asset_360() raises ValueError with 'not found' for unknown assets."""
        svc = self._make_service(graph_returns_none=True)

        async def run():
            with pytest.raises(ValueError, match="not found"):
                await svc.get_asset_360("asset_nonexistent")

        asyncio.get_event_loop().run_until_complete(run())

    def test_invalid_id_raises_value_error(self):
        """get_asset_360() raises ValueError for invalid IDs before any graph call."""
        svc = self._make_service()

        async def run():
            with pytest.raises(ValueError):
                await svc.get_asset_360("")   # empty ID

        asyncio.get_event_loop().run_until_complete(run())


# ---------------------------------------------------------------------------
# AssetService — cache behaviour
# ---------------------------------------------------------------------------

class TestAssetServiceCache:
    """Verify in-memory TTL cache: second call returns cached result."""

    def _make_service_with_data(self):
        mock_repo = MagicMock(spec=AssetRepository)
        mock_repo.fetch_asset_360_parallel = AsyncMock(
            return_value=(
                _make_asset_360_data("asset_p101"),
                [],   # no neighbors
                [],   # no chunks
            )
        )
        svc = AssetService(
            repository=mock_repo,
            builder=AssetBuilder(),
            validator=AssetValidator(),
        )
        return svc, mock_repo

    def test_second_call_uses_cache(self):
        """fetch_asset_360_parallel is called only once for two identical requests."""
        svc, mock_repo = self._make_service_with_data()

        async def run():
            await svc.get_asset_360("asset_p101")
            await svc.get_asset_360("asset_p101")

        asyncio.get_event_loop().run_until_complete(run())
        # fetch should have been called exactly once
        mock_repo.fetch_asset_360_parallel.assert_awaited_once()


# ---------------------------------------------------------------------------
# SummaryBuilder — asset identity priority
# ---------------------------------------------------------------------------

class TestAssetIdentityPriority:
    """
    Per Assets.md §Asset Identity:
    Priority: Asset Tag → Equipment ID → UUID.
    Display names are never used as identifiers.
    """

    def setup_method(self):
        self.builder = SummaryBuilder()

    def test_asset_tag_extracted_when_present(self):
        """asset_tag field is populated when the graph node carries it."""
        asset_360 = {
            "a": {
                "entity_id": "asset_p101",
                "name": "Pump P101",
                "asset_tag": "P-101",
                "equipment_id": "EQ-001",
                "source_document": "manual.pdf",
                "confidence": 0.95,
            }
        }
        node = self.builder.build_asset_node("asset_p101", asset_360)
        assert node.asset_tag == "P-101"
        assert node.equipment_id == "EQ-001"

    def test_entity_id_is_the_stable_key(self):
        """entity_id in the output is the validated stable entity_id, not any display name."""
        asset_360 = {
            "a": {
                "entity_id": "asset_p101",
                "name": "Main Pump",   # display name — should NOT become entity_id
                "source_document": "manual.pdf",
                "confidence": 0.95,
            }
        }
        node = self.builder.build_asset_node("asset_p101", asset_360)
        assert node.entity_id == "asset_p101"
        assert node.name == "Main Pump"

    def test_missing_asset_data_returns_shell_node(self):
        """None asset_360_data returns a minimal AssetNode without crashing."""
        node = self.builder.build_asset_node("asset_unknown", None)
        assert node.entity_id == "asset_unknown"

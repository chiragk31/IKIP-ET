"""
Epic 3 — AI Knowledge Extraction Tests

Unit tests for:
  - AIValidator (JSON parsing, schema validation, deduplication, confidence filtering)
  - PromptManager (loading, rendering, caching)
  - ExtractionService (multi-stage pipeline, graceful degradation)
  - KnowledgeRepository (save, load, failure records)
  - InngestClient (knowledge.extracted event emission)

All external dependencies (Gemini, Supabase, Inngest) are mocked.
No real API calls are made in tests.
"""

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.ai.validator import AIValidator
from app.ai.prompt_manager import PromptManager
from app.ai.llm_service import TokenUsage
from app.schemas.knowledge import (
    CanonicalKnowledgeObject,
    EntityExtractionResult,
    RelationshipExtractionResult,
    MeasurementExtractionResult,
    ProcedureExtractionResult,
    RiskExtractionResult,
    DocumentSummaryResult,
    OntologyDiscoveryResult,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractedMeasurement,
    KnowledgeRecord,
)
from app.repositories.knowledge_repository import KnowledgeRepository
from app.events.inngest_client import InngestClient


# ==============================================================
# Fixtures
# ==============================================================

SAMPLE_ENTITY_RESPONSE = {
    "entities": [
        {
            "entity_id": "asset_p101",
            "entity_type": "Asset",
            "label": "Pump P101",
            "aliases": ["P101", "Main Feed Pump"],
            "confidence": 0.97,
            "page": 3,
            "properties": {"manufacturer": "Grundfos"},
        },
        {
            "entity_id": "person_john",
            "entity_type": "Person",
            "label": "John Smith",
            "aliases": ["J. Smith"],
            "confidence": 0.85,
            "page": 1,
            "properties": {},
        },
    ]
}

SAMPLE_RELATIONSHIP_RESPONSE = {
    "relationships": [
        {
            "source": "asset_p101",
            "relationship": "HAS_FAILURE",
            "target": "failure_bearing",
            "confidence": 0.92,
            "properties": {"severity": "high"},
        }
    ]
}

SAMPLE_MEASUREMENT_RESPONSE = {
    "measurements": [
        {
            "measurement_id": "meas_001",
            "name": "Operating Pressure",
            "value": 120.0,
            "unit": "psi",
            "value_min": None,
            "value_max": None,
            "tolerance": None,
            "measurement_type": "operating",
            "applies_to_entity": "asset_p101",
            "applies_to_label": "Pump P101",
            "context": "Normal operating pressure",
            "page": 4,
            "confidence": 0.95,
        }
    ]
}

SAMPLE_PROCEDURE_RESPONSE = {
    "procedures": [
        {
            "procedure_id": "proc_001",
            "name": "Bearing Replacement",
            "procedure_type": "maintenance",
            "applies_to_entity": "asset_p101",
            "applies_to_label": "Pump P101",
            "steps": [
                {"step_number": 1, "description": "Isolate pump", "warning": "Use LOTO", "tools": ["LOTO kit"]}
            ],
            "required_tools": ["LOTO kit", "bearing puller"],
            "required_ppe": ["safety glasses"],
            "applicable_standards": ["ISO 4413"],
            "estimated_duration_hours": 4.0,
            "page": 12,
            "confidence": 0.91,
        }
    ]
}

SAMPLE_RISK_RESPONSE = {
    "risks": [
        {
            "risk_id": "risk_001",
            "name": "Bearing Overheating",
            "category": "operational",
            "severity": "high",
            "probability": "medium",
            "applies_to_entity": "asset_p101",
            "applies_to_label": "Pump P101",
            "description": "Insufficient lubrication causes overheating",
            "consequences": ["Pump shutdown"],
            "mitigations": ["Regular lubrication"],
            "applicable_standards": ["ISO 4413"],
            "page": 8,
            "confidence": 0.88,
        }
    ],
    "warnings": [
        {
            "warning_id": "warn_001",
            "text": "Do not operate above 1500 RPM without approval.",
            "severity": "high",
            "applies_to_entity": "asset_p101",
            "page": 5,
            "confidence": 0.96,
        }
    ],
    "compliance_gaps": [],
}

SAMPLE_SUMMARY_RESPONSE = {
    "summary": "This maintenance report documents a bearing failure on Pump P101.",
    "document_type": "maintenance_report",
    "language": "en",
    "keywords": ["pump", "bearing", "P101"],
    "topics": ["Bearing Failure", "Pump Maintenance"],
    "key_dates": ["2026-03-15"],
    "key_assets": ["Pump P101"],
    "key_findings": ["Bearing overheated due to insufficient lubrication"],
}

SAMPLE_ONTOLOGY_RESPONSE = {
    "new_concepts": [
        {
            "concept_name": "LOTO Permit",
            "category": "Procedure",
            "description": "Lock-Out/Tag-Out safety permit",
            "confidence": 0.88,
            "justification": "Appears 5 times as a distinct safety requirement",
            "related_to_existing": ["Procedure", "Risk"],
        }
    ]
}


# ==============================================================
# TestAIValidator — JSON Parsing
# ==============================================================

class TestAIValidatorJsonParsing:
    """Tests for AIValidator.parse_json_response()"""

    def test_parse_dict_passthrough(self):
        data = {"entities": []}
        result = AIValidator.parse_json_response(data)
        assert result == data

    def test_parse_valid_json_string(self):
        raw = '{"entities": []}'
        result = AIValidator.parse_json_response(raw)
        assert result == {"entities": []}

    def test_parse_markdown_fenced_json(self):
        raw = '```json\n{"entities": []}\n```'
        result = AIValidator.parse_json_response(raw)
        assert result == {"entities": []}

    def test_parse_fenced_json_without_language(self):
        raw = '```\n{"entities": []}\n```'
        result = AIValidator.parse_json_response(raw)
        assert result == {"entities": []}

    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            AIValidator.parse_json_response("not json at all {{")

    def test_wrong_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unexpected AI response type"):
            AIValidator.parse_json_response(12345)


# ==============================================================
# TestAIValidator — Schema Validation
# ==============================================================

class TestAIValidatorSchemaValidation:
    """Tests for AIValidator schema validation methods."""

    def setup_method(self):
        self.validator = AIValidator()

    def test_validate_entities_success(self):
        result = self.validator.validate_entities(SAMPLE_ENTITY_RESPONSE)
        assert len(result.entities) == 2
        assert result.entities[0].entity_id == "asset_p101"
        assert result.entities[0].confidence == 0.97

    def test_validate_entities_empty_list(self):
        result = self.validator.validate_entities({"entities": []})
        assert result.entities == []

    def test_validate_relationships_success(self):
        result = self.validator.validate_relationships(SAMPLE_RELATIONSHIP_RESPONSE)
        assert len(result.relationships) == 1
        assert result.relationships[0].source == "asset_p101"

    def test_validate_measurements_success(self):
        result = self.validator.validate_measurements(SAMPLE_MEASUREMENT_RESPONSE)
        assert len(result.measurements) == 1
        assert result.measurements[0].value == 120.0
        assert result.measurements[0].unit == "psi"

    def test_validate_procedures_success(self):
        result = self.validator.validate_procedures(SAMPLE_PROCEDURE_RESPONSE)
        assert len(result.procedures) == 1
        assert result.procedures[0].name == "Bearing Replacement"
        assert len(result.procedures[0].steps) == 1

    def test_validate_risks_success(self):
        result = self.validator.validate_risks(SAMPLE_RISK_RESPONSE)
        assert len(result.risks) == 1
        assert len(result.warnings) == 1
        assert len(result.compliance_gaps) == 0

    def test_validate_summary_success(self):
        result = self.validator.validate_summary(SAMPLE_SUMMARY_RESPONSE)
        assert "bearing failure" in result.summary.lower()
        assert result.document_type == "maintenance_report"
        assert "pump" in result.keywords

    def test_validate_ontology_success(self):
        result = self.validator.validate_ontology_discovery(SAMPLE_ONTOLOGY_RESPONSE)
        assert len(result.new_concepts) == 1
        assert result.new_concepts[0].concept_name == "LOTO Permit"

    def test_invalid_schema_raises_value_error(self):
        # confidence > 1.0 should fail Pydantic validation
        bad_data = {
            "entities": [
                {
                    "entity_id": "x",
                    "entity_type": "Asset",
                    "label": "X",
                    "confidence": 1.5,  # Invalid
                }
            ]
        }
        with pytest.raises(ValueError, match="schema validation"):
            self.validator.validate_entities(bad_data)


# ==============================================================
# TestAIValidator — Deduplication
# ==============================================================

class TestAIValidatorDeduplication:
    """Tests for entity and relationship deduplication."""

    def setup_method(self):
        self.validator = AIValidator()

    def test_duplicate_entities_merged_keeping_highest_confidence(self):
        data = {
            "entities": [
                {"entity_id": "asset_p101", "entity_type": "Asset", "label": "Pump P101", "confidence": 0.7},
                {"entity_id": "asset_p101", "entity_type": "Asset", "label": "P101", "confidence": 0.9},
            ]
        }
        result = self.validator.validate_entities(data)
        assert len(result.entities) == 1
        assert result.entities[0].confidence == 0.9
        assert result.entities[0].label == "P101"

    def test_unique_entities_preserved(self):
        result = self.validator.validate_entities(SAMPLE_ENTITY_RESPONSE)
        assert len(result.entities) == 2

    def test_duplicate_relationships_merged(self):
        data = {
            "relationships": [
                {"source": "a", "relationship": "USES", "target": "b", "confidence": 0.8},
                {"source": "a", "relationship": "USES", "target": "b", "confidence": 0.95},
            ]
        }
        result = self.validator.validate_relationships(data)
        assert len(result.relationships) == 1
        assert result.relationships[0].confidence == 0.95


# ==============================================================
# TestAIValidator — Confidence Filtering
# ==============================================================

class TestAIValidatorConfidence:
    """Tests for confidence-based filtering."""

    def setup_method(self):
        self.validator = AIValidator()

    def test_split_by_confidence_high_confidence_accepted(self):
        entities = [
            ExtractedEntity(entity_id="a", entity_type="Asset", label="A", confidence=0.9),
            ExtractedEntity(entity_id="b", entity_type="Person", label="B", confidence=0.6),
        ]
        accepted, flagged = self.validator.split_by_confidence(entities, threshold=0.75)
        assert len(accepted) == 1
        assert len(flagged) == 1
        assert accepted[0].entity_id == "a"
        assert flagged[0].entity_id == "b"

    def test_all_high_confidence_all_accepted(self):
        entities = [
            ExtractedEntity(entity_id="a", entity_type="Asset", label="A", confidence=0.9),
            ExtractedEntity(entity_id="b", entity_type="Asset", label="B", confidence=0.8),
        ]
        accepted, flagged = self.validator.split_by_confidence(entities, threshold=0.75)
        assert len(accepted) == 2
        assert len(flagged) == 0

    def test_empty_entities_returns_empty_lists(self):
        accepted, flagged = self.validator.split_by_confidence([])
        assert accepted == []
        assert flagged == []

    def test_compute_overall_confidence_with_entities_and_relationships(self):
        entities = [
            ExtractedEntity(entity_id="a", entity_type="Asset", label="A", confidence=0.9),
            ExtractedEntity(entity_id="b", entity_type="Asset", label="B", confidence=0.8),
        ]
        relationships = [
            ExtractedRelationship(source="a", relationship="USES", target="b", confidence=0.85),
        ]
        score = AIValidator.compute_overall_confidence(entities, relationships, summary_present=True)
        assert 0.0 < score <= 1.0

    def test_compute_overall_confidence_no_data_returns_zero(self):
        score = AIValidator.compute_overall_confidence([], [], summary_present=False)
        assert score == 0.0


# ==============================================================
# TestPromptManager
# ==============================================================

class TestPromptManager:
    """Tests for PromptManager loading, rendering, and caching."""

    def setup_method(self):
        # Use the actual prompts directory
        self.prompts_dir = Path(__file__).parent.parent / "app" / "prompts"
        self.manager = PromptManager(prompts_dir=self.prompts_dir)

    def test_load_entity_extraction_prompt(self):
        template = self.manager.load("entity_extraction")
        assert "{{document_text}}" in template
        assert "{{document_id}}" in template

    def test_load_relationship_extraction_prompt(self):
        template = self.manager.load("relationship_extraction")
        assert "{{document_text}}" in template
        assert "{{entities}}" in template

    def test_load_measurement_extraction_prompt(self):
        template = self.manager.load("measurement_extraction")
        assert "{{document_text}}" in template

    def test_load_procedure_extraction_prompt(self):
        template = self.manager.load("procedure_extraction")
        assert "{{document_text}}" in template

    def test_load_risk_analysis_prompt(self):
        template = self.manager.load("risk_analysis")
        assert "{{document_text}}" in template

    def test_load_summary_prompt(self):
        template = self.manager.load("summary")
        assert "{{document_text}}" in template
        assert "{{filename}}" in template

    def test_load_ontology_discovery_prompt(self):
        template = self.manager.load("ontology_discovery")
        assert "{{document_text}}" in template
        assert "{{current_ontology}}" in template

    def test_render_substitutes_variables(self):
        rendered = self.manager.render(
            "entity_extraction",
            {"document_text": "Pump P101 failed.", "document_id": "doc-123"},
        )
        assert "Pump P101 failed." in rendered
        assert "doc-123" in rendered
        assert "{{document_text}}" not in rendered

    def test_missing_variable_shows_placeholder(self):
        rendered = self.manager.render(
            "entity_extraction",
            {"document_text": "some text"},  # missing document_id
        )
        assert "MISSING: document_id" in rendered

    def test_prompt_caching_second_load_from_cache(self):
        # Load once
        self.manager.load("entity_extraction")
        assert "entity_extraction" in self.manager._cache

        # Load again should use cache
        self.manager.load("entity_extraction")
        assert "entity_extraction" in self.manager._cache

    def test_clear_cache_removes_entries(self):
        self.manager.load("entity_extraction")
        self.manager.clear_cache()
        assert self.manager._cache == {}

    def test_missing_prompt_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.manager.load("nonexistent_prompt_xyz")

    def test_list_available_returns_prompt_names(self):
        available = self.manager.list_available()
        assert "entity_extraction" in available
        assert "relationship_extraction" in available
        assert "measurement_extraction" in available
        assert "procedure_extraction" in available
        assert "risk_analysis" in available
        assert "summary" in available
        assert "ontology_discovery" in available


# ==============================================================
# TestExtractionService
# ==============================================================

class TestExtractionService:
    """Tests for ExtractionService multi-stage pipeline."""

    def _make_service(self, llm_responses: dict = None):
        """Create ExtractionService with mocked dependencies."""
        from app.services.extraction_service import ExtractionService

        llm_service = AsyncMock()
        knowledge_repo = MagicMock()
        storage_repo = MagicMock()
        document_repo = MagicMock()
        inngest = MagicMock()

        # Default LLM responses per prompt
        responses = llm_responses or {
            "entity_extraction": SAMPLE_ENTITY_RESPONSE,
            "relationship_extraction": SAMPLE_RELATIONSHIP_RESPONSE,
            "measurement_extraction": SAMPLE_MEASUREMENT_RESPONSE,
            "procedure_extraction": SAMPLE_PROCEDURE_RESPONSE,
            "risk_analysis": SAMPLE_RISK_RESPONSE,
            "summary": SAMPLE_SUMMARY_RESPONSE,
            "ontology_discovery": SAMPLE_ONTOLOGY_RESPONSE,
        }

        async def mock_generate(prompt_name, variables, **kwargs):
            return responses.get(prompt_name, {}), TokenUsage.zero()

        llm_service.generate = mock_generate
        llm_service.model_name = "gemini-2.5-flash"

        # Mock canonical document download
        canonical_doc = {
            "document_id": "doc-123",
            "original_filename": "test.pdf",
            "storage_path": "documents/2026/07/test.pdf",
            "metadata": {"title": "Test Doc", "page_count": 10},
            "full_text": "Pump P101 bearing failure at 150°C. Operator John performed inspection.",
            "tables": [],
            "language": "en",
        }
        storage_repo.download_file.return_value = json.dumps(canonical_doc).encode("utf-8")

        # Mock knowledge repo save
        knowledge_record = MagicMock()
        knowledge_record.id = "knowledge-id-123"
        knowledge_repo.save.return_value = knowledge_record

        # Mock event emission
        inngest.send_knowledge_extracted_event.return_value = True

        service = ExtractionService(
            llm_service=llm_service,
            knowledge_repo=knowledge_repo,
            storage_repo=storage_repo,
            document_repo=document_repo,
            inngest=inngest,
        )

        return service, knowledge_repo, inngest, document_repo

    @pytest.mark.asyncio
    async def test_extract_returns_canonical_knowledge_object(self):
        service, _, _, _ = self._make_service()
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        assert isinstance(cko, CanonicalKnowledgeObject)
        assert cko.document_id == "doc-123"

    @pytest.mark.asyncio
    async def test_extract_entities_extracted(self):
        service, _, _, _ = self._make_service()
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        assert len(cko.entities) > 0

    @pytest.mark.asyncio
    async def test_extract_relationships_extracted(self):
        service, _, _, _ = self._make_service()
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        assert len(cko.relationships) > 0

    @pytest.mark.asyncio
    async def test_extract_measurements_extracted(self):
        service, _, _, _ = self._make_service()
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        assert len(cko.measurements) > 0

    @pytest.mark.asyncio
    async def test_extract_procedures_extracted(self):
        service, _, _, _ = self._make_service()
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        assert len(cko.procedures) > 0

    @pytest.mark.asyncio
    async def test_extract_risks_extracted(self):
        service, _, _, _ = self._make_service()
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        assert len(cko.risks) > 0

    @pytest.mark.asyncio
    async def test_extract_summary_generated(self):
        service, _, _, _ = self._make_service()
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        assert len(cko.summary) > 0

    @pytest.mark.asyncio
    async def test_extract_knowledge_repo_save_called(self):
        service, knowledge_repo, _, _ = self._make_service()
        await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        knowledge_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_knowledge_extracted_event_emitted(self):
        service, _, inngest, _ = self._make_service()
        await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        inngest.send_knowledge_extracted_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_cko_has_model_version(self):
        service, _, _, _ = self._make_service()
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        assert cko.model_version == "gemini-2.5-flash"

    @pytest.mark.asyncio
    async def test_extract_cko_has_prompt_version(self):
        service, _, _, _ = self._make_service()
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        assert cko.prompt_version == "1.1"

    @pytest.mark.asyncio
    async def test_entity_stage_failure_graceful_degradation(self):
        """If entity extraction fails, pipeline continues with empty entities."""
        service, _, _, _ = self._make_service(llm_responses={
            "entity_extraction": {},  # Bad response → validation will fail
            "relationship_extraction": SAMPLE_RELATIONSHIP_RESPONSE,
            "measurement_extraction": SAMPLE_MEASUREMENT_RESPONSE,
            "procedure_extraction": SAMPLE_PROCEDURE_RESPONSE,
            "risk_analysis": SAMPLE_RISK_RESPONSE,
            "summary": SAMPLE_SUMMARY_RESPONSE,
            "ontology_discovery": SAMPLE_ONTOLOGY_RESPONSE,
        })
        # Should not raise — graceful degradation
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        # Entities empty (stage failed gracefully)
        assert cko.entities == []
        # Other stages should still have data
        assert len(cko.measurements) > 0

    @pytest.mark.asyncio
    async def test_confidence_score_computed(self):
        service, _, _, _ = self._make_service()
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        assert 0.0 < cko.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_stage_latencies_tracked(self):
        service, _, _, _ = self._make_service()
        cko = await service.extract(
            document_id="doc-123",
            canonical_storage_path="processed/doc-123/canonical.json",
        )
        assert "entity_extraction" in cko.stage_latencies
        assert "summary_generation" in cko.stage_latencies
        assert all(v >= 0 for v in cko.stage_latencies.values())


# ==============================================================
# TestKnowledgeRepository
# ==============================================================

class TestKnowledgeRepository:
    """Tests for KnowledgeRepository save and load."""

    def _make_repo(self):
        from app.repositories.knowledge_repository import KnowledgeRepository
        supabase = MagicMock()
        return KnowledgeRepository(supabase=supabase), supabase

    def _make_cko(self, document_id="doc-123"):
        return CanonicalKnowledgeObject(
            document_id=document_id,
            document={"id": document_id},
            summary="Test summary",
            entities=[
                ExtractedEntity(
                    entity_id="asset_p101",
                    entity_type="Asset",
                    label="Pump P101",
                    confidence=0.95,
                )
            ],
            relationships=[],
            measurements=[],
            procedures=[],
            risks=[],
            confidence=0.87,
            model_version="gemini-2.5-flash",
            prompt_version="1.0",
        )

    def test_save_uploads_to_storage(self):
        repo, supabase = self._make_repo()
        supabase.storage.from_().upload.return_value = None
        supabase.client.table().upsert().execute.return_value = MagicMock(data=[{"id": "rec-1"}])

        cko = self._make_cko()
        record = repo.save(cko)

        assert supabase.storage.from_.called
        assert record.document_id == "doc-123"
        assert record.status == "completed"

    def test_save_failed_creates_failure_record(self):
        repo, supabase = self._make_repo()
        supabase.client.table().upsert().execute.return_value = MagicMock(data=[])

        record = repo.save_failed(
            document_id="doc-456",
            error_message="Gemini API timeout",
            model_version="gemini-2.5-flash",
        )

        assert record.document_id == "doc-456"
        assert record.status == "failed"
        assert "Gemini API timeout" in record.error_message

    def test_storage_path_pattern(self):
        path = KnowledgeRepository._build_storage_path("doc-789")
        assert path == "knowledge/doc-789/cko.json"

    def test_get_record_not_found_returns_none(self):
        repo, supabase = self._make_repo()
        supabase.client.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

        result = repo.get_record("nonexistent-doc")
        assert result is None


# ==============================================================
# TestInngestClient — knowledge.extracted
# ==============================================================

class TestInngestClientKnowledgeEvent:
    """Tests for InngestClient.send_knowledge_extracted_event()."""

    def test_send_knowledge_extracted_event_calls_send_event(self):
        client = InngestClient(event_key="test-key", is_development=True)
        client.send_event = MagicMock(return_value=True)

        result = client.send_knowledge_extracted_event(
            document_id="doc-123",
            knowledge_id="knowledge-456",
            confidence=0.92,
            user_id="user-789",
        )

        client.send_event.assert_called_once_with(
            event_name="knowledge.extracted",
            payload={
                "document_id": "doc-123",
                "knowledge_id": "knowledge-456",
                "confidence": 0.92,
                "user_id": "user-789",
            },
            user_id="user-789",
        )
        assert result is True

    def test_send_knowledge_extracted_event_without_user(self):
        client = InngestClient(event_key="test-key", is_development=True)
        client.send_event = MagicMock(return_value=True)

        result = client.send_knowledge_extracted_event(
            document_id="doc-123",
            knowledge_id="k-456",
            confidence=0.88,
        )

        payload = client.send_event.call_args[1]["payload"]
        assert payload["document_id"] == "doc-123"
        assert payload["confidence"] == 0.88
        assert payload["user_id"] is None
        assert result is True

    def test_event_key_in_payload(self):
        client = InngestClient(event_key="test-key", is_development=True)
        client.send_event = MagicMock(return_value=True)

        client.send_knowledge_extracted_event(
            document_id="d-1",
            knowledge_id="k-1",
            confidence=0.75,
        )

        call_args = client.send_event.call_args
        assert call_args[1]["event_name"] == "knowledge.extracted"


# ==============================================================
# TestCanonicalKnowledgeObject — Schema
# ==============================================================

class TestCanonicalKnowledgeObjectSchema:
    """Tests for CKO Pydantic schema validation."""

    def test_cko_with_minimum_fields(self):
        cko = CanonicalKnowledgeObject(document_id="doc-1")
        assert cko.document_id == "doc-1"
        assert cko.entities == []
        assert cko.relationships == []
        assert cko.confidence == 0.0

    def test_cko_confidence_out_of_range_raises(self):
        with pytest.raises(Exception):
            CanonicalKnowledgeObject(document_id="doc-1", confidence=1.5)

    def test_cko_serializes_to_dict(self):
        cko = CanonicalKnowledgeObject(
            document_id="doc-1",
            summary="Test",
            confidence=0.85,
        )
        data = cko.model_dump()
        assert data["document_id"] == "doc-1"
        assert data["summary"] == "Test"
        assert data["confidence"] == 0.85

    def test_knowledge_record_schema(self):
        record = KnowledgeRecord(
            id="rec-1",
            document_id="doc-1",
            storage_path="knowledge/doc-1/cko.json",
            model_version="gemini-2.5-flash",
            prompt_version="1.0",
            confidence=0.9,
            extraction_time_seconds=12.5,
            extraction_timestamp="2026-07-20T10:00:00",
        )
        assert record.status == "completed"
        assert record.entity_count == 0

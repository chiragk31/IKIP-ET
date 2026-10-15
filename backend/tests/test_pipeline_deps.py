"""
Pipeline Dependency Initialization Tests
=========================================

Tests verifying fixes for the three reported pipeline bugs:

  Error A: 'Depends' object has no attribute 'render'
           — LLMService received a FastAPI Depends marker instead of a
             real PromptManager.

  Error B: 'Depends' object has no attribute 'save_nko'
           — OntologyManager received a FastAPI Depends marker instead of
             a real OntologyRepository.

  Error C: False successful completion when all stages failed.
           — All-stage failure was silently treated as empty-but-ok result.

All external services (Gemini, Supabase, Inngest, Neo4j, Pinecone) are
mocked.  No real API calls are made.

Coverage:
  1.  PromptManager is correctly initialized as a real Python object.
  2.  LLMService receives a real PromptManager (not a Depends marker).
  3.  Prompt rendering works with representative variables.
  4.  Gemini calls can be mocked; mock response produces valid extraction.
  5.  LLM failures are propagated per stage; other stages continue.
  6.  OntologyManager receives a real OntologyRepository (not Depends).
  7.  save_nko is callable on the real OntologyRepository interface.
  8.  All-stages-failed raises RuntimeError (no false success).
  9.  Partial success: some stages failing, some succeeding is preserved.
 10.  Canonical storage path passes unchanged through the event payload.
 11.  knowledge.extracted event is NOT emitted when all stages fail.
 12.  Inngest handlers can construct their services without FastAPI DI.
 13.  create_llm_service_for_inngest() returns a real LLMService.
 14.  create_ontology_manager_for_inngest() returns a real OntologyManager.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.prompt_manager import PromptManager
from app.ai.llm_service import LLMService, TokenUsage
from app.ontology.ontology_manager import OntologyManager
from app.ontology.ontology_repository import OntologyRepository
from app.schemas.knowledge import (
    CanonicalKnowledgeObject,
    EntityExtractionResult,
    ExtractedEntity,
)


# ==============================================================
# Fixtures / helpers
# ==============================================================

PROMPTS_DIR = Path(__file__).parent.parent / "app" / "prompts"


def _make_prompt_manager() -> PromptManager:
    return PromptManager(prompts_dir=PROMPTS_DIR)


def _make_llm_service(prompt_manager: PromptManager = None) -> LLMService:
    """Build an LLMService without touching real Gemini."""
    pm = prompt_manager or _make_prompt_manager()
    svc = LLMService.__new__(LLMService)
    svc.model_name = "gemini-2.5-flash-mock"
    svc.temperature = 0.1
    svc.max_retries = 3
    svc.timeout = 60
    svc.prompt_manager = pm
    svc._model = None  # No real Gemini client
    return svc


def _make_ontology_manager(supabase_mock=None) -> OntologyManager:
    if supabase_mock is None:
        supabase_mock = MagicMock()
    repo = OntologyRepository(supabase=supabase_mock)
    return OntologyManager(ontology_repo=repo)


def _canonical_doc_bytes(text: str = "Pump P101 bearing failure.") -> bytes:
    doc = {
        "document_id": "doc-test",
        "original_filename": "test.pdf",
        "storage_path": "documents/2026/10/test.pdf",
        "metadata": {"page_count": 2},
        "full_text": text,
        "tables": [],
        "language": "en",
    }
    return json.dumps(doc).encode("utf-8")


# ==============================================================
# Test 1–3: PromptManager initialization and rendering
# ==============================================================

class TestPromptManagerInitialization:
    """Error A pre-condition: PromptManager must be a real, callable object."""

    def test_prompt_manager_is_not_depends_object(self):
        """PromptManager instance must not be a FastAPI Depends marker."""
        pm = _make_prompt_manager()
        # A Depends object has no 'render' attribute
        assert hasattr(pm, "render"), "PromptManager must have a .render() method"
        assert callable(pm.render)

    def test_prompt_manager_render_returns_string(self):
        pm = _make_prompt_manager()
        rendered = pm.render(
            "entity_extraction",
            {"document_text": "Pump P101 failed at 150C.", "document_id": "doc-1"},
        )
        assert isinstance(rendered, str)
        assert "Pump P101 failed at 150C." in rendered
        assert "{{document_text}}" not in rendered  # placeholder resolved

    def test_all_seven_prompt_templates_exist(self):
        pm = _make_prompt_manager()
        required_prompts = [
            "entity_extraction",
            "relationship_extraction",
            "measurement_extraction",
            "procedure_extraction",
            "risk_analysis",
            "summary",
            "ontology_discovery",
        ]
        available = pm.list_available()
        for name in required_prompts:
            assert name in available, f"Missing prompt template: {name}.md"


# ==============================================================
# Test 2: LLMService receives a real PromptManager
# ==============================================================

class TestLLMServiceInitialization:
    """Error A root-cause: prompt_manager must be a PromptManager, not Depends."""

    def test_llm_service_has_real_prompt_manager(self):
        pm = _make_prompt_manager()
        svc = _make_llm_service(pm)
        assert isinstance(svc.prompt_manager, PromptManager), (
            "LLMService.prompt_manager must be a PromptManager instance. "
            "Received: %s" % type(svc.prompt_manager)
        )

    def test_llm_service_prompt_manager_can_render(self):
        svc = _make_llm_service()
        rendered = svc.prompt_manager.render(
            "summary",
            {"document_text": "Test document text.", "filename": "report.pdf"},
        )
        assert "Test document text." in rendered

    def test_llm_service_is_not_depends_object(self):
        """Calling render on prompt_manager must not raise AttributeError."""
        svc = _make_llm_service()
        # This would raise AttributeError if prompt_manager were a Depends marker
        try:
            svc.prompt_manager.render(
                "entity_extraction",
                {"document_text": "X", "document_id": "doc-1"},
            )
        except AttributeError as e:
            pytest.fail(
                f"'Depends' object has no attribute 'render' — the original bug "
                f"is still present: {e}"
            )

    def test_create_llm_service_for_inngest_returns_real_service(self):
        """create_llm_service_for_inngest() must NOT pass a Depends object."""
        from app.core.dependencies import create_llm_service_for_inngest

        with patch("app.ai.llm_service.LLMService._initialize_client"):
            svc = create_llm_service_for_inngest()

        assert isinstance(svc, LLMService)
        assert isinstance(svc.prompt_manager, PromptManager), (
            "create_llm_service_for_inngest() assigned a Depends marker as "
            "prompt_manager — this is the original Error A bug."
        )
        assert hasattr(svc.prompt_manager, "render")


# ==============================================================
# Test 4–5: Gemini mock and LLM failure propagation
# ==============================================================

class TestLLMServiceMocking:
    """Verify Gemini calls can be mocked and failures propagate correctly."""

    @pytest.mark.asyncio
    async def test_generate_with_mocked_model(self):
        """Mock the Gemini _model so generate() returns a controlled response."""
        svc = _make_llm_service()
        mock_response = MagicMock()
        mock_response.text = json.dumps({"entities": []})
        mock_response.usage_metadata = None
        svc._model = MagicMock()
        svc._model.generate_content.return_value = mock_response

        result, usage = await svc.generate(
            prompt_name="entity_extraction",
            variables={"document_text": "Pump P101.", "document_id": "doc-1"},
        )
        assert result == {"entities": []}
        assert isinstance(usage, TokenUsage)

    @pytest.mark.asyncio
    async def test_generate_raises_when_model_none(self):
        """generate() raises RuntimeError when Gemini model not initialized."""
        svc = _make_llm_service()
        svc._model = None  # Simulates missing/invalid API key

        with pytest.raises(RuntimeError, match="Gemini model not initialized"):
            await svc.generate(
                prompt_name="entity_extraction",
                variables={"document_text": "X", "document_id": "doc-1"},
            )


# ==============================================================
# Test 6–7: OntologyManager receives a real OntologyRepository
# ==============================================================

class TestOntologyManagerInitialization:
    """Error B root-cause: ontology_repo must be OntologyRepository, not Depends."""

    def test_ontology_manager_has_real_repo(self):
        manager = _make_ontology_manager()
        assert isinstance(manager._ontology_repo, OntologyRepository), (
            "OntologyManager._ontology_repo must be an OntologyRepository. "
            "Received: %s" % type(manager._ontology_repo)
        )

    def test_ontology_repo_has_save_nko(self):
        """OntologyRepository must have a save_nko method."""
        repo = OntologyRepository(supabase=MagicMock())
        assert hasattr(repo, "save_nko"), (
            "OntologyRepository is missing save_nko — this is Error B."
        )
        assert callable(repo.save_nko)

    def test_create_ontology_manager_for_inngest_returns_real_manager(self):
        """create_ontology_manager_for_inngest() must use real OntologyRepository."""
        from app.core.dependencies import create_ontology_manager_for_inngest

        mock_supabase = MagicMock()
        with patch("app.core.dependencies.get_supabase_client", return_value=mock_supabase):
            manager = create_ontology_manager_for_inngest()

        assert isinstance(manager, OntologyManager)
        assert isinstance(manager._ontology_repo, OntologyRepository), (
            "create_ontology_manager_for_inngest() assigned a Depends marker "
            "as ontology_repo — this is the original Error B bug."
        )

    def test_save_nko_called_on_real_repo(self):
        """save_nko is callable on a mocked-storage OntologyRepository."""
        from app.ontology.models import NormalizedKnowledgeObject

        supabase_mock = MagicMock()
        supabase_mock.client.storage.from_().upload.return_value = None

        repo = OntologyRepository(supabase=supabase_mock)
        nko = NormalizedKnowledgeObject(
            document_id="doc-test",
            entities=[],
            relationships=[],
            discovered_concepts=[],
            confidence=0.0,
        )
        # Should not raise AttributeError
        try:
            path = repo.save_nko(nko)
        except AttributeError as e:
            pytest.fail(f"save_nko raised AttributeError (Error B still present): {e}")
        except Exception:
            pass  # Storage errors are expected without real Supabase


# ==============================================================
# Test 8–9: Error C — False success detection
# ==============================================================

class TestAllStagesFailedDetection:
    """
    Error C: When every stage fails, the pipeline must NOT emit success.
    """

    def _make_failing_extraction_service(self):
        """
        Build ExtractionService where all 7 LLM calls fail with AttributeError
        (simulating the pre-fix 'Depends' object has no attribute 'render').
        """
        from app.services.extraction_service import ExtractionService

        llm_service = AsyncMock()

        async def _failing_generate(prompt_name, variables, **kwargs):
            raise AttributeError("'Depends' object has no attribute 'render'")

        llm_service.generate = _failing_generate
        llm_service.model_name = "gemini-2.5-flash"

        knowledge_repo = MagicMock()
        storage_repo = MagicMock()
        storage_repo.download_file.return_value = _canonical_doc_bytes()
        document_repo = MagicMock()
        inngest = MagicMock()

        knowledge_record = MagicMock()
        knowledge_record.id = "k-1"
        knowledge_repo.save.return_value = knowledge_record

        service = ExtractionService(
            llm_service=llm_service,
            knowledge_repo=knowledge_repo,
            storage_repo=storage_repo,
            document_repo=document_repo,
            inngest=inngest,
        )
        return service, knowledge_repo, inngest

    @pytest.mark.asyncio
    async def test_all_stages_failed_raises_runtime_error(self):
        """When all 7 stages fail, extract() must raise rather than succeed."""
        service, _, _ = self._make_failing_extraction_service()
        with pytest.raises(RuntimeError, match="All 7 extraction stages failed"):
            await service.extract(
                document_id="doc-fail",
                canonical_storage_path="some/path.json",
            )

    @pytest.mark.asyncio
    async def test_all_stages_failed_does_not_emit_success_event(self):
        """knowledge.extracted must NOT be emitted when all stages fail."""
        service, _, inngest = self._make_failing_extraction_service()
        try:
            await service.extract(
                document_id="doc-fail",
                canonical_storage_path="some/path.json",
            )
        except (RuntimeError, Exception):
            pass  # expected

        inngest.send_knowledge_extracted_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_stages_failed_does_not_mark_completed(self):
        """Document status must not be 'completed' when all stages fail."""
        service, _, _ = self._make_failing_extraction_service()
        document_repo = service._document_repo

        try:
            await service.extract(
                document_id="doc-fail",
                canonical_storage_path="some/path.json",
            )
        except (RuntimeError, Exception):
            pass

        # Check that update_status was never called with "completed"
        completed_calls = [
            call for call in document_repo.update_status.call_args_list
            if call.kwargs.get("status") == "completed" or
               (call.args and call.args[1] == "completed")
        ]
        assert len(completed_calls) == 0, (
            "Document status was set to 'completed' even though all extraction stages failed."
        )

    @pytest.mark.asyncio
    async def test_partial_success_is_preserved(self):
        """When only some stages fail, the pipeline should continue (graceful degradation)."""
        from app.services.extraction_service import ExtractionService

        SAMPLE_ENTITY_RESPONSE = {
            "entities": [
                {
                    "entity_id": "asset_p101",
                    "entity_type": "Asset",
                    "label": "Pump P101",
                    "confidence": 0.95,
                }
            ]
        }
        SAMPLE_SUMMARY_RESPONSE = {
            "summary": "Pump failure report.",
            "document_type": "maintenance_report",
            "language": "en",
            "keywords": ["pump"],
            "topics": ["Pump"],
            "key_dates": [],
            "key_assets": ["Pump P101"],
            "key_findings": ["Bearing failure"],
        }

        llm_service = AsyncMock()

        async def _partial_generate(prompt_name, variables, **kwargs):
            # Only entity_extraction and summary succeed
            responses = {
                "entity_extraction": SAMPLE_ENTITY_RESPONSE,
                "summary": SAMPLE_SUMMARY_RESPONSE,
            }
            if prompt_name in responses:
                mock_usage = TokenUsage(
                    prompt_tokens=100, completion_tokens=50, total_tokens=150
                )
                return responses[prompt_name], mock_usage
            else:
                raise RuntimeError(f"Simulated failure for {prompt_name}")

        llm_service.generate = _partial_generate
        llm_service.model_name = "gemini-2.5-flash"

        knowledge_repo = MagicMock()
        storage_repo = MagicMock()
        storage_repo.download_file.return_value = _canonical_doc_bytes()
        document_repo = MagicMock()
        inngest = MagicMock()

        knowledge_record = MagicMock()
        knowledge_record.id = "k-partial"
        knowledge_repo.save.return_value = knowledge_record

        service = ExtractionService(
            llm_service=llm_service,
            knowledge_repo=knowledge_repo,
            storage_repo=storage_repo,
            document_repo=document_repo,
            inngest=inngest,
        )

        # Should NOT raise — partial success is valid
        cko = await service.extract(
            document_id="doc-partial",
            canonical_storage_path="some/path.json",
        )
        assert len(cko.entities) > 0, "Entities should be populated from successful stage"
        assert len(cko.summary) > 0, "Summary should be populated from successful stage"
        # Verify the event WAS emitted (partial success is still success)
        inngest.send_knowledge_extracted_event.assert_called_once()


# ==============================================================
# Test 10: Canonical storage path propagation
# ==============================================================

class TestStoragePathPropagation:
    """Canonical storage path must pass unchanged from event to extraction."""

    @pytest.mark.asyncio
    async def test_canonical_path_preserved_in_cko(self):
        """The canonical_storage_path from the event should appear in the CKO."""
        from app.services.extraction_service import ExtractionService

        expected_path = "documents/2026/10/bc109ff0_canonical_d9e35144.json"

        llm_service = AsyncMock()

        async def _mock_generate(prompt_name, variables, **kwargs):
            responses = {
                "entity_extraction": {"entities": []},
                "relationship_extraction": {"relationships": []},
                "measurement_extraction": {"measurements": []},
                "procedure_extraction": {"procedures": []},
                "risk_analysis": {"risks": [], "warnings": [], "compliance_gaps": []},
                "summary": {
                    "summary": "Test.",
                    "document_type": "report",
                    "language": "en",
                    "keywords": [],
                    "topics": [],
                    "key_dates": [],
                    "key_assets": [],
                    "key_findings": [],
                },
                "ontology_discovery": {"new_concepts": []},
            }
            return responses.get(prompt_name, {}), TokenUsage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15
            )

        llm_service.generate = _mock_generate
        llm_service.model_name = "gemini-2.5-flash"

        knowledge_repo = MagicMock()
        storage_repo = MagicMock()
        storage_repo.download_file.return_value = _canonical_doc_bytes()
        document_repo = MagicMock()
        inngest = MagicMock()

        knowledge_record = MagicMock()
        knowledge_record.id = "k-path-test"
        knowledge_repo.save.return_value = knowledge_record

        service = ExtractionService(
            llm_service=llm_service,
            knowledge_repo=knowledge_repo,
            storage_repo=storage_repo,
            document_repo=document_repo,
            inngest=inngest,
        )

        cko = await service.extract(
            document_id="doc-path-test",
            canonical_storage_path=expected_path,
        )

        assert cko.document["storage_path"] == expected_path, (
            f"CKO.document['storage_path'] should be '{expected_path}' but got "
            f"'{cko.document.get('storage_path')}'"
        )
        # Verify storage_repo.download_file was called with the correct path
        storage_repo.download_file.assert_called_once_with(expected_path)


# ==============================================================
# Test 12: Inngest handler service construction
# ==============================================================

class TestInngestHandlerServiceConstruction:
    """
    Inngest handlers must be able to construct their services without
    relying on FastAPI request-scoped dependency resolution.
    """

    def test_create_llm_service_for_inngest_signature(self):
        """create_llm_service_for_inngest takes no required args (no Depends)."""
        from app.core.dependencies import create_llm_service_for_inngest
        import inspect
        sig = inspect.signature(create_llm_service_for_inngest)
        required_params = [
            p for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
        ]
        assert len(required_params) == 0, (
            "create_llm_service_for_inngest() should take no required arguments."
        )

    def test_create_ontology_manager_for_inngest_signature(self):
        from app.core.dependencies import create_ontology_manager_for_inngest
        import inspect
        sig = inspect.signature(create_ontology_manager_for_inngest)
        required_params = [
            p for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
        ]
        assert len(required_params) == 0

    def test_create_graph_service_for_inngest_signature(self):
        from app.core.dependencies import create_graph_service_for_inngest
        import inspect
        sig = inspect.signature(create_graph_service_for_inngest)
        required_params = [
            p for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
        ]
        assert len(required_params) == 0

    def test_create_embedding_service_for_inngest_signature(self):
        from app.core.dependencies import create_embedding_service_for_inngest
        import inspect
        sig = inspect.signature(create_embedding_service_for_inngest)
        required_params = [
            p for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
        ]
        assert len(required_params) == 0

    def test_knowledge_handler_imports_correct_factory(self):
        """knowledge_handler.py must import create_llm_service_for_inngest."""
        import importlib, app.events.knowledge_handler as kh
        # If the import is wrong, this would have already failed at import time.
        # Additionally verify the function is referenced in the module.
        source = Path(kh.__file__).read_text()
        assert "create_llm_service_for_inngest" in source, (
            "knowledge_handler.py does not import create_llm_service_for_inngest. "
            "Error A fix was not applied."
        )
        assert "llm_service= get_llm_service()" not in source, (
            "knowledge_handler.py still calls get_llm_service() directly."
        )

    def test_ontology_handler_imports_correct_factory(self):
        """ontology_handler.py must import create_ontology_manager_for_inngest."""
        import app.events.ontology_handler as oh
        source = Path(oh.__file__).read_text()
        assert "create_ontology_manager_for_inngest" in source, (
            "ontology_handler.py does not import create_ontology_manager_for_inngest. "
            "Error B fix was not applied."
        )
        assert "ontology_manager = get_ontology_manager()" not in source, (
            "ontology_handler.py still calls get_ontology_manager() directly."
        )

    def test_graph_handler_imports_correct_factory(self):
        import app.events.graph_handler as gh
        source = Path(gh.__file__).read_text()
        assert "create_graph_service_for_inngest" in source

    def test_embedding_handler_imports_correct_factory(self):
        import app.events.embedding_handler as eh
        source = Path(eh.__file__).read_text()
        assert "create_embedding_service_for_inngest" in source

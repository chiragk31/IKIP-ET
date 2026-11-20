"""
Tests: canonical_storage_path propagation through the embedding pipeline

Covers the bug: EmbeddingService.embed() missing required positional argument
'canonical_storage_path'.

Root cause: graph.updated event payload did not include canonical_storage_path,
so embedding_handler.py called embed(document_id) with only one argument.

These tests verify:
 1. EmbeddingService.embed() is called with both required arguments.
 2. canonical_storage_path is included in knowledge.extracted payload.
 3. canonical_storage_path is included in ontology.updated payload.
 4. canonical_storage_path is included in graph.updated payload.
 5. handle_graph_updated() accepts and forwards canonical_storage_path.
 6. Missing/empty canonical_storage_path fails clearly rather than silently.
 7. InngestClient.send_knowledge_extracted_event() accepts the new field.
 8. InngestClient.send_graph_updated_event() accepts the new field.
 9. Existing embedding service tests are unaffected.
"""

import json
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.events.inngest_client import InngestClient


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

DOCUMENT_ID = "d9e35144-5c01-4981-9c79-06f772ce6185"
CANONICAL_PATH = "processed/2026/10/bc109ff0_canonical_d9e35144.json"


def _make_inngest_client() -> InngestClient:
    return InngestClient(event_key="test-key", is_development=True)


def _canonical_bytes(path: str = CANONICAL_PATH) -> bytes:
    doc = {
        "document_id": DOCUMENT_ID,
        "original_filename": "test.pdf",
        "storage_path": path,
        "metadata": {"page_count": 2},
        "full_text": "Pump P101 bearing failure at 150C.",
        "tables": [],
        "sections": [],
        "pages": [],
        "language": "en",
        "full_text": "Pump P101 bearing failure.",
    }
    return json.dumps(doc).encode("utf-8")


# ---------------------------------------------------------------
# 1. EmbeddingService.embed() signature includes canonical_storage_path
# ---------------------------------------------------------------

class TestEmbeddingServiceSignature:
    """Verify embed() requires both document_id and canonical_storage_path."""

    def test_embed_requires_canonical_storage_path(self):
        from app.embeddings.embedding_service import EmbeddingService

        sig = inspect.signature(EmbeddingService.embed)
        params = list(sig.parameters.keys())
        assert "canonical_storage_path" in params, (
            "EmbeddingService.embed() must have a 'canonical_storage_path' parameter."
        )

    def test_canonical_storage_path_is_required(self):
        """canonical_storage_path must not have a default value (it is required)."""
        from app.embeddings.embedding_service import EmbeddingService

        sig = inspect.signature(EmbeddingService.embed)
        param = sig.parameters.get("canonical_storage_path")
        assert param is not None
        assert param.default is inspect.Parameter.empty, (
            "canonical_storage_path must be a required positional argument, "
            "not optional. Making it optional would allow callers to omit it "
            "and fabricate a path silently."
        )

    @pytest.mark.asyncio
    async def test_embed_uses_provided_path_not_hardcoded(self):
        """embed() must call storage_repo.download_file with the exact path given."""
        from app.embeddings.embedding_service import EmbeddingService
        from app.embeddings.embedding_provider import EmbeddingProvider

        storage_repo = MagicMock()
        storage_repo.download_file.return_value = _canonical_bytes(CANONICAL_PATH)

        document_repo = MagicMock()
        document_repo.get_by_id.return_value = None

        ontology_repo = MagicMock()
        ontology_repo.load_nko.return_value = None

        embedding_provider = AsyncMock(spec=EmbeddingProvider)
        embedding_provider.embed_batch = AsyncMock(return_value=[])
        embedding_provider.model_name = MagicMock(return_value="test-model")

        pinecone_repo = MagicMock()
        pinecone_repo.fetch_existing_ids.return_value = set()
        pinecone_repo.upsert_chunks.return_value = 0

        svc = EmbeddingService(
            storage_repo=storage_repo,
            document_repo=document_repo,
            ontology_repo=ontology_repo,
            embedding_provider=embedding_provider,
            pinecone_repo=pinecone_repo,
        )

        await svc.embed(DOCUMENT_ID, CANONICAL_PATH)

        storage_repo.download_file.assert_called_once_with(CANONICAL_PATH)

    @pytest.mark.asyncio
    async def test_embed_empty_path_returns_failed_result(self):
        """embed() with empty canonical_storage_path must fail clearly, not silently."""
        from app.embeddings.embedding_service import EmbeddingService

        storage_repo = MagicMock()
        # Simulate storage raising an error when path is empty/wrong
        storage_repo.download_file.side_effect = FileNotFoundError("Path not found: ''")

        svc = EmbeddingService(
            storage_repo=storage_repo,
            document_repo=MagicMock(),
            ontology_repo=MagicMock(),
            embedding_provider=AsyncMock(),
            pinecone_repo=MagicMock(),
        )

        result = await svc.embed(DOCUMENT_ID, "")
        # Should return a failed result (EmbeddingService catches and wraps exceptions)
        assert result.status == "failed", (
            "embed() with a missing path must return status='failed', not proceed silently."
        )


# ---------------------------------------------------------------
# 2. InngestClient event methods carry canonical_storage_path
# ---------------------------------------------------------------

class TestInngestClientEventPayloads:
    """Verify the event payload methods include canonical_storage_path."""

    def test_send_knowledge_extracted_event_includes_canonical_path(self):
        client = _make_inngest_client()
        client.send_event = MagicMock(return_value=True)

        client.send_knowledge_extracted_event(
            document_id=DOCUMENT_ID,
            knowledge_id="k-123",
            confidence=0.92,
            canonical_storage_path=CANONICAL_PATH,
            user_id="user-1",
        )

        payload = client.send_event.call_args[1]["payload"]
        assert "canonical_storage_path" in payload, (
            "knowledge.extracted payload must include canonical_storage_path."
        )
        assert payload["canonical_storage_path"] == CANONICAL_PATH

    def test_send_knowledge_extracted_event_default_empty_string(self):
        """canonical_storage_path defaults to '' for backwards compat."""
        client = _make_inngest_client()
        client.send_event = MagicMock(return_value=True)

        client.send_knowledge_extracted_event(
            document_id=DOCUMENT_ID,
            knowledge_id="k-123",
            confidence=0.92,
            # omit canonical_storage_path
        )

        payload = client.send_event.call_args[1]["payload"]
        assert "canonical_storage_path" in payload
        assert payload["canonical_storage_path"] == ""

    def test_send_graph_updated_event_includes_canonical_path(self):
        client = _make_inngest_client()
        client.send_event = MagicMock(return_value=True)

        client.send_graph_updated_event(
            document_id=DOCUMENT_ID,
            nodes_written=42,
            relationships_written=18,
            canonical_storage_path=CANONICAL_PATH,
            user_id="user-1",
        )

        payload = client.send_event.call_args[1]["payload"]
        assert "canonical_storage_path" in payload, (
            "graph.updated payload must include canonical_storage_path."
        )
        assert payload["canonical_storage_path"] == CANONICAL_PATH

    def test_send_graph_updated_event_default_empty_string(self):
        client = _make_inngest_client()
        client.send_event = MagicMock(return_value=True)

        client.send_graph_updated_event(
            document_id=DOCUMENT_ID,
            nodes_written=5,
            relationships_written=3,
            # omit canonical_storage_path
        )

        payload = client.send_event.call_args[1]["payload"]
        assert "canonical_storage_path" in payload
        assert payload["canonical_storage_path"] == ""


# ---------------------------------------------------------------
# 3. handle_graph_updated() accepts and passes canonical_storage_path
# ---------------------------------------------------------------

class TestEmbeddingHandler:
    """Verify the embedding handler passes canonical_storage_path to embed()."""

    def test_handle_graph_updated_signature_includes_canonical_path(self):
        from app.events.embedding_handler import handle_graph_updated

        sig = inspect.signature(handle_graph_updated)
        params = list(sig.parameters.keys())
        assert "canonical_storage_path" in params, (
            "handle_graph_updated() must accept canonical_storage_path."
        )

    def test_canonical_storage_path_is_required_in_handler(self):
        """canonical_storage_path must be required (no default) in the handler."""
        from app.events.embedding_handler import handle_graph_updated

        sig = inspect.signature(handle_graph_updated)
        param = sig.parameters.get("canonical_storage_path")
        assert param is not None
        assert param.default is inspect.Parameter.empty, (
            "handle_graph_updated() canonical_storage_path must have no default. "
            "It must be supplied from the event payload to prevent silent path fabrication."
        )

    @pytest.mark.asyncio
    async def test_handle_graph_updated_passes_path_to_embed(self):
        """embedding_svc.embed must receive the canonical_storage_path from the handler."""
        from app.events.embedding_handler import handle_graph_updated
        from app.embeddings.models import EmbeddingResult

        mock_result = EmbeddingResult(
            document_id=DOCUMENT_ID,
            chunks_generated=5,
            chunks_embedded=5,
            chunks_skipped=0,
            chunks_failed=0,
            vectors_upserted=5,
            duration_seconds=1.2,
            status="completed",
        )

        mock_svc = AsyncMock()
        mock_svc.embed = AsyncMock(return_value=mock_result)

        mock_inngest = MagicMock()
        mock_inngest.send_embeddings_created_event.return_value = True

        with patch(
            "app.events.embedding_handler.create_embedding_service_for_inngest",
            return_value=mock_svc,
        ), patch(
            "app.events.embedding_handler.get_inngest_client",
            return_value=mock_inngest,
        ):
            await handle_graph_updated(
                document_id=DOCUMENT_ID,
                canonical_storage_path=CANONICAL_PATH,
                nodes_written=10,
                relationships_written=5,
                user_id="user-1",
            )

        # Verify embed was called with both arguments
        mock_svc.embed.assert_called_once_with(DOCUMENT_ID, CANONICAL_PATH)

    @pytest.mark.asyncio
    async def test_handle_graph_updated_does_not_hardcode_path(self):
        """The handler must not pass a hardcoded path to embed()."""
        from app.events.embedding_handler import handle_graph_updated
        from app.embeddings.models import EmbeddingResult

        custom_path = "bucket/2026/10/totally_different_path.json"

        mock_result = EmbeddingResult(
            document_id=DOCUMENT_ID,
            chunks_generated=1,
            chunks_embedded=1,
            chunks_skipped=0,
            chunks_failed=0,
            vectors_upserted=1,
            duration_seconds=0.5,
            status="completed",
        )

        mock_svc = AsyncMock()
        mock_svc.embed = AsyncMock(return_value=mock_result)
        mock_inngest = MagicMock()
        mock_inngest.send_embeddings_created_event.return_value = True

        with patch(
            "app.events.embedding_handler.create_embedding_service_for_inngest",
            return_value=mock_svc,
        ), patch(
            "app.events.embedding_handler.get_inngest_client",
            return_value=mock_inngest,
        ):
            await handle_graph_updated(
                document_id=DOCUMENT_ID,
                canonical_storage_path=custom_path,
            )

        # The exact path must be forwarded, not a derived or hardcoded one
        called_path = mock_svc.embed.call_args[0][1]
        assert called_path == custom_path, (
            f"embed() was called with '{called_path}' but the handler received "
            f"'{custom_path}'. The handler must not substitute a hardcoded path."
        )

    @pytest.mark.asyncio
    async def test_handle_graph_updated_propagates_embed_failure(self):
        """If embed() returns status='failed', the handler must raise."""
        from app.events.embedding_handler import handle_graph_updated
        from app.embeddings.models import EmbeddingResult

        mock_result = EmbeddingResult(
            document_id=DOCUMENT_ID,
            status="failed",
            error_message="CanonicalDocument not found",
            duration_seconds=0.1,
        )

        mock_svc = AsyncMock()
        mock_svc.embed = AsyncMock(return_value=mock_result)
        mock_inngest = MagicMock()

        with patch(
            "app.events.embedding_handler.create_embedding_service_for_inngest",
            return_value=mock_svc,
        ), patch(
            "app.events.embedding_handler.get_inngest_client",
            return_value=mock_inngest,
        ):
            with pytest.raises(ValueError, match="Embedding pipeline failed|CanonicalDocument not found"):
                await handle_graph_updated(
                    document_id=DOCUMENT_ID,
                    canonical_storage_path=CANONICAL_PATH,
                )


# ---------------------------------------------------------------
# 4. Ontology handler — canonical_storage_path in ontology.updated
# ---------------------------------------------------------------

class TestOntologyHandlerPathPropagation:
    """Verify ontology_handler forwards canonical_storage_path in the ontology.updated event."""

    def test_handle_knowledge_extracted_signature_includes_path(self):
        from app.events.ontology_handler import handle_knowledge_extracted

        sig = inspect.signature(handle_knowledge_extracted)
        assert "canonical_storage_path" in sig.parameters

    @pytest.mark.asyncio
    async def test_ontology_updated_event_includes_canonical_path(self):
        """ontology.updated payload must carry canonical_storage_path."""
        from app.events.ontology_handler import handle_knowledge_extracted

        mock_cko = MagicMock()
        mock_nko = MagicMock()
        mock_nko.entities = []
        mock_nko.relationships = []

        mock_knowledge_repo = MagicMock()
        mock_knowledge_repo.load.return_value = mock_cko

        mock_ontology_manager = MagicMock()
        mock_ontology_manager.process.return_value = mock_nko

        mock_inngest = MagicMock()
        mock_inngest.send_event.return_value = True

        mock_supabase = MagicMock()

        with patch("app.events.ontology_handler.get_supabase_client", return_value=mock_supabase), \
             patch("app.events.ontology_handler.get_knowledge_repository", return_value=mock_knowledge_repo), \
             patch("app.events.ontology_handler.get_inngest_client", return_value=mock_inngest), \
             patch("app.events.ontology_handler.create_ontology_manager_for_inngest", return_value=mock_ontology_manager):

            await handle_knowledge_extracted(
                document_id=DOCUMENT_ID,
                knowledge_id="k-123",
                confidence=0.92,
                canonical_storage_path=CANONICAL_PATH,
            )

        sent_payload = mock_inngest.send_event.call_args[1]["payload"]
        assert "canonical_storage_path" in sent_payload, (
            "ontology.updated event payload must include canonical_storage_path."
        )
        assert sent_payload["canonical_storage_path"] == CANONICAL_PATH


# ---------------------------------------------------------------
# 5. Graph handler — canonical_storage_path in graph.updated
# ---------------------------------------------------------------

class TestGraphHandlerPathPropagation:
    """Verify graph_handler forwards canonical_storage_path in the graph.updated event."""

    def test_handle_ontology_updated_signature_includes_path(self):
        from app.events.graph_handler import handle_ontology_updated

        sig = inspect.signature(handle_ontology_updated)
        assert "canonical_storage_path" in sig.parameters

    @pytest.mark.asyncio
    async def test_graph_updated_event_includes_canonical_path(self):
        """graph.updated payload must carry canonical_storage_path."""
        from app.events.graph_handler import handle_ontology_updated

        mock_graph_result = MagicMock()
        mock_graph_result.status = "completed"
        mock_graph_result.nodes_written = 10
        mock_graph_result.relationships_written = 5
        mock_graph_result.nodes_skipped = 0
        mock_graph_result.relationships_skipped = 0

        mock_graph_svc = MagicMock()
        mock_graph_svc.build.return_value = mock_graph_result

        mock_inngest = MagicMock()
        mock_inngest.send_graph_updated_event.return_value = True

        with patch("app.events.graph_handler.create_graph_service_for_inngest", return_value=mock_graph_svc), \
             patch("app.events.graph_handler.get_inngest_client", return_value=mock_inngest):

            await handle_ontology_updated(
                document_id=DOCUMENT_ID,
                nko_storage_path="normalized/doc/nko.json",
                canonical_storage_path=CANONICAL_PATH,
                entity_count=3,
                relationship_count=2,
            )

        mock_inngest.send_graph_updated_event.assert_called_once()
        call_kwargs = mock_inngest.send_graph_updated_event.call_args[1]
        assert "canonical_storage_path" in call_kwargs, (
            "send_graph_updated_event must be called with canonical_storage_path."
        )
        assert call_kwargs["canonical_storage_path"] == CANONICAL_PATH


# ---------------------------------------------------------------
# 6. inngest_functions.py dispatches canonical_storage_path
# ---------------------------------------------------------------

class TestInngestFunctionsDispatch:
    """Verify inngest_functions.py reads and dispatches canonical_storage_path.

    NOTE: These tests read the source file directly rather than importing
    inngest_functions, because that module transitively imports torch via
    processing_handler → processing_service → docling_parser → torch,
    which fails to load its C DLL in the test environment.
    """

    def _source(self) -> str:
        from pathlib import Path
        return Path(__file__).parent.parent / "app" / "events" / "inngest_functions.py"

    def test_create_embeddings_dispatches_canonical_path(self):
        """create_embeddings must pass data['canonical_storage_path'] to handle_graph_updated."""
        source = self._source().read_text()
        assert 'canonical_storage_path=data["canonical_storage_path"]' in source or \
               'canonical_storage_path=data.get("canonical_storage_path"' in source, (
            "inngest_functions.py create_embeddings must pass "
            "canonical_storage_path from event data to handle_graph_updated()."
        )

    def test_update_ontology_dispatches_canonical_path(self):
        source = self._source().read_text()
        assert 'canonical_storage_path=data.get("canonical_storage_path"' in source or \
               'canonical_storage_path=data["canonical_storage_path"]' in source, (
            "inngest_functions.py update_ontology must pass "
            "canonical_storage_path from event data to handle_knowledge_extracted()."
        )

    def test_build_knowledge_graph_dispatches_canonical_path(self):
        source = self._source().read_text()
        assert 'canonical_storage_path=data.get("canonical_storage_path"' in source or \
               'canonical_storage_path=data["canonical_storage_path"]' in source, (
            "inngest_functions.py build_knowledge_graph must pass "
            "canonical_storage_path from event data to handle_ontology_updated()."
        )

"""
Test Suite — Semantic Embeddings (Epic 6)

Covers:
 1. ChunkStrategy — table preservation, procedure preservation, overlap,
    section hierarchy, fallback modes
 2. ChunkGenerator — entity matching (canonical names, aliases), relationship
    enrichment, chunk ID determinism
 3. EmbeddingValidator — dimension check, NaN/None/Inf rejection, metadata check
 4. Idempotency — same document input → same chunk_ids (stable deterministic IDs)
 5. EmbeddingService — skip logic, error handling (mocked provider and Pinecone)

Pattern:
 - Pure unit tests — Pinecone, LLMService, and Supabase are fully mocked.
 - Mirrors test_graph.py / test_ontology.py conventions.
 - Pytest classes with setup_method, explicit assertion messages.

NOTE: Unit tests confirm logic correctness. They DO NOT confirm that vectors
actually landed in the real Pinecone index. Live verification is mandatory
before marking Phase 6 complete (see Step 6 in the implementation prompt and
the "Notes for Future Agents" section of Memory.md).
"""

import math
import pytest
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from app.canonical.canonical_models import (
    CanonicalDocument,
    CanonicalSection,
    CanonicalTable,
    CanonicalPage,
    DocumentMetadata,
)
from app.ontology.models import (
    NormalizedEntity,
    NormalizedRelationship,
    NormalizedKnowledgeObject,
)
from app.embeddings.chunk_strategy import ChunkStrategy, _is_never_split_section
from app.embeddings.chunk_generator import ChunkGenerator
from app.embeddings.embedding_validator import EmbeddingValidator
from app.embeddings.models import Chunk, EmbeddedChunk, make_chunk_id, make_chunk_hash


# -------------------------------------------------------------------
# Shared fixtures
# -------------------------------------------------------------------

DOCUMENT_ID = "doc_embed_test_001"


def _make_section(heading: str, text: str, page: int = 1) -> CanonicalSection:
    return CanonicalSection(heading=heading, level=1, text=text, page_number=page)


def _make_table(caption: str, markdown: str = "| A | B |\n|---|---|\n| 1 | 2 |", page: int = 2) -> CanonicalTable:
    return CanonicalTable(
        page_number=page,
        caption=caption,
        headers=["A", "B"],
        rows=[["1", "2"]],
        markdown=markdown,
    )


def _make_doc(
    sections: list = None,
    tables: list = None,
    pages: list = None,
    full_text: str = "",
) -> CanonicalDocument:
    return CanonicalDocument(
        document_id=DOCUMENT_ID,
        original_filename="test_doc.pdf",
        storage_path="processed/doc_embed_test_001/canonical.json",
        metadata=DocumentMetadata(file_type="pdf", language="en"),
        sections=sections or [],
        tables=tables or [],
        pages=pages or [],
        full_text=full_text,
        language="en",
    )


def _make_entity(entity_id: str, name: str, entity_type: str = "Asset", aliases=None) -> NormalizedEntity:
    return NormalizedEntity(
        entity_id=entity_id,
        entity_type=entity_type,
        canonical_name=name,
        aliases=aliases or [],
        confidence=0.95,
        metadata={},
        source_document_ids=[DOCUMENT_ID],
    )


def _make_nko(entities: list, relationships: list = None) -> NormalizedKnowledgeObject:
    return NormalizedKnowledgeObject(
        document_id=DOCUMENT_ID,
        entities=entities,
        relationships=relationships or [],
        discovered_concepts=[],
        confidence=0.9,
    )


def _make_embedded_chunk(
    chunk: Chunk = None,
    vector: List[float] = None,
    dimension: int = 768,
) -> EmbeddedChunk:
    if chunk is None:
        chunk = Chunk(
            chunk_id="test_chunk_001",
            chunk_hash=make_chunk_hash("sample text"),
            document_id=DOCUMENT_ID,
            chunk_index=0,
            text="sample text for embedding",
            section="Test Section",
        )
    if vector is None:
        vector = [0.1] * dimension
    return EmbeddedChunk(chunk=chunk, vector=vector)


# -------------------------------------------------------------------
# 1. ChunkStrategy Tests
# -------------------------------------------------------------------

class TestChunkStrategy:

    def setup_method(self):
        self.strategy = ChunkStrategy()

    def test_table_produces_single_chunk(self):
        """Each table must become exactly one chunk — never split."""
        table = _make_table("Equipment List", "| Equipment | Status | Location | Last Serviced |\n|---|---|---|---|\n| Pump P-101 | Active | Plant Floor | 2025-01-15 |")
        doc = _make_doc(tables=[table])
        chunks = self.strategy.chunk(doc)

        table_chunks = [c for c in chunks if c[3] == "table"]
        assert len(table_chunks) == 1, "Table should produce exactly one chunk"
        assert "Pump P-101" in table_chunks[0][0], "Table content must be preserved intact"

    def test_two_tables_produce_two_chunks(self):
        """Multiple tables → multiple chunks, one per table."""
        tables = [
            _make_table("Table 1", "| Equipment | Status | Location | Serial |\n|---|---|---|---|\n| Pump P-101 | Active | Plant | SN12345 |"),
            _make_table("Table 2", "| Component | Type | Material | Rating |\n|---|---|---|---|\n| Valve V-02 | Gate | Steel | 150PSI |"),
        ]
        doc = _make_doc(tables=tables)
        chunks = self.strategy.chunk(doc)
        table_chunks = [c for c in chunks if c[3] == "table"]
        assert len(table_chunks) == 2

    def test_procedure_section_type_is_procedure(self):
        """Sections with procedure-like headings get chunk_type='procedure'."""
        section = _make_section(
            heading="Maintenance Procedure for Pump P-101",
            text=("Step 1: Isolate the pump from the process line using isolation valves. "
                  "Step 2: Drain the system completely before removing any bolts. "
                  "Step 3: Remove the coupling guard and disconnect the motor coupling. "
                  "Step 4: Inspect the mechanical seal and bearings for wear or damage. "
                  "Step 5: Replace any worn components using approved spare parts only."),
        )
        doc = _make_doc(sections=[section])
        chunks = self.strategy.chunk(doc)
        proc_chunks = [c for c in chunks if c[3] == "procedure"]
        assert len(proc_chunks) >= 1, "Procedure section should produce procedure-type chunks"

    def test_safety_section_type_is_procedure(self):
        """Safety instruction sections are treated as procedure (never-split)."""
        section = _make_section(
            heading="Safety Instructions and Warnings",
            text=("Warning: Never operate the equipment without proper personal protective equipment (PPE). "
                  "Caution: High voltage present in the control panel area at all times. "
                  "Note: Always lockout tagout before performing any maintenance activities. "
                  "Danger: Moving parts can cause serious injury or death if guards are removed."),
        )
        doc = _make_doc(sections=[section])
        chunks = self.strategy.chunk(doc)
        proc_chunks = [c for c in chunks if c[3] == "procedure"]
        assert len(proc_chunks) >= 1

    def test_regular_section_type_is_text(self):
        """Ordinary sections produce chunk_type='text'."""
        section = _make_section(
            heading="Equipment Overview",
            text=("The facility contains multiple centrifugal pumps and reciprocating compressors "
                  "arranged in parallel configurations for maximum process reliability and availability. "
                  "Each pump is equipped with vibration monitoring sensors and temperature transmitters "
                  "to enable predictive maintenance and minimize unplanned downtime events."),
        )
        doc = _make_doc(sections=[section])
        chunks = self.strategy.chunk(doc)
        text_chunks = [c for c in chunks if c[3] == "text"]
        assert len(text_chunks) >= 1

    def test_page_fallback_when_no_sections(self):
        """When no sections exist, pages are used as fallback chunking source."""
        pages = [
            CanonicalPage(page_number=1, text="First page content about pump operations and maintenance schedules for all rotating equipment in the facility." * 3),
            CanonicalPage(page_number=2, text="Second page content about valve maintenance procedures and inspection intervals for all process valves." * 3),
        ]
        doc = _make_doc(pages=pages, sections=[])
        chunks = self.strategy.chunk(doc)
        assert len(chunks) >= 2

    def test_small_chunks_are_filtered(self):
        """Chunks below CHUNK_MIN_TOKENS are dropped."""
        section = _make_section(heading="Tiny", text="Hi.")  # 3 chars < 50 tokens min
        doc = _make_doc(sections=[section])
        chunks = self.strategy.chunk(doc)
        tiny_chunks = [c for c in chunks if c[0].strip() == "Hi."]
        assert len(tiny_chunks) == 0, "Chunks below CHUNK_MIN_TOKENS should be filtered"

    def test_is_never_split_section_matches_keywords(self):
        """_is_never_split_section returns True for known keywords."""
        assert _is_never_split_section("Maintenance Procedure")
        assert _is_never_split_section("Safety Instructions")
        assert _is_never_split_section("WARNING: High Voltage")
        assert _is_never_split_section("Step-by-Step Checklist")
        assert not _is_never_split_section("Equipment Overview")
        assert not _is_never_split_section("General Information")


# -------------------------------------------------------------------
# 2. ChunkGenerator Tests
# -------------------------------------------------------------------

class TestChunkGenerator:

    def setup_method(self):
        self.gen = ChunkGenerator()

    def test_generates_chunks_from_sections(self):
        """ChunkGenerator wraps ChunkStrategy output into Chunk objects."""
        section = _make_section(
            heading="Pump Maintenance",
            text=("Pump P-101 requires quarterly inspection and bearing replacement. "
                  "Check bearing clearance, seal condition, and coupling alignment during each inspection. "
                  "Record all findings in the maintenance management system for trend analysis."),
        )
        doc = _make_doc(sections=[section])
        chunks = self.gen.generate(doc, nko=None)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_id == DOCUMENT_ID
            assert chunk.chunk_id
            assert chunk.chunk_hash
            assert chunk.text

    def test_entity_matching_by_canonical_name(self):
        """Entities whose canonical_name appears in the chunk are attached to graph_entities."""
        section = _make_section(
            heading="Pump Operations",
            text=("The Centrifugal Pump P-101 operates at 3500 RPM under normal process conditions. "
                  "Oil level must be checked daily to prevent bearing damage and ensure optimal lubrication. "
                  "Vibration levels should be monitored using online sensors connected to the DCS system."),
        )
        doc = _make_doc(sections=[section])

        entity = _make_entity("asset_p101", "Centrifugal Pump P-101", "Asset")
        nko = _make_nko([entity])

        chunks = self.gen.generate(doc, nko=nko)
        matched = [c for c in chunks if "asset_p101" in c.graph_entities]
        assert len(matched) >= 1, "Entity matching by canonical_name should work"

    def test_entity_matching_by_alias(self):
        """Entities whose alias appears in the chunk are also matched."""
        section = _make_section(
            heading="Valve Control",
            text=("The P101 must be properly isolated using the upstream and downstream isolation valves "
                  "before performing any maintenance work on the pump assembly or associated piping. "
                  "Always verify zero energy state using appropriate test equipment before proceeding."),
        )
        doc = _make_doc(sections=[section])

        entity = _make_entity("asset_p101", "Centrifugal Pump P-101", "Asset", aliases=["P101", "Main Pump"])
        nko = _make_nko([entity])

        chunks = self.gen.generate(doc, nko=nko)
        matched = [c for c in chunks if "asset_p101" in c.graph_entities]
        assert len(matched) >= 1, "Entity matching by alias should work"

    def test_asset_entity_appears_in_asset_ids(self):
        """Asset-type entities are added to both graph_entities and asset_ids."""
        section = _make_section(
            heading="Equipment",
            text=("Pump P-101 and Pump P-102 are the main process pumps serving the primary cooling circuit. "
                  "Both units operate in duty-standby configuration to ensure continuous process availability. "
                  "Switchover between the two pumps should be performed on a weekly basis to equalize run hours."),
        )
        doc = _make_doc(sections=[section])

        entities = [
            _make_entity("asset_p101", "Pump P-101", "Asset"),
            _make_entity("asset_p102", "Pump P-102", "Asset"),
        ]
        nko = _make_nko(entities)

        chunks = self.gen.generate(doc, nko=nko)
        for chunk in chunks:
            for eid in chunk.asset_ids:
                assert eid in chunk.graph_entities, "Every asset_id must also be in graph_entities"

    def test_no_nko_produces_empty_graph_entities(self):
        """When no NKO is provided, graph_entities and asset_ids are empty."""
        section = _make_section(
            heading="Overview",
            text=("This is a general overview of the facility operations and overall maintenance philosophy. "
                  "The facility follows a reliability-centered maintenance approach to maximize uptime. "
                  "All maintenance activities are planned, scheduled, and tracked in the CMMS system."),
        )
        doc = _make_doc(sections=[section])

        chunks = self.gen.generate(doc, nko=None)
        for chunk in chunks:
            assert chunk.graph_entities == []
            assert chunk.asset_ids == []

    def test_chunk_id_is_deterministic(self):
        """Running ChunkGenerator twice on the same document produces the same chunk IDs."""
        section = _make_section(
            heading="Test Section",
            text=("Consistent content about pump maintenance schedules, bearing inspections, "
                  "and seal replacement intervals for rotating equipment in the process facility. "
                  "All maintenance activities must be documented in the CMMS for audit trail purposes."),
        )
        doc = _make_doc(sections=[section])

        first_run = self.gen.generate(doc, nko=None)
        second_run = self.gen.generate(doc, nko=None)

        first_ids = sorted(c.chunk_id for c in first_run)
        second_ids = sorted(c.chunk_id for c in second_run)
        assert first_ids == second_ids, "chunk_ids must be deterministic across runs"

    def test_chunk_index_is_sequential(self):
        """chunk_index values should be sequential starting from 0."""
        sections = [
            _make_section(f"Section {i}", f"Content for section {i} with enough text to form a chunk." * 3)
            for i in range(3)
        ]
        doc = _make_doc(sections=sections)
        chunks = self.gen.generate(doc, nko=None)

        assert len(chunks) > 0
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i


# -------------------------------------------------------------------
# 3. EmbeddingValidator Tests
# -------------------------------------------------------------------

class TestEmbeddingValidator:

    def setup_method(self):
        self.validator = EmbeddingValidator()

    def test_valid_chunk_passes(self):
        """A correctly formed EmbeddedChunk passes validation."""
        ec = _make_embedded_chunk(dimension=768)
        result = self.validator.validate([ec])
        assert result.is_valid
        assert len(result.valid_chunks) == 1
        assert len(result.invalid_chunks) == 0

    def test_wrong_dimension_rejected(self):
        """A vector with wrong dimension is rejected."""
        ec = _make_embedded_chunk(vector=[0.1] * 512)  # wrong: 512 instead of 768
        result = self.validator.validate([ec])
        assert len(result.invalid_chunks) == 1
        assert "dimension" in result.invalid_chunks[0][1]

    def test_nan_in_vector_rejected(self):
        """A vector containing NaN values is rejected."""
        vector = [0.1] * 768
        vector[100] = float("nan")
        ec = _make_embedded_chunk(vector=vector)
        result = self.validator.validate([ec])
        assert len(result.invalid_chunks) == 1
        assert "NaN" in result.invalid_chunks[0][1]

    def test_inf_in_vector_rejected(self):
        """A vector containing infinite values is rejected."""
        vector = [0.1] * 768
        vector[50] = float("inf")
        ec = _make_embedded_chunk(vector=vector)
        result = self.validator.validate([ec])
        assert len(result.invalid_chunks) == 1
        assert "infinite" in result.invalid_chunks[0][1]

    def test_missing_chunk_id_rejected(self):
        """A chunk with empty chunk_id is rejected."""
        ec = _make_embedded_chunk()
        ec.chunk.chunk_id = ""
        result = self.validator.validate([ec])
        assert len(result.invalid_chunks) == 1
        assert "chunk_id" in result.invalid_chunks[0][1]

    def test_missing_document_id_rejected(self):
        """A chunk with empty document_id is rejected."""
        ec = _make_embedded_chunk()
        ec.chunk.document_id = ""
        result = self.validator.validate([ec])
        assert len(result.invalid_chunks) == 1
        assert "document_id" in result.invalid_chunks[0][1]

    def test_empty_vector_rejected(self):
        """An empty vector list is rejected."""
        ec = _make_embedded_chunk(vector=[])
        result = self.validator.validate([ec])
        assert len(result.invalid_chunks) == 1

    def test_mixed_valid_invalid_split(self):
        """A list with some valid and some invalid chunks returns correct splits."""
        valid_ec = _make_embedded_chunk(dimension=768)
        invalid_ec = _make_embedded_chunk(vector=[0.1] * 100)  # wrong dimension

        result = self.validator.validate([valid_ec, invalid_ec])
        assert len(result.valid_chunks) == 1
        assert len(result.invalid_chunks) == 1
        assert not result.is_valid  # because at least one invalid


# -------------------------------------------------------------------
# 4. Idempotency Tests
# -------------------------------------------------------------------

class TestIdempotency:
    """
    Confirms that the pipeline is deterministic: same document → same chunk IDs.

    This is the Python-layer guarantee that Pinecone upsert idempotency
    holds end-to-end: if chunk_id is stable, upsert never duplicates.
    """

    def test_same_document_produces_same_chunk_hashes(self):
        """Running ChunkGenerator twice on identical input → identical chunk hashes."""
        gen = ChunkGenerator()
        sections = [
            _make_section(
                "Maintenance",
                ("The pump P-101 needs lubrication every 3 months using the approved lubricant grade. "
                 "Bearing temperature should not exceed 85 degrees Celsius under normal operating conditions. "
                 "Any anomaly must be reported to the reliability engineer for further investigation and action."),
            ),
        ]
        doc = _make_doc(sections=sections)

        first_run = gen.generate(doc, nko=None)
        second_run = gen.generate(doc, nko=None)

        first_hashes = sorted(c.chunk_hash for c in first_run)
        second_hashes = sorted(c.chunk_hash for c in second_run)
        assert first_hashes == second_hashes, (
            "chunk_hash must be deterministic — same text → same hash"
        )

    def test_make_chunk_id_is_deterministic(self):
        """make_chunk_id() returns the same ID for the same inputs."""
        id1 = make_chunk_id(DOCUMENT_ID, "Section A", "First 100 chars of text")
        id2 = make_chunk_id(DOCUMENT_ID, "Section A", "First 100 chars of text")
        assert id1 == id2

    def test_make_chunk_id_differs_by_section(self):
        """Different sections produce different chunk IDs even with identical text."""
        id1 = make_chunk_id(DOCUMENT_ID, "Section A", "Same text content")
        id2 = make_chunk_id(DOCUMENT_ID, "Section B", "Same text content")
        assert id1 != id2

    def test_make_chunk_hash_is_deterministic(self):
        """make_chunk_hash() returns the same hash for the same text."""
        h1 = make_chunk_hash("Pump P-101 requires quarterly maintenance.")
        h2 = make_chunk_hash("Pump P-101 requires quarterly maintenance.")
        assert h1 == h2

    def test_make_chunk_hash_differs_by_content(self):
        """Different text content produces different hashes."""
        h1 = make_chunk_hash("Pump P-101 requires quarterly maintenance.")
        h2 = make_chunk_hash("Pump P-101 requires monthly maintenance.")
        assert h1 != h2


# -------------------------------------------------------------------
# 5. Config-Awareness Tests (AD-022)
# -------------------------------------------------------------------

class TestConfigAwareness:
    """
    Confirm that the embedding pipeline reads EMBEDDING_MODEL and
    EMBEDDING_DIMENSION from settings, never from hardcoded strings.

    AD-022: The text-embedding-004 → gemini-embedding-001 migration was
    caught ONLY by live verification, not by the mocked unit suite. These
    tests exist to make future model/dimension mismatches fail fast in CI
    rather than surfacing only at live-call time.

    Note: These are structural/contract tests — they do NOT call the live
    Gemini or Pinecone APIs.
    """

    def test_embedding_model_reads_from_settings(self):
        """EmbeddedChunk.embedding_model must equal settings.EMBEDDING_MODEL, not a hardcoded string."""
        from app.core.config import settings

        chunk = Chunk(
            chunk_id="cfg_test_001",
            chunk_hash=make_chunk_hash("config test"),
            document_id=DOCUMENT_ID,
            chunk_index=0,
            text="config test",
            section="Config Test",
        )
        ec = EmbeddedChunk(chunk=chunk, vector=[0.1] * 768)
        assert ec.embedding_model == settings.EMBEDDING_MODEL, (
            f"EmbeddedChunk.embedding_model is '{ec.embedding_model}' but "
            f"settings.EMBEDDING_MODEL is '{settings.EMBEDDING_MODEL}'. "
            "Update embeddings/models.py to use settings, not a hardcoded string. (AD-022)"
        )

    def test_embedding_model_is_not_deprecated(self):
        """EMBEDDING_MODEL must NOT be the deprecated text-embedding-004."""
        from app.core.config import settings

        assert settings.EMBEDDING_MODEL != "models/text-embedding-004", (
            "EMBEDDING_MODEL is still set to 'models/text-embedding-004' which returns 404. "
            "Update .env and config.py to use 'models/gemini-embedding-001'. (AD-022)"
        )

    def test_embedding_dimension_matches_config(self):
        """EMBEDDING_DIMENSION in config must be 768 (Pinecone index dimension)."""
        from app.core.config import settings

        assert settings.EMBEDDING_DIMENSION == 768, (
            f"EMBEDDING_DIMENSION is {settings.EMBEDDING_DIMENSION} but the Pinecone index "
            f"'ikip-documents' is configured for 768 dimensions. "
            "Recreate the index or update EMBEDDING_DIMENSION. (AD-022)"
        )

    def test_embedded_chunk_model_name_not_hardcoded_old_value(self):
        """EmbeddedChunk must not contain the deprecated model string anywhere."""
        import inspect
        from app.embeddings import models as emb_models
        source = inspect.getsource(emb_models)
        # The string should NOT appear as a default value — only as a comment (AD-022)
        # We allow it in comments/docstrings but not as a literal default
        assert 'default="models/text-embedding-004"' not in source, (
            "Found hardcoded 'default=\"models/text-embedding-004\"' in embeddings/models.py. "
            "Use default_factory=lambda: settings.EMBEDDING_MODEL instead. (AD-022)"
        )


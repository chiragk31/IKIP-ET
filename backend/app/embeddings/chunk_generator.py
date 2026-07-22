"""
Chunk Generator

Orchestrates chunking of a CanonicalDocument and enriches each chunk
with graph entity references from the NormalizedKnowledgeObject.

Pipeline:
    CanonicalDocument + NKO → ChunkStrategy → raw tuples → Chunk objects

Graph-aware enrichment (per Embeddings.md §Graph-Aware Chunks):
    For each chunk, scan the NKO's entities for any whose canonical_name
    or aliases appear as substrings in the chunk text (case-insensitive).
    Matching entity_ids are stored in chunk.graph_entities.
    Asset-type entity_ids are additionally stored in chunk.asset_ids.

    Relationship types are inferred: if two entities from the same
    NKO relationship both appear in the chunk, add the relationship type
    to chunk.graph_relationships.

This module does NOT call any external service — pure Python logic.
"""

import json
from typing import List, Optional
import structlog

from app.canonical.canonical_models import CanonicalDocument
from app.ontology.models import NormalizedKnowledgeObject
from app.embeddings.chunk_strategy import ChunkStrategy
from app.embeddings.models import Chunk, make_chunk_id, make_chunk_hash
from app.embeddings.constants import CHUNK_PIPELINE_VERSION

logger = structlog.get_logger(__name__)


class ChunkGenerator:
    """
    Generates semantic chunks from a CanonicalDocument, enriched with
    graph entity references from the NKO.

    Purpose:
        Produce a list of Chunk objects ready for embedding.
    Input:
        CanonicalDocument (text source) + NormalizedKnowledgeObject (graph metadata).
    Output:
        List[Chunk] with graph_entities, graph_relationships, and asset_ids populated.
    """

    def __init__(self) -> None:
        """Initialize ChunkGenerator with a ChunkStrategy."""
        self._strategy = ChunkStrategy()
        logger.info("chunk_generator_initialized")

    def generate(
        self,
        doc: CanonicalDocument,
        nko: Optional[NormalizedKnowledgeObject] = None,
    ) -> List[Chunk]:
        """
        Chunk a CanonicalDocument and attach NKO entity references.

        Args:
            doc: CanonicalDocument from Epic 2 (processed/{id}/canonical.json).
            nko: NormalizedKnowledgeObject from Epic 4 (normalized/{id}/nko.json).
                 If None, chunks are produced without graph enrichment.

        Returns:
            List of Chunk objects with full citation metadata.
        """
        logger.info(
            "chunk_generator_start",
            document_id=doc.document_id,
            has_nko=nko is not None,
        )

        # Step 1: Apply chunking strategy to get raw (text, section, page, type) tuples
        raw_chunks = self._strategy.chunk(doc)

        # Step 2: Build entity lookup table from NKO for fast matching
        entity_lookup = self._build_entity_lookup(nko)
        rel_lookup = self._build_relationship_lookup(nko)

        # Step 3: Wrap each raw chunk into a Chunk model with enrichment
        chunks: List[Chunk] = []
        for idx, (text, section, page, chunk_type) in enumerate(raw_chunks):
            # Deterministic IDs for idempotency
            chunk_id = make_chunk_id(doc.document_id, section, text[:100])
            chunk_hash = make_chunk_hash(text)

            # Graph enrichment: find NKO entities mentioned in this chunk
            graph_entities, asset_ids = self._match_entities(text, entity_lookup)
            graph_rels = self._match_relationships(
                text, entity_lookup, rel_lookup
            )

            chunk = Chunk(
                chunk_id=chunk_id,
                chunk_hash=chunk_hash,
                document_id=doc.document_id,
                chunk_index=idx,
                text=text,
                section=section,
                chunk_type=chunk_type,
                page_number=page,
                document_type=doc.metadata.file_type,
                language=doc.language,
                graph_entities=graph_entities,
                graph_relationships=graph_rels,
                asset_ids=asset_ids,
                chunk_pipeline_version=CHUNK_PIPELINE_VERSION,
            )
            chunks.append(chunk)

        logger.info(
            "chunk_generator_complete",
            document_id=doc.document_id,
            chunks_generated=len(chunks),
            chunks_with_entities=sum(1 for c in chunks if c.graph_entities),
        )
        return chunks

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    def _build_entity_lookup(
        self,
        nko: Optional[NormalizedKnowledgeObject],
    ) -> dict:
        """
        Build a dict mapping entity_id → {canonical_name, aliases, entity_type}
        for fast substring matching.

        Args:
            nko: NKO to build the lookup from (may be None).

        Returns:
            Dict keyed by entity_id, or empty dict if no NKO.
        """
        if not nko:
            return {}

        lookup = {}
        for entity in nko.entities:
            names = [entity.canonical_name.lower()] + [
                a.lower() for a in (entity.aliases or [])
            ]
            lookup[entity.entity_id] = {
                "names": names,
                "entity_type": entity.entity_type,
            }
        return lookup

    def _build_relationship_lookup(
        self,
        nko: Optional[NormalizedKnowledgeObject],
    ) -> list:
        """
        Build a list of (source_id, relationship_type, target_id) tuples
        from the NKO for relationship enrichment.

        Args:
            nko: NKO to build from (may be None).

        Returns:
            List of relationship triples.
        """
        if not nko:
            return []
        return [
            (r.source_id, r.relationship, r.target_id)
            for r in (nko.relationships or [])
        ]

    def _match_entities(
        self,
        text: str,
        entity_lookup: dict,
    ) -> tuple:
        """
        Find entity_ids whose canonical_name or aliases appear in the chunk text.

        Logs a debug line for each match so future engineers can tune the heuristic.

        Args:
            text: Chunk text to search.
            entity_lookup: Dict from _build_entity_lookup().

        Returns:
            Tuple of (matched_entity_ids: List[str], asset_ids: List[str]).
        """
        lower_text = text.lower()
        matched_ids: List[str] = []
        asset_ids: List[str] = []

        for entity_id, info in entity_lookup.items():
            found = any(name in lower_text for name in info["names"])
            if found:
                matched_ids.append(entity_id)
                if info["entity_type"] == "Asset":
                    asset_ids.append(entity_id)

        return matched_ids, asset_ids

    def _match_relationships(
        self,
        text: str,
        entity_lookup: dict,
        rel_lookup: list,
    ) -> List[str]:
        """
        Find relationship types where BOTH source and target entities appear in the chunk.

        Args:
            text: Chunk text.
            entity_lookup: Dict from _build_entity_lookup().
            rel_lookup: List from _build_relationship_lookup().

        Returns:
            List of relationship type strings (deduplicated).
        """
        lower_text = text.lower()
        rel_types: set = set()

        for source_id, rel_type, target_id in rel_lookup:
            source_info = entity_lookup.get(source_id)
            target_info = entity_lookup.get(target_id)
            if not source_info or not target_info:
                continue
            source_in_text = any(n in lower_text for n in source_info["names"])
            target_in_text = any(n in lower_text for n in target_info["names"])
            if source_in_text and target_in_text:
                rel_types.add(rel_type)

        return list(rel_types)

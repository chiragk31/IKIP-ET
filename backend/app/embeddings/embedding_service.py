"""
Embedding Service

Orchestrates the complete embedding pipeline for a single document:

    1. Load CanonicalDocument from Supabase Storage
       (processed/{document_id}/canonical.json)
    2. Load NKO from Supabase Storage
       (normalized/{document_id}/nko.json)
    3. ChunkGenerator → List[Chunk]
    4. Idempotency check: fetch existing chunk IDs from Pinecone;
       mark already-embedded chunks as "skip" (explicit + logged)
    5. EmbeddingProvider.embed_batch() → List[List[float]]
       (batched, per Embeddings.md §Performance)
    6. Wrap into EmbeddedChunk objects
    7. EmbeddingValidator.validate() → ValidationResult
    8. PineconeRepository.upsert_chunks() (batch upsert)
    9. Return EmbeddingResult with counts

Rules:
 - Never calls Pinecone SDK directly (PineconeRepository is the only gateway).
 - Never calls Gemini directly (routes through EmbeddingProvider → LLMService).
 - Never modifies the CanonicalDocument or NKO.
 - Logs start / complete / failure / duration on every run.
 - Chunk skips are explicit and logged (not silent).
"""

import json
import time
from typing import List, Optional
import structlog

from app.repositories.storage_repository import StorageRepository
from app.repositories.document_repository import DocumentRepository
from app.ontology.ontology_repository import OntologyRepository
from app.canonical.canonical_models import CanonicalDocument
from app.embeddings.chunk_generator import ChunkGenerator
from app.embeddings.embedding_provider import EmbeddingProvider
from app.embeddings.embedding_validator import EmbeddingValidator
from app.embeddings.pinecone_repository import PineconeRepository
from app.embeddings.models import Chunk, EmbeddedChunk, EmbeddingResult
from app.embeddings.constants import EMBEDDING_PIPELINE_VERSION

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """
    Orchestrates the CanonicalDocument → Pinecone embedding pipeline.

    Purpose:
        Load document artifacts, chunk, embed, validate, and upsert to Pinecone.
    Input:
        document_id — string ID of the document to embed.
    Output:
        EmbeddingResult with chunk counts, vector count, and status.
    """

    def __init__(
        self,
        storage_repo: StorageRepository,
        document_repo: DocumentRepository,
        ontology_repo: OntologyRepository,
        embedding_provider: EmbeddingProvider,
        pinecone_repo: PineconeRepository,
    ) -> None:
        """
        Initialize EmbeddingService.

        Args:
            storage_repo: For downloading canonical JSON from Supabase Storage.
            ontology_repo: For loading the NKO from Supabase Storage.
            embedding_provider: Provider abstraction (Google or future alternatives).
            pinecone_repo: Exclusive Pinecone gateway.
        """
        self._storage = storage_repo
        self._document_repo = document_repo
        self._ontology_repo = ontology_repo
        self._provider = embedding_provider
        self._pinecone = pinecone_repo
        self._chunk_gen = ChunkGenerator()
        self._validator = EmbeddingValidator()
        logger.info("embedding_service_initialized")

    async def embed(
    self,
    document_id: str,
    canonical_storage_path: str,
) -> EmbeddingResult:
        """
        Run the full embedding pipeline for a document.

        Args:
            document_id: ID of the document to embed.

        Returns:
            EmbeddingResult with chunk counts and status.
        """
        start_time = time.time()
        logger.info("embedding_service_start", document_id=document_id)

        try:
            # Step 1: Load CanonicalDocument
            canonical_doc = self._load_canonical_document(canonical_storage_path)
            if canonical_doc is None:
                return self._fail(
                    document_id, start_time,
                    f"CanonicalDocument not found for {document_id}. "
                    "Run processing pipeline first."
                )

            # Step 2: Load NKO (optional — graph enrichment if available)
            nko = self._ontology_repo.load_nko(document_id)
            if nko is None:
                logger.warning(
                    "embedding_service_no_nko",
                    document_id=document_id,
                    note="Proceeding without graph enrichment.",
                )

            # Step 3: Generate chunks
            chunks: List[Chunk] = self._chunk_gen.generate(canonical_doc, nko)
            if not chunks:
                return self._fail(
                    document_id, start_time,
                    "No chunks generated — document may be empty."
                )

            # Step 3.5: Populate document name
            doc_name = "unknown"
            try:
                # get_by_id is synchronous — no 'await'
                doc_meta = self._document_repo.get_by_id(document_id)
                if doc_meta and doc_meta.original_filename:
                    doc_name = doc_meta.original_filename
                    logger.info("document_name_resolved", doc_id=document_id, name=doc_name)
                else:
                    logger.warning("document_name_missing_or_null", doc_id=document_id)
            except Exception as e:
                logger.error("document_name_lookup_failed", doc_id=document_id, error=str(e))

            for chunk in chunks:
                chunk.document_name = doc_name

            # Step 4: Idempotency check (explicit + logged, not silent)
            all_chunk_ids = [c.chunk_id for c in chunks]
            existing_ids = self._pinecone.fetch_existing_ids(all_chunk_ids)

            chunks_to_embed: List[Chunk] = []
            chunks_skipped = 0
            for chunk in chunks:
                if chunk.chunk_id in existing_ids:
                    logger.info(
                        "embedding_chunk_skip_existing",
                        chunk_id=chunk.chunk_id,
                        document_id=document_id,
                    )
                    chunks_skipped += 1
                else:
                    chunks_to_embed.append(chunk)

            # Step 5: Generate embeddings (batched)
            embedded_chunks: List[EmbeddedChunk] = []
            if chunks_to_embed:
                texts = [c.text for c in chunks_to_embed]
                vectors = await self._provider.embed_batch(texts)

                for chunk, vector in zip(chunks_to_embed, vectors):
                    embedded_chunks.append(EmbeddedChunk(
                        chunk=chunk,
                        vector=vector,
                        embedding_model=self._provider.model_name(),
                        embedding_pipeline_version=EMBEDDING_PIPELINE_VERSION,
                    ))

            # Step 6: Validate vectors before upsert
            validation = self._validator.validate(embedded_chunks)

            if validation.invalid_chunks:
                logger.warning(
                    "embedding_validation_failures",
                    document_id=document_id,
                    invalid_count=len(validation.invalid_chunks),
                )

            # Step 7: Upsert valid vectors to Pinecone
            vectors_upserted = 0
            if validation.valid_chunks:
                vectors_upserted = self._pinecone.upsert_chunks(validation.valid_chunks)

            duration = time.time() - start_time
            result = EmbeddingResult(
                document_id=document_id,
                chunks_generated=len(chunks),
                chunks_embedded=len(embedded_chunks),
                chunks_skipped=chunks_skipped,
                chunks_failed=len(validation.invalid_chunks),
                vectors_upserted=vectors_upserted,
                duration_seconds=round(duration, 2),
                status="completed",
            )

            logger.info(
                "embedding_service_complete",
                document_id=document_id,
                chunks_generated=result.chunks_generated,
                chunks_embedded=result.chunks_embedded,
                chunks_skipped=result.chunks_skipped,
                vectors_upserted=result.vectors_upserted,
                duration_seconds=result.duration_seconds,
            )
            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "embedding_service_failed",
                document_id=document_id,
                error=str(e),
                duration_seconds=round(duration, 2),
            )
            return EmbeddingResult(
                document_id=document_id,
                status="failed",
                error_message=str(e),
                duration_seconds=round(duration, 2),
            )

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    # 
    def _load_canonical_document(
        self,
        canonical_storage_path: str,
    ) -> Optional[CanonicalDocument]:
        """
        Download and deserialize the CanonicalDocument from Supabase Storage.

    Args:
        canonical_storage_path: Actual storage path of canonical.json

    Returns:
        CanonicalDocument if found, None otherwise.
    """
        logger.info(
            "embedding_loading_canonical",
            path=canonical_storage_path,
        )

        try:
            raw_bytes = self._storage.download_file(canonical_storage_path)
            data = json.loads(raw_bytes.decode("utf-8"))
            return self._dict_to_canonical(data)

        except Exception as e:
            logger.error(
                "embedding_canonical_load_failed",
                path=canonical_storage_path,
                error=str(e),
            )
        return None

    def _dict_to_canonical(self, data: dict) -> CanonicalDocument:
        """
        Reconstruct a CanonicalDocument from its serialized dict form.

        Mirrors the to_dict() format defined in canonical_models.py.

        Args:
            data: Deserialized JSON dict from storage.

        Returns:
            CanonicalDocument dataclass instance.
        """
        from app.canonical.canonical_models import (
            CanonicalDocument,
            DocumentMetadata,
            CanonicalPage,
            CanonicalSection,
            CanonicalTable,
            CanonicalImage,
        )

        meta_data = data.get("metadata", {})
        meta = DocumentMetadata(
            title=meta_data.get("title", ""),
            author=meta_data.get("author", ""),
            created_at=meta_data.get("created_at"),
            modified_at=meta_data.get("modified_at"),
            page_count=meta_data.get("page_count", 0),
            word_count=meta_data.get("word_count", 0),
            language=meta_data.get("language", "en"),
            file_type=meta_data.get("file_type", ""),
            file_size=meta_data.get("file_size", 0),
            image_count=meta_data.get("image_count", 0),
            table_count=meta_data.get("table_count", 0),
            parser_version=meta_data.get("parser_version", ""),
            ocr_version=meta_data.get("ocr_version"),
            pipeline_version=meta_data.get("pipeline_version", "1.0.0"),
        )

        pages = [
            CanonicalPage(
                page_number=p.get("page_number", 0),
                text=p.get("text", ""),
                ocr_applied=p.get("ocr_applied", False),
            )
            for p in data.get("pages", [])
        ]

        sections = [
            CanonicalSection(
                heading=s.get("heading", ""),
                level=s.get("level", 1),
                text=s.get("text", ""),
                page_number=s.get("page_number"),
            )
            for s in data.get("sections", [])
        ]

        tables = [
            CanonicalTable(
                page_number=t.get("page_number"),
                caption=t.get("caption", ""),
                headers=t.get("headers", []),
                rows=t.get("rows", []),
                markdown=t.get("markdown", ""),
            )
            for t in data.get("tables", [])
        ]

        return CanonicalDocument(
            document_id=data["document_id"],
            original_filename=data.get("original_filename", ""),
            storage_path=data.get("storage_path", ""),
            metadata=meta,
            pages=pages,
            sections=sections,
            tables=tables,
            full_text=data.get("full_text", ""),
            language=data.get("language", "en"),
            warnings=data.get("warnings", []),
            ocr_applied=data.get("ocr_applied", False),
            processing_time_seconds=data.get("processing_time_seconds", 0.0),
            processed_at=data.get("processed_at", ""),
        )

    def _fail(
        self,
        document_id: str,
        start_time: float,
        error_message: str,
    ) -> EmbeddingResult:
        """
        Return a failed EmbeddingResult with logging.

        Args:
            document_id: Document ID.
            start_time: Pipeline start time for duration calculation.
            error_message: Human-readable failure reason.

        Returns:
            EmbeddingResult with status="failed".
        """
        duration = time.time() - start_time
        logger.error(
            "embedding_service_failed",
            document_id=document_id,
            error=error_message,
            duration_seconds=round(duration, 2),
        )
        return EmbeddingResult(
            document_id=document_id,
            status="failed",
            error_message=error_message,
            duration_seconds=round(duration, 2),
        )

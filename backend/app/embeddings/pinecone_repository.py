"""
Pinecone Repository

The ONLY module that calls the Pinecone SDK directly (mirrors GraphRepository's
exclusivity pattern from Epic 5 — AD-003 analogous rule for Pinecone).

Responsibilities:
 - Batch upsert of embedded chunks into Pinecone.
 - Idempotent: uses chunk_id as the Pinecone vector ID directly.
   Pinecone upsert on an existing ID overwrites the record — it never
   creates duplicates. This is confirmed behavior from Pinecone docs.
 - Query vectors for semantic search with optional metadata filters.
 - Fetch existing vector IDs for idempotency pre-check.
 - Delete all vectors for a document (for re-embedding workflows).

No other module in the platform may call PineconeClient or the Pinecone
SDK directly. All Pinecone operations must flow through this repository.
"""

import time
from typing import Any, Dict, List, Optional
import structlog

from app.database.pinecone_client import PineconeClient
from app.embeddings.models import EmbeddedChunk
from app.embeddings.constants import (
    PINECONE_UPSERT_BATCH_SIZE,
    EMBEDDING_PIPELINE_VERSION,
)

logger = structlog.get_logger(__name__)


class PineconeRepository:
    """
    Repository for all Pinecone vector database operations.

    Purpose:
        Exclusive Pinecone SDK wrapper; all embedding/search operations
        go through this class.
    Input:
        EmbeddedChunk objects (upsert) or query vectors (search).
    Output:
        Upsert counts or raw Pinecone query results.
    """

    def __init__(self, pinecone_client: PineconeClient) -> None:
        """
        Initialize PineconeRepository.

        Args:
            pinecone_client: PineconeClient instance (injected via DI).
        """
        self._client = pinecone_client
        logger.info("pinecone_repository_initialized")

    def upsert_chunks(
        self,
        embedded_chunks: List[EmbeddedChunk],
        namespace: str = "",
    ) -> int:
        """
        Upsert a list of EmbeddedChunks into Pinecone in batches.

        Uses chunk_id as the Pinecone vector ID. Pinecone upsert on an
        existing ID overwrites the record — idempotency is guaranteed by
        the database, not by pre-checking existence.

        Args:
            embedded_chunks: List of EmbeddedChunk objects to store.
            namespace: Optional Pinecone namespace (default: "").

        Returns:
            Total number of vectors successfully upserted.
        """
        if not embedded_chunks:
            return 0

        start_time = time.time()
        total_upserted = 0

        for batch_start in range(0, len(embedded_chunks), PINECONE_UPSERT_BATCH_SIZE):
            batch = embedded_chunks[batch_start: batch_start + PINECONE_UPSERT_BATCH_SIZE]
            vectors = [self._to_pinecone_vector(ec) for ec in batch]

            self._client.upsert_vectors(vectors=vectors, namespace=namespace)
            total_upserted += len(vectors)

            logger.info(
                "pinecone_upsert_batch_done",
                batch_start=batch_start,
                batch_size=len(batch),
                total_upserted=total_upserted,
            )

        duration = time.time() - start_time
        logger.info(
            "pinecone_upsert_complete",
            total_upserted=total_upserted,
            duration_seconds=round(duration, 2),
        )
        return total_upserted

    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        namespace: str = "",
        filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query Pinecone for similar vectors.

        Args:
            vector: Query embedding vector (768-dim for text-embedding-004).
            top_k: Maximum results to return.
            namespace: Optional Pinecone namespace.
            filter: Optional Pinecone metadata filter dict.

        Returns:
            Raw Pinecone query response dict with 'matches' key.
        """
        start_time = time.time()
        logger.info(
            "pinecone_query_start",
            top_k=top_k,
            has_filter=filter is not None,
        )

        result = self._client.query_vectors(
            vector=vector,
            top_k=top_k,
            namespace=namespace,
            filter=filter,
            include_metadata=True,
        )

        matches = result.get("matches", [])
        duration = time.time() - start_time
        logger.info(
            "pinecone_query_complete",
            matches_found=len(matches),
            duration_seconds=round(duration, 2),
        )
        return result

    def fetch_existing_ids(
        self,
        chunk_ids: List[str],
        namespace: str = "",
    ) -> set:
        """
        Fetch which of the given chunk_ids already exist in Pinecone.

        Used by EmbeddingService for explicit idempotency logging
        (so we can report "N chunks skipped" rather than silently overwriting).
        Note: Pinecone upsert is idempotent regardless — this is for
        REPORTING, not for preventing corruption.

        Args:
            chunk_ids: List of chunk IDs to check.
            namespace: Optional Pinecone namespace.

        Returns:
            Set of chunk_ids that already exist in the index.

        Note:
            Pinecone's fetch() endpoint is used here. If it fails
            (e.g. network error), we return an empty set (conservative:
            all chunks will be upserted).
        """
        if not chunk_ids:
            return set()

        try:
            index = self._client._get_index()
            response = index.fetch(ids=chunk_ids, namespace=namespace)
            existing = set(response.get("vectors", {}).keys())
            logger.info(
                "pinecone_fetch_existing_ids",
                checked=len(chunk_ids),
                found_existing=len(existing),
            )
            return existing
        except Exception as e:
            logger.warning(
                "pinecone_fetch_existing_ids_failed",
                error=str(e),
                fallback="proceeding with upsert (safe — idempotent)",
            )
            return set()

    def delete_document_vectors(
        self,
        document_id: str,
        namespace: str = "",
    ) -> None:
        """
        Delete all vectors for a given document from Pinecone.

        Used when a document is re-embedded with a new pipeline version
        or when a document is deleted from the platform.

        Args:
            document_id: ID of the document whose vectors to delete.
            namespace: Optional Pinecone namespace.

        Note:
            Pinecone's delete-by-metadata is only available on non-Starter
            plans. This method uses metadata filter delete if available;
            otherwise logs a warning.
        """
        logger.info(
            "pinecone_delete_document_start",
            document_id=document_id,
        )
        try:
            index = self._client._get_index()
            # delete_by_metadata is a Pinecone paid tier feature.
            # On Starter/Free, this will raise — catch and log.
            index.delete(
                filter={"document_id": {"$eq": document_id}},
                namespace=namespace,
            )
            logger.info(
                "pinecone_delete_document_complete",
                document_id=document_id,
            )
        except Exception as e:
            logger.warning(
                "pinecone_delete_document_unsupported",
                document_id=document_id,
                error=str(e),
                note="delete-by-metadata may require a paid Pinecone plan",
            )

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    def _to_pinecone_vector(self, ec: EmbeddedChunk) -> Dict[str, Any]:
        """
        Convert an EmbeddedChunk to the Pinecone vector dict format.

        Pinecone metadata values must be strings, numbers, booleans, or
        lists of strings. Complex objects are excluded.

        Args:
            ec: EmbeddedChunk to convert.

        Returns:
            Dict with 'id', 'values', and 'metadata' keys.
        """
        chunk = ec.chunk

        metadata: Dict[str, Any] = {
            # Required for retrieval and filtering
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "section": chunk.section,
            "chunk_type": chunk.chunk_type,
            "language": chunk.language,
            "document_type": chunk.document_type,
            # Citation
            "text": chunk.text[:1000],  # Pinecone metadata has size limits; store preview
            # Graph-aware fields (per Embeddings.md §Graph-Aware Chunks)
            "graph_entities": chunk.graph_entities,
            "graph_relationships": chunk.graph_relationships,
            "asset_ids": chunk.asset_ids,
            # Idempotency
            "chunk_hash": chunk.chunk_hash,
            "pipeline_version": ec.embedding_pipeline_version,
            "embedding_model": ec.embedding_model,
            # Timestamps
            "created_at": chunk.created_at,
            "embedded_at": ec.embedded_at,
        }

        # Optional citation field
        if chunk.page_number is not None:
            metadata["page_number"] = chunk.page_number

        return {
            "id": chunk.chunk_id,      # chunk_id IS the Pinecone vector ID
            "values": ec.vector,
            "metadata": metadata,
        }

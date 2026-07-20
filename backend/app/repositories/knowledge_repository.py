"""
Knowledge Repository

Persists the Canonical Knowledge Object (CKO) and its metadata.

Architecture:
    ExtractionService → KnowledgeRepository → StorageRepository + SupabaseClient

Rules:
    - Services NEVER call Supabase SDK directly.
    - The full CKO JSON is stored in Supabase Storage (not DB columns).
    - Only metadata (IDs, counts, confidence, timestamps) is stored in the DB table.
    - The storage path pattern is: knowledge/{document_id}/cko.json

Table: `knowledge_extractions` (must be created via migration)
Storage path: knowledge/{document_id}/cko.json
"""

import json
import uuid
from datetime import datetime
from typing import Optional
import structlog

from app.database.supabase import SupabaseClient
from app.schemas.knowledge import CanonicalKnowledgeObject, KnowledgeRecord

logger = structlog.get_logger(__name__)

# Supabase storage bucket (reuse the same documents bucket)
STORAGE_BUCKET = "documents"
TABLE_NAME = "knowledge_extractions"


class KnowledgeRepository:
    """
    Repository for Canonical Knowledge Object persistence.

    Two-layer storage:
      1. Supabase Storage: Full CKO JSON blob at knowledge/{document_id}/cko.json
      2. Supabase DB table `knowledge_extractions`: Metadata record with reference

    Services use this repository to save and retrieve CKOs.
    """

    def __init__(self, supabase: SupabaseClient) -> None:
        """
        Initialize the KnowledgeRepository.

        Args:
            supabase: Injected Supabase client wrapper
        """
        self._supabase = supabase
        logger.info("knowledge_repository_initialized")

    # -----------------------------------------------
    # Storage Path Builder
    # -----------------------------------------------

    @staticmethod
    def _build_storage_path(document_id: str) -> str:
        """
        Build the Supabase Storage path for a CKO JSON blob.

        Pattern: knowledge/{document_id}/cko.json

        Args:
            document_id: Supabase document UUID

        Returns:
            Storage path string
        """
        return f"knowledge/{document_id}/cko.json"

    # -----------------------------------------------
    # Save CKO
    # -----------------------------------------------

    def save(self, cko: CanonicalKnowledgeObject) -> KnowledgeRecord:
        """
        Persist a Canonical Knowledge Object.

        Steps:
          1. Serialize CKO to JSON
          2. Upload JSON to Supabase Storage
          3. Insert metadata record in DB table

        Args:
            cko: Fully assembled Canonical Knowledge Object

        Returns:
            KnowledgeRecord with storage path and DB ID

        Raises:
            Exception: On storage or DB failure
        """
        record_id = str(uuid.uuid4())
        storage_path = self._build_storage_path(cko.document_id)

        logger.info(
            "knowledge_save_start",
            document_id=cko.document_id,
            knowledge_id=record_id,
            entity_count=len(cko.entities),
            relationship_count=len(cko.relationships),
        )

        # 1. Serialize CKO to JSON
        try:
            cko_json = cko.model_dump_json(indent=2)
        except Exception as e:
            logger.error(
                "knowledge_serialization_failed",
                document_id=cko.document_id,
                error=str(e),
            )
            raise

        # 2. Upload to Supabase Storage
        try:
            self._supabase.storage.from_(STORAGE_BUCKET).upload(
                path=storage_path,
                file=cko_json.encode("utf-8"),
                file_options={
                    "content-type": "application/json",
                    "upsert": "true",   # Allow overwrite on reprocessing
                },
            )
            logger.info(
                "knowledge_storage_upload_success",
                document_id=cko.document_id,
                storage_path=storage_path,
            )
        except Exception as e:
            logger.error(
                "knowledge_storage_upload_failed",
                document_id=cko.document_id,
                storage_path=storage_path,
                error=str(e),
            )
            raise

        # 3. Insert/upsert metadata record in DB
        record = KnowledgeRecord(
            id=record_id,
            document_id=cko.document_id,
            storage_path=storage_path,
            model_version=cko.model_version,
            prompt_version=cko.prompt_version,
            confidence=cko.confidence,
            entity_count=len(cko.entities),
            relationship_count=len(cko.relationships),
            measurement_count=len(cko.measurements),
            procedure_count=len(cko.procedures),
            risk_count=len(cko.risks),
            extraction_time_seconds=cko.extraction_time_seconds,
            extraction_timestamp=cko.extraction_timestamp,
            status="completed",
        )

        try:
            self._save_metadata_record(record)
        except Exception as e:
            logger.error(
                "knowledge_metadata_save_failed",
                document_id=cko.document_id,
                error=str(e),
            )
            # Non-fatal: storage blob was saved — log and continue
            logger.warning(
                "knowledge_metadata_save_fallback",
                note="CKO blob saved but DB metadata insert failed",
            )

        logger.info(
            "knowledge_save_complete",
            document_id=cko.document_id,
            knowledge_id=record_id,
            storage_path=storage_path,
            confidence=cko.confidence,
        )

        return record

    def save_failed(
        self,
        document_id: str,
        error_message: str,
        model_version: str = "",
        prompt_version: str = "1.0",
    ) -> KnowledgeRecord:
        """
        Persist a failure record when extraction fails.

        Ensures a traceable record exists even for failed extractions.

        Args:
            document_id: Document that failed extraction
            error_message: Failure reason
            model_version: LLM model used
            prompt_version: Prompt version used

        Returns:
            KnowledgeRecord with status='failed'
        """
        record_id = str(uuid.uuid4())
        record = KnowledgeRecord(
            id=record_id,
            document_id=document_id,
            storage_path="",
            model_version=model_version,
            prompt_version=prompt_version,
            confidence=0.0,
            extraction_time_seconds=0.0,
            extraction_timestamp=datetime.utcnow().isoformat(),
            status="failed",
            error_message=error_message[:500],  # Truncate long errors
        )

        try:
            self._save_metadata_record(record)
        except Exception as e:
            logger.error(
                "knowledge_failure_record_save_failed",
                document_id=document_id,
                error=str(e),
            )

        logger.warning(
            "knowledge_failed_record_saved",
            document_id=document_id,
            knowledge_id=record_id,
            error=error_message[:200],
        )

        return record

    # -----------------------------------------------
    # Load CKO
    # -----------------------------------------------

    def load(self, document_id: str) -> Optional[CanonicalKnowledgeObject]:
        """
        Load a CKO from Supabase Storage by document ID.

        Args:
            document_id: Supabase document UUID

        Returns:
            CanonicalKnowledgeObject if found, None otherwise
        """
        storage_path = self._build_storage_path(document_id)
        logger.info("knowledge_load_start", document_id=document_id)

        try:
            content = self._supabase.storage.from_(STORAGE_BUCKET).download(storage_path)
            data = json.loads(content.decode("utf-8"))
            cko = CanonicalKnowledgeObject.model_validate(data)
            logger.info("knowledge_load_success", document_id=document_id)
            return cko
        except Exception as e:
            logger.warning(
                "knowledge_load_failed",
                document_id=document_id,
                storage_path=storage_path,
                error=str(e),
            )
            return None

    def get_record(self, document_id: str) -> Optional[KnowledgeRecord]:
        """
        Retrieve knowledge extraction metadata record for a document.

        Args:
            document_id: Supabase document UUID

        Returns:
            KnowledgeRecord if found, None otherwise
        """
        logger.info("knowledge_record_get_start", document_id=document_id)
        try:
            response = (
                self._supabase.client.table(TABLE_NAME)
                .select("*")
                .eq("document_id", document_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if response.data:
                row = response.data[0]
                record = KnowledgeRecord(
                    id=row["id"],
                    document_id=row["document_id"],
                    storage_path=row.get("storage_path", ""),
                    model_version=row.get("model_version", ""),
                    prompt_version=row.get("prompt_version", "1.0"),
                    confidence=row.get("confidence", 0.0),
                    entity_count=row.get("entity_count", 0),
                    relationship_count=row.get("relationship_count", 0),
                    measurement_count=row.get("measurement_count", 0),
                    procedure_count=row.get("procedure_count", 0),
                    risk_count=row.get("risk_count", 0),
                    extraction_time_seconds=row.get("extraction_time_seconds", 0.0),
                    extraction_timestamp=row.get("extraction_timestamp", ""),
                    status=row.get("status", "unknown"),
                    error_message=row.get("error_message"),
                    created_at=row.get("created_at"),
                )
                logger.info("knowledge_record_get_success", document_id=document_id)
                return record
            logger.info("knowledge_record_not_found", document_id=document_id)
            return None
        except Exception as e:
            logger.error(
                "knowledge_record_get_failed",
                document_id=document_id,
                error=str(e),
            )
            return None

    # -----------------------------------------------
    # Internal Helpers
    # -----------------------------------------------

    def _save_metadata_record(self, record: KnowledgeRecord) -> None:
        """
        Insert or update the knowledge extraction metadata record in DB.

        Uses upsert on document_id to handle reprocessing gracefully.

        Args:
            record: KnowledgeRecord to persist

        Raises:
            Exception: On database error
        """
        data = {
            "id": record.id,
            "document_id": record.document_id,
            "storage_path": record.storage_path,
            "model_version": record.model_version,
            "prompt_version": record.prompt_version,
            "confidence": record.confidence,
            "entity_count": record.entity_count,
            "relationship_count": record.relationship_count,
            "measurement_count": record.measurement_count,
            "procedure_count": record.procedure_count,
            "risk_count": record.risk_count,
            "extraction_time_seconds": record.extraction_time_seconds,
            "extraction_timestamp": record.extraction_timestamp,
            "status": record.status,
            "error_message": record.error_message,
        }

        try:
            self._supabase.client.table(TABLE_NAME).upsert(
                data,
                on_conflict="document_id",
            ).execute()
        except Exception as e:
            # Table might not exist yet — log prominently
            logger.error(
                "knowledge_db_upsert_failed",
                table=TABLE_NAME,
                document_id=record.document_id,
                error=str(e),
                hint="Run the knowledge_extractions migration if table does not exist",
            )
            raise

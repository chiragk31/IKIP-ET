"""
Document Repository

Wraps Supabase Database SDK for all document metadata CRUD operations.

Architecture:
    DocumentService → DocumentRepository → SupabaseClient → Supabase DB

Rules:
    - Services NEVER call Supabase SDK directly.
    - All DB operations go through this repository.
    - Never store AI output or extracted text here.
    - Never store file content here (use StorageRepository for files).

Table: `documents` and `processing_jobs`
"""

from typing import Optional, List, Dict, Any
import structlog

from app.database.supabase import SupabaseClient
from app.models.document import DocumentModel, ProcessingJobModel, _parse_dt

logger = structlog.get_logger(__name__)


class DocumentRepository:
    """
    Repository for Supabase `documents` and `processing_jobs` table operations.

    Provides create, read, update, delete for document metadata.
    Returns DocumentModel instances (never raw Supabase dicts to services).
    """

    def __init__(self, supabase: SupabaseClient) -> None:
        """
        Initialize the DocumentRepository.

        Args:
            supabase: Supabase client wrapper (injected)
        """
        self._supabase = supabase
        logger.info("document_repository_initialized")

    # -------------------------------------------
    # Document CRUD
    # -------------------------------------------

    def create(self, document: DocumentModel) -> DocumentModel:
        """
        Insert a new document record into Supabase.

        Args:
            document: DocumentModel to persist

        Returns:
            DocumentModel with any server-generated fields (created_at, etc.)

        Raises:
            Exception: If insert fails
        """
        logger.info(
            "document_create_start",
            document_id=document.id,
            filename=document.filename,
        )

        try:
            data = document.to_dict()
            response = (
                self._supabase.client.table("documents")
                .insert(data)
                .execute()
            )

            if response.data:
                created = DocumentModel.from_dict(response.data[0])
                logger.info(
                    "document_create_success",
                    document_id=created.id,
                    filename=created.filename,
                )
                return created

            raise RuntimeError("Supabase insert returned empty data")

        except Exception as e:
            logger.error(
                "document_create_failed",
                document_id=document.id,
                error=str(e),
            )
            raise

    def get_by_id(self, document_id: str) -> Optional[DocumentModel]:
        """
        Retrieve a document by its ID.

        Args:
            document_id: UUID of the document

        Returns:
            DocumentModel if found, None if not found

        Raises:
            Exception: On database error
        """
        logger.info("document_get_start", document_id=document_id)

        try:
            response = (
                self._supabase.client.table("documents")
                .select("*")
                .eq("id", document_id)
                .execute()
            )

            if response.data:
                doc = DocumentModel.from_dict(response.data[0])
                logger.info("document_get_success", document_id=document_id)
                return doc

            logger.info("document_get_not_found", document_id=document_id)
            return None

        except Exception as e:
            logger.error("document_get_failed", document_id=document_id, error=str(e))
            raise

    def list_all(
        self,
        page: int = 1,
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> tuple[List[DocumentModel], int]:
        """
        List documents with pagination and optional user filter.

        Args:
            page: Page number (1-indexed)
            limit: Number of items per page
            user_id: Filter by owner (None = all documents)

        Returns:
            Tuple of (list of DocumentModel, total count)

        Raises:
            Exception: On database error
        """
        offset = (page - 1) * limit
        logger.info("document_list_start", page=page, limit=limit, user_id=user_id)

        try:
            query = (
                self._supabase.client.table("documents")
                .select("*", count="exact")
                .order("upload_time", desc=True)
                .range(offset, offset + limit - 1)
            )

            if user_id:
                query = query.eq("user_id", user_id)

            response = query.execute()
            documents = [DocumentModel.from_dict(row) for row in (response.data or [])]
            total = response.count or len(documents)

            logger.info(
                "document_list_success",
                count=len(documents),
                total=total,
                page=page,
            )
            return documents, total

        except Exception as e:
            logger.error("document_list_failed", error=str(e))
            raise

    def update_status(
        self,
        document_id: str,
        status: str,
        processing_stage: Optional[str] = None,
    ) -> None:
        """
        Update the processing status of a document.

        Called by the processing pipeline as each stage completes.

        Args:
            document_id: UUID of the document
            status: New status value (must be a valid DocumentStatus enum value)
            processing_stage: Current pipeline stage label (optional)

        Raises:
            Exception: On database error
        """
        logger.info(
            "document_status_update_start",
            document_id=document_id,
            status=status,
            stage=processing_stage,
        )

        try:
            update_data: Dict[str, Any] = {"status": status}
            if processing_stage is not None:
                update_data["processing_stage"] = processing_stage

            self._supabase.client.table("documents").update(update_data).eq("id", document_id).execute()

            logger.info(
                "document_status_update_success",
                document_id=document_id,
                status=status,
            )

        except Exception as e:
            logger.error(
                "document_status_update_failed",
                document_id=document_id,
                error=str(e),
            )
            raise

    def delete(self, document_id: str) -> None:
        """
        Delete a document record from Supabase.

        Note: This does NOT delete the file from storage.
        The caller is responsible for calling StorageRepository.delete_file().

        Args:
            document_id: UUID of the document

        Raises:
            Exception: On database error
        """
        logger.info("document_delete_start", document_id=document_id)

        try:
            self._supabase.client.table("documents").delete().eq("id", document_id).execute()
            logger.info("document_delete_success", document_id=document_id)
        except Exception as e:
            logger.error("document_delete_failed", document_id=document_id, error=str(e))
            raise

    # -------------------------------------------
    # Processing Jobs
    # -------------------------------------------

    def create_processing_job(self, job: ProcessingJobModel) -> ProcessingJobModel:
        """
        Insert a new processing job record.

        Called by the processing pipeline as each stage begins.

        Args:
            job: ProcessingJobModel to persist

        Returns:
            ProcessingJobModel with server-generated fields

        Raises:
            Exception: On database error
        """
        logger.info(
            "processing_job_create_start",
            job_id=job.id,
            document_id=job.document_id,
            job_type=job.job_type,
        )

        try:
            response = (
                self._supabase.client.table("processing_jobs")
                .insert(job.to_dict())
                .execute()
            )

            if response.data:
                logger.info("processing_job_create_success", job_id=job.id)
                return job

            raise RuntimeError("Supabase insert returned empty data for processing_job")

        except Exception as e:
            logger.error("processing_job_create_failed", job_id=job.id, error=str(e))
            raise

    def get_jobs_for_document(self, document_id: str) -> List[ProcessingJobModel]:
        """
        Retrieve all processing jobs for a document.

        Args:
            document_id: Parent document UUID

        Returns:
            List of ProcessingJobModel sorted by creation time
        """
        try:
            response = (
                self._supabase.client.table("processing_jobs")
                .select("*")
                .eq("document_id", document_id)
                .order("created_at", desc=False)
                .execute()
            )

            jobs = []
            for row in (response.data or []):
                jobs.append(ProcessingJobModel(
                    id=row["id"],
                    document_id=row["document_id"],
                    job_type=row["job_type"],
                    status=row.get("status", "pending"),
                    started_at=_parse_dt(row.get("started_at")) if row.get("started_at") else None,
                    completed_at=_parse_dt(row.get("completed_at")) if row.get("completed_at") else None,
                    execution_time=row.get("execution_time"),
                    error_message=row.get("error_message"),
                    created_at=_parse_dt(row.get("created_at")),
                ))

            return jobs

        except Exception as e:
            logger.error("processing_job_list_failed", document_id=document_id, error=str(e))
            raise

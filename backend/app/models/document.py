"""
Document Model

Python dataclass representation of the `documents` Supabase table.

This is the internal domain object used by services and repositories.
It is NOT a Pydantic model — it represents the DB row as a Python object.

The data flow is:
    Supabase row dict → DocumentModel (internal) → DocumentSchema (API response)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class DocumentModel:
    """
    Internal representation of a document record.

    Mirrors the Supabase `documents` table columns.
    Created by DocumentRepository and passed between service layers.

    Args:
        id: UUID primary key
        user_id: Owner user ID (nullable until auth is implemented)
        filename: Sanitized filename used in storage
        original_filename: Original name as uploaded by user
        storage_path: Full path in Supabase storage bucket
        file_type: Detected file extension type (pdf, docx, etc.)
        file_size: File size in bytes
        upload_time: Timestamp of upload
        status: Current processing status
        processing_stage: Current step in the AI pipeline
        summary: AI-generated summary (set by processing pipeline)
        language: Detected language code (default: en)
        document_type: Classified document type (e.g., maintenance_report)
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    # Required fields
    filename: str
    original_filename: str
    storage_path: str
    file_type: str
    file_size: int

    # Auto-generated
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    upload_time: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Status tracking
    status: str = "queued"
    processing_stage: Optional[str] = None

    # AI-populated fields (set by processing pipeline, not upload)
    summary: Optional[str] = None
    language: str = "en"
    document_type: Optional[str] = None

    # Auth (deferred to Phase 10)
    user_id: Optional[str] = None

    def to_dict(self) -> dict:
        """
        Convert to a plain dictionary suitable for Supabase insert.

        Returns:
            Dict representation of all fields
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "storage_path": self.storage_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "upload_time": self.upload_time.isoformat(),
            "status": self.status,
            "processing_stage": self.processing_stage,
            "summary": self.summary,
            "language": self.language,
            "document_type": self.document_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DocumentModel":
        """
        Create a DocumentModel from a Supabase row dictionary.

        Args:
            data: Raw row dictionary from Supabase

        Returns:
            DocumentModel instance
        """
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id"),
            filename=data["filename"],
            original_filename=data["original_filename"],
            storage_path=data["storage_path"],
            file_type=data["file_type"],
            file_size=data.get("file_size", 0),
            upload_time=_parse_dt(data.get("upload_time")),
            status=data.get("status", "queued"),
            processing_stage=data.get("processing_stage"),
            summary=data.get("summary"),
            language=data.get("language", "en"),
            document_type=data.get("document_type"),
            created_at=_parse_dt(data.get("created_at")),
            updated_at=_parse_dt(data.get("updated_at")),
        )


@dataclass
class ProcessingJobModel:
    """
    Internal representation of a processing_jobs table row.

    One document can have multiple processing jobs (one per pipeline stage).

    Args:
        document_id: Parent document ID
        job_type: Type of processing job (parsing, ocr, knowledge_extraction, etc.)
        status: Current job status (pending, running, completed, failed)
        id: UUID primary key (auto-generated)
        started_at: When the job started running
        completed_at: When the job finished
        execution_time: Duration in seconds
        error_message: Error detail if status is failed
    """

    document_id: str
    job_type: str

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to Supabase-insertable dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "job_type": self.job_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
        }


def _parse_dt(value) -> datetime:
    """
    Safely parse a datetime value from a Supabase response.

    Args:
        value: String, datetime, or None

    Returns:
        Parsed datetime or utcnow() as fallback
    """
    if value is None:
        return datetime.utcnow()
    if isinstance(value, datetime):
        return value
    try:
        # Handle ISO 8601 with timezone offset
        from datetime import timezone
        if isinstance(value, str):
            value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value).replace(tzinfo=None)
    except (ValueError, TypeError):
        pass
    return datetime.utcnow()

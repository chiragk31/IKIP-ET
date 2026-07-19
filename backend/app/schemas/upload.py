"""
Upload Schemas

Pydantic request/response models for the document upload API.

All upload API endpoints use these schemas for type safety and validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# -----------------------------------------------
# Upload Request / Response
# -----------------------------------------------

class UploadResponse(BaseModel):
    """
    Response returned immediately after a successful file upload.

    The upload endpoint always returns 202 Accepted.
    Processing happens asynchronously in the background.
    """

    document_id: str = Field(..., description="Unique ID of the created document record")
    status: str = Field(default="queued", description="Initial processing status")
    filename: str = Field(..., description="Stored filename")
    original_filename: str = Field(..., description="Original filename as uploaded")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="Detected file type (pdf, docx, etc.)")
    upload_time: datetime = Field(..., description="Timestamp of upload")
    message: str = Field(default="Document uploaded successfully and queued for processing")


# -----------------------------------------------
# Document Schemas
# -----------------------------------------------

class DocumentSchema(BaseModel):
    """
    Full document representation returned by list/detail endpoints.

    Mirrors the Supabase `documents` table.
    """

    id: str
    user_id: Optional[str] = None
    filename: str
    original_filename: str
    storage_path: str
    file_type: str
    file_size: int
    upload_time: datetime
    status: str
    processing_stage: Optional[str] = None
    summary: Optional[str] = None
    language: Optional[str] = "en"
    document_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    documents: List[DocumentSchema]
    total: int
    page: int
    limit: int
    pages: int


class DocumentStatusResponse(BaseModel):
    """
    Processing status response for a specific document.

    Consumed by the frontend to poll for progress updates.
    """

    document_id: str
    status: str
    processing_stage: Optional[str] = None
    updated_at: datetime
    error: Optional[str] = None


# -----------------------------------------------
# Processing Job Schemas
# -----------------------------------------------

class ProcessingJobSchema(BaseModel):
    """Processing job record for a document pipeline stage."""

    id: str
    document_id: str
    job_type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    error_message: Optional[str] = None


# -----------------------------------------------
# Inngest Event Payload
# -----------------------------------------------

class DocumentUploadedEventPayload(BaseModel):
    """
    Payload for the `document.uploaded` Inngest event.

    Emitted by UploadService after every successful upload.
    Consumed by the Document Processing Pipeline (Epic 2).
    """

    document_id: str = Field(..., description="Document ID in Supabase")
    storage_path: str = Field(..., description="Full path in Supabase Storage bucket")
    mime_type: str = Field(..., description="MIME type of the uploaded file")
    file_size: int = Field(..., description="File size in bytes")
    original_filename: str = Field(..., description="Original filename for display")
    user_id: Optional[str] = Field(default=None, description="Uploader user ID (None if auth deferred)")

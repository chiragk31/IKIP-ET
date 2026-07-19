# 01-upload.md

# Epic 1 — Document Upload

Version: 1.0

Status: Planned

---

# Objective

Build a robust, scalable, and asynchronous document upload system.

This module is responsible only for accepting files, validating them, storing them, creating metadata, and triggering the AI pipeline.

No AI processing should occur directly inside the upload endpoint.

---

# References

Must follow:

- PRD.md
- Architecture.md
- Rules.md
- Database.md
- API.md

---

# Dependencies

Requires:

- Epic 0 completed
- Backend running
- Frontend running
- Supabase Storage configured
- Inngest configured

---

# Deliverables

✓ Upload API

✓ Upload UI

✓ File Validation

✓ Upload History

✓ Metadata Storage

✓ Processing Queue

✓ Event Trigger

---

# Architecture

```
User

↓

Next.js Upload Page

↓

Upload Service

↓

Document Service

↓

Document Repository

↓

Supabase Storage

↓

Metadata Repository

↓

Supabase Database

↓

Emit Event

↓

Inngest

↓

202 Accepted
```

---

# Important Architecture Rules

The Upload API **must never**:

- Parse documents
- Run OCR
- Call Gemini
- Generate embeddings
- Build Neo4j nodes
- Create summaries

Its responsibility ends after:

1. Saving the file
2. Saving metadata
3. Triggering an event

Everything else belongs to later epics.

---

# Folder Structure

Backend

```
backend/app/

api/v1/documents.py

services/

upload_service.py

document_service.py

repositories/

storage_repository.py

document_repository.py

schemas/

upload.py

models/

document.py
```

Frontend

```
features/upload/

components/

hooks/

services/

types/

pages/
```

---

# Task 1.1 — Storage Setup

## Goal

Prepare storage layer.

---

### Responsibilities

Create storage bucket.

Verify permissions.

Create folder hierarchy.

---

### Folder Structure

```
documents/

2026/

07/

maintenance_report.pdf
```

---

### Acceptance Criteria

✓ Upload bucket exists

✓ SDK uploads file successfully

---

# Task 1.2 — Storage Repository

## Goal

Abstract file storage.

---

### Responsibilities

Upload File

Delete File

Download File

Generate Public URL

Generate Signed URL

---

### Rules

Business logic must never communicate directly with Supabase SDK.

Always use

StorageRepository.

---

### Acceptance Criteria

✓ Repository reusable

---

# Task 1.3 — Metadata Repository

## Goal

Store metadata separately from files.

---

Metadata includes

- document_id
- filename
- original_filename
- mime_type
- file_size
- storage_path
- upload_time
- processing_status

---

### Rules

Never store extracted text here.

Never store AI output here.

---

### Acceptance Criteria

✓ Metadata saved

---

# Task 1.4 — Upload Service

## Goal

Coordinate upload workflow.

---

Workflow

Validate

↓

Upload Storage

↓

Save Metadata

↓

Emit Event

↓

Return Response

---

### Responsibilities

Validate request

Call Storage Repository

Call Metadata Repository

Emit Event

Return document_id

---

### Rules

No AI logic.

No OCR.

No parsing.

---

### Acceptance Criteria

✓ Service coordinates upload correctly

---

# Task 1.5 — Upload API

Endpoint

POST

/api/v1/documents/upload

---

Input

multipart/form-data

```
file
```

---

Response

```
{
    "document_id":"...",
    "status":"queued"
}
```

---

Status Code

202 Accepted

---

### Rules

Never block until processing completes.

Return immediately.

---

### Acceptance Criteria

✓ API uploads successfully

---

# Task 1.6 — Upload Validation

Supported

PDF

DOCX

PPTX

XLSX

TXT

CSV

PNG

JPG

JPEG

TIFF

---

Maximum Size

50 MB

---

Validation

Extension

MIME Type

File Size

Duplicate Filename

Corrupted Files

---

### Acceptance Criteria

✓ Invalid uploads rejected

---

# Task 1.7 — Upload UI

Components

Upload Zone

Progress Bar

File Preview

Upload History

Status Badge

Error Toast

---

Features

Drag & Drop

Click Upload

Multiple Files

Retry Upload

Cancel Upload

---

### Acceptance Criteria

✓ UX responsive

---

# Task 1.8 — Upload History

Display

File Name

Upload Time

Status

Size

Type

---

Status

Queued

Uploading

Uploaded

Processing

Completed

Failed

---

### Acceptance Criteria

✓ History updates automatically

---

# Task 1.9 — Event Creation

After upload

Emit

```
document.uploaded
```

Payload

```
{
    "document_id":"",
    "storage_path":"",
    "mime_type":""
}
```

---

### Rules

Never start parser directly.

Always use events.

---

### Acceptance Criteria

✓ Event received by Inngest

---

# Task 1.10 — Health Checks

Verify

Storage

Metadata

Upload API

Inngest Event

---

### Acceptance Criteria

✓ All checks pass

---

# Recommended Improvements (Mandatory)

## Split Setup and Integration

Instead of one large task, separate infrastructure from implementation.

Example

Task 1.1

Storage Setup

↓

Task 1.2

Storage Repository

↓

Task 1.3

Metadata Repository

↓

Task 1.4

Upload Service

↓

Task 1.5

Upload API

This produces cleaner commits and allows AI coding assistants to work on isolated tasks.

---

## Repository Pattern

Always follow

```
API

↓

Service

↓

Repository

↓

External SDK
```

Never call Supabase directly from the Service layer.

---

## Async Processing

Return immediately after upload.

Never wait for:

- OCR
- Parsing
- AI
- Embeddings

This keeps upload latency low and improves scalability.

---

## Error Handling

Return structured responses only.

```
{
    "status":"error",
    "message":"Invalid file type",
    "errors":{}
}
```

Never expose stack traces.

---

# Verification Checklist

✓ Upload API works

✓ Upload UI works

✓ Metadata saved

✓ File stored

✓ Event emitted

✓ Upload history visible

✓ Validation working

✓ Error handling implemented

✓ Logging enabled

✓ Unit tests pass

---

# Definition of Done

Epic 1 is complete when:

✓ User uploads a supported document.

✓ File is stored successfully.

✓ Metadata is persisted.

✓ `document.uploaded` event is emitted.

✓ API returns within acceptable response time.

✓ No AI processing occurs in the upload request.

✓ The system is ready for Epic 2 — Document Processing Pipeline.
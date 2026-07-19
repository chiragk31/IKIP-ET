# 02-processing.md

# Epic 2 — Document Processing Pipeline

Version: 1.0

Status: Planned

---

# Objective

Transform uploaded documents into structured textual content ready for AI processing.

This epic is responsible for orchestrating the processing pipeline, extracting raw content from various document types, and generating a canonical document representation.

This phase **does not perform any AI reasoning or knowledge extraction**.

---

# References

Must follow:

- PRD.md
- Architecture.md
- Rules.md
- Database.md
- API.md
- Prompts.md

---

# Dependencies

Requires:

- Epic 0 completed
- Epic 1 completed

---

# Deliverables

✓ Inngest Workflow

✓ Document Parser

✓ OCR Pipeline

✓ Metadata Extraction

✓ Canonical Document Object

✓ Processing Status Updates

✓ Error Handling

---

# Architecture

```
document.uploaded

↓

Inngest

↓

Document Loader

↓

Document Type Detection

↓

Docling Parser

↓

Needs OCR?

↓

Yes
↓

PaddleOCR

↓

Merge Content

↓

Canonical Document

↓

Store Processed Text

↓

Emit Event

↓

document.processed
```

---

# Responsibilities

This module is responsible for:

- Parsing documents
- Running OCR when required
- Extracting text
- Extracting tables
- Extracting images
- Extracting document metadata
- Building Canonical Document Object

This module must **NOT**

- Call Gemini
- Extract entities
- Create embeddings
- Build Neo4j graph
- Generate summaries

---

# Folder Structure

```
backend/app/

events/

processing_handler.py

parser/

document_loader.py

document_detector.py

docling_parser.py

ocr/

ocr_service.py

image_preprocessor.py

canonical/

canonical_builder.py

canonical_models.py

services/

processing_service.py
```

---

# Canonical Document Model

Every parser must output the same structure.

```json
{
  "document": {},
  "metadata": {},
  "pages": [],
  "sections": [],
  "tables": [],
  "images": [],
  "text": "",
  "language": "",
  "warnings": []
}
```

No downstream module should know whether the source was PDF, DOCX, or image.

---

# Task 2.1 — Inngest Workflow

## Goal

Create the processing workflow.

---

Trigger

```
document.uploaded
```

Pipeline

```
Load Document

↓

Detect File Type

↓

Extract Content

↓

OCR (Optional)

↓

Canonical Builder

↓

Store Result

↓

Emit document.processed
```

---

### Acceptance Criteria

✓ Event triggers automatically

✓ Retry works

✓ Failure handling works

---

# Task 2.2 — Document Type Detection

Supported Types

PDF

DOCX

PPTX

XLSX

TXT

CSV

PNG

JPEG

TIFF

---

Responsibilities

Determine parser

Determine OCR requirement

Determine MIME validation

---

### Acceptance Criteria

✓ Correct parser selected

---

# Task 2.3 — Docling Parser

## Goal

Extract structured document content.

---

Extract

Text

Tables

Lists

Headers

Footers

Page Numbers

Captions

Images

---

Rules

Never lose document hierarchy.

Maintain page order.

---

Acceptance Criteria

✓ Structured content extracted

---

# Task 2.4 — OCR Pipeline

Use

PaddleOCR

---

OCR only when

Image

Scanned PDF

Embedded Image

Low text confidence

---

Preprocessing

Deskew

Resize

Denoise

Contrast Enhancement

Rotation Correction

---

Output

```json
{
    "page":1,
    "text":"..."
}
```

---

Acceptance Criteria

✓ OCR only runs when necessary

---

# Task 2.5 — Canonical Builder

Goal

Normalize parser outputs.

---

Responsibilities

Merge OCR text

Merge Docling text

Normalize whitespace

Normalize encoding

Remove duplicated OCR blocks

Build Canonical Object

---

Rules

Every downstream module consumes only the Canonical Document.

Never expose parser-specific formats.

---

Acceptance Criteria

✓ Canonical Document generated

---

# Task 2.6 — Metadata Extraction

Extract

Document Title

Author

Creation Date

Modified Date

Language

Page Count

Image Count

Table Count

File Size

---

Acceptance Criteria

✓ Metadata extracted correctly

---

# Task 2.7 — Processed Storage

Store

Canonical JSON

Extracted Text

Metadata

Processing Duration

Parser Version

OCR Version

---

Rules

Store processed output separately from uploaded file.

Never overwrite original file.

---

Acceptance Criteria

✓ Processed document stored

---

# Task 2.8 — Processing Status

Statuses

Uploaded

Queued

Parsing

OCR

Normalizing

Completed

Failed

---

Frontend should poll or subscribe for updates.

---

Acceptance Criteria

✓ Status visible in UI

---

# Task 2.9 — Error Handling

Recoverable Errors

Temporary storage failure

OCR timeout

Retryable parser error

---

Non-Recoverable

Unsupported document

Corrupted file

Invalid encoding

---

Retry Policy

3 retries

Exponential backoff

Dead Letter Queue after repeated failures

---

Acceptance Criteria

✓ Failures logged correctly

---

# Task 2.10 — Emit Processing Event

After completion emit

```
document.processed
```

Payload

```json
{
  "document_id":"",
  "canonical_document":"",
  "processing_time":0
}
```

---

Acceptance Criteria

✓ Event received by AI Extraction module

---

# Recommended Improvements (Mandatory)

## Event-Driven Architecture

Never invoke processing directly from upload.

Always communicate using events.

```
Upload

↓

document.uploaded

↓

Processing

↓

document.processed
```

---

## Canonical Representation

Every parser should return a common document model.

Never allow downstream services to depend on Docling or PaddleOCR output formats.

This enables replacing parsers without affecting AI modules.

---

## Modular Parser Strategy

Implement a parser interface.

```
DocumentParser

↓

PDFParser

DOCXParser

ImageParser

SpreadsheetParser
```

Each parser should implement the same contract.

---

## OCR Optimization

Do not run OCR on every document.

Detection should decide whether OCR is necessary.

This significantly reduces processing time and API costs.

---

## Version Tracking

Store

Parser Version

OCR Version

Pipeline Version

These values should be stored with every processed document to support future migrations and debugging.

---

## Observability

Log

Processing Time

OCR Time

Parser Time

Failure Reason

Retry Count

Document Type

These metrics will later power the Dashboard.

---

# Verification Checklist

✓ Processing event received

✓ Parser selected correctly

✓ OCR executed only when required

✓ Canonical Document generated

✓ Metadata extracted

✓ Status updates visible

✓ Processed document stored

✓ document.processed event emitted

✓ Retry mechanism working

✓ Logging implemented

---

# Definition of Done

Epic 2 is complete when:

✓ Every supported document type can be processed.

✓ A Canonical Document Object is generated.

✓ OCR executes only when required.

✓ Processed content is stored separately from original files.

✓ The processing pipeline is fully event-driven.

✓ `document.processed` is emitted successfully.

✓ The system is ready for Epic 3 — AI Knowledge Extraction.
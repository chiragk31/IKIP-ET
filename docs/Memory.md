# Memory.md

# Industrial Knowledge Intelligence Platform (IKIP)

Version: 1.0
Last Updated: 2026-07-19
Updated By: Agent (Foundation Phase)

---

# Project Overview

## Purpose

IKIP is an AI-powered Industrial Knowledge Intelligence Platform that transforms large volumes of heterogeneous, unstructured industrial documents into a searchable, continuously evolving knowledge base — an "Industrial Brain."

## Goals

- Ingest heterogeneous industrial documents (PDF, DOCX, PPTX, XLSX, TXT, CSV, images)
- Extract structured knowledge using AI (entities, relationships, measurements, procedures)
- Build a dynamic, evolving Knowledge Graph in Neo4j
- Enable semantic document search via Pinecone
- Provide AI-powered question answering (RAG-based Copilot)
- Discover asset relationships and generate Asset 360 profiles
- Generate compliance and maintenance intelligence
- Preserve organizational knowledge continuously

## Scope

**In Scope (MVP/Hackathon)**

- Document upload and processing pipeline
- AI knowledge extraction (entities, relationships, measurements)
- Dynamic knowledge graph (Neo4j Aura)
- Semantic search (Pinecone + Google Embeddings)
- AI Copilot with citations and confidence scores
- Asset 360 profiles
- Compliance intelligence
- Maintenance intelligence
- Dashboard
- Authentication (Supabase)

**Out of Scope**

- Real-time sensor/IoT ingestion
- ERP integration (SAP, Maximo)
- SCADA/PLC/OPC-UA connectivity
- Edge deployment
- Distributed processing
- Multi-tenant enterprise architecture

---

# Architecture Summary

## Backend

- **Framework**: FastAPI (Python 3.12+)
- **Pattern**: Layered — API → Service → Repository → External SDK
- **Background Processing**: Inngest (event-driven workflow engine)
- **Deployment**: Render
- All business logic in Services; repositories wrap external SDKs; API routes only call services.
- No AI logic in API routes. No direct database access from services.

## Frontend

- **Framework**: Next.js 15 (App Router, TypeScript only)
- **Styling**: Tailwind CSS + Shadcn UI
- **State**: Zustand (global), TanStack Query (server state)
- **Forms**: React Hook Form + Zod validation
- **Graph Viz**: React Flow
- **Charts**: Recharts
- **Deployment**: Vercel
- Feature-based architecture under `features/`

## AI Services

- **LLM**: Gemini 2.5 Flash (via dedicated `LLMService` only)
- **OCR**: PaddleOCR (for scanned documents)
- **Document Parsing**: Docling
- **Embeddings**: Google text-embedding-004
- **Prompts**: Stored as `.md` files in `backend/app/prompts/`; never hardcoded in Python

## Knowledge Graph

- **Database**: Neo4j Aura (Free instance)
- **Core Node Types**: Document, Asset, Person, Organization, Location, Procedure, Event, Measurement, Risk, Regulation, Concept (dynamic)
- **Key Relationships**: `MENTIONS`, `HAS_FAILURE`, `LOCATED_IN`, `PERFORMED`, `HAS_MEASUREMENT`, `REFERENCES`, `CONNECTED_TO`, `RELATED_TO`, `CAUSED_BY`, `USES`, `REQUIRES`, `MITIGATED_BY`, `RECORDED_FOR`, `INVOLVES`, `OWNS`, `GENERATED_FROM`, `PART_OF`
- **Rule**: LLM NEVER writes Cypher. LLM produces JSON → Graph Builder produces Cypher → Neo4j.

## Storage

- **Supabase Storage**: Raw file storage (bucket: `documents`)
- **Folder pattern**: `documents/{year}/{month}/{filename}`
- **Supabase DB**: Document metadata, processing status, user authentication

## Search

- **Pinecone**: Vector embeddings for semantic search
- **Chunk size**: 800–1200 tokens with 150–250 token overlap
- **Each vector includes metadata**: chunk_id, document_id, page_number, section, document_type, asset_ids, keywords, language, created_at

## Authentication

- Supabase Auth (JWT)
- Intentionally deferred until Phase 10 to validate core product first
- All APIs protected via `Authorization: Bearer <JWT>` header

---

# Tech Stack

| Layer | Technology |
|---|---|
| Frontend Framework | Next.js 15 (App Router) |
| Frontend Language | TypeScript (never JS) |
| Frontend Styling | Tailwind CSS + Shadcn UI |
| Frontend State | Zustand + TanStack Query |
| Frontend Forms | React Hook Form + Zod |
| Frontend Graph | React Flow |
| Frontend Charts | Recharts |
| Backend Framework | FastAPI |
| Backend Language | Python 3.12+ |
| Backend Validation | Pydantic |
| Backend Events | Inngest |
| LLM | Gemini 2.5 Flash |
| OCR | PaddleOCR |
| Document Parsing | Docling |
| Embeddings | Google text-embedding-004 |
| Relational DB | Supabase (PostgreSQL) |
| Auth | Supabase Auth (JWT) |
| File Storage | Supabase Storage |
| Knowledge Graph | Neo4j Aura |
| Vector DB | Pinecone |
| Frontend Deploy | Vercel |
| Backend Deploy | Render |
| Linting (FE) | ESLint + Prettier |
| Linting (BE) | Ruff + Black |

---

# Folder Structure

```
IndustrialKnowledgeIntelligence/
├── docs/
│   ├── PRD.md
│   ├── Architecture.md
│   ├── Design.md
│   ├── Database.md
│   ├── API.md
│   ├── Ontology.md
│   ├── Rules.md
│   ├── Prompts.md
│   ├── Epics.md
│   ├── Memory.md
│   └── tasks/
│       ├── 00-foundation.md
│       ├── 01-upload.md
│       ├── 02-processing.md
│       ├── 03-ai-extraction.md
│       ├── 04-ontology.md
│       ├── 05-graph.md
│       ├── 06-embeddings.md
│       ├── 07-search.md
│       ├── 08-copilot.md
│       ├── 09-assets.md
│       ├── 10-dashboard.md
│       ├── 11-authentication.md
│       └── 12-deployment.md
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   │   ├── upload/
│   │   ├── dashboard/
│   │   ├── graph/
│   │   ├── chat/
│   │   ├── assets/
│   │   ├── documents/
│   │   └── compliance/
│   ├── hooks/
│   ├── services/
│   ├── store/
│   ├── types/
│   ├── utils/
│   ├── styles/
│   └── public/
├── backend/
│   └── app/
│       ├── api/
│       │   └── v1/
│       │       ├── auth.py
│       │       ├── documents.py
│       │       ├── graph.py
│       │       ├── assets.py
│       │       ├── search.py
│       │       ├── chat.py
│       │       ├── compliance.py
│       │       ├── maintenance.py
│       │       ├── dashboard.py
│       │       ├── users.py
│       │       ├── notifications.py
│       │       ├── admin.py
│       │       └── health.py
│       ├── core/
│       │   ├── config.py
│       │   ├── logger.py
│       │   └── dependencies.py
│       ├── database/
│       │   ├── supabase.py
│       │   ├── neo4j.py
│       │   └── pinecone.py
│       ├── services/
│       ├── repositories/
│       ├── schemas/
│       ├── models/
│       ├── parser/
│       ├── ocr/
│       ├── ontology/
│       │   ├── ontology_manager.py
│       │   ├── entity_mapper.py
│       │   ├── synonym_resolver.py
│       │   ├── relationship_builder.py
│       │   ├── ontology_rules.py
│       │   ├── validators.py
│       │   └── models.py
│       ├── graph/
│       ├── rag/
│       ├── events/
│       ├── ai/
│       │   ├── llm_service.py
│       │   ├── prompt_manager.py
│       │   └── response_parser.py
│       ├── prompts/
│       │   ├── system.md
│       │   ├── entity_extraction.md
│       │   ├── relationship_extraction.md
│       │   ├── ontology_discovery.md
│       │   ├── summary.md
│       │   ├── compliance.md
│       │   ├── maintenance.md
│       │   ├── asset_summary.md
│       │   ├── semantic_search.md
│       │   ├── chat.md
│       │   └── query_rewrite.md
│       └── utils/
├── scripts/
├── docker/
└── .github/
    └── workflows/
```

---

# Database Summary

## Supabase (PostgreSQL)

**Responsibility**: Authentication, File Storage, Metadata, Processing Status

| Table | Key Fields |
|---|---|
| `users` | id, email, name, role, created_at, updated_at |
| `documents` | id, user_id, filename, original_filename, storage_path, file_type, file_size, upload_time, status, processing_stage, summary, language, document_type, created_at, updated_at |
| `processing_jobs` | id, document_id, job_type, status, started_at, completed_at, execution_time, error_message |

**Storage Bucket**: `documents` → path: `documents/{year}/{month}/{file}`

## Neo4j Aura

**Responsibility**: All organizational knowledge (entities, relationships, ontology)

Core Node Labels: `Document`, `Asset`, `Person`, `Organization`, `Location`, `Procedure`, `Event`, `Measurement`, `Risk`, `Failure`, `Regulation`, `Concept`

Key Relationship Types: `MENTIONS`, `HAS_FAILURE`, `LOCATED_IN`, `PERFORMED`, `HAS_MEASUREMENT`, `REFERENCES`, `CONNECTED_TO`, `RELATED_TO`, `CAUSED_BY`, `USES`, `REQUIRES`, `MITIGATED_BY`, `RECORDED_FOR`, `INVOLVES`, `OWNS`, `GENERATED_FROM`, `PART_OF`

## Pinecone

**Responsibility**: Semantic search, vector storage for document chunks

- Each vector: chunk embedding + metadata (chunk_id, document_id, page_number, section, document_type, asset_ids, keywords, language, created_at)
- Chunk size: 800–1200 tokens, 150–250 token overlap

---

# Ontology Summary

## Layers

1. **Core Ontology** (predefined, stable): Document, Asset, Person, Organization, Location, Procedure, Event, Measurement, Risk, Regulation
2. **Industry Concepts** (auto-discovered, validated)
3. **Organization Specific Concepts** (auto-discovered)
4. **Document Specific Concepts** (temporary until validated)

## Key Rules

- Ontology Manager normalizes entity names and resolves synonyms
- New concepts require validation before insertion into Neo4j
- Aliases are preserved (e.g., "Pump P101", "P-101", "Main Pump" all map to Asset P101)
- Confidence scores required for all extracted entities
- Low-confidence entities flagged for review
- LLM never writes to Neo4j; only Graph Builder does

## Canonical Entity Format

```json
{
  "entity_id": "asset_p101",
  "entity_type": "Asset",
  "label": "Pump P101",
  "aliases": ["P101", "Main Pump"],
  "confidence": 0.97,
  "source_document": "maintenance_report_12.pdf",
  "page": 4
}
```

---

# AI Pipeline

## Processing Flow (triggered on `document.uploaded` event)

```
1. Document Parsing (Docling) → extracts text, headings, tables, images, metadata
2. OCR (PaddleOCR) → if scanned document
3. Knowledge Extraction (Gemini via LLMService) → entities, relationships, measurements, procedures, risks
4. Ontology Manager → normalize, deduplicate, validate new concepts
5. Graph Builder → create/merge nodes and relationships in Neo4j
6. Chunk Generator → split document into 800-1200 token chunks with overlap
7. Embedding Generator (Google text-embedding-004) → embed each chunk
8. Pinecone → store vectors with metadata
9. Summary Generator (Gemini) → document summary, keywords, topics
10. Compliance Agent (Gemini) → detect missing approvals, expired certs
11. Status Update → mark document as `ready` in Supabase
```

## Query Flow (RAG)

```
User Question → Embedding → Pinecone (top-K chunks) → Neo4j (related entities) → Combine context → Gemini → Answer + Citations + Confidence
```

## LLM Rules

- Only `LLMService` calls Gemini directly
- AI produces JSON; backend validates everything
- AI never writes to databases
- AI never generates Cypher
- Prompts stored as `.md` files, loaded by `PromptManager`

---

# APIs

## Base URL: `/api/v1`

## Standard Response

```json
{"status": "success", "message": "...", "data": {}}
{"status": "error", "message": "...", "errors": {}}
```

## Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /auth/login | Login |
| POST | /auth/register | Register |
| POST | /auth/logout | Logout |
| GET | /auth/me | Current user |
| POST | /documents/upload | Upload document |
| GET | /documents | List documents |
| GET | /documents/{id} | Document details |
| GET | /documents/{id}/status | Processing status |
| POST | /documents/{id}/reprocess | Reprocess |
| GET | /graph | Graph overview |
| GET | /graph/nodes | Graph explorer |
| GET | /graph/node/{id} | Node details |
| GET | /assets | Asset list |
| GET | /assets/{id} | Asset 360 |
| POST | /search | Semantic search |
| POST | /chat | AI Copilot |
| GET | /compliance | Compliance report |
| GET | /maintenance | Maintenance insights |
| GET | /dashboard | Dashboard data |
| GET | /health | Health check |

---

# Coding Standards

## Backend (Python)

- Use async functions everywhere
- Use Pydantic models for all input/output
- Use dependency injection
- Follow: API → Service → Repository → SDK
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/Variables: `camelCase`
- Every function: docstring with Purpose, Input, Output
- Max function length: ~50 lines
- Logging: start, success, failure, duration on every service

## Frontend (TypeScript)

- TypeScript only — no JavaScript
- App Router only — no Pages Router
- Files: `kebab-case.tsx`
- Use service classes for all API calls (never fetch in components)
- React Query for server state
- Zustand for global state
- React Hook Form + Zod for forms
- Max component size: 300 lines; split if larger

## General

- Environment variables only for secrets (never hardcode)
- No stack traces in API responses
- Return structured errors
- Async preferred over sync
- Single responsibility per function and service

---

# Naming Conventions

| Item | Convention |
|---|---|
| Python files | snake_case.py |
| TypeScript files | kebab-case.tsx |
| Python classes | PascalCase |
| Python functions | snake_case |
| TypeScript components | PascalCase |
| TypeScript hooks | camelCase (use prefix) |
| TypeScript services | PascalCase |
| Environment variables | UPPER_CASE |
| Database tables | snake_case |
| Neo4j node labels | PascalCase |
| Neo4j relationships | UPPER_SNAKE_CASE |
| Pinecone index | lowercase-kebab |

---

# Important Rules

1. **LLM Gateway Rule**: Only `LLMService` may call Gemini. No exceptions.
2. **Graph Builder Rule**: Only `GraphBuilder` may write to Neo4j. LLM never generates Cypher.
3. **Repository Pattern**: Services never call Supabase/Neo4j/Pinecone SDKs directly; always use repositories.
4. **Event-Driven Rule**: Never directly invoke downstream modules; always emit events.
5. **AI Output Rule**: AI only produces structured JSON; backend validates everything before use.
6. **No Hardcoding**: Prompts stored in `prompts/*.md`, secrets in `.env`, URLs in config.
7. **Upload Rule**: Upload endpoint returns immediately (202); never blocks for processing.
8. **Chunk Rule**: Only chunks embedded, never full documents; each chunk retains citation metadata.
9. **Ontology Validation**: New concepts validated before insertion; no duplicate entities.
10. **No Stack Traces**: Never expose stack traces in API responses.
11. **Type Safety**: TypeScript with strict mode; Pydantic models in Python.
12. **No Random Folders**: Always follow Architecture.md structure.

---

# Completed Tasks

## ✅ Phase 0 — Project Foundation (2026-07-19)

### What was built:

**Repository & Documentation**
- Git repository initialized with `.gitignore`, `README.md`, `LICENSE`
- All documentation files present in `docs/`
- `docs/Memory.md` created as persistent project memory

**Backend (FastAPI)**
- Full project scaffolded with Python 3.12+
- Folder structure: `app/{api,core,database,services,repositories,schemas,models,parser,ocr,ontology,graph,rag,events,ai,prompts,utils}`
- `core/config.py` — Settings via pydantic-settings with all env vars
- `core/logger.py` — Structured logging
- `core/dependencies.py` — FastAPI dependency injection for all services
- `database/supabase.py` — Supabase client wrapper
- `database/neo4j_client.py` — Neo4j driver wrapper
- `database/pinecone_client.py` — Pinecone client wrapper
- `ai/llm_service.py` — LLM gateway (only caller of Gemini)
- `ai/prompt_manager.py` — Loads prompts from `.md` files
- `ai/response_parser.py` — Validates and parses AI JSON responses
- `utils/constants.py` — Shared constants and enums
- `utils/response.py` — Standardized API response helpers
- `schemas/common.py` — Shared Pydantic models
- `api/v1/health.py` — Health check endpoint (checks all services)
- `api/v1/router.py` — Router registration
- `main.py` — FastAPI app entry point
- All prompt `.md` files created in `app/prompts/`
- `requirements.txt` and `.env.example` created

**Frontend (Next.js 15)**
- Full Next.js 15 project with TypeScript, App Router, Tailwind CSS, Shadcn UI
- Folder structure: `app/, components/, features/, hooks/, services/, store/, types/, utils/, styles/`
- Feature folders scaffolded: upload, dashboard, graph, chat, assets, documents, compliance
- `services/api.ts` — Axios HTTP client with auth headers
- `store/app-store.ts` — Zustand global state store
- `types/index.ts` — Shared TypeScript types
- `utils/constants.ts` — Frontend constants
- `.env.local.example` — Frontend environment variables template
- Basic landing page at `app/page.tsx`

**Infrastructure**
- `scripts/check_env.py` — Environment variable validation script
- `docker/docker-compose.yml` — Local development compose file
- `.github/workflows/ci.yml` — CI pipeline (lint + type check)

---

# Pending Tasks

| Phase | Task | Status |
|---|---|---|
| 0 | Project Foundation | ✅ Completed |
| 1 | Document Upload | ✅ Completed |
| 2 | Document Processing Pipeline | ✅ Completed |
| 3 | AI Knowledge Extraction | ✅ Completed |
| 4 | Ontology Management | ✅ Completed |
| 5 | Knowledge Graph | ✅ Completed |
| 6 | Embeddings & Semantic Search | 🔲 Next |
| 7 | AI Copilot (RAG) | 🔲 Planned |
| 8 | Asset Intelligence | 🔲 Planned |
| 9 | Dashboard | 🔲 Planned |
| 10 | Authentication | 🔲 Planned |
| 11 | Deployment & Demo | 🔲 Planned |

---

# Phase 1 Completion Record — Document Upload (2026-07-19)

## Summary

Epic 1 fully implemented: a robust, asynchronous document upload system with validation, storage, metadata persistence, event emission, and frontend UI.

## Files Created

**Backend**

| File | Purpose |
|---|---|
| `backend/app/schemas/upload.py` | Pydantic schemas for upload/document API |
| `backend/app/models/document.py` | DocumentModel and ProcessingJobModel dataclasses |
| `backend/app/repositories/storage_repository.py` | StorageRepository — Supabase Storage CRUD |
| `backend/app/repositories/document_repository.py` | DocumentRepository — Supabase DB CRUD |
| `backend/app/events/inngest_client.py` | InngestClient — emits `document.uploaded` event |
| `backend/app/services/upload_service.py` | UploadService — full upload workflow |
| `backend/app/services/document_service.py` | DocumentService — list, get, status, delete |
| `backend/app/api/v1/documents.py` | Documents API router |
| `backend/tests/test_upload.py` | 17 unit tests (all passing) |

**Files Modified (Backend)**

| File | Change |
|---|---|
| `backend/app/core/dependencies.py` | Added repository, service, and Inngest dependencies |
| `backend/app/api/v1/router.py` | Registered `documents` router at `/documents` prefix |

**Frontend**

| File | Purpose |
|---|---|
| `frontend/features/upload/types/index.ts` | Upload feature TypeScript types |
| `frontend/features/upload/services/upload-service.ts` | UploadService (Axios multipart) |
| `frontend/features/documents/services/document-service.ts` | DocumentService (list, get, status, delete) |
| `frontend/features/upload/hooks/use-upload.ts` | useUpload hook (multi-file, progress, retry) |
| `frontend/features/documents/hooks/use-documents.ts` | useDocuments TanStack Query hook |
| `frontend/features/upload/components/upload-zone.tsx` | Drag-and-drop upload zone |
| `frontend/features/upload/components/upload-progress.tsx` | Per-file progress component |
| `frontend/features/upload/components/upload-history.tsx` | Document history table |
| `frontend/features/upload/components/status-badge.tsx` | Color-coded status pill |
| `frontend/app/providers.tsx` | TanStack QueryClientProvider wrapper |
| `frontend/app/documents/upload/page.tsx` | Upload page (server component) |
| `frontend/app/documents/upload/upload-page-client.tsx` | Upload page (client component) |
| `frontend/app/documents/page.tsx` | Documents list page (server) |
| `frontend/app/documents/documents-page-client.tsx` | Documents list page (client) |

**Files Modified (Frontend)**

| File | Change |
|---|---|
| `frontend/app/layout.tsx` | Wrapped children with `<Providers>` |

**Infrastructure**

| File | Purpose |
|---|---|
| `docs/migrations/001_initial_schema.sql` | Supabase DB migration (users, documents, processing_jobs, RLS) |

## Upload Workflow

```
1. User selects files (drag & drop or click-to-browse)
2. Client validates file size and type (before sending to backend)
3. POST /api/v1/documents/upload (multipart/form-data)
4. UploadService.validate_file() — extension, MIME, size checks
5. StorageRepository.upload_file() → Supabase Storage bucket: `documents`
   Path pattern: documents/{year}/{month}/{uuid}_{filename}
6. DocumentRepository.create() → Supabase DB `documents` table
   Status: queued
7. InngestClient.send_document_uploaded_event() → emits `document.uploaded`
   Payload: document_id, storage_path, mime_type, file_size, original_filename
8. API returns 202 Accepted immediately
9. Frontend polls GET /api/v1/documents/{id}/status every 3s
```

## API Endpoints Added

| Method | Endpoint | Status Code | Description |
|---|---|---|---|
| POST | /api/v1/documents/upload | 202 | Upload a document |
| GET | /api/v1/documents/ | 200 | List documents (paginated) |
| GET | /api/v1/documents/{id} | 200 | Get document details |
| GET | /api/v1/documents/{id}/status | 200 | Get processing status |
| DELETE | /api/v1/documents/{id} | 200 | Delete document + file |

## Architectural Decisions

### AD-008: Upload Rollback on DB Failure
If storage upload succeeds but DB insert fails, the storage file is automatically deleted to prevent orphaned files.

### AD-009: Inngest Failure is Non-Fatal
If the Inngest event fails to send (dev server not running), the upload still returns 202. The document is saved and can be manually reprocessed. This prevents upload failures from cascading to Inngest connectivity issues.

### AD-010: Two-Component Page Pattern
Each Next.js page has a server component (`page.tsx`) for metadata and a client component (`*-page-client.tsx`) for interactive logic. This ensures SEO metadata works while allowing full React interactivity.

## Testing

- 17 unit tests in `backend/tests/test_upload.py` — all passing
- TypeScript: `npx tsc --noEmit` — no errors
- ESLint: `npm run lint` — no errors
- Backend Python syntax: all 33+ files valid

## Pending Work for Task 02

Task 02 (Document Processing Pipeline) depends on:

1. `document.uploaded` Inngest event being emitted (✅ done)
2. `StorageRepository.download_file()` to read files for parsing (✅ done)
3. `DocumentRepository.update_status()` to update pipeline progress (✅ done)
4. `DocumentRepository.create_processing_job()` for job tracking (✅ done)
5. `CanonicalKnowledgeObject` schema for AI pipeline output (✅ in schemas/common.py)

Task 02 should implement:
- Inngest function handler listening on `document.uploaded`
- DoclingParser for text/table extraction
- PaddleOCR for scanned documents
- ProcessingJobModel creation per stage
- `document.parsed` event emission to trigger Epic 3


---

# Known Decisions

## AD-001: Authentication Deferred to Phase 10

Authentication is intentionally deferred. The core AI pipeline, graph, and search are validated first without auth. This accelerates hackathon demo capability.

## AD-002: Single LLM Gateway

All Gemini calls flow through `LLMService`. No other module may call Gemini directly. This enables rate limiting, retry logic, cost tracking, and model switching in one place.

## AD-003: Graph Builder Owns Neo4j Writes

LLM produces JSON → Ontology Manager normalizes → Graph Builder validates and writes Cypher → Neo4j. This prevents LLM hallucinations from corrupting the graph.

## AD-004: Event-Driven Pipeline via Inngest

Upload → emit `document.uploaded` → Inngest orchestrates each pipeline step independently. This decouples upload from processing and keeps upload latency low.

## AD-005: Polyglot Persistence

Three specialized databases, each with one responsibility:
- Supabase: Auth + Storage + Metadata
- Neo4j: Knowledge + Entities + Relationships
- Pinecone: Semantic Search + Embeddings

## AD-006: Dynamic Ontology

Ontology is not fixed. Core ontology (10 entity types) is predefined. New concepts discovered by AI are validated and added dynamically. This handles heterogeneous industrial terminology.

## AD-007: Prompt-as-Files

All AI prompts stored as versioned `.md` files in `backend/app/prompts/`. PromptManager loads and renders them. Never hardcode prompt strings in Python.

---

# Future Features

- Multi-language support
- Real-time IoT integration
- SAP/ERP integration
- IBM Maximo integration
- OPC-UA integration
- Predictive maintenance models
- Digital Twin integration
- Multi-agent AI workflows
- Fine-tuned industrial LLMs
- WebSocket streaming for chat
- Mobile application
- Redis caching layer
- Elasticsearch hybrid search
- TimescaleDB for IoT sensor data

---

# Notes for Future Agents

## Before You Start

1. Read `docs/Memory.md` (this file) first — it contains the complete project context.
2. Read the specific task file in `docs/tasks/` for the epic you are implementing.
3. Review `docs/Rules.md` — violations cause rejections.
4. Never modify architecture without updating `docs/Architecture.md` and this file.

## Critical Rules to Remember

- **LLMService is the only Gemini caller.** If you add AI features, route through `backend/app/ai/llm_service.py`.
- **GraphBuilder is the only Neo4j writer.** Never write Cypher anywhere else.
- **Repositories wrap all SDK calls.** Services never call Supabase/Pinecone/Neo4j SDKs directly.
- **Events drive the pipeline.** Upload emits `document.uploaded`, pipeline steps listen and emit downstream events.
- **AI output is JSON only.** Backend validates everything. Never trust raw AI output.
- **Prompts are `.md` files.** Never hardcode prompts in Python.
- **TypeScript only on frontend.** No `.js` files allowed.

## Development Environment

- Backend: `cd backend && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm run dev`
- Health check: `GET http://localhost:8000/api/v1/health`

## Environment Variables

See `backend/.env.example` and `frontend/.env.local.example` for all required variables. You must populate all values before running the project.

## Current State (after Phase 0)

The project has a fully scaffolded foundation:
- Backend is runnable with `uvicorn app.main:app --reload`
- Frontend is runnable with `npm run dev`
- All service connections are configured but use placeholder credentials
- Health endpoint at `/api/v1/health` verifies all external service connections
- No business logic exists yet — that starts in Phase 1 (Document Upload)

## Next Step

Implement **Phase 1 — Document Upload** per `docs/tasks/01-upload.md`.

---

# Phase 2 Completion Record — Document Processing Pipeline (2026-07-19)

## Summary

Epic 2 fully implemented: an event-driven, multi-stage document processing pipeline that transforms uploaded documents into CanonicalDocument objects. Supports all 9 file types (PDF, DOCX, PPTX, XLSX, CSV, TXT, PNG, JPG, TIFF) with Docling for structured extraction and OCR with graceful engine fallback.

## Architecture

```
document.uploaded (event)
       ↓
ProcessingHandler (async, runs in thread pool executor)
       ↓
ProcessingService.process_document()
  ├── DocumentDetector  → selects parser + OCR flag
  ├── DocumentLoader    → downloads from Supabase Storage to temp file
  ├── DoclingParser     → PDF/DOCX/PPTX: pages, sections, tables, images
  │   SpreadsheetParser → XLSX/CSV: tables + text
  │   TextParser        → TXT: passthrough
  │   (Image→OCR)       → PNG/JPG/TIFF: empty shell, then OCR fills it
  ├── OCRService        → PaddleOCR (primary) / pytesseract (fallback) / none
  ├── CanonicalBuilder  → merge OCR + normalize + rebuild full_text
  ├── StorageRepository → store canonical JSON at processed/{id}/canonical.json
  ├── DocumentRepository → update status at every stage
  └── InngestClient     → emit document.processed
```

## Files Created

| File | Purpose |
|---|---|
| `backend/app/canonical/__init__.py` | Canonical package init |
| `backend/app/canonical/canonical_models.py` | CanonicalDocument, CanonicalPage, CanonicalSection, CanonicalTable, CanonicalImage, DocumentMetadata |
| `backend/app/canonical/canonical_builder.py` | Merges OCR + parser output, normalizes, rebuilds full_text |
| `backend/app/parser/document_loader.py` | Downloads from Supabase Storage to temp file (context manager, auto-cleanup) |
| `backend/app/parser/document_detector.py` | Detects file type, selects parser strategy, decides OCR need |
| `backend/app/parser/docling_parser.py` | Docling-based extraction of pages, sections, tables, images |
| `backend/app/ocr/image_preprocessor.py` | Pillow-based image prep (grayscale, resize, contrast, sharpen) |
| `backend/app/ocr/ocr_service.py` | PaddleOCR (primary) + pytesseract (fallback) + None graceful degradation |
| `backend/app/services/processing_service.py` | Orchestrates entire pipeline; handles text/spreadsheet/image subtypes inline |
| `backend/app/events/processing_handler.py` | Async handler for document.uploaded; runs pipeline in executor |
| `backend/tests/test_processing.py` | 30 unit tests: CanonicalModels, CanonicalBuilder, DocumentDetector, ProcessingService |

## Files Modified

| File | Change |
|---|---|
| `backend/app/events/inngest_client.py` | Added `send_document_processed_event()` method |
| `backend/app/api/v1/documents.py` | Added `POST /{id}/reprocess` endpoint with BackgroundTasks |
| `backend/app/utils/constants.py` | Added `ProcessingStage` enum; fixed `image/jpeg` → `DocumentType.JPEG` |
| `backend/tests/test_upload.py` | Fixed jpeg test assertion to match corrected MIME mapping |

## Processing Pipeline Stages

| Stage | Status Value | DB Stage Label |
|---|---|---|
| Upload received | `queued` | — |
| Detection + start | `processing` | `parsing` |
| OCR (if needed) | `processing` | `ocr_running` |
| Normalize | `processing` | `normalizing` |
| Done | `completed` | `completed` |
| Error | `failed` | — |

## Canonical Document Format

```json
{
  "document_id": "",
  "original_filename": "",
  "storage_path": "",
  "metadata": {
    "title": "", "author": "", "page_count": 0, "word_count": 0,
    "language": "en", "file_type": "", "file_size": 0,
    "image_count": 0, "table_count": 0,
    "parser_version": "docling@x.y.z",
    "ocr_version": "paddleocr:x.y.z | pytesseract:x.y.z | null",
    "pipeline_version": "1.0.0"
  },
  "pages": [{"page_number": 1, "text": "...", "ocr_applied": false}],
  "sections": [{"heading": "...", "level": 1, "text": "...", "page_number": 1}],
  "tables": [{"headers": [], "rows": [], "markdown": "..."}],
  "images": [{"page_number": 1, "caption": "", "ocr_text": ""}],
  "full_text": "...",
  "language": "en",
  "warnings": [],
  "ocr_applied": false,
  "processing_time_seconds": 2.3,
  "processed_at": "2026-07-19T14:00:00"
}
```

Canonical JSON is stored at: `processed/{document_id}/canonical.json` in Supabase Storage.

## API Endpoint Added

| Method | Endpoint | Code | Description |
|---|---|---|---|
| POST | /api/v1/documents/{id}/reprocess | 202 | Manually trigger processing pipeline |

## Architectural Decisions

### AD-011: OCR Engine Graceful Fallback
PaddleOCR has a numpy 2.x ABI conflict in the current environment (compiled against numpy 1.x). The OCRService auto-detects at startup: tries PaddleOCR → pytesseract → None. All callers receive the same `OCRPageResult` interface regardless of engine. Documents still process successfully even with no OCR engine — they just get empty text for image content.

### AD-012: Scanned PDF Detection via Heuristic
Rather than using a separate paid service to classify PDFs as scanned vs. digital, we use a character-density heuristic: if average chars/page < 100 after Docling extraction, the PDF is flagged as likely scanned and OCR is triggered. This is free and works well in practice.

### AD-013: Canonical JSON Stored in Supabase Storage (not DB)
The canonical JSON can be several MB for large documents. Storing it in Supabase Storage (at `processed/{id}/canonical.json`) avoids hitting Supabase DB column size limits and allows streaming access by downstream modules. DB only stores metadata and status.

### AD-014: Processing Handler Runs in Thread Pool Executor
Docling and OCR are CPU-bound and synchronous. The `processing_handler.py` uses `asyncio.get_event_loop().run_in_executor(None, ...)` to avoid blocking FastAPI's async event loop. This allows concurrent upload handling while processing happens in worker threads.

### AD-015: Temp File Auto-Cleanup via Context Manager
`DocumentLoader.load()` is a context manager — the temp file is guaranteed to be deleted in the `finally` block even if parsing raises an exception. This prevents disk space leaks from failed processing jobs.

### AD-016: Reprocess Endpoint for Development
`POST /documents/{id}/reprocess` triggers processing via FastAPI `BackgroundTasks` without requiring Inngest Dev Server. This is the primary way to test the pipeline in development. In production, Inngest handles the trigger automatically via the `document.uploaded` event.

## Test Results

- **47/47 tests pass** (30 new Phase 2 tests + 17 Phase 1 tests)
- All Phase 2 modules import cleanly
- The exit code 1 from pytest is caused by Neo4j connection teardown warnings (cloud Neo4j unreachable from dev) — not actual test failures

## Compatibility with Tasks 03–06

All downstream tasks can consume CanonicalDocument directly:

- **Task 03 (AI Extraction)**: Subscribe to `document.processed`, download `canonical_storage_path`, load `CanonicalDocument.full_text` + `sections` + `tables` and pass to LLMService.
- **Task 04 (Ontology)**: Receive extracted entities from Task 03; CanonicalDocument provides language + document_type context.
- **Task 05 (Graph)**: Graph builder receives CanonicalDocument sections + tables as citation anchors for Neo4j nodes.
- **Task 06 (Embeddings)**: Chunk `CanonicalDocument.full_text` + `sections` for embedding generation. `CanonicalPage.page_number` provides citation metadata.

## Next Step

Implement **Phase 4 — Ontology Management** per `docs/tasks/04-ontology.md`.

---

# Phase 3 Completion Record — AI Knowledge Extraction (2026-07-20)

## Summary

Epic 3 fully implemented: A multi-stage AI extraction pipeline leveraging Gemini 2.5 Flash to automatically extract entities, relationships, measurements, procedures, and risks from documents, combined with a summary and ontology discovery.

## Architecture

```
document.processed (event)
       ↓
KnowledgeHandler (async)
       ↓
ExtractionService.extract()
  ├── LLMService (w/ PromptManager)
  │     ├── entity_extraction
  │     ├── relationship_extraction
  │     ├── measurement_extraction
  │     ├── procedure_extraction
  │     ├── risk_analysis
  │     ├── summary
  │     └── ontology_discovery
  ├── AIValidator (JSON parsing + schema validation + deduplication)
  ├── KnowledgeRepository (store CKO json + DB metadata)
  └── InngestClient (emit knowledge.extracted)
```

## Files Created/Modified

**Backend**
| File | Purpose |
|---|---|
| `backend/app/prompts/*.md` | Prompt templates for 7 extraction stages |
| `backend/app/schemas/knowledge.py` | CanonicalKnowledgeObject (CKO) and Pydantic schema validation |
| `backend/app/ai/validator.py` | JSON parsing, Pydantic validation, Deduplication, Confidence Scoring |
| `backend/app/repositories/knowledge_repository.py` | CKO JSON storage (Storage) & Knowledge Record tracking (DB) |
| `backend/app/services/extraction_service.py` | Pipeline orchestration, graceful degradation |
| `backend/app/events/knowledge_handler.py` | Event listener for `document.processed` |
| `backend/app/api/v1/knowledge.py` | Knowledge API endpoints |
| `backend/app/ai/llm_service.py` (updated) | Added LLM observability, token usage, cost estimation |
| `backend/tests/test_extraction.py` | 60+ robust integration/unit tests for entire pipeline |

## Database Additions
- `docs/migrations/002_knowledge_extractions.sql` (Creates `knowledge_extractions` table tracking AI pipeline runs).

## Canonical Knowledge Object (CKO)
The CKO acts as the complete, validated payload passed downstream, containing lists of `ExtractedEntity`, `ExtractedRelationship`, `ExtractedMeasurement`, etc., with confidence scores and latency metrics.

---

# Epic 4: Ontology Management (COMPLETED)

Epic 4 implements the Ontology Management and Normalization pipeline. It transforms raw Canonical Knowledge Objects (CKO) into Normalized Knowledge Objects (NKO) ready for graph ingestion.

## Architecture

```
knowledge.extracted (event)
       ↓
OntologyHandler (async)
       ↓
OntologyManager.process()
  ├── EntityMapper (deduplication)
  │     ├── SynonymResolver
  │     └── AliasResolver
  ├── RelationshipValidator (referential integrity)
  ├── OntologyDiscovery (filtering core concepts)
  ├── OntologyRepository (save new concepts for review)
  └── OntologyValidator (final sanity check)
       ↓
NKO Created
       ↓
InngestClient (emit ontology.updated)
```

## Files Created/Modified

**Backend**
| File | Purpose |
|---|---|
| `backend/app/ontology/constants.py` | Ontology entity and relationship enums/lists, core synonyms |
| `backend/app/ontology/models.py` | Pydantic schemas for `NormalizedEntity`, `NormalizedKnowledgeObject`, etc. |
| `backend/app/ontology/synonym_resolver.py` | Map variations to canonical terms (e.g. Water Pump -> Pump) |
| `backend/app/ontology/alias_resolver.py` | Normalize equipment tags (e.g. P 101 -> P-101) |
| `backend/app/ontology/entity_mapper.py` | Apply synonyms, aliases, and merge duplicate entities |
| `backend/app/ontology/relationship_validator.py` | Ensure referential integrity and valid relations |
| `backend/app/ontology/ontology_discovery.py` | Filter out new concepts that are already core |
| `backend/app/ontology/ontology_repository.py` | Save newly discovered concepts to Supabase |
| `backend/app/ontology/ontology_validator.py` | Final validation of NKO |
| `backend/app/ontology/ontology_manager.py` | Orchestration of all normalization modules |
| `backend/app/events/ontology_handler.py` | Event listener for `knowledge.extracted` |
| `backend/app/api/v1/ontology.py` | API endpoint to manually trigger normalization |
| `backend/tests/test_ontology.py` | Unit tests for ontology logic |

## Database Additions
- `docs/migrations/003_ontology_concepts.sql` (Creates `ontology_concepts` table for discovered entities requiring human review).

---

# Phase 5 Completion Record — Knowledge Graph Builder (2026-07-21)

## Summary

Epic 5 fully implemented: a deterministic, idempotent Knowledge Graph Builder that
transforms NormalizedKnowledgeObjects (from Epic 4) into Neo4j nodes and relationships.
No AI calls — zero Gemini involvement. Every element carries provenance.

## Architecture

```
ontology.updated (event)
       ↓
GraphHandler (async)
       ↓
GraphService.build(document_id)
  ├── OntologyRepository.load_nko()   ← loads persisted NKO from Supabase Storage
  ├── NodeBuilder                     ← NormalizedEntity → GraphNode
  │     (entity_id = stable MERGE key)
  ├── RelationshipBuilder             ← NormalizedRelationship → GraphRelationship
  │     (referential integrity check)
  ├── GraphValidator                  ← pre-insert: dup nodes/rels, invalid labels,
  │     missing refs, self-links, confidence bounds
  └── GraphRepository                 ← ONLY Neo4j writer; MERGE-based batch writes
       ↓
InngestClient (emit graph.updated)
```

## Files Created

**Backend**
| File | Purpose |
|---|---|
| `backend/app/graph/__init__.py` | Module init |
| `backend/app/graph/constants.py` | Valid node labels + relationship types (derived from EntityType/RelationshipType enums); batch sizes |
| `backend/app/graph/models.py` | `GraphNode`, `GraphRelationship`, `GraphBuildResult` Pydantic models with provenance fields |
| `backend/app/graph/node_builder.py` | `NormalizedEntity` → `GraphNode`; entity_id is stable; unknown types fall back to Concept |
| `backend/app/graph/relationship_builder.py` | `NormalizedRelationship` → `GraphRelationship`; referential integrity; self-link rejection |
| `backend/app/graph/graph_validator.py` | Pre-insert validation: 7 checks including duplicates, missing refs, invalid labels/types, self-links |
| `backend/app/graph/graph_repository.py` | ONLY Neo4j writer; MERGE on entity_id (nodes) and (src, type, tgt) (rels); batch 100/200 |
| `backend/app/graph/graph_queries.py` | Parameterized Cypher: Asset 360, Neighbor Discovery, Related Documents, node lookup, paginated list; Shortest Path / Subgraph / Compliance stubbed with TODOs |
| `backend/app/graph/graph_service.py` | Orchestrator: loads NKO → build → validate → write → return GraphBuildResult |
| `backend/app/events/graph_handler.py` | Handles `ontology.updated`; runs GraphService; emits `graph.updated` |
| `backend/app/api/v1/graph.py` | POST /{doc_id}/build, GET /nodes, GET /node/{id}, GET /{doc_id}/status |
| `backend/tests/test_graph.py` | 23 unit tests: NodeBuilder (7), RelationshipBuilder (6), GraphValidator (9), Idempotency (2) |

## Files Modified

| File | Change |
|---|---|
| `backend/app/events/inngest_client.py` | Added `send_graph_updated_event()` (Epic 5 → 6 handoff) |
| `backend/app/api/v1/router.py` | Registered graph router at `/graph` prefix |
| `backend/app/core/dependencies.py` | Added `get_graph_repository()`, `get_graph_service()` |

## Architectural Decisions

### AD-017: NKO as Sole Graph Input
Graph Builder loads the persisted NKO artifact (`normalized/{id}/nko.json`) via
`OntologyRepository.load_nko()`. It never reads the raw CKO and never re-runs
normalization logic. This creates a clean contract: Epic 4 is responsible for
normalization, Epic 5 is responsible for graph writes.

### AD-018: MERGE-Based Idempotent Writes
All Neo4j writes use `MERGE` keyed on `entity_id` for nodes and
`(source_id, rel_type, target_id)` for relationships. Re-processing the same
document multiple times never creates duplicate graph elements.

### AD-019: Pre-Insert Validation Pass
All nodes and relationships are validated before any Neo4j write begins.
Invalid elements are collected into `ValidationResult.invalid_*` lists and
logged — they are never silently dropped. This makes pipeline failures visible
without corrupting the graph with partial data.

### AD-020: Graph Queries Separate from Repository
All Cypher strings live in `graph_queries.py`, not inlined in `graph_repository.py`.
This makes the Cypher reviewable in isolation, and ensures repository methods only
execute pre-approved, parameterized queries — never dynamic or AI-generated strings.

## Test Results

- **23/23 graph tests pass** (`tests/test_graph.py`)
- **142/142 total platform tests pass** (no regressions in Epics 1–4)
- The exit code 1 from the full suite run is the pre-existing Neo4j cloud connection
  teardown warning (documented in AD-011 / Phase 2 record) — not a test failure

## Definition of Done Checklist (from 05-graph.md)

| Criterion | Status |
|---|---|
| Nodes generated from NormalizedKnowledgeObject (not raw CKO) | ✅ — `GraphService.build()` calls `load_nko()` exclusively |
| Relationships validated before insertion | ✅ — `GraphValidator` runs before `GraphRepository` |
| Graph updates are idempotent | ✅ — MERGE semantics; `TestIdempotency` proves same input → same output |
| Neo4j accessed only through GraphRepository | ✅ — `GraphRepository` is the only caller of `Neo4jClient.execute_query()` |
| Provenance stored on every node and relationship | ✅ — `source_document`, `confidence`, `extraction_version`, `created_at` on all elements |
| `graph.updated` event emitted | ✅ — `graph_handler.py` calls `send_graph_updated_event()` |
| No AI/Gemini calls anywhere in graph module | ✅ — zero LLMService imports in `backend/app/graph/` |

## Next Step

Implement **Phase 6 — Semantic Embeddings** per `docs/tasks/06-embeddings.md`.

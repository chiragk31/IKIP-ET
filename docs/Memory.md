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
- **Key Relationships**: MENTIONS, HAS_FAILURE, LOCATED_IN, PERFORMED, HAS_MEASUREMENT, REFERENCES, CONNECTED_TO, RELATED_TO, CAUSED_BY, USES, OWNED_BY
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

Key Relationship Types: `MENTIONS`, `HAS_FAILURE`, `LOCATED_IN`, `PERFORMED`, `HAS_MEASUREMENT`, `REFERENCES`, `CONNECTED_TO`, `RELATED_TO`, `CAUSED_BY`, `USES`, `REQUIRES`, `MITIGATED_BY`, `RECORDED_FOR`, `INVOLVES`, `OWNS`

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
| 1 | Document Upload | 🔲 Next |
| 2 | Document Processing Pipeline | 🔲 Planned |
| 3 | AI Knowledge Extraction | 🔲 Planned |
| 4 | Ontology Management | 🔲 Planned |
| 5 | Knowledge Graph | 🔲 Planned |
| 6 | Embeddings & Semantic Search | 🔲 Planned |
| 7 | AI Copilot (RAG) | 🔲 Planned |
| 8 | Asset Intelligence | 🔲 Planned |
| 9 | Dashboard | 🔲 Planned |
| 10 | Authentication | 🔲 Planned |
| 11 | Deployment & Demo | 🔲 Planned |

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

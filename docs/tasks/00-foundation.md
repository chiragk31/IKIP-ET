# 00-foundation.md

# Epic 0 - Project Foundation

Version: 1.0

---

# Objective

Establish the complete project foundation before implementing any business functionality.

At the end of this epic:

- Frontend is running
- Backend is running
- External services are configured
- Folder structure is finalized
- Documentation is complete
- Development environment is reproducible

No business logic should be implemented in this phase.

---

# References

Must follow:

- PRD.md
- Architecture.md
- Rules.md
- Database.md
- API.md
- Ontology.md
- Prompts.md

---

# Dependencies

None.

This is the first implementation phase.

---

# Deliverables

✓ Next.js Project

✓ FastAPI Project

✓ Documentation Folder

✓ Supabase Project

✓ Neo4j Aura Database

✓ Pinecone Index

✓ Gemini API

✓ Inngest

✓ Git Repository

✓ Environment Variables

✓ CI Ready Structure

---

# Recommended Folder Structure

```
project/

docs/

frontend/

backend/

scripts/

docker/

.github/

```

---

# Task 0.1 — Initialize Repository

## Goal

Create the Git repository.

---

### Steps

Initialize repository.

Create README.

Create .gitignore.

Create LICENSE.

Configure branch protection strategy.

---

### Acceptance Criteria

✓ Repository initialized

✓ Initial commit completed

---

# Task 0.2 — Documentation Setup

## Goal

Create documentation structure.

---

### Create

```
docs/

PRD.md

Architecture.md

Rules.md

Database.md

Ontology.md

API.md

Prompts.md

Phases.md

Tasks.md

Memory.md

Design.md

Conventions.md

Environment.md

ADR.md

Testing.md

Deployment.md
```

---

### Create Task Folder

```
docs/tasks/

00-foundation.md

01-upload.md

02-processing.md

03-ai-extraction.md

04-ontology.md

05-graph.md

06-embeddings.md

07-search.md

08-copilot.md

09-assets.md

10-dashboard.md

11-authentication.md

12-deployment.md
```

---

### Create Prompt Folder

```
docs/prompts/

system.md

entity_extraction.md

relationship_extraction.md

summary.md

chat.md

maintenance.md

compliance.md

ontology_discovery.md

query_rewrite.md

semantic_search.md
```

---

### Acceptance Criteria

✓ Documentation structure complete

---

# Task 0.3 — Frontend Setup

## Goal

Initialize the frontend.

---

### Framework

Next.js 15

TypeScript

App Router

---

### Install

- TailwindCSS
- Shadcn UI
- Zustand
- TanStack Query
- React Hook Form
- Zod
- Axios
- React Flow
- Recharts
- Lucide Icons

---

### Folder Structure

```
frontend/

app/

components/

features/

hooks/

services/

store/

types/

utils/

styles/

public/
```

---

### Configure

TypeScript

ESLint

Prettier

Absolute imports

Environment variables

---

### Acceptance Criteria

✓ Frontend starts successfully

✓ No lint errors

✓ No TypeScript errors

---

# Task 0.4 — Backend Setup

## Goal

Initialize backend.

---

### Framework

FastAPI

Python 3.12+

---

### Install

FastAPI

Uvicorn

Pydantic

python-dotenv

Supabase SDK

Neo4j Driver

Pinecone SDK

Google Generative AI SDK

Docling

PaddleOCR

Inngest

---

### Folder Structure

```
backend/

app/

api/

core/

database/

services/

repositories/

schemas/

models/

parser/

ocr/

ontology/

graph/

rag/

events/

prompts/

ai/

utils/
```

---

### Acceptance Criteria

✓ FastAPI starts

✓ Swagger available

✓ Environment loads correctly

---

# Task 0.5 — Configure Supabase

## Goal

Prepare Supabase.

---

### Create

Project

Storage Bucket

Database

Authentication (disabled for now)

---

### Buckets

documents

---

### Acceptance Criteria

✓ Storage bucket created

✓ SDK connection works

---

# Task 0.6 — Configure Neo4j Aura

## Goal

Prepare graph database.

---

### Create

Aura Free Instance

---

### Configure

URI

Username

Password

---

### Acceptance Criteria

✓ Connection successful

---

# Task 0.7 — Configure Pinecone

## Goal

Prepare vector database.

---

### Create

Index

Dimension

Metric

Region

---

### Acceptance Criteria

✓ Connection successful

---

# Task 0.8 — Configure Gemini

## Goal

Configure AI model.

---

### Configure

API Key

Default Model

Temperature

Retry Policy

Timeout

---

### Acceptance Criteria

✓ Test prompt succeeds

---

# Task 0.9 — Configure Inngest

## Goal

Configure workflow engine.

---

### Create

Development App

Event Handler

Health Endpoint

---

### Acceptance Criteria

✓ Local event received

---

# Task 0.10 — Environment Variables

Create

Frontend

```
NEXT_PUBLIC_API_URL

NEXT_PUBLIC_SUPABASE_URL

NEXT_PUBLIC_SUPABASE_ANON_KEY
```

Backend

```
SUPABASE_URL

SUPABASE_SERVICE_ROLE_KEY

GEMINI_API_KEY

NEO4J_URI

NEO4J_USERNAME

NEO4J_PASSWORD

PINECONE_API_KEY

PINECONE_INDEX

INNGEST_SIGNING_KEY

INNGEST_EVENT_KEY
```

---

### Acceptance Criteria

✓ All services load configuration

---

# Task 0.11 — Shared Utilities

Create

Logger

Settings Manager

HTTP Client

Response Models

Error Models

Constants

Enums

Utility Functions

---

### Acceptance Criteria

✓ Shared utilities reusable

---

# Task 0.12 — Health Checks

Backend

GET

/api/v1/health

Checks

Backend

Supabase

Neo4j

Pinecone

Gemini

---

### Expected Response

```
{
    "status":"healthy",
    "services":{
        "supabase":"up",
        "neo4j":"up",
        "pinecone":"up",
        "gemini":"up"
    }
}
```

---

# Verification Checklist

Project builds.

Frontend starts.

Backend starts.

Supabase connected.

Neo4j connected.

Pinecone connected.

Gemini connected.

Inngest connected.

Swagger loads.

No lint errors.

No TypeScript errors.

No Python errors.

---

# Out of Scope

Authentication

Upload API

Knowledge Graph

Embeddings

Semantic Search

AI Copilot

Dashboard

These belong to later epics.

---

# Definition of Done

This epic is complete when:

✓ Frontend starts successfully

✓ Backend starts successfully

✓ External services connected

✓ Documentation complete

✓ Environment variables configured

✓ Folder structure finalized

✓ Repository initialized

✓ Health endpoint reports all services healthy

✓ Project ready for Epic 1 (Document Upload)
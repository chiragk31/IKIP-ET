# Design.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Purpose

This document defines the software design principles, architectural patterns, coding conventions, UI philosophy, and engineering guidelines that must be followed throughout the project.

Unlike Architecture.md, which describes **what** the system is, this document describes **how** it should be built.

---

# Design Philosophy

The project should prioritize:

- Simplicity
- Maintainability
- Scalability
- Loose Coupling
- High Cohesion
- Event Driven Processing
- AI-first Architecture
- Modular Components

Every feature should be independently testable and replaceable.

---

# Architecture Principles

## Layered Architecture

```
Frontend

↓

API Layer

↓

Service Layer

↓

Repository Layer

↓

External Services
```

Business logic must never communicate directly with databases or third-party SDKs.

---

## Repository Pattern

Every external dependency must be wrapped.

Example

```
Supabase

↓

StorageRepository

↓

UploadService
```

Never call SDKs directly from business services.

---

## Service Layer

Every business capability belongs inside a Service.

Example

```
UploadService

DocumentService

GraphService

SearchService

CopilotService
```

Services should only coordinate business logic.

---

## AI Layer

Only one component may communicate with the LLM.

```
LLM Gateway

↓

Gemini
```

No other module may call Gemini directly.

---

## Event Driven Architecture

Modules communicate through events.

```
Upload

↓

document.uploaded

↓

Processing

↓

document.processed

↓

AI Extraction

↓

knowledge.extracted

↓

Ontology

↓

ontology.updated

↓

Graph

↓

graph.updated

↓

Embeddings

↓

embeddings.created
```

Never directly invoke downstream modules.

---

# Frontend Design

Use Feature-Based Architecture.

```
features/

upload/

dashboard/

graph/

chat/

assets/
```

Each feature owns:

- Components
- Hooks
- Services
- Types

---

# Backend Design

Backend follows Domain Modules.

```
api/

services/

repositories/

events/

parser/

ontology/

graph/

rag/

ai/
```

Each module should be independently deployable in the future.

---

# UI Principles

Use:

- Shadcn UI
- Tailwind CSS
- Responsive Layouts
- Accessible Components
- Minimal Animations

Avoid unnecessary visual complexity.

---

# State Management

Server State

→ TanStack Query

Client State

→ Zustand

Forms

→ React Hook Form

Validation

→ Zod

---

# API Design

REST First

Versioned

```
/api/v1/
```

Every response follows

```json
{
    "success": true,
    "data": {},
    "message": "",
    "errors": []
}
```

---

# Error Handling

Never expose stack traces.

Always return structured errors.

Log everything.

---

# Logging

Every service should log

- Start
- Success
- Failure
- Duration

---

# Security

Validate all inputs.

Validate file types.

Never trust client data.

Environment variables only.

Secrets never committed.

---

# Performance

Prefer async APIs.

Avoid blocking requests.

Lazy load UI components.

Cache where appropriate.

---

# AI Principles

AI must never

- Write directly to databases
- Generate Cypher
- Modify ontology
- Create embeddings

AI only produces structured JSON.

Backend validates everything.

---

# Documentation

Every major feature must update

- Architecture.md
- API.md
- Database.md
- Memory.md

---

# Code Quality

Use

- ESLint
- Prettier
- Ruff
- Black

CI should fail on lint errors.

---

# Git Workflow

Feature Branch

↓

Implementation

↓

Testing

↓

Documentation

↓

Pull Request

↓

Merge

---

# Definition of Good Design

A module is considered well designed if

- It has one responsibility.
- It can be replaced independently.
- It can be tested independently.
- It has no circular dependencies.
- It follows repository and service patterns.
- It communicates through events where applicable.
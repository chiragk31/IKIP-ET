# Rules.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Purpose

This document defines the engineering rules that every AI coding assistant must follow while generating code.

These rules are mandatory.

Never violate these rules.

---

# General Principles

The codebase should be:

- Modular
- Maintainable
- Scalable
- Production Ready
- Event Driven
- AI First
- Type Safe

Every component should have a single responsibility.

---

# Project Structure

Never create random folders.

Always follow the existing architecture.

Frontend and Backend must remain independent.

Never place backend logic inside frontend.

Never place AI logic inside API routes.

---

# Backend Rules

Framework

FastAPI

Language

Python 3.12+

Every endpoint must use:

- Pydantic Models
- Async Functions
- Dependency Injection

Never access the database directly from API routes.

API

↓

Service

↓

Repository

↓

Database

Always follow this pattern.

---

# Frontend Rules

Framework

Next.js 15

Language

TypeScript

Never use JavaScript.

Always use App Router.

Never use Pages Router.

Always use:

React Query

for data fetching.

Use Zustand

for global state.

Use React Hook Form

for forms.

Use Zod

for validation.

Never fetch APIs directly inside components.

Always use service classes.

---

# Component Rules

Each component must:

- Be reusable
- Be independent
- Have a single responsibility

Never create components larger than 300 lines.

Split large components.

---

# Styling Rules

Use only

Tailwind CSS

Do not write custom CSS unless absolutely required.

Prefer Shadcn components.

Use CSS variables.

Support dark mode.

---

# Folder Rules

Frontend

features/

Each feature owns:

components/

hooks/

services/

types/

Backend

Every module owns:

api/

service/

repository/

schema/

Never mix responsibilities.

---

# Naming Conventions

Variables

camelCase

Functions

camelCase

Classes

PascalCase

Files

snake_case.py (backend)

kebab-case.tsx (frontend)

Environment Variables

UPPER_CASE

---

# AI Rules

No module should communicate directly with Gemini.

Always use:

LLM Service

Business Services

↓

LLM Service

↓

Gemini

Only the LLM Service may call the model.

---

# Prompt Rules

Never hardcode prompts.

Store prompts in:

backend/app/prompts/

Prompts must be versioned.

Every prompt should have:

Purpose

Expected Input

Expected Output

Example

---

# OCR Rules

Always try:

Docling

If OCR required

↓

PaddleOCR

Never OCR a digital PDF.

---

# Parsing Rules

Always preserve:

Tables

Images

Sections

Metadata

Never discard extracted information.

---

# Ontology Rules

Do not use a fixed ontology.

Maintain:

Core Ontology

+

Dynamic Ontology

New concepts should be validated before insertion.

Never create duplicate entity types.

Normalize names.

---

# Knowledge Graph Rules

Graph Database

Neo4j

The LLM never generates Cypher.

LLM

↓

JSON

↓

Graph Builder

↓

Neo4j

Only the Graph Builder may write to Neo4j.

---

# Vector Database Rules

Only chunks should be embedded.

Never embed entire documents.

Chunk Size

800–1200 tokens

Overlap

150–250 tokens

Every chunk must retain:

Document ID

Page Number

Section

Citation

---

# Database Rules

Supabase

Authentication

Storage

Metadata

Pinecone

Embeddings

Neo4j

Knowledge Graph

Do not duplicate information across databases.

Each database has a single responsibility.

---

# Event Rules

Every major operation should be event-driven.

Example

document.uploaded

↓

document.parsed

↓

ocr.completed

↓

entities.extracted

↓

graph.updated

↓

embeddings.generated

↓

document.ready

Never block upload while processing.

---

# API Rules

Always return

{
    "status": "...",
    "message": "...",
    "data": {}
}

Never return raw exceptions.

Use proper HTTP status codes.

---

# Error Handling

Every service should:

Catch exceptions

Log errors

Return meaningful messages

Never expose stack traces.

---

# Logging

Every service must log:

Timestamp

User ID

Document ID

Execution Time

Status

Errors

---

# Security Rules

Never hardcode:

API Keys

Secrets

Passwords

Always use

.env

Validate every upload.

Validate file size.

Validate MIME type.

---

# Performance Rules

Prefer async code.

Avoid blocking operations.

Cache repeated LLM calls when possible.

Reuse embeddings.

Do not duplicate vector storage.

---

# Code Quality

Every function should:

Do one thing.

Every service should:

Do one thing.

Avoid nested logic.

Prefer composition over inheritance.

Keep functions under 50 lines where practical.

---

# Documentation Rules

Every service must include:

Purpose

Input

Output

Dependencies

Every API should have OpenAPI documentation.

---

# Testing Rules

Write unit tests for:

Services

Repositories

Utility functions

Integration tests for:

API

Graph

RAG

Upload Pipeline

---

# Git Rules

Commit after each completed feature.

Commit message format:

feat:

fix:

refactor:

docs:

test:

Never commit:

.env

Secrets

Credentials

---

# Things AI Must Never Do

Never modify architecture.

Never introduce new frameworks without approval.

Never bypass the LLM Service.

Never bypass Graph Builder.

Never bypass Repository Layer.

Never duplicate business logic.

Never hardcode prompts.

Never hardcode URLs.

Never hardcode credentials.

Never invent APIs.

Never remove comments that explain architecture.

---

# Definition of Done

A feature is complete only if:

✓ Code Compiles

✓ API Works

✓ Type Safe

✓ Tested

✓ Logged

✓ Documented

✓ Error Handling Exists

✓ Responsive UI

✓ Integrated into existing architecture

✓ No architectural rules violated

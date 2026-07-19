# Architecture.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# System Overview

The platform is designed as an event-driven AI pipeline.

Instead of directly answering user questions, the platform continuously transforms unstructured industrial documents into structured organizational knowledge.

The architecture follows four major layers:

1. Presentation Layer
2. API Layer
3. AI Processing Layer
4. Data Layer

---

# High Level Architecture

                    Browser
                       │
                       ▼
                Next.js Frontend
                       │
                 REST API / HTTPS
                       │
                       ▼
                 FastAPI Backend
                       │
      ┌────────────────┼────────────────┐
      │                │                │
      ▼                ▼                ▼
 Supabase         Inngest Events     AI Services
 Storage
      │
      ▼
Document Uploaded Event
      │
      ▼
─────────────────────────────────────────────
AI Processing Pipeline
─────────────────────────────────────────────

Document Parsing

↓

OCR

↓

Entity Extraction

↓

Relationship Extraction

↓

Ontology Manager

↓

Knowledge Graph Builder

↓

Chunk Generator

↓

Embedding Generator

↓

Vector Database

↓

Document Summary

↓

Compliance Analysis

↓

Ready

─────────────────────────────────────────────

User Query

↓

Retriever

↓

Pinecone

+

Neo4j

↓

Gemini

↓

Answer

---

# Architectural Principles

The system should follow:

- Modular Architecture
- Event Driven Processing
- AI First Design
- Retrieval Augmented Generation
- Knowledge Graph Driven Reasoning
- Explainable AI
- Stateless Backend
- Separation of Concerns

---

# Technology Stack

## Frontend

Framework

Next.js 15

Language

TypeScript

Styling

Tailwind CSS

UI Components

Shadcn UI

State Management

Zustand

Data Fetching

TanStack Query

Forms

React Hook Form

Validation

Zod

Graph Visualization

React Flow

Charts

Recharts

Icons

Lucide

Authentication

Supabase Auth

Deployment

Vercel

---

## Backend

Framework

FastAPI

Language

Python 3.12

Validation

Pydantic

ORM

SQLAlchemy

Authentication

Supabase JWT

Background Tasks

Inngest

Deployment

Render

---

## AI Stack

LLM

Gemini 2.5 Flash

OCR

PaddleOCR

Document Parsing

Docling

Embeddings

Google text-embedding-004

---

## Databases

Supabase

Purpose

Authentication

Storage

Metadata

Processing Status

Pinecone

Purpose

Semantic Search

Vector Storage

Neo4j Aura

Purpose

Knowledge Graph

---

# Frontend Architecture

frontend/

app/

components/

features/

hooks/

lib/

services/

store/

types/

styles/

public/

Each feature should be isolated.

Example

features/

upload/

chat/

graph/

assets/

dashboard/

documents/

compliance/

---

# Backend Architecture

backend/

app/

api/

core/

database/

services/

repositories/

schemas/

models/

events/

agents/

graph/

ontology/

rag/

ocr/

parser/

embeddings/

utils/

prompts/

Every module should have a single responsibility.


# Instead of every service calling Gemini directly, introduce a dedicated LLM Service.

Upload Service
          │
Chat Service
          │
Compliance Agent
          │
Ontology Manager
          │
Summary Agent
          │
Maintenance Agent
          │
          ▼
      LLM Service
          │
          ▼
        Gemini

---

# AI Processing Pipeline

Step 1

User uploads document.

↓

Store in Supabase.

↓

Emit document.uploaded event.

---

Step 2

Parser Service

Uses

Docling

Extracts

Text

Headings

Tables

Images

Metadata

---

Step 3

OCR Service

If scanned

↓

PaddleOCR

↓

Extract searchable text.

---

Step 4

Knowledge Extraction Service

Gemini extracts

- entities
- relationships
- measurements
- procedures
- risks
- standards
- organizations

Returns structured JSON.

---

Step 5

Ontology Manager

Responsibilities

Normalize entities

Merge duplicates

Discover new concepts

Maintain ontology consistency

---

Step 6

Knowledge Graph Builder

Input

Canonical JSON

↓

Generate graph

↓

Insert into Neo4j

Never allow LLM to write directly into Neo4j.

---

Step 7

Chunk Generator

Split document

↓

Generate chunks

↓

Preserve citations

---

Step 8

Embedding Generator

Generate embeddings

↓

Store inside Pinecone

---

Step 9

Summary Generator

Generate

Summary

Keywords

Topics

Document Classification

---

Step 10

Compliance Agent

Detect

Missing approvals

Expired certificates

Compliance issues

---

Step 11

Document Ready

Update processing status.

---

# Query Architecture

User asks question.

↓

Embedding

↓

Pinecone Search

↓

Retrieve relevant chunks

↓

Neo4j Query

↓

Retrieve relationships

↓

Combine context

↓

Gemini

↓

Generate answer

↓

Return

Answer

Citations

Confidence

Related Assets

---

# Event Driven Workflow

document.uploaded

↓

document.parsed

↓

ocr.completed

↓

entities.extracted

↓

ontology.updated

↓

graph.updated

↓

embeddings.generated

↓

summary.generated

↓

document.ready

Each stage should be independent.

---

# Knowledge Graph Architecture

Graph Database

Neo4j Aura

Graph Builder receives

Canonical JSON

↓

Creates

Nodes

Relationships

Ontology Updates

Graph should never be directly generated by the LLM.

---

# Vector Search Architecture

Chunks

↓

Embeddings

↓

Pinecone

↓

Semantic Search

↓

Top K Retrieval

↓

Context

---

# Canonical Knowledge Object

Every AI module must produce and consume the same structure.

{
    document,
    metadata,
    sections,
    tables,
    entities,
    relationships,
    measurements,
    chunks,
    summary,
    citations
}

No module should use proprietary internal formats.

---

# API Layer

Frontend

↓

REST API

↓

FastAPI

↓

Services

↓

Repositories

↓

Database

Routes must never directly communicate with databases.

---

# Security

JWT Authentication

Role Based Access

Environment Variables

HTTPS

Server Side Validation

Secure File Upload

Input Validation

---

# Deployment

Frontend

Vercel

Backend

Render

Storage

Supabase

Knowledge Graph

Neo4j Aura

Vector Database

Pinecone

---

# Logging

Every pipeline stage should log:

Start Time

End Time

Status

Errors

Document ID

User ID

Duration

---

# Error Handling

Every module should return

Status

Message

Error Code

Details

Never expose stack traces.

---

# Performance Goals

Upload < 5 sec

Search < 2 sec

AI Response < 10 sec

Graph Update < 10 sec

Semantic Search < 3 sec

---

# Future Architecture

Future modules can include

IoT

Digital Twin

SAP

SCADA

Maximo

Predictive Maintenance

Multi-Agent Systems

without changing existing architecture.

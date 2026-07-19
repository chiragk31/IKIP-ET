# Database.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Database Philosophy

The platform follows a polyglot persistence architecture.

Each database has a single responsibility.

Never duplicate the same data across databases.

The databases are:

1. Supabase
2. Neo4j Aura
3. Pinecone

---

# Database Responsibilities

| Database | Responsibility |
|-----------|----------------|
| Supabase | Authentication, Storage, Metadata |
| Neo4j | Knowledge Graph |
| Pinecone | Vector Search |

---

# Supabase

Supabase is NOT the primary knowledge database.

It stores:

- Users
- Authentication
- File Metadata
- Upload Status
- Processing Status
- Storage Bucket

It DOES NOT store:

- Knowledge Graph
- Embeddings
- AI Relationships

---

## Authentication

Table

users

Fields

id

email

name

role

created_at

updated_at

---

## Documents

Table

documents

Fields

id

user_id

filename

original_filename

storage_path

file_type

file_size

upload_time

status

processing_stage

summary

language

document_type

created_at

updated_at

---

## Processing Status

Table

processing_jobs

Fields

id

document_id

job_type

status

started_at

completed_at

execution_time

error_message

---

## Storage

Bucket

documents

Folder Structure

documents/

year/

month/

document.pdf

---

# Neo4j

Neo4j stores all organizational knowledge.

Never store raw files.

Never store embeddings.

Never store authentication.

---

# Node Types

## Document

Properties

document_id

title

document_type

created_at

summary

---

## Asset

Properties

asset_id

name

asset_type

subtype

manufacturer

serial_number

---

## Person

Properties

person_id

name

designation

department

---

## Organization

Properties

organization_id

name

---

## Location

Properties

location_id

name

plant

section

---

## Procedure

Properties

procedure_id

name

type

---

## Event

Properties

event_id

event_type

timestamp

severity

---

## Measurement

Properties

measurement_id

parameter

value

unit

timestamp

---

## Risk

Properties

risk_id

name

severity

likelihood

---

## Failure

Properties

failure_id

name

category

root_cause

---

## Regulation

Properties

regulation_id

code

authority

---

## Concept

Dynamic ontology node.

Properties

concept_name

category

confidence

created_by

---

# Relationship Types

Document

MENTIONS

Entity

---

Asset

HAS_FAILURE

Failure

---

Asset

LOCATED_IN

Location

---

Person

PERFORMED

Procedure

---

Document

GENERATED_FROM

Procedure

---

Asset

HAS_MEASUREMENT

Measurement

---

Procedure

REQUIRES

Asset

---

Asset

PART_OF

Organization

---

Failure

RELATED_TO

Risk

---

Document

REFERENCES

Document

---

Asset

CONNECTED_TO

Asset

---

Concept

RELATED_TO

Concept

---

# Dynamic Ontology

The ontology is not fixed.

When Gemini discovers a new concept:

↓

Ontology Manager validates

↓

If accepted

↓

Create Concept Node

↓

Create Relationships

↓

Graph expands automatically.

---

# Pinecone

Purpose

Semantic Search

Stores

Chunks

Embeddings

Metadata

Never store documents.

Never store graph relationships.

---

# Pinecone Metadata

Each vector must contain

chunk_id

document_id

page_number

section

document_type

asset_ids

keywords

language

created_at

---

# Chunk Strategy

Chunk Size

800-1200 Tokens

Overlap

200 Tokens

Every chunk must preserve context.

---

# Embeddings

One embedding per chunk.

Never embed the complete document.

Never embed images directly.

---

# Canonical Knowledge Object

Every module communicates using this object.

{
    "document": {},
    "metadata": {},
    "sections": [],
    "tables": [],
    "entities": [],
    "relationships": [],
    "measurements": [],
    "chunks": [],
    "summary": "",
    "citations": []
}

This object is never stored directly.

It is transformed into:

↓

Neo4j

↓

Pinecone

↓

Supabase Metadata

---

# Data Flow

User Uploads PDF

↓

Supabase Storage

↓

Document Metadata

↓

Inngest Event

↓

Parser

↓

OCR

↓

Knowledge Extraction

↓

Canonical Knowledge Object

↓

Graph Builder

↓

Neo4j

↓

Chunk Generator

↓

Embedding Generator

↓

Pinecone

↓

Processing Complete

↓

Supabase Status Updated

---

# Database Rules

Supabase

Single Source Of Truth For

Authentication

File Metadata

Storage

---

Neo4j

Single Source Of Truth For

Knowledge

Entities

Relationships

Ontology

---

Pinecone

Single Source Of Truth For

Semantic Search

Embeddings

Document Chunks

---

Never duplicate knowledge across databases.

---

# Backup Strategy

Supabase

Automatic

Neo4j

Periodic Export

Pinecone

Rebuildable From Documents

---

# Future Expansion

Future databases may include

Redis

Caching

Elasticsearch

Hybrid Search

TimescaleDB

IoT Sensor Data

S3

Large File Storage

Without changing the current architecture.

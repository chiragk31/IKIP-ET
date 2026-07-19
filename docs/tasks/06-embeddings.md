# Embeddings.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Purpose

This document defines the embedding architecture used by the Industrial Knowledge Intelligence Platform.

Embeddings transform processed industrial knowledge into dense vector representations that enable semantic search, Retrieval-Augmented Generation (RAG), and GraphRAG.

Pinecone serves as the vector database.

---

# Goals

The embedding system should

- Enable semantic retrieval
- Support GraphRAG
- Preserve document context
- Support hybrid search
- Minimize hallucinations
- Scale efficiently
- Remain model independent

---

# Design Philosophy

Documents should never be embedded directly.

Instead

```
Industrial Document

↓

Canonical Document

↓

Canonical Knowledge Object

↓

Chunk Generator

↓

Embedding Generator

↓

Pinecone
```

This preserves structure and improves retrieval quality.

---

# Responsibilities

The embedding module is responsible for

- Chunk Generation
- Metadata Generation
- Embedding Creation
- Vector Storage
- Similarity Search

The embedding module is NOT responsible for

- OCR
- AI Extraction
- Ontology
- Graph Construction
- Chat
- Response Generation

---

# Architecture

```
Canonical Knowledge Object

↓

Chunk Generator

↓

Metadata Enrichment

↓

Embedding Generator

↓

Vector Validator

↓

Pinecone Repository

↓

Pinecone
```

---

# Folder Structure

```
backend/app/

embeddings/

chunk_generator.py

chunk_strategy.py

embedding_service.py

embedding_provider.py

embedding_validator.py

pinecone_repository.py

search_service.py

models.py

schemas.py

constants.py
```

---

# Event Flow

```
graph.updated

↓

Chunk Generator

↓

Embedding Generator

↓

Pinecone

↓

embeddings.created
```

---

# Chunking Strategy

Every document is divided into semantic chunks.

Never split purely by character count.

Preferred hierarchy

```
Document

↓

Section

↓

Subsection

↓

Paragraph

↓

Chunk
```

Chunk boundaries should preserve meaning.

---

# Chunk Types

Supported chunk categories

- Text
- Table
- Procedure
- Maintenance Log
- Incident Report
- Measurement
- Compliance Section
- Checklist

Different chunk types may use different retrieval strategies.

---

# Canonical Chunk Model

```json
{
    "chunk_id":"",
    "document_id":"",
    "section":"Maintenance",
    "text":"",
    "metadata":{},
    "graph_entities":[],
    "graph_relationships":[]
}
```

---

# Metadata Enrichment

Every chunk should contain

- Document ID
- Section
- Page Number
- Entity IDs
- Asset IDs
- Relationship IDs
- Confidence
- Source
- Timestamp

Metadata enables hybrid filtering during retrieval.

---

# Embedding Model

Default Provider

Google Embedding API

Recommended Model

```
text-embedding-004
```

Future providers

- OpenAI
- Voyage AI
- Cohere
- Local Embedding Models

---

# Embedding Provider Pattern

```
Embedding Service

↓

Embedding Provider Interface

↓

Google

OpenAI

Voyage

Local Models
```

Business logic should never depend on a specific embedding model.

---

# Embedding Schema

```json
{
    "id":"",
    "embedding":[],
    "metadata":{},
    "created_at":""
}
```

---

# Pinecone Index

Each vector stores

- Chunk ID
- Document ID
- Asset IDs
- Entity IDs
- Metadata
- Embedding

Never store full documents inside Pinecone.

---

# Search Pipeline

```
User Query

↓

Query Embedding

↓

Pinecone Similarity Search

↓

Metadata Filtering

↓

Graph Expansion

↓

LLM Context
```

---

# Metadata Filters

Supported filters

- Asset
- Document
- Date
- Document Type
- Entity Type
- Procedure
- Confidence
- Plant
- Department

Metadata filtering should occur before graph expansion.

---

# Hybrid Retrieval

The retrieval strategy combines

Semantic Search

+

Metadata Filters

+

Graph Expansion

This provides significantly better grounding than vector search alone.

---

# Similarity Search

Default Metric

Cosine Similarity

Top K

```
10
```

Reranking occurs in a later stage.

---

# Chunk Size Strategy

Target

```
400–800 tokens
```

Overlap

```
80–120 tokens
```

Never split

- Procedures
- Tables
- Numbered Steps
- Safety Instructions

Maintain semantic integrity.

---

# Graph-Aware Chunks

Every chunk should reference graph entities.

Example

```
Chunk

↓

Pump P-101

Valve V-02

Maintenance Procedure

Failure Event
```

These references enable GraphRAG.

---

# Duplicate Detection

Before embedding

Check

- Duplicate Chunk
- Duplicate Hash
- Duplicate Document
- Duplicate Embedding Request

Avoid redundant vectors.

---

# Repository Layer

Only PineconeRepository communicates with Pinecone.

```
Embedding Service

↓

Pinecone Repository

↓

Pinecone
```

Never call Pinecone SDK directly.

---

# Versioning

Store

- Embedding Model
- Embedding Version
- Chunk Version
- Pipeline Version

Supports future re-embedding.

---

# Performance

Implement

- Batch Embedding
- Batch Upserts
- Async Requests
- Retry Logic
- Connection Pooling

Avoid generating embeddings one chunk at a time.

---

# Security

Never expose Pinecone API keys.

Never store sensitive credentials in vectors.

Validate metadata before insertion.

---

# Logging

Log

- Chunks Generated
- Embeddings Created
- Batch Size
- Token Count
- Embedding Duration
- Pinecone Upsert Time
- Duplicate Skips

---

# Future Enhancements

Potential future capabilities

- Multi-vector Retrieval
- Image Embeddings
- Audio Embeddings
- Cross-modal Search
- Reranking Models
- Local Embedding Models
- Hybrid Sparse + Dense Search

---

# Recommended Architecture Improvements (Mandatory)

## Semantic Chunking

Do NOT chunk by characters.

Chunk by meaning.

Preferred hierarchy

Document

↓

Section

↓

Paragraph

↓

Chunk

This significantly improves retrieval quality.

---

## Graph-Aware Embeddings

Every chunk should contain references to

- Asset IDs
- Entity IDs
- Graph Node IDs

This allows semantic retrieval to seamlessly transition into graph traversal.

---

## Embedding Provider Abstraction

Never depend directly on Google's embedding API.

Implement

```
EmbeddingProvider

↓

Google

OpenAI

Voyage

Local Models
```

This enables painless provider replacement.

---

## Idempotent Embedding Pipeline

Before generating embeddings

Check

- Chunk Hash
- Existing Vector
- Existing Version

Avoid duplicate vectors.

---

## Re-Embedding Support

Whenever

- Embedding model changes
- Chunk strategy changes
- Ontology changes

The system should support re-embedding without reprocessing original documents.

Store version information for every vector.

---

## Hybrid Search First

Never rely solely on vector similarity.

Preferred retrieval

Semantic Search

↓

Metadata Filters

↓

Graph Expansion

↓

LLM

This architecture is more accurate than plain vector search.

---

## Definition of Done

The embedding module is complete when

✓ Semantic chunks are generated.

✓ Metadata is attached.

✓ Embeddings are created.

✓ Pinecone stores vectors.

✓ Duplicate vectors are avoided.

✓ Versioning is implemented.

✓ Graph-aware chunks are supported.

✓ `embeddings.created` events are emitted.

✓ The system is ready for Semantic Search.
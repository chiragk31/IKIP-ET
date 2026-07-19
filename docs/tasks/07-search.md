# Search.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Purpose

This document defines the search architecture for the Industrial Knowledge Intelligence Platform.

The search system is responsible for retrieving the most relevant knowledge from multiple sources including vector embeddings, knowledge graph, metadata, and document repository.

It provides the foundation for:

- AI Copilot
- GraphRAG
- Asset Intelligence
- Compliance Analysis
- Maintenance Intelligence
- Semantic Search

---

# Goals

The search system should

- Return highly relevant results
- Combine semantic and graph retrieval
- Support metadata filtering
- Minimize hallucinations
- Provide explainable retrieval
- Scale efficiently
- Remain provider independent

---

# Design Philosophy

Search is not vector search.

Search is an orchestration layer.

The retrieval pipeline combines

- Semantic Search
- Metadata Filtering
- Knowledge Graph Expansion
- Context Assembly

before sending context to the LLM.

---

# Responsibilities

The search module is responsible for

- Query Processing
- Query Embedding
- Semantic Search
- Metadata Filtering
- Graph Expansion
- Context Assembly
- Result Ranking

The search module is NOT responsible for

- OCR
- AI Extraction
- Graph Construction
- Embedding Generation
- Response Generation

---

# Architecture

```
User Query

↓

Query Processor

↓

Query Understanding

↓

Query Embedding

↓

Pinecone Search

↓

Metadata Filtering

↓

Graph Expansion

↓

Context Builder

↓

Search Result

↓

AI Copilot
```

---

# Folder Structure

```
backend/app/

search/

query_processor.py

query_rewriter.py

search_service.py

semantic_search.py

graph_search.py

metadata_filter.py

context_builder.py

reranker.py

search_validator.py

search_repository.py

models.py

schemas.py

constants.py
```

---

# Search Pipeline

```
User Query

↓

Normalize Query

↓

Generate Embedding

↓

Pinecone Search

↓

Metadata Filter

↓

Graph Expansion

↓

Context Builder

↓

Reranking

↓

Final Search Result
```

---

# Query Processing

The query processor should

- Normalize whitespace
- Remove unnecessary characters
- Detect language
- Extract entities
- Detect filters
- Identify search intent

---

# Supported Search Types

The platform supports

## Semantic Search

Uses embeddings to find similar knowledge.

---

## Graph Search

Traverses relationships stored in Neo4j.

---

## Metadata Search

Filters documents using structured metadata.

---

## Hybrid Search

Combines

Semantic Search

+

Metadata

+

Graph

Recommended default strategy.

---

## Asset Search

Retrieve

- Asset History
- Procedures
- Incidents
- Measurements
- Maintenance Records

---

## Compliance Search

Retrieve

- Standards
- Regulations
- Compliance Reports

---

# Query Rewriting

Before embedding

Rewrite ambiguous queries.

Example

Input

```
pump inspection
```

↓

Expanded

```
pump inspection procedure maintenance checklist inspection report
```

Improves semantic recall.

---

# Semantic Search

Responsibilities

- Generate Query Embedding
- Retrieve Similar Chunks
- Return Top K Results

Default

Top K

```
10
```

Similarity

Cosine Similarity

---

# Metadata Filtering

Supported filters

- Asset
- Plant
- Department
- Date
- Document Type
- Procedure
- Confidence
- Author

Filters reduce irrelevant retrieval.

---

# Graph Expansion

Graph expansion retrieves

- Neighbor Assets
- Connected Procedures
- Related Failures
- Maintenance History
- Compliance Links

Traversal depth

Recommended

```
2
```

Maximum

```
3
```

Avoid excessive traversal.

---

# Context Builder

Responsibilities

Merge

- Semantic Chunks
- Graph Nodes
- Metadata

into one structured context.

Output

```
Context Package

↓

AI Copilot
```

---

# Context Package

```json
{
    "query":"",
    "chunks":[],
    "graph_nodes":[],
    "relationships":[],
    "metadata":{},
    "citations":[]
}
```

---

# Reranking

After graph expansion

Rank results using

- Semantic Similarity
- Graph Distance
- Metadata Match
- Confidence Score
- Document Freshness

---

# Search Result Schema

```json
{
    "query":"",
    "results":[],
    "citations":[],
    "confidence":0.94
}
```

---

# Citations

Every search result should include

- Document Name
- Section
- Page Number
- Chunk ID
- Asset
- Confidence

The AI should never answer without citations.

---

# Repository Layer

Repositories

```
Search Service

↓

Pinecone Repository

Neo4j Repository

Metadata Repository
```

Business logic never communicates directly with databases.

---

# Search Strategies

Recommended priority

```
Semantic Search

↓

Metadata Filter

↓

Graph Expansion

↓

Rerank

↓

Context Builder
```

---

# Query Cache

Frequently executed queries should be cached.

Cache

- Embeddings
- Search Results
- Metadata Filters

Invalidate cache when

- Documents change
- Graph updates
- Embeddings regenerated

---

# Performance

Implement

- Async Search
- Parallel Retrieval
- Batch Metadata Queries
- Query Cache
- Pagination

Avoid sequential retrieval.

---

# Explainability

Every search result should explain

- Why it matched
- Which chunk matched
- Which graph node matched
- Which metadata filter matched

This improves user trust.

---

# Security

Validate all user queries.

Prevent

- Cypher Injection
- Invalid Metadata Filters
- Excessive Traversal
- Unsupported Queries

Never expose raw database queries.

---

# Logging

Log

- Query
- Embedding Time
- Pinecone Duration
- Graph Traversal Time
- Metadata Filters
- Result Count
- Total Search Duration

---

# Future Enhancements

Potential future capabilities

- Multi-Query Retrieval
- Query Decomposition
- Cross-Language Search
- Personalized Ranking
- Sparse + Dense Hybrid Search
- Learning-to-Rank Models
- Agentic Retrieval

---

# Recommended Architecture Improvements (Mandatory)

## Search Orchestrator

Search should not directly call databases.

Instead

```
Search Service

↓

Semantic Search

↓

Metadata Filter

↓

Graph Search

↓

Context Builder

↓

Result
```

This keeps responsibilities separated.

---

## Hybrid Retrieval First

Always use

Semantic Search

+

Metadata

+

Graph

Avoid vector-only retrieval.

---

## Query Understanding

Before generating embeddings

Extract

- Assets
- Dates
- Procedures
- Intent

This improves precision.

---

## Explainable Search

Every result must be traceable.

Return

- Matching Chunk
- Graph Node
- Confidence
- Citation

Never return opaque results.

---

## Context Before LLM

The LLM should never perform retrieval.

The search module assembles all required context before invoking the AI.

---

## Model Independence

Search should work with any embedding provider.

The search layer should never depend directly on

- Google
- OpenAI
- Voyage

Use provider abstraction.

---

## Definition of Done

The search module is complete when

✓ Query processing is implemented.

✓ Semantic search works.

✓ Metadata filtering works.

✓ Graph expansion works.

✓ Context packages are generated.

✓ Results are reranked.

✓ Citations are attached.

✓ Search explanations are available.

✓ Ready for AI Copilot integration.
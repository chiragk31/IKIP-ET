# Graph.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Purpose

This document defines the Knowledge Graph architecture used by the Industrial Knowledge Intelligence Platform.

The Knowledge Graph represents industrial knowledge as interconnected entities and relationships, enabling intelligent reasoning, semantic retrieval, asset intelligence, and AI-assisted decision making.

The graph is the system of record for relationships, while vector embeddings (Pinecone) are used for semantic similarity.

---

# Goals

The Knowledge Graph should:

- Represent industrial knowledge as a graph
- Connect entities extracted from documents
- Enable multi-hop reasoning
- Support Asset 360 views
- Power GraphRAG
- Support future Digital Twin integration
- Remain deterministic and explainable

---

# Design Philosophy

The graph is **deterministic**.

LLMs never modify the graph directly.

Pipeline

```
Industrial Document

↓

Canonical Document

↓

AI Knowledge Extraction

↓

Canonical Knowledge Object

↓

Ontology Manager

↓

Graph Builder

↓

Neo4j
```

---

# Responsibilities

The graph is responsible for

- Entity Storage
- Relationship Storage
- Asset Connections
- Graph Queries
- Multi-hop Traversal
- Graph Analytics

The graph is NOT responsible for

- OCR
- Document Parsing
- Prompt Engineering
- Embeddings
- Chat
- Semantic Ranking

---

# Architecture

```
Knowledge Object

↓

Graph Builder

↓

Node Builder

↓

Relationship Builder

↓

Graph Validator

↓

Neo4j Repository

↓

Neo4j
```

---

# Folder Structure

```
backend/app/

graph/

graph_builder.py

node_builder.py

relationship_builder.py

graph_validator.py

graph_repository.py

graph_queries.py

graph_service.py

models.py

schemas.py

constants.py
```

---

# Graph Pipeline

```
knowledge.extracted

↓

Ontology Validation

↓

Node Builder

↓

Relationship Builder

↓

Graph Validation

↓

Batch Insert

↓

graph.updated
```

---

# Graph Design Principles

## Principle 1

One real-world object = One graph node.

Example

```
Pump P-101

↓

One Node
```

Never create duplicate nodes.

---

## Principle 2

Relationships are directional.

Example

```
Pump

↓

PART_OF

↓

Cooling System
```

Always preserve relationship direction.

---

## Principle 3

Graph stores facts.

Never store AI opinions.

Allowed

✓ Pump P-101 failed on 12 Jan.

Not Allowed

✗ Pump probably has bearing failure.

---

## Principle 4

Every graph element has provenance.

Every node and relationship should reference

- Source Document
- Confidence
- Timestamp
- Extraction Version

---

# Node Types

## Asset

Examples

- Pump
- Boiler
- Compressor
- Turbine
- Motor

---

## Component

Examples

- Bearing
- Gearbox
- Seal
- Shaft

---

## Person

Examples

- Operator
- Technician
- Inspector

---

## Organization

Examples

- Vendor
- OEM
- Plant

---

## Procedure

Examples

- Startup
- Shutdown
- Calibration

---

## Event

Examples

- Failure
- Inspection
- Maintenance

---

## Measurement

Examples

- Pressure
- Temperature
- Voltage
- Current

---

## Document

Examples

- SOP
- Manual
- Incident Report
- Work Order

---

## Location

Examples

- Plant
- Building
- Unit
- Floor

---

## Regulation

Examples

- OSHA
- ISO
- API

---

# Relationship Types

```
PART_OF

CONNECTED_TO

LOCATED_IN

USES

OPERATED_BY

INSPECTED_BY

MAINTAINED_BY

CAUSES

RESULTS_IN

REQUIRES

MENTIONED_IN

REFERENCES

RELATED_TO

COMPLIES_WITH

GENERATED_FROM
```

---

# Node Schema

```json
{
    "id":"",
    "type":"Asset",
    "name":"Pump P-101",
    "properties":{},
    "confidence":0.95,
    "source_document":"",
    "created_at":""
}
```

---

# Relationship Schema

```json
{
    "source":"",
    "relationship":"PART_OF",
    "target":"",
    "confidence":0.92,
    "source_document":""
}
```

---

# Graph Builder

Responsibilities

- Create nodes
- Merge duplicates
- Create relationships
- Validate graph
- Batch writes

Graph Builder must NEVER

- Call Gemini
- Run OCR
- Parse documents
- Generate Cypher using AI

---

# Node Builder

Responsibilities

- Convert entities into Neo4j nodes
- Merge duplicates
- Add metadata
- Apply labels

---

# Relationship Builder

Responsibilities

- Validate endpoints
- Validate relationship types
- Remove duplicates
- Create graph edges

---

# Graph Validator

Before insertion

Validate

- Duplicate Nodes
- Duplicate Relationships
- Invalid Labels
- Missing Nodes
- Circular Self Links
- Invalid Confidence
- Invalid Relationship Types

Reject invalid graph objects.

---

# Repository Layer

Only GraphRepository communicates with Neo4j.

Architecture

```
Graph Service

↓

Graph Repository

↓

Neo4j Driver

↓

Neo4j
```

Never call Neo4j directly from services.

---

# Graph Queries

Supported queries

Asset 360

Failure History

Related Documents

Inspection Timeline

Maintenance Timeline

Neighbor Discovery

Shortest Path

Subgraph Retrieval

Compliance Mapping

---

# Cypher Guidelines

Use parameterized queries only.

Never concatenate strings.

Never execute AI-generated Cypher.

All queries should be predefined or generated by backend logic.

---

# Batch Operations

Always batch writes.

Avoid individual node insertion.

Example

```
100 Nodes

↓

Batch

↓

Neo4j
```

Improves performance significantly.

---

# Provenance

Every node stores

- Source Document
- Extraction Version
- Confidence
- Timestamp

Every relationship stores

- Source Document
- Confidence
- Created Time

This enables explainability.

---

# Graph Versioning

Every graph update should record

- Graph Version
- Pipeline Version
- Ontology Version
- AI Model Version

This supports future rebuilding.

---

# Event Flow

```
knowledge.extracted

↓

Graph Builder

↓

Neo4j

↓

graph.updated
```

No downstream module should call Neo4j directly.

---

# Integration with Pinecone

Neo4j

Stores

Relationships

Hierarchy

Connections

Reasoning

Pinecone

Stores

Embeddings

Semantic Similarity

Natural Language Retrieval

Together

```
User Question

↓

Embedding Search (Pinecone)

↓

Relevant Documents

↓

Relevant Graph Nodes

↓

Graph Traversal

↓

Context Assembly

↓

LLM

↓

Final Answer
```

---

# GraphRAG Strategy

The graph provides

- Neighbor Expansion
- Related Assets
- Connected Procedures
- Maintenance History
- Compliance Links

Pinecone provides

- Semantic Recall

LLM generates

- Final grounded answer

---

# Performance

Implement

- Batch Inserts
- Indexed Properties
- Cached Queries
- Lazy Loading
- Pagination
- Query Profiling

---

# Security

Never expose raw Neo4j access.

Never allow arbitrary Cypher execution.

Validate every graph mutation.

Use repository abstraction.

---

# Logging

Log

- Nodes Created
- Relationships Created
- Batch Duration
- Duplicate Merges
- Validation Failures
- Query Performance

---

# Future Enhancements

Potential future capabilities

- Temporal Graphs
- Digital Twin
- Predictive Maintenance
- Graph Analytics
- Community Detection
- Root Cause Analysis
- Graph Embeddings
- Knowledge Graph Visualization
- Agentic Graph Traversal

---

# Recommended Architecture Improvements (Mandatory)

## Graph Builder Pattern

Always separate graph construction into distinct builders.

```
Knowledge Object

↓

Node Builder

↓

Relationship Builder

↓

Validator

↓

Repository

↓

Neo4j
```

This makes testing significantly easier.

---

## Graph as Source of Truth

Neo4j is the authoritative source for relationships.

Pinecone should NEVER store relationships.

---

## Deterministic Graph Construction

Graph creation must be deterministic.

The same Canonical Knowledge Object should always generate the same graph.

Avoid random IDs or non-repeatable graph structures.

---

## Stable Node Identity

Every node should use a stable identifier.

Preferred priority

1. Asset Tag
2. Equipment ID
3. UUID
4. Generated Hash

Never identify nodes solely by display names.

---

## Idempotent Graph Updates

Running the same pipeline multiple times must not create duplicate nodes or duplicate relationships.

Use MERGE semantics and deterministic identifiers.

---

## Graph Explainability

Every node and relationship must be traceable back to its originating document.

The UI should be able to answer:

- Which document created this node?
- Which AI extraction produced this relationship?
- What confidence was assigned?
- When was it created?

---

## Definition of Done

The graph module is complete when

✓ Nodes are generated from Canonical Knowledge Objects.

✓ Relationships are validated before insertion.

✓ Graph updates are idempotent.

✓ Neo4j is accessed only through GraphRepository.

✓ Provenance is stored for every graph element.

✓ GraphRAG integration is supported.

✓ `graph.updated` events are emitted.

✓ The system is ready for Semantic Search and AI Copilot.
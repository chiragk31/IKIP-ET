# Assets.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Purpose

This document defines the Asset Intelligence architecture used by the Industrial Knowledge Intelligence Platform.

The Asset Intelligence module provides a unified 360° view of every industrial asset by combining information from documents, the knowledge graph, semantic search, and historical records.

It transforms fragmented information into actionable intelligence.

---

# Goals

The Asset Intelligence module should

- Build a complete Asset 360 view
- Aggregate information from multiple sources
- Display maintenance history
- Display inspection history
- Display compliance status
- Display connected assets
- Support future predictive maintenance

---

# Design Philosophy

Asset Intelligence is an aggregation layer.

It never performs document parsing.

It never performs OCR.

It never generates embeddings.

It consumes validated information from existing platform components.

---

# Responsibilities

The Asset module is responsible for

- Asset Profiles
- Asset History
- Asset Relationships
- Asset Timeline
- Asset Health Summary
- Asset Analytics

The Asset module is NOT responsible for

- OCR
- AI Extraction
- Graph Construction
- Embedding Generation
- Semantic Search

---

# Architecture

```
Asset Request

↓

Asset Service

↓

Graph Service

↓

Search Service

↓

Metadata Repository

↓

Asset Builder

↓

Asset 360 Profile
```

---

# Folder Structure

```
backend/app/

assets/

asset_service.py

asset_builder.py

asset_repository.py

asset_summary.py

asset_history.py

asset_relationships.py

asset_health.py

asset_validator.py

models.py

schemas.py

constants.py
```

---

# Asset Pipeline

```
Asset Request

↓

Graph Query

↓

Metadata Lookup

↓

Related Documents

↓

Timeline Builder

↓

Health Summary

↓

Asset 360
```

---

# Asset Identity

Every asset must have a unique identifier.

Preferred priority

1. Asset Tag
2. Equipment ID
3. UUID

Display names are never used as identifiers.

---

# Asset Profile

Each asset should contain

- Asset Name
- Asset Tag
- Asset Type
- Manufacturer
- Model
- Serial Number
- Installation Date
- Location
- Department
- Status

---

# Asset Relationships

Supported relationships

- Part Of
- Connected To
- Uses
- Powered By
- Controlled By
- Monitored By
- Maintained By
- Inspected By

These relationships are retrieved from Neo4j.

---

# Asset Timeline

Timeline includes

- Installation
- Inspections
- Maintenance
- Failures
- Repairs
- Replacements
- Compliance Audits

Timeline should be displayed chronologically.

---

# Asset Health Summary

Health summary combines

- Maintenance Frequency
- Failure Count
- Inspection Status
- Compliance Status
- Recent Alerts

This is descriptive only.

Predictive analytics belongs to future versions.

---

# Asset Documents

Associated documents include

- SOPs
- Manuals
- Work Orders
- Maintenance Reports
- Inspection Reports
- Incident Reports
- Compliance Reports

Documents are retrieved using metadata and graph relationships.

---

# Asset Search

Users should be able to search by

- Asset Tag
- Asset Name
- Equipment ID
- Location
- Department
- Asset Type

---

# Asset Summary

The Asset Summary contains

- Basic Information
- Connected Assets
- Active Procedures
- Maintenance History
- Inspection History
- Compliance Overview
- Related Documents

---

# Asset 360 Response

```json
{
  "asset": {},
  "timeline": [],
  "relationships": [],
  "documents": [],
  "procedures": [],
  "maintenance": [],
  "inspections": [],
  "compliance": [],
  "health_summary": {}
}
```

---

# Graph Integration

The Asset module retrieves

- Connected Assets
- Neighbor Nodes
- Maintenance Events
- Inspection Events
- Procedures

Only from the Graph module.

---

# Search Integration

The Search module retrieves

- Related Chunks
- Semantic Matches
- Supporting Documents

The Asset module never performs vector search directly.

---

# Repository Layer

```
Asset Service

↓

Asset Repository

↓

Graph Repository

↓

Metadata Repository
```

Business logic never communicates directly with Neo4j or Supabase.

---

# Performance

Implement

- Asset Cache
- Lazy Loading
- Timeline Pagination
- Parallel Graph Queries
- Async APIs

---

# Security

Validate

- Asset IDs
- Query Parameters
- User Permissions

Never expose internal graph identifiers.

---

# Logging

Log

- Asset Requests
- Timeline Generation
- Graph Queries
- Search Queries
- Response Time
- Cache Hits

---

# Future Enhancements

Potential future capabilities

- Predictive Maintenance
- Remaining Useful Life (RUL)
- Failure Probability
- Sensor Integration
- Digital Twin
- Asset Benchmarking
- KPI Dashboards

---

# Recommended Architecture Improvements (Mandatory)

## Asset Builder Pattern

Separate profile construction.

```
Asset Service

↓

Asset Builder

↓

Timeline Builder

↓

Relationship Builder

↓

Health Builder

↓

Asset Profile
```

Each builder should have one responsibility.

---

## Asset as Central Entity

Every feature should reference assets using the unique Asset ID.

Documents, graph nodes, embeddings, and timelines should all point back to the same asset.

---

## Timeline First Design

Rather than displaying isolated information, present asset events as a chronological timeline.

This improves usability for maintenance and investigation workflows.

---

## Aggregation Instead of Duplication

Never duplicate information already available in

- Graph
- Search
- Metadata

The Asset module aggregates existing knowledge into a single response.

---

## Explainability

Every field in the Asset 360 profile should be traceable.

Users should be able to identify

- Which document provided the information
- Which graph relationship was used
- Which maintenance event contributed
- Which inspection report was referenced

---

## Definition of Done

The Asset Intelligence module is complete when

✓ Asset profiles are generated.

✓ Asset timelines are available.

✓ Graph relationships are retrieved.

✓ Related documents are linked.

✓ Asset summaries are generated.

✓ Health summaries are available.

✓ Asset 360 responses are explainable.

✓ Ready for Dashboard and AI Copilot integration.
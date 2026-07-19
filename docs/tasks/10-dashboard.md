# Dashboard.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Purpose

This document defines the Dashboard architecture used by the Industrial Knowledge Intelligence Platform.

The Dashboard provides a unified operational view of the platform by visualizing documents, assets, knowledge graphs, AI insights, processing pipelines, and system health.

The Dashboard is a presentation layer only.

It never contains business logic.

---

# Goals

The Dashboard should

- Provide operational visibility
- Display Asset Intelligence
- Visualize the Knowledge Graph
- Monitor document processing
- Surface AI insights
- Display system health
- Support real-time updates

---

# Design Philosophy

The Dashboard is an aggregation layer.

It consumes APIs from backend services.

It never

- Parses documents
- Runs OCR
- Calls LLMs
- Queries databases directly
- Generates embeddings
- Traverses Neo4j directly

---

# Responsibilities

The Dashboard is responsible for

- Data Visualization
- Metrics Display
- Graph Visualization
- Asset Overview
- Document Status
- Search Analytics
- System Monitoring

The Dashboard is NOT responsible for

- Business Logic
- AI Processing
- Graph Construction
- Embedding Generation
- Search Logic

---

# Architecture

```
User

↓

Dashboard

↓

Dashboard API

↓

Backend Services

↓

Graph

Search

Assets

Documents

System
```

---

# Folder Structure

```
frontend/

features/

dashboard/

components/

OverviewCards/

RecentDocuments/

AssetOverview/

KnowledgeGraph/

ProcessingStatus/

SearchAnalytics/

SystemHealth/

hooks/

services/

types/

pages/

dashboard/
```

---

# Dashboard Layout

```
--------------------------------------------------------

Header

--------------------------------------------------------

Overview Cards

--------------------------------------------------------

Asset Summary | Processing Status

--------------------------------------------------------

Knowledge Graph | Search Analytics

--------------------------------------------------------

Recent Documents | System Health

--------------------------------------------------------

Recent Activity Timeline

--------------------------------------------------------
```

---

# Overview Cards

Display

- Total Documents
- Total Assets
- Knowledge Graph Nodes
- Graph Relationships
- Embeddings
- Processed Documents
- Failed Documents

These cards are refreshed automatically.

---

# Asset Overview

Display

- Asset Count
- Asset Types
- Active Assets
- Recent Maintenance
- Recent Failures
- Compliance Status

Data source

Asset Service

---

# Document Overview

Display

- Uploaded Documents
- Processing Queue
- Completed
- Failed
- Pending

Data source

Document Service

---

# Knowledge Graph Widget

Display

- Interactive Graph
- Connected Assets
- Procedures
- Failures
- Documents

The graph is read-only.

Users cannot modify graph data.

---

# Search Analytics

Display

- Search Volume
- Top Queries
- Average Search Time
- Most Accessed Documents
- Search Success Rate

Data source

Search Service

---

# AI Copilot Widget

Display

- Recent Conversations
- Suggested Questions
- Recent Citations

Future versions may embed the full Copilot.

---

# System Health

Display

- API Status
- Database Status
- Neo4j Status
- Pinecone Status
- AI Provider Status
- Queue Status

Use health endpoints.

---

# Processing Pipeline

Display

Current document processing stage

```
Uploaded

↓

Processing

↓

Knowledge Extraction

↓

Ontology

↓

Graph

↓

Embeddings

↓

Ready
```

Each stage displays

- Status
- Timestamp
- Duration

---

# Activity Timeline

Recent events

- Document Uploaded
- Processing Completed
- Graph Updated
- Embeddings Created
- Asset Updated
- User Searches

Display newest first.

---

# Dashboard APIs

Dashboard consumes

```
GET /dashboard/overview

GET /dashboard/assets

GET /dashboard/documents

GET /dashboard/system

GET /dashboard/search

GET /dashboard/activity

GET /dashboard/graph
```

The Dashboard never aggregates data on the client.

---

# Graph Visualization

Display

- Asset Nodes
- Procedure Nodes
- Event Nodes
- Relationships

Support

- Zoom
- Pan
- Node Selection

Graph editing is not supported.

---

# Refresh Strategy

Use

TanStack Query

Refresh

- Overview
- Activity
- System Health

Use polling or WebSockets in future versions.

---

# State Management

Use

Server State

→ TanStack Query

Local UI State

→ Zustand

Forms

→ React Hook Form

---

# Performance

Implement

- Lazy Loading
- Virtual Lists
- Pagination
- Cached Queries
- Code Splitting

Avoid rendering unnecessary widgets.

---

# Security

Validate

- User Authentication
- Dashboard Permissions
- API Authorization

Never expose

- API Keys
- Internal IDs
- Database Queries

---

# Logging

Track

- Dashboard Visits
- Widget Load Time
- API Response Time
- User Interactions
- Search Requests

---

# Future Enhancements

Potential future capabilities

- Live Event Streaming
- IoT Sensor Dashboard
- Predictive Maintenance Dashboard
- KPI Monitoring
- SLA Monitoring
- Executive Dashboard
- Plant Comparison
- Custom Dashboard Widgets

---

# Recommended Architecture Improvements (Mandatory)

## Widget-Based Architecture

Each dashboard section should be an independent widget.

Example

```
Dashboard

│

├── Overview Widget

├── Assets Widget

├── Graph Widget

├── Documents Widget

├── Search Widget

├── Health Widget

└── Activity Widget
```

Each widget owns

- API
- Components
- Loading State
- Error State

---

## Dashboard Service

Instead of every widget calling multiple APIs

Implement

```
Dashboard

↓

Dashboard Service

↓

Backend APIs
```

This simplifies the frontend.

---

## Read-Only Dashboard

The Dashboard is for visualization.

Mutating actions belong to dedicated modules.

---

## Progressive Loading

Load widgets independently.

If one widget fails

The remaining dashboard should continue working.

---

## Real-Time Ready

The architecture should support future

- WebSockets
- Server-Sent Events
- Event Streaming

without redesign.

---

## Explainability

Every dashboard metric should identify

- Source Service
- Last Updated
- Data Freshness

Users should know where every metric originates.

---

# UI Guidelines

Use

- Next.js App Router
- Tailwind CSS
- shadcn/ui
- Recharts
- React Flow (Knowledge Graph)

Maintain

- Responsive Layout
- Accessible Components
- Minimal Animations

---

# Definition of Done

The Dashboard module is complete when

✓ Overview metrics are displayed.

✓ Asset Intelligence is visualized.

✓ Document processing status is available.

✓ Knowledge Graph is interactive.

✓ Search analytics are displayed.

✓ System health is monitored.

✓ Activity timeline works.

✓ Widgets load independently.

✓ Ready for production deployment.
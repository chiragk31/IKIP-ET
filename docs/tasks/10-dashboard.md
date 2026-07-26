# Dashboard.md

# Industrial Knowledge Intelligence Platform


Added Visual Design System (§) per hackathon UI requirements. No architectural or API changes.

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Initial Release | Dashboard architecture |
| 1.1 | 2026-07-26 | Added Visual Design System |
| 1.2 | TBD | Added Grid Layout, Interaction Model, Loading & Empty States, Asset 360 Navigation, Document Ingestion UI Specification |

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

# Visual Design System (Mandatory)

## Positioning

This is not a generic admin panel and must not read as one. The visual target is **industrial control-room software** — the category occupied by Siemens Insights Hub, Azure Digital Twins Explorer, AVEVA System Platform, and Grafana's operational dashboards. These products share a visual language because their users are plant engineers and reliability managers making real decisions from dense, high-stakes data — not consumers browsing a SaaS marketing site. Every visual choice below is justified by that context, not decoration.

**Explicitly avoid**: rounded pastel SaaS cards, generic purple/indigo gradients, playful illustration, centered marketing-style hero sections, or anything that reads as a Bootstrap/shadcn default left untouched. If a component would look at home on a project-management tool or a consumer fintech app, it is wrong for this product.

## Design Tokens

### Color Palette

| Token | Hex | Usage |
|---|---|---|
| `--canvas` | `#0B0E11` | Base app background — near-black graphite, like a powered HMI screen |
| `--surface` | `#151A1F` | Panel/card backgrounds, one step up from canvas |
| `--surface-raised` | `#1D242B` | Hover states, active panels, modals |
| `--border` | `#2A333B` | Hairline dividers and card borders — always 1px, never soft shadows as the primary separator |
| `--text-primary` | `#E8ECEF` | Primary text — off-white, never pure `#FFFFFF` (too harsh against graphite) |
| `--text-secondary` | `#8A96A3` | Labels, captions, metadata |
| `--signal-amber` | `#F5A623` | Primary accent — warnings, active alerts, the platform's signature color (the universal industrial "attention" hue, evoking an annunciator panel light) |
| `--signal-cyan` | `#3DDBD9` | Secondary accent — healthy/active/online states, live data, graph edges |
| `--signal-red` | `#E5484D` | Critical failures, compliance violations only — used sparingly, never for routine UI |
| `--signal-green` | `#4ADE80` | Confirmed-good states (passed compliance, completed pipeline stage) |

This is a **dark-canvas-first** design — do not build a light theme as the default; a light mode may exist as a toggle but the control-room identity lives in the dark palette.

### Typography

| Role | Typeface | Notes |
|---|---|---|
| Display / Headings | **IBM Plex Sans** (or Inter as fallback) | Engineering-grade grotesk, not a warm humanist face — headings should feel drafted, not designed |
| Body / UI text | **IBM Plex Sans**, regular weights | Same family as display, different weights — avoid mixing in a second humanist sans |
| Data / Numeric / Code | **IBM Plex Mono** (or JetBrains Mono) | **Mandatory for every number on the dashboard**: entity counts, confidence scores, timestamps, durations, node IDs. This is the single most important typographic decision — numeric data set in a monospace face is what makes the platform read as instrumentation rather than a content site. Tabular figures (`font-variant-numeric: tabular-nums`) required wherever numbers stack in a column. |

Type scale should be tight and information-dense (14–16px body, not the generous 18px+ spacing common in consumer SaaS). Plant engineers scanning many panels need density, not whitespace-as-luxury.

### Layout Signature

- **Hairline grid, not shadow-based elevation.** Panels are separated by 1px `--border` lines, not soft drop-shadows. This is the single biggest tell that distinguishes control-room software from consumer dashboards.
- **Zero or minimal border-radius** (0–4px). Sharp, instrument-panel edges — not the 12–16px rounded cards common in generic admin templates.
- **Status is always color + icon + text together**, never color alone (accessibility, and because operators scan fast under fluorescent light, not gradient-lit marketing screens).
- Grid density should assume a widescreen operator monitor as the primary target, with graceful degradation to laptop and tablet — not mobile-first.

## Signature Element (Mandatory)

The Overview page must include one element that could not be mistaken for any other product's dashboard: a **live "Knowledge Pulse" strip** — a thin horizontal band beneath the header showing a continuously animated, subtle particle/node flow (using the same node-and-edge visual vocabulary as the Knowledge Graph widget) representing documents actively moving through the pipeline stages (Uploaded → Processing → Extraction → Ontology → Graph → Embeddings → Ready). This is not decorative animation — it is the one place motion is deliberately spent, and it should visually echo the real pipeline defined in the Processing Pipeline section below, using `--signal-cyan` for in-flight items and `--signal-amber` for items with warnings. Everywhere else, motion should be restrained: brief hover states and a single, deliberate load-in for each widget — no scroll-triggered flourishes, no bouncing, no confetti-style success states.

## Component Direction by Widget

- **Overview Cards**: Numeric-first, monospace figures at the visual anchor of each card, `--text-secondary` label beneath — not the reverse. Sparkline trend (via Recharts) using `--signal-cyan`, no fill gradient.
- **Asset Overview**: Table-dense, not card-grid. Status indicators as small filled squares (not rounded pills) in signal colors — echoing physical indicator lights on real equipment panels.
- **Knowledge Graph Widget** (React Flow): Canvas background `--canvas`, nodes colored by entity type using a **restrained** 4–5 color subset of the palette (do not invent a rainbow category-color system — reuse signal colors plus one or two neutral greys for less-critical node types), edges in `--border`-adjacent grey with `--signal-cyan` highlight on hover/selection only.
- **Processing Pipeline**: Rendered as a literal horizontal stepper matching the 7-stage flow in this document, each stage as a small square node connected by a thin line — this component's visual language should directly match the Knowledge Pulse signature element, reinforcing one consistent visual system rather than two different "progress bar" idioms.
- **System Health**: Status dot + service name + latency number (monospace), grouped in a single dense row per service, not individual large cards — this is a systems status board, not a marketing feature grid.

## Explicit Non-Goals

- No pastel colors anywhere in the primary UI.
- No default shadcn/ui component styling left unthemed — every component must be restyled to the token system above before shipping.
- No stock illustration or iconography sets that look consumer-facing (avoid rounded duotone icon packs; prefer a technical/outline icon set like Lucide, used sparingly).
- No light-mode-first design.

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

Knowledge Pulse (signature live strip)

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
- shadcn/ui (restyled entirely per §Visual Design System — no default theme left in place)
- Recharts (styled with signal-color palette, no default chart colors)
- React Flow (Knowledge Graph) — canvas and node styling per §Visual Design System

Maintain

- Responsive Layout (widescreen operator monitor as primary target — see §Visual Design System)
- Accessible Components (status conveyed by color + icon + text, never color alone)
- Minimal Animations (motion budget spent on the Knowledge Pulse signature element only — see §Visual Design System)

All Tailwind theme tokens (colors, border-radius, font families) must be configured in `tailwind.config.ts` to match the token table in §Visual Design System exactly — no ad hoc hex values in component files.

---

---

# Dashboard Grid Layout (Mandatory)

The Dashboard uses a responsive 12-column grid optimized for widescreen operator monitors.

Desktop (≥1440px)

```
+--------------------------------------------------------------+
| Header                                                       |
+--------------------------------------------------------------+
| Knowledge Pulse                                              |
+--------------------------------------------------------------+
| KPI Cards (12 Columns)                                       |
+-------------------------+------------------------------------+
| Asset Intelligence (5)  | Processing Pipeline (7)            |
+-------------------------+------------------------------------+
| Knowledge Graph (8)     | Search Analytics (4)              |
+-------------------------+------------------------------------+
| Recent Documents (6)    | System Health (6)                 |
+--------------------------------------------------------------+
| Activity Timeline (12)                                     |
+--------------------------------------------------------------+
```

Laptop (1024–1440px)

- Knowledge Graph expands full width
- Search Analytics moves below
- Asset Intelligence stacks above Processing Pipeline

Tablet

Widgets stack vertically while preserving independent loading.

Mobile

Dashboard supports monitoring only.

Knowledge Graph becomes an optional expandable page.


---

# Widget Interaction Guidelines

All widgets follow consistent interaction rules.

Hover

- Elevate using surface-raised background only
- Never use large drop shadows
- Highlight border using signal-cyan

Click

- Navigate to detailed module
- Preserve filters
- Preserve scroll position

Double Click

Knowledge Graph

- Center selected node

Asset Card

- Open Asset 360

Document Card

- Open Document Viewer

Right Click

Reserved for future contextual actions.


---

# Loading States

Widgets load independently.

Every widget provides

- Skeleton Placeholder
- Loading Indicator
- Error State
- Empty State

Examples

Overview Cards

- Skeleton KPI cards

Knowledge Graph

- Animated node placeholders

Recent Documents

- Skeleton rows

System Health

- Placeholder status indicators

Never block the entire Dashboard while a single widget is loading.


---

# Empty States

Widgets must provide meaningful empty states.

Examples

Recent Maintenance

✓ No maintenance records found.

Failures

✓ No active failures detected.

Search Analytics

No search activity available.

Knowledge Graph

No connected entities.

Processing Queue

No active processing jobs.

Empty states should communicate system status rather than appearing unfinished.


---

# Asset 360 Navigation Flow

The Dashboard is the primary entry point for Asset Intelligence.

Users may access Asset 360 from

- Asset Overview
- Knowledge Graph
- Search Results
- Recent Activity
- AI Copilot Citations

Navigation Flow

```
Dashboard

↓

Asset Widget

↓

Asset Summary

↓

Asset 360

↓

Timeline

↓

Related Documents

↓

Knowledge Graph

↓

Source Evidence
```

Navigation must preserve

- Current filters
- Selected document
- Selected asset
- Search context

Back navigation returns users to the previous dashboard state.
---

# Design Principles

Every dashboard screen should satisfy the following principles.

Information First

Engineering data has higher priority than decorative visuals.

Scanability

Critical operational information should be discoverable within five seconds.

Explainability

Every metric identifies

- Source Service
- Last Updated
- Data Freshness

Consistency

Every widget follows the same interaction model, typography, spacing, and status indicators.

Drill-down

Every KPI, graph node, and asset card should provide a path to more detailed information.

Performance

Partial loading is preferred over blocking the entire Dashboard.

Accessibility

Status is always communicated using

- Color
- Icon
- Text

Never color alone.
---

# Document Ingestion UI (Current Implementation)

The platform already includes a Document Ingestion interface for uploading industrial documents into the processing pipeline.

The existing implementation shall be updated to fully adopt the Dashboard Visual Design System defined in this document.

## Purpose

The Document Ingestion module serves as the primary entry point for all industrial knowledge entering the platform.

Supported document types include

- PDF
- DOCX
- Images
- CAD Drawings (future)
- Spreadsheets (future)

## Updated Visual Direction

The ingestion experience must match the industrial control-room theme.

### Upload Zone

Replace consumer-style dashed upload cards with a structured industrial upload panel.

Display

- Upload Queue
- File Size
- File Type
- Upload Progress
- Processing Status
- Validation Results

### Upload Queue

Each uploaded document appears in a dense table layout.

Columns

- File Name
- Document Type
- Upload Time
- Status
- Current Processing Stage
- Confidence
- Actions

Status indicators use the standard signal colors.

- Cyan → Uploading
- Green → Completed
- Amber → Processing
- Red → Failed

### Processing Progress

After upload, display the complete processing pipeline.

Uploaded
→ Processing
→ OCR
→ Knowledge Extraction
→ Ontology
→ Knowledge Graph
→ Embeddings
→ Ready

Each stage displays

- Current Status
- Timestamp
- Duration

### Document Preview

Selecting a document opens a preview panel containing

- Metadata
- Extracted Text
- Processing Logs
- Related Assets
- Related Knowledge Graph Nodes

### Explainability

Every processed document displays

- Source Document ID
- Processing Duration
- AI Confidence
- Last Updated
- Processing Pipeline Stage

### Navigation

Completed documents provide direct navigation to

- Asset 360
- Knowledge Graph
- Document Viewer
- AI Copilot

The Document Ingestion module follows the same typography, spacing, color palette, component styling, loading states, and interaction patterns defined by the Dashboard Visual Design System.




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

✓ Visual Design System tokens are implemented exactly as specified — no default shadcn/ui, Tailwind, or Recharts styling remains unthemed.

✓ Ready for production deployment.
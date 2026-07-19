# Ontology.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Purpose

The ontology defines how industrial knowledge is represented inside the Knowledge Graph.

The ontology should not be completely predefined.

Instead, it consists of:

1. Core Ontology
2. Dynamic Ontology

The Core Ontology provides stable entity types.

The Dynamic Ontology continuously expands as new concepts are discovered from uploaded documents.

---

# Ontology Philosophy

Industrial documents are highly heterogeneous.

Different organizations use different terminology.

Examples

Pump

Motor

Compressor

Drive Unit

Prime Mover

may all describe similar concepts.

Therefore,

the ontology should normalize concepts while preserving original terminology.

---

# Ontology Layers

Layer 1

Core Ontology

↓

Layer 2

Industry Concepts

↓

Layer 3

Organization Specific Concepts

↓

Layer 4

Document Specific Concepts

Only Layer 1 is predefined.

The remaining layers evolve automatically.

---

# Core Entity Types

These entities always exist.

## Document

Represents uploaded documents.

Properties

- document_id
- title
- type
- language
- created_at

---

## Asset

Represents industrial equipment.

Examples

Pump

Valve

Boiler

Motor

Compressor

Tank

Generator

Properties

- asset_id
- asset_name
- asset_type
- manufacturer
- serial_number

---

## Person

Examples

Engineer

Operator

Supervisor

Inspector

Properties

- person_id
- name
- department
- designation

---

## Organization

Examples

Plant

Vendor

OEM

Contractor

Properties

- organization_id
- name

---

## Location

Examples

Plant

Area

Section

Unit

Building

Properties

- location_id
- name
- hierarchy

---

## Procedure

Examples

Inspection

Calibration

Shutdown

Maintenance

Startup

LOTO

Properties

- procedure_id
- name
- category

---

## Event

Examples

Failure

Shutdown

Inspection

Repair

Alarm

Maintenance

Properties

- event_id
- timestamp
- severity

---

## Measurement

Examples

Temperature

Pressure

Flow

Voltage

Current

RPM

Properties

- measurement_id
- parameter
- value
- unit

---

## Risk

Examples

Leak

Explosion

Corrosion

Fire

Properties

- risk_id
- category
- severity

---

## Regulation

Examples

ISO

OSHA

Factory Rules

Properties

- regulation_id
- authority

---

# Dynamic Entity Types

The AI may discover new concepts.

Examples

LOTO Permit

Maintenance Window

Safety Zone

Inspection Class

Calibration Grade

Vendor Checklist

Hazard Category

Failure Pattern

These should be created dynamically after validation.

---

# Relationship Types

Relationships connect entities.

Examples

Document

MENTIONS

Asset

---

Asset

HAS_FAILURE

Failure

---

Failure

CAUSED_BY

Risk

---

Asset

LOCATED_IN

Location

---

Procedure

USES

Asset

---

Person

PERFORMED

Procedure

---

Procedure

REQUIRES

Regulation

---

Document

REFERENCES

Document

---

Organization

OWNS

Asset

---

Asset

CONNECTED_TO

Asset

---

Measurement

RECORDED_FOR

Asset

---

Event

INVOLVES

Asset

---

Risk

MITIGATED_BY

Procedure

---

# Ontology Discovery Workflow

Document Uploaded

↓

Parser

↓

OCR

↓

LLM Extraction

↓

Structured JSON

↓

Ontology Manager

↓

Validation

↓

Graph Builder

↓

Neo4j

The ontology is updated only after validation.

---

# Ontology Manager Responsibilities

The Ontology Manager is responsible for:

- Normalizing entity names
- Removing duplicates
- Mapping synonyms
- Validating new entity types
- Assigning categories
- Creating graph-ready entities
- Maintaining ontology consistency

The Ontology Manager never calls the LLM directly.

It only consumes structured JSON.

---

# Synonym Resolution

Different documents may use different terms.

Example

Motor

Electric Motor

Drive Motor

Main Motor

↓

Normalized

Motor

Original values should still be preserved as aliases.

---

# Entity Normalization

Example

Input

Pump P101

P-101

Main Pump

Pump No.1

↓

Normalized Entity

Asset

asset_id = P101

Aliases

Pump P101

P-101

Main Pump

Pump No.1

---

# Confidence Scores

Every extracted entity must include

confidence

Example

95%

80%

65%

Low-confidence entities should be flagged for review.

---

# Canonical Entity Format

Every extracted entity follows the same schema.

```json
{
  "entity_id": "asset_p101",
  "entity_type": "Asset",
  "label": "Pump P101",
  "aliases": [
    "P101",
    "Main Pump"
  ],
  "confidence": 0.97,
  "source_document": "maintenance_report_12.pdf",
  "page": 4
}
```

---

# Canonical Relationship Format

```json
{
  "source": "asset_p101",
  "relationship": "HAS_FAILURE",
  "target": "failure_bearing",
  "confidence": 0.94
}
```

---

# Ontology Validation Rules

A new entity type should only be created if:

- It does not already exist.
- It appears in multiple documents or has high confidence.
- It has a meaningful relationship to existing entities.

Otherwise, classify it as a temporary concept until validated.

---

# Graph Evolution

The ontology should improve over time.

New documents may:

- Add entities
- Add relationships
- Add aliases
- Merge duplicates
- Enrich existing nodes

The graph should never create duplicate entities for the same real-world object.

---

# Retrieval Strategy

When a user asks a question:

1. Retrieve relevant chunks from Pinecone.
2. Retrieve related entities from Neo4j.
3. Expand neighboring nodes.
4. Combine graph context with document context.
5. Generate an answer with citations.

The Knowledge Graph provides relationships.

The Vector Database provides semantic relevance.

Together they improve answer quality.

---

# Future Enhancements

The ontology should support future integrations such as:

- IoT sensor streams
- Digital Twin models
- ERP systems (SAP)
- CMMS platforms (IBM Maximo)
- SCADA events
- Predictive maintenance models

The core ontology should remain stable while the dynamic ontology continues to evolve.


# Backend Structure
backend/
└── app/
    └── ontology/
        ├── ontology_manager.py      # Normalization & validation
        ├── entity_mapper.py         # Maps raw AI output to canonical entities
        ├── synonym_resolver.py      # Handles aliases and duplicates
        ├── relationship_builder.py  # Validates graph relationships
        ├── ontology_rules.py        # Core ontology definitions
        ├── validators.py            # Confidence & schema validation
        └── models.py                # Pydantic models for entities/relationships
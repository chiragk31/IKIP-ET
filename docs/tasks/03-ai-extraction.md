# 03-ai-extraction.md

# Epic 3 — AI Knowledge Extraction

Version: 1.0

Status: Planned

---

# Objective

Transform processed industrial documents into structured organizational knowledge.

This module is responsible for extracting:

- Entities
- Relationships
- Measurements
- Procedures
- Risks
- Standards
- Equipment
- Events
- Industrial Metadata

using Large Language Models.

The output of this epic is a **Canonical Knowledge Object** that serves as the foundation for the Ontology, Knowledge Graph, Semantic Search, and AI Copilot.

---

# References

Must follow:

- PRD.md
- Architecture.md
- Rules.md
- Database.md
- Ontology.md
- Prompts.md
- Epics.md

---

# Dependencies

Requires:

✓ Epic 0

✓ Epic 1

✓ Epic 2

---

# Deliverables

✓ LLM Gateway

✓ Prompt Manager

✓ Entity Extraction

✓ Relationship Extraction

✓ Ontology Discovery

✓ Measurement Extraction

✓ Document Summary

✓ Canonical Knowledge Object

✓ Validation Pipeline

✓ AI Event Pipeline

---

# Architecture

```
document.processed

↓

LLM Gateway

↓

Prompt Manager

↓

Gemini

↓

Response Parser

↓

Validation

↓

Canonical Knowledge Object

↓

Store AI Output

↓

Emit knowledge.extracted
```

---

# Responsibilities

This module is responsible for

- Calling Gemini
- Running AI prompts
- Parsing AI responses
- Validating AI output
- Creating Canonical Knowledge Object

This module must NOT

- Build Neo4j graph
- Generate embeddings
- Update ontology
- Perform retrieval
- Answer user questions

---

# Folder Structure

```
backend/app/

ai/

llm_service.py

prompt_manager.py

response_parser.py

validator.py

prompts/

entity_extraction.md

relationship_extraction.md

ontology_discovery.md

measurement_extraction.md

summary.md

risk_analysis.md

repositories/

knowledge_repository.py

schemas/

knowledge.py

events/

knowledge_handler.py
```

---

# Canonical Knowledge Object

Every AI pipeline must generate the same output format.

```json
{
    "document":{},
    "summary":"",
    "entities":[],
    "relationships":[],
    "measurements":[],
    "procedures":[],
    "risks":[],
    "standards":[],
    "warnings":[],
    "confidence":0.94
}
```

No downstream module should consume raw Gemini output.

---

# AI Processing Pipeline

Each capability runs independently.

```
Canonical Document

↓

Entity Extraction

↓

Relationship Extraction

↓

Measurement Extraction

↓

Procedure Extraction

↓

Risk Extraction

↓

Summary Generation

↓

Ontology Discovery

↓

Validation

↓

Canonical Knowledge Object
```

Each stage should use a dedicated prompt.

---

# Task 3.1 — LLM Gateway

## Goal

Centralize all communication with Gemini.

---

Responsibilities

Load Model

Retry

Timeout

Logging

Rate Limiting

Model Configuration

---

Rules

Business services must NEVER call Gemini directly.

Only

LLMService

may communicate with Gemini.

---

Acceptance Criteria

✓ Centralized AI communication

---

# Task 3.2 — Prompt Manager

Goal

Load prompts dynamically.

---

Responsibilities

Load Markdown Prompts

Inject Variables

Version Prompts

Cache Prompts

---

Rules

Never hardcode prompts in Python.

Every prompt must exist inside

docs/prompts/

---

Acceptance Criteria

✓ Prompt loading works

---

# Task 3.3 — Entity Extraction

Extract

Assets

Equipment

Persons

Organizations

Locations

Procedures

Permits

Documents

Failures

Components

---

Example

```
Pump P-101

Valve V-12

Operator John

Boiler B-02
```

---

Acceptance Criteria

✓ Major industrial entities extracted

---

# Task 3.4 — Relationship Extraction

Extract

PART_OF

CONNECTED_TO

CAUSES

INSPECTED_BY

REQUIRES

COMPLIES_WITH

MENTIONED_IN

RELATED_TO

---

Output

```json
{
    "source":"",
    "relationship":"",
    "target":""
}
```

---

Acceptance Criteria

✓ Relationships extracted correctly

---

# Task 3.5 — Measurement Extraction

Extract

Temperature

Pressure

Voltage

Flow Rate

Current

Humidity

Dimensions

Tolerance

Units

---

Output

```json
{
    "name":"Pressure",
    "value":120,
    "unit":"psi"
}
```

---

Acceptance Criteria

✓ Numerical values extracted

---

# Task 3.6 — Procedure Extraction

Extract

Step-by-step procedures

Maintenance workflows

Safety instructions

Shutdown procedures

Start-up procedures

Inspection checklists

---

Acceptance Criteria

✓ Procedures extracted

---

# Task 3.7 — Risk Extraction

Extract

Hazards

Safety Risks

Failure Modes

Warnings

Compliance Violations

Critical Operations

---

Acceptance Criteria

✓ Risks identified

---

# Task 3.8 — Document Summary

Generate

Executive Summary

Technical Summary

Maintenance Summary

Compliance Summary

---

Rules

Summaries must be factual.

Never hallucinate missing information.

---

Acceptance Criteria

✓ Accurate summaries

---

# Task 3.9 — Ontology Discovery

Discover

New Entity Types

New Relationship Types

Unknown Concepts

Industrial Terminology

---

Rules

Never modify ontology directly.

Only suggest discoveries.

---

Acceptance Criteria

✓ Suggestions generated

---

# Task 3.10 — Response Validation

Validate

JSON

Required Fields

Confidence

Duplicate Entities

Duplicate Relationships

Missing References

---

Rules

Reject malformed responses.

---

Acceptance Criteria

✓ Invalid responses rejected

---

# Task 3.11 — Knowledge Repository

Store

Canonical Knowledge Object

AI Version

Prompt Version

Model Version

Extraction Timestamp

Confidence

---

Acceptance Criteria

✓ Knowledge stored

---

# Task 3.12 — Event Emission

Emit

```
knowledge.extracted
```

Payload

```json
{
    "document_id":"",
    "knowledge_id":"",
    "confidence":0.93
}
```

---

Acceptance Criteria

✓ Event emitted

---

# Recommended Improvements (Mandatory)

## Multi-Stage AI Pipeline

Never ask the LLM to perform every task in a single prompt.

Instead use specialized prompts.

```
Entity Prompt

↓

Relationship Prompt

↓

Measurement Prompt

↓

Summary Prompt

↓

Ontology Prompt
```

Benefits

- Better accuracy

- Easier debugging

- Independent prompt improvements

- Lower maintenance cost

---

## LLM Gateway Pattern

Only

LLMService

communicates with Gemini.

```
Service

↓

LLM Gateway

↓

Gemini
```

Never expose Gemini SDK outside the AI layer.

---

## Prompt Versioning

Every prompt should contain

Version

Purpose

Input

Output Schema

Expected JSON

Store prompt version with every extraction.

This allows future reprocessing.

---

## Strict JSON Validation

Never trust LLM output.

Validate

- JSON schema

- Required fields

- Confidence

- Duplicate entities

Reject invalid responses before storage.

---

## Confidence Threshold

Every extracted entity and relationship should include confidence.

Low-confidence results should be flagged for future review.

Suggested threshold

```
0.75
```

---

## Model Independence

The AI layer should support future replacement of Gemini.

```
LLM Interface

↓

Gemini

Claude

OpenAI

Azure OpenAI

Local LLM
```

Business logic should remain unchanged.

---

## Observability

Log

Prompt Version

Model

Latency

Input Tokens

Output Tokens

Estimated Cost

Retry Count

Failure Reason

These metrics will later power analytics and optimization.

---

# Verification Checklist

✓ LLM Gateway working

✓ Prompt Manager working

✓ Entity extraction working

✓ Relationship extraction working

✓ Measurement extraction working

✓ Summary generation working

✓ Validation working

✓ Knowledge stored

✓ knowledge.extracted emitted

✓ Logging implemented

---

# Definition of Done

Epic 3 is complete when

✓ Every processed document generates a Canonical Knowledge Object.

✓ AI outputs are validated.

✓ Responses are stored.

✓ Prompt versioning is implemented.

✓ Model versioning is implemented.

✓ knowledge.extracted event is emitted.

✓ The system is ready for Epic 4 — Ontology Management.
# Prompts.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Purpose

This document defines all prompts used by the AI system.

Prompts are treated as application assets and must be:

- Version controlled
- Tested
- Reusable
- Independent
- Maintainable

Prompts must never be hardcoded inside Python files.

---

# Prompt Architecture

Business Service

↓

LLM Service

↓

Prompt Manager

↓

Prompt Template

↓

Gemini

↓

Response Parser

---

# Prompt Folder Structure

backend/
└── app/
    └── prompts/
        ├── entity_extraction.md
        ├── relationship_extraction.md
        ├── ontology_discovery.md
        ├── summary.md
        ├── compliance.md
        ├── maintenance.md
        ├── asset_summary.md
        ├── semantic_search.md
        ├── chat.md
        ├── query_rewrite.md
        └── system.md

---

# Prompt Design Rules

Every prompt must include:

1. Purpose
2. Context
3. Instructions
4. Constraints
5. Output Format
6. Example Input
7. Example Output

---

# Global AI Rules

The AI must:

- Never hallucinate.
- Never invent entities.
- Never fabricate citations.
- Preserve industrial terminology.
- Preserve units of measurement.
- Return valid JSON where requested.
- State uncertainty when confidence is low.

---

# Shared System Prompt

Every AI request begins with a common system prompt.

Responsibilities:

- Behave as an industrial knowledge extraction assistant.
- Prefer factual extraction over interpretation.
- Preserve evidence.
- Never answer beyond supplied context.
- Return structured output.

---

# Entity Extraction Prompt

Purpose

Extract industrial entities from parsed documents.

Input

Plain text from a document.

Output

JSON

Required Entity Types

- Asset
- Person
- Procedure
- Organization
- Location
- Event
- Measurement
- Regulation
- Risk
- Failure

Return

{
    "entities":[]
}

---

# Relationship Extraction Prompt

Purpose

Discover relationships between extracted entities.

Input

Document text

Previously extracted entities

Output

{
    "relationships":[]
}

Relationship examples

HAS_FAILURE

LOCATED_IN

USES

REQUIRES

CONNECTED_TO

PART_OF

REFERENCES

---

# Ontology Discovery Prompt

Purpose

Discover new industrial concepts that are not part of the current ontology.

Input

Document

Current ontology

Output

{
    "new_concepts":[]
}

Only suggest concepts that:

- are meaningful
- appear important
- are reusable

---

# Document Summary Prompt

Purpose

Generate a concise technical summary.

Output

{
    "summary":"",
    "keywords":[],
    "topics":[]
}

---

# Compliance Prompt

Purpose

Identify compliance-related observations.

Output

{
    "violations":[],
    "recommendations":[]
}

Do not invent regulations.

Use only evidence from the supplied document.

---

# Maintenance Prompt

Purpose

Generate maintenance intelligence.

Output

{
    "root_causes":[],
    "recommendations":[],
    "failure_patterns":[]
}

---

# Asset Summary Prompt

Purpose

Generate an overview for an asset.

Input

Asset

Related Documents

Related Events

Measurements

Output

{
    "asset_summary":"",
    "risk_level":"",
    "recommendations":[]
}

---

# Semantic Search Prompt

Purpose

Generate the final response using retrieved chunks.

Input

User Question

Retrieved Chunks

Graph Context

Output

{
    "answer":"",
    "citations":[],
    "confidence":0.95
}

Never answer beyond the retrieved context.

---

# Query Rewrite Prompt

Purpose

Rewrite user questions into optimized search queries.

Example

Input

Why is Pump P101 overheating?

Output

[
"Pump P101 overheating",
"Bearing temperature",
"Maintenance history Pump P101"
]

---

# Chat Prompt

Purpose

Industrial AI Copilot.

Input

Conversation

Retrieved Chunks

Knowledge Graph Context

Output

{
    "answer":"",
    "citations":[],
    "related_assets":[],
    "confidence":0.91
}

The answer must:

- cite evidence
- explain reasoning
- avoid speculation

---

# Prompt Variables

Use placeholders.

Example

{{document_text}}

{{question}}

{{entities}}

{{graph_context}}

{{retrieved_chunks}}

{{asset}}

Never concatenate strings manually inside business logic.

---

# Prompt Versioning

Every prompt must include:

Version

Last Updated

Author

Purpose

---

# Response Validation

Every AI response must be validated.

Validation includes:

- JSON schema validation
- Required fields
- Confidence score
- Empty response detection
- Duplicate entity removal

Invalid responses should trigger:

Retry

↓

Fallback Prompt

↓

Error

---

# Prompt Testing

Every prompt must have test cases.

Example

Input

Maintenance Report

Expected

Entities extracted correctly

Relationships discovered

Summary generated

---

# Future Prompt Types

Future prompts may include:

- Root Cause Analysis
- Predictive Maintenance
- SOP Generation
- Incident Timeline
- Risk Assessment
- Multi-document Comparison
- Engineering Drawing Interpretation
- IoT Event Analysis

without modifying the current architecture.

# Recommended Folder Strucutre

backend/
└── app/
    ├── prompts/
    │   ├── system.md
    │   ├── entity_extraction.md
    │   ├── relationship_extraction.md
    │   ├── ontology_discovery.md
    │   ├── summary.md
    │   ├── compliance.md
    │   ├── maintenance.md
    │   ├── asset_summary.md
    │   ├── semantic_search.md
    │   ├── chat.md
    │   └── query_rewrite.md
    │
    └── ai/
        ├── llm_service.py
        ├── prompt_manager.py
        └── response_parser.py
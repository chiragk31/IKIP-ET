# Copilot.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Purpose

This document defines the AI Copilot architecture used by the Industrial Knowledge Intelligence Platform.

The AI Copilot is the intelligent assistant responsible for answering user questions using grounded industrial knowledge retrieved from the platform.

The Copilot never performs retrieval directly.

Instead, it receives an already assembled context package from the Search module and generates reliable, explainable responses.

---

# Goals

The AI Copilot should

- Answer industrial questions accurately
- Use grounded knowledge only
- Minimize hallucinations
- Provide citations
- Support conversational memory
- Explain reasoning
- Remain model independent

---

# Design Philosophy

The AI Copilot is not a search engine.

The AI Copilot is not a database.

The AI Copilot is not an OCR engine.

The AI Copilot is a reasoning engine.

Everything required for answering should already be retrieved before the LLM is called.

---

# Responsibilities

The AI Copilot is responsible for

- Response Generation
- Context Reasoning
- Citation Generation
- Conversation Memory
- Answer Formatting
- Follow-up Question Handling

The AI Copilot is NOT responsible for

- Document Parsing
- OCR
- Knowledge Extraction
- Ontology Updates
- Graph Construction
- Embedding Generation
- Search

---

# Architecture

```
User Question

↓

Search Module

↓

Context Package

↓

Prompt Manager

↓

LLM Gateway

↓

Response Validator

↓

AI Response
```

---

# Folder Structure

```
backend/app/

copilot/

copilot_service.py

conversation_manager.py

memory_manager.py

response_generator.py

response_validator.py

citation_builder.py

followup_handler.py

llm_gateway.py

models.py

schemas.py

constants.py
```

---

# Copilot Pipeline

```
User Question

↓

Conversation Manager

↓

Search Service

↓

Context Package

↓

Prompt Manager

↓

LLM Gateway

↓

Response Validation

↓

Citation Builder

↓

Final Response
```

---

# Conversation Memory

Memory stores

- Previous Questions
- Previous Answers
- Current Topic
- Referenced Assets
- Active Filters

Memory is session scoped by default.

Future versions may support persistent user memory.

---

# Context Package

The Copilot always receives structured context.

```json
{
  "query": "",
  "chunks": [],
  "graph_nodes": [],
  "relationships": [],
  "metadata": {},
  "citations": []
}
```

The Copilot must never retrieve additional information.

---

# Prompt Management

Prompt files

```
backend/app/prompts/

system.md

chat.md

asset_summary.md

maintenance.md

compliance.md

followup.md
```

All prompts are externalized.

Never hardcode prompts inside Python files.

---

# LLM Gateway

The Copilot communicates only through

```
LLM Gateway

↓

Gemini

OpenAI

Claude

Local Models
```

Never call providers directly.

---

# Response Generation

The LLM receives

- User Question
- Conversation History
- Context Package
- System Prompt

The response must be grounded only in the provided context.

---

# Response Validation

Before returning

Validate

- Response exists
- Citations exist
- Confidence acceptable
- No unsupported claims
- Output schema valid

Reject invalid responses.

---

# Citation Builder

Every answer must include

- Document Name
- Section
- Page
- Asset
- Confidence

The AI must never answer without citations.

---

# Supported Capabilities

The Copilot supports

## Question Answering

Example

"What caused Pump P-101 failure?"

---

## Asset Summary

Example

"Summarize Pump P-101."

---

## Maintenance Assistant

Example

"What is the startup procedure?"

---

## Compliance Assistant

Example

"Show OSHA requirements for this equipment."

---

## Incident Investigation

Example

"Which failures were related to overheating?"

---

## Follow-up Questions

Example

"When was it last inspected?"

The Copilot should resolve references using conversation memory.

---

# Conversation Memory

Track

- Active Asset
- Active Procedure
- Current Plant
- Current Topic
- Previous Search

This improves follow-up questions.

---

# Response Format

```json
{
  "answer": "",
  "citations": [],
  "confidence": 0.95,
  "followup_questions": []
}
```

---

# Hallucination Prevention

The Copilot must

Never invent

- Assets
- Procedures
- Measurements
- Relationships
- Documents

If information is unavailable

Respond

"I could not find supporting evidence in the available knowledge base."

---

# Confidence

Confidence combines

- Search Score
- Graph Coverage
- Metadata Match
- LLM Confidence

Never rely only on model confidence.

---

# Explainability

Every answer should explain

- Which documents were used
- Which graph relationships were used
- Which assets were referenced

---

# Repository Layer

The Copilot never communicates directly with

- Pinecone
- Neo4j
- Supabase

It only communicates with

```
Search Service

↓

Context Package

↓

LLM Gateway
```

---

# Security

Validate

- User input
- Prompt injection attempts
- Conversation memory
- Context package

Never expose

- Internal prompts
- API keys
- Database queries

---

# Logging

Log

- Question
- Search Duration
- Prompt Tokens
- Completion Tokens
- LLM Duration
- Citations Used
- Total Response Time

---

# Performance

Implement

- Streaming Responses
- Prompt Caching
- Conversation Cache
- Async LLM Calls
- Token Optimization

---

# Future Enhancements

Potential future capabilities

- Multi-Agent Copilot
- Voice Assistant
- Image-based Question Answering
- Predictive Maintenance Assistant
- Root Cause Investigation Agent
- Autonomous Workflow Suggestions

---

# Recommended Architecture Improvements (Mandatory)

## AI Orchestrator Pattern

The Copilot should orchestrate reasoning only.

Never perform retrieval.

```
User

↓

Search

↓

Context

↓

Copilot

↓

LLM

↓

Validated Response
```

---

## Provider Independence

Implement

```
LLM Provider

↓

Gemini

OpenAI

Claude

Local Models
```

Switching providers should require configuration only.

---

## Grounded Responses

The LLM must answer only using

- Context Package
- Conversation Memory

Never allow external assumptions.

---

## Structured Outputs

Every response should follow a schema.

Avoid free-form outputs.

---

## Session Memory

Conversation memory should be isolated per session.

Never mix contexts across users.

---

## Tool Calling Ready

Design the Copilot so future tools can be added.

Examples

- Create Maintenance Ticket
- Schedule Inspection
- Generate Work Order
- Export Report

The orchestration layer should support tool execution without changing business logic.

---

# Definition of Done

The AI Copilot is complete when

✓ Conversation memory works.

✓ Context packages are consumed.

✓ Responses are grounded.

✓ Citations are generated.

✓ Hallucination checks are implemented.

✓ Response validation works.

✓ LLM provider abstraction exists.

✓ Streaming responses are supported.

✓ Ready for enterprise deployment.
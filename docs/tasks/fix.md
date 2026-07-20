# fix.md

# Industrial Knowledge Intelligence Platform (IKIP)

## Epic 3 – Bug Fixes & Observability Improvements

Version: 1.0

Status: Mandatory Fixes

---

# Objective

Fix the remaining issues in Epic 3 without changing the overall architecture or business logic.

This is **NOT** a refactor.

This is **NOT** a redesign.

The AI extraction pipeline is already working correctly.

The goal is to improve:

- Correctness
- Observability
- Traceability
- Downstream compatibility

while preserving all existing APIs and data structures.

---

# DO NOT CHANGE

Do NOT modify:

- Overall pipeline
- Event flow
- Prompt structure
- Canonical Knowledge Object schema
- Database schema
- API responses
- Repository pattern
- LLM Gateway pattern
- Prompt Manager
- Validation flow

Do NOT introduce new frameworks.

Do NOT redesign Epic 3.

Only implement the fixes below.

---

# Bug 1 — total_tokens_used always equals 0

## Problem

The Canonical Knowledge Object currently stores:

```json
"total_tokens_used": 0
```

even though multiple Gemini requests are executed.

This breaks:

- observability
- analytics
- cost estimation

---

## Expected Behaviour

Every LLM request already returns usage metadata.

Accumulate usage across every extraction stage.

Example

Entity Prompt

↓

3200 tokens

Relationship Prompt

↓

2100 tokens

Measurement Prompt

↓

900 tokens

Summary Prompt

↓

700 tokens

Final stored value

```json
{
    "total_tokens_used":6900
}
```

---

## Requirements

Do NOT estimate.

Use actual values returned by Gemini.

Accumulate

- prompt tokens
- completion tokens
- total tokens

Store

```
total_prompt_tokens

total_completion_tokens

total_tokens_used
```

If cost estimation already exists, compute it using total tokens.

---

# Bug 2 — Entity ID consistency

## Problem

Entity extraction creates canonical IDs such as

```
asset_pump_p101
```

Later extraction stages sometimes generate

```
asset_p101

asset_p101_strainer

asset_p101_upstream_strainer
```

These refer to the same asset but use different IDs.

This breaks downstream graph construction.

---

## Required Fix

Entity Extraction remains the source of truth.

Immediately after Entity Extraction completes:

Create an in-memory Entity Registry.

Example

```json
[
  {
    "entity_id":"asset_pump_p101",
    "label":"Pump P-101",
    "aliases":[
      "P-101",
      "Main Feed Pump",
      "Centrifugal Pump P-101"
    ]
  }
]
```

Pass this registry into every later extraction prompt.

Specifically

- Relationship Extraction
- Measurement Extraction
- Procedure Extraction
- Risk Extraction
- Ontology Discovery

Prompt instructions should explicitly state:

> Never invent entity IDs.

> Use ONLY the supplied entity_id values.

If an entity cannot be matched,

return

```
unknown_entity
```

instead of inventing a new ID.

---

## IMPORTANT

Do NOT redesign the pipeline.

Only provide already extracted entity IDs as additional prompt context.

---

# Bug 3 — Missing terminal logs

## Problem

During processing the terminal is almost silent.

Large documents appear frozen.

Users cannot determine:

- current stage
- elapsed time
- failures
- retries
- model being used

---

## Required Logging

Every extraction stage must log:

Starting stage

Completed stage

Duration

Prompt version

Model

Tokens

Confidence

Retry count (if any)

Errors

---

## Example

```
==================================================

Document:
maintenance_report_P101.pdf

Knowledge Extraction Started

==================================================

[1/7] Entity Extraction

Model:
gemini-2.5-flash

Prompt:
entity_extraction v1.0

Started...

✓ Completed

Entities:
58

Confidence:
0.96

Tokens:
3210

Duration:
64.2 sec

--------------------------------------------------

[2/7] Relationship Extraction

Started...

✓ Completed

Relationships:
71

Tokens:
2150

Duration:
66.4 sec

--------------------------------------------------

[3/7] Measurement Extraction

Started...

✓ Completed

Measurements:
16

Tokens:
910

Duration:
28 sec

--------------------------------------------------

[4/7] Procedure Extraction

✓ Completed

Procedures:
1

Duration:
19 sec

--------------------------------------------------

[5/7] Risk Extraction

✓ Completed

Risks:
9

Duration:
45 sec

--------------------------------------------------

[6/7] Summary Generation

✓ Completed

Duration:
13 sec

--------------------------------------------------

[7/7] Ontology Discovery

✓ Completed

New Concepts:
6

Duration:
25 sec

==================================================

Knowledge Extraction Finished

Total Time:
269 sec

Total Prompt Tokens:
xxxx

Total Completion Tokens:
xxxx

Total Tokens:
xxxx

Overall Confidence:
0.92

==================================================
```

---

## Error Logging

If a stage fails

Print

```
Stage:
Measurement Extraction

Status:
FAILED

Reason:
Gemini timeout

Retry:
2/3
```

Continue using the existing retry logic.

---

# Bug 4 — Extraction Metrics

Store execution metrics for every stage.

Example

```json
{
    "stage_latencies":{

        "entity_extraction":65.2,

        "relationship_extraction":66.1,

        "measurement_extraction":27.4,

        "procedure_extraction":19.8,

        "risk_extraction":45.3,

        "summary_generation":13.5,

        "ontology_discovery":25.9
    }
}
```

Also store

```
overall_duration

overall_confidence

total_tokens_used

prompt_version

model_version
```

---

# Code Quality Requirements

Keep existing architecture.

Keep Service → Repository pattern.

Keep LLMService as the only Gemini caller.

Keep PromptManager.

Keep ResponseParser.

Keep Validator.

Do not duplicate logic.

Use helper methods where appropriate.

---

# Performance

Do NOT parallelize anything.

The project currently uses the Gemini Free API.

Maintain the existing sequential execution order.

Do not introduce asyncio.gather().

Future optimization can be handled in a later epic.

---

# Acceptance Criteria

✓ Existing functionality remains unchanged.

✓ No API changes.

✓ No schema changes (except adding missing metrics fields if absent).

✓ total_tokens_used reports actual Gemini usage.

✓ Entity IDs remain consistent across every extraction stage.

✓ Measurements reference canonical entity IDs.

✓ Risks reference canonical entity IDs.

✓ Relationships reference canonical entity IDs.

✓ Stage-by-stage logs appear in the terminal.

✓ Total execution summary is printed after extraction.

✓ Existing tests continue to pass.

✓ Epic 3 remains fully compatible with Epic 4 (Ontology Manager) and Epic 5 (Knowledge Graph).

---

# Final Note

This task is a stabilization pass only.

Do not redesign the extraction pipeline.

Do not modify business logic.

Implement only the fixes described above while preserving the existing architecture and behaviour.
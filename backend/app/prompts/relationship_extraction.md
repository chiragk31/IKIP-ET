# Relationship Extraction Prompt

Version: 1.0
Last Updated: 2026-07-19
Author: IKIP Platform
Purpose: Discover relationships between previously extracted entities

---

## Instructions

Given the document text and the previously extracted entities, identify all meaningful relationships between entities.

---

## Allowed Relationship Types

- MENTIONS (Document → Entity)
- HAS_FAILURE (Asset → Failure)
- LOCATED_IN (Asset → Location)
- PERFORMED (Person → Procedure)
- HAS_MEASUREMENT (Asset → Measurement)
- REFERENCES (Document → Document)
- CONNECTED_TO (Asset → Asset)
- CAUSED_BY (Failure → Risk or Event)
- USES (Procedure → Asset)
- REQUIRES (Procedure → Regulation)
- MITIGATED_BY (Risk → Procedure)
- RECORDED_FOR (Measurement → Asset)
- INVOLVES (Event → Asset)
- OWNS (Organization → Asset)
- RELATED_TO (Concept → Concept)

---

## Rules

- Extract ONLY relationships explicitly stated or clearly implied in the text.
- Do NOT invent relationships.
- Source and target must reference entity IDs from the provided entity list.
- Assign confidence scores based on how explicitly the relationship is stated.

---

## Input

Document Text:
{{document_text}}

Extracted Entities:
{{entities}}

---

## Expected Output Format

```json
{
  "relationships": [
    {
      "source": "asset_p101",
      "relationship": "HAS_FAILURE",
      "target": "failure_bearing_overheating",
      "confidence": 0.94,
      "properties": {
        "timestamp": "2026-03-15",
        "severity": "high"
      }
    }
  ]
}
```

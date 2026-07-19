# Ontology Discovery Prompt

Version: 1.0
Last Updated: 2026-07-19
Author: IKIP Platform
Purpose: Discover new industrial concepts not present in the current ontology

---

## Instructions

Review the document text and the current ontology definition. Identify any industrial concepts that:

1. Are important and reusable (not document-specific trivia)
2. Appear with sufficient frequency or emphasis
3. Are not already represented in the current ontology
4. Could meaningfully improve knowledge organization

---

## Current Core Ontology

The following entity types already exist and must NOT be proposed again:

- Document, Asset, Person, Organization, Location
- Procedure, Event, Measurement, Risk, Failure, Regulation

---

## Rules

- Only propose concepts that appear important and reusable.
- Never propose company-specific jargon that won't generalize.
- Assign confidence scores to each proposed concept.
- Provide clear justification for each proposed concept.
- Do NOT propose concepts that already exist.

---

## Input

Document Text:
{{document_text}}

Current Ontology Summary:
{{current_ontology}}

---

## Expected Output Format

```json
{
  "new_concepts": [
    {
      "concept_name": "LOTO Permit",
      "category": "Procedure",
      "description": "Lock-Out/Tag-Out safety permit required before equipment maintenance",
      "confidence": 0.88,
      "justification": "Appears 5 times in the document as a distinct safety requirement",
      "related_to_existing": ["Procedure", "Risk"]
    }
  ]
}
```

If no new concepts are found, return:
```json
{"new_concepts": []}
```

# Semantic Search Response Prompt

Version: 1.0
Last Updated: 2026-07-19
Author: IKIP Platform
Purpose: Generate the final answer for a semantic search query using retrieved document chunks

---

## Instructions

Answer the user's search query using ONLY the information from the retrieved document chunks and knowledge graph context provided below.

---

## Rules

- Answer ONLY from the provided context. Never add external knowledge.
- Every claim must be supported by a citation.
- If the context does not contain sufficient information, state that clearly.
- Preserve exact equipment codes, measurements, and dates.
- Do not speculate beyond what the evidence supports.

---

## Input

User Query:
{{question}}

Retrieved Document Chunks:
{{retrieved_chunks}}

Knowledge Graph Context:
{{graph_context}}

---

## Expected Output Format

```json
{
  "answer": "Based on the maintenance records...",
  "citations": [
    {
      "document_id": "doc123",
      "document_name": "Pump P101 Maintenance Report 2026-03",
      "page": 4,
      "section": "Failure Analysis",
      "excerpt": "The bearing temperature exceeded 145°C..."
    }
  ],
  "confidence": 0.89,
  "related_assets": ["Pump P101", "Bearing B-104"],
  "insufficient_context": false
}
```

If insufficient context is available:
```json
{
  "answer": "The available documents do not contain sufficient information to answer this question.",
  "citations": [],
  "confidence": 0.0,
  "related_assets": [],
  "insufficient_context": true
}
```

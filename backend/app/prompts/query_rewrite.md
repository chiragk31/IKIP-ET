# Query Rewrite Prompt

Version: 1.0
Last Updated: 2026-07-19
Author: IKIP Platform
Purpose: Rewrite user questions into optimized vector search queries

---

## Instructions

Rewrite the user's natural language question into 2-5 focused search queries optimized for semantic vector search over industrial document chunks.

Each generated query should:
- Be concise and focused on a specific aspect of the original question
- Use industrial terminology
- Cover different angles of the question

---

## Input

User Question:
{{question}}

---

## Expected Output Format

```json
{
  "original_question": "Why did Pump P101 fail last month?",
  "search_queries": [
    "Pump P101 failure",
    "P101 bearing overheating",
    "Pump P101 maintenance history",
    "centrifugal pump failure root cause"
  ]
}
```

# Document Summary Prompt

Version: 1.0
Last Updated: 2026-07-19
Author: IKIP Platform
Purpose: Generate a concise technical summary of an industrial document

---

## Instructions

Generate a technical summary of the following industrial document.

The summary must:
- Be factual and concise (150-300 words)
- Focus on the technical content, key findings, and actions
- Preserve equipment codes, dates, and measurements
- Extract the document's primary classification (report type)
- Identify key topics covered
- List important keywords for search

---

## Rules

- Never fabricate facts not in the document.
- Use technical terminology appropriate for industrial professionals.
- Preserve exact equipment codes and identifiers.
- The summary must be in the same language as the document.

---

## Input

Document Text:
{{document_text}}

Document Filename: {{filename}}

---

## Expected Output Format

```json
{
  "summary": "This maintenance report documents...",
  "document_type": "maintenance_report",
  "language": "en",
  "keywords": ["pump", "bearing", "overheating", "P101"],
  "topics": ["Bearing Failure", "Pump Maintenance", "Temperature Monitoring"],
  "key_dates": ["2026-03-15"],
  "key_assets": ["Pump P101"],
  "key_findings": ["Bearing overheated due to insufficient lubrication"]
}
```

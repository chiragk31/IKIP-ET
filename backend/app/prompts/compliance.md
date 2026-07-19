# Compliance Analysis Prompt

Version: 1.0
Last Updated: 2026-07-19
Author: IKIP Platform
Purpose: Identify compliance observations and violations from industrial documents

---

## Instructions

Analyze the following industrial document for compliance-related observations.

Look for:
- Missing required approvals or signatures
- Expired certificates or permits
- Overdue inspections
- Regulatory standard violations
- Missing safety documentation
- Incomplete procedures
- Non-compliant measurements

---

## Rules

- Extract ONLY compliance observations explicitly supported by the document content.
- Do NOT invent regulations that are not referenced.
- Use only evidence from the supplied document.
- For each observation, cite the specific section or page.
- Distinguish between definite violations and potential risks.

---

## Input

Document Text:
{{document_text}}

Document Type: {{document_type}}

---

## Expected Output Format

```json
{
  "violations": [
    {
      "type": "missing_approval",
      "description": "Work order lacks supervisor sign-off",
      "severity": "high",
      "section": "Section 4.2",
      "regulation_reference": null,
      "confidence": 0.91
    }
  ],
  "recommendations": [
    {
      "action": "Obtain supervisor approval before closing work order",
      "priority": "high"
    }
  ],
  "compliance_score": 0.75
}
```

If no violations are found, return:
```json
{"violations": [], "recommendations": [], "compliance_score": 1.0}
```

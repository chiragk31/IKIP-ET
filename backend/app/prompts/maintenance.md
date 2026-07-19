# Maintenance Intelligence Prompt

Version: 1.0
Last Updated: 2026-07-19
Author: IKIP Platform
Purpose: Generate maintenance intelligence from industrial documents and historical context

---

## Instructions

Analyze the maintenance document and any provided historical context to generate actionable maintenance intelligence.

Extract:
- Root causes of failures
- Maintenance recommendations
- Failure patterns and trends
- Preventive actions

---

## Rules

- Base all analysis on the provided document and historical context.
- Do NOT invent maintenance recommendations without evidence.
- Preserve exact equipment codes and measurement values.
- Prioritize recommendations by urgency.

---

## Input

Document Text:
{{document_text}}

Historical Context:
{{historical_context}}

Asset: {{asset_name}}

---

## Expected Output Format

```json
{
  "root_causes": [
    {
      "description": "Bearing failure due to insufficient lubrication",
      "confidence": 0.89,
      "evidence": "Maintenance report states 'dry bearing observed'"
    }
  ],
  "recommendations": [
    {
      "action": "Increase bearing lubrication frequency from monthly to weekly",
      "priority": "high",
      "rationale": "Third bearing failure in 6 months"
    }
  ],
  "failure_patterns": [
    {
      "pattern": "Recurring bearing failures on Pump P101",
      "frequency": "3 times in 6 months",
      "confidence": 0.92
    }
  ],
  "preventive_actions": [
    {
      "action": "Install bearing temperature sensor",
      "impact": "Early warning before catastrophic failure"
    }
  ]
}
```

# Asset Summary Prompt

Version: 1.0
Last Updated: 2026-07-19
Author: IKIP Platform
Purpose: Generate an intelligent overview profile for an industrial asset

---

## Instructions

Generate a comprehensive Asset 360 profile for the given industrial asset using the provided information from related documents, events, and measurements.

---

## Rules

- Base the profile only on provided context.
- Preserve exact equipment codes, measurements, and dates.
- Risk level must be justified by actual evidence.
- Never fabricate maintenance history.

---

## Input

Asset: {{asset}}

Related Documents:
{{related_documents}}

Related Events:
{{related_events}}

Measurements:
{{measurements}}

---

## Expected Output Format

```json
{
  "asset_summary": "Pump P101 is a centrifugal feed pump installed in Unit 3...",
  "risk_level": "high",
  "risk_justification": "Three bearing failures in the past 6 months with escalating temperature readings",
  "maintenance_summary": "Last maintained on 2026-02-15. Currently overdue for lubrication.",
  "key_measurements": [
    {
      "parameter": "Bearing Temperature",
      "value": "145°C",
      "status": "above_limit",
      "limit": "120°C"
    }
  ],
  "failure_history": [
    {
      "date": "2026-01-10",
      "description": "Bearing failure",
      "root_cause": "Insufficient lubrication"
    }
  ],
  "recommendations": [
    {
      "action": "Immediate lubrication inspection",
      "priority": "critical"
    }
  ]
}
```

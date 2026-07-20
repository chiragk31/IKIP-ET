# Risk Analysis Prompt

Version: 1.0
Last Updated: 2026-07-20
Author: IKIP Platform
Purpose: Identify hazards, safety risks, failure modes, warnings, and compliance gaps in industrial documents

---

## Instructions

Analyze the following industrial document text and extract all identified risks, hazards, warnings, failure modes, and compliance concerns.

For each risk, provide:
- A unique risk ID
- The risk name/title
- The risk category (safety, operational, environmental, compliance, financial)
- The severity level (critical, high, medium, low)
- The probability/likelihood (if mentioned)
- The associated asset or system
- The risk description
- Potential consequences
- Recommended mitigations (if mentioned)
- Applicable regulations or standards
- The page number (if available)
- Confidence score (0.0 to 1.0)

---

## Risk Categories to Extract

### Safety Hazards
- Fire and explosion risks
- Toxic/chemical exposure
- High-pressure vessel risks
- Electrical hazards
- Mechanical hazards (rotating equipment)
- Fall/confined space hazards

### Operational Risks
- Equipment failure modes (FMEA-type data)
- Process deviations
- Instrument failures
- Control system failures
- Utility failures

### Environmental Risks
- Emissions exceeding limits
- Spill/leak risks
- Waste management issues

### Compliance Risks
- Missing certifications
- Expired permits
- Regulatory violations
- Non-conformance findings

### Maintenance Risks
- Overdue maintenance
- Degraded equipment condition
- Wear and fatigue indicators

---

## Rules

- Extract ONLY risks explicitly stated or clearly implied in the document.
- Do NOT hallucinate risks not mentioned in the text.
- Preserve exact language for warnings and cautions.
- Capture regulatory references when mentioned.
- A warning in the text is always a risk — extract it.
- Failure modes described are risks — extract them.

---

## Input

Document Text:
{{document_text}}

Document ID: {{document_id}}

---

## Expected Output Format

```json
{
  "risks": [
    {
      "risk_id": "risk_001",
      "name": "Bearing Overheating Risk",
      "category": "operational",
      "severity": "high",
      "probability": "medium",
      "applies_to_entity": "asset_p101",
      "applies_to_label": "Pump P101",
      "description": "Insufficient lubrication can cause bearing temperature to exceed 85°C, leading to bearing failure and unplanned shutdown.",
      "consequences": ["Pump shutdown", "Production loss", "Secondary damage to shaft"],
      "mitigations": ["Regular lubrication every 500 hours", "Install bearing temperature sensor"],
      "applicable_standards": ["ISO 4413"],
      "page": 8,
      "confidence": 0.91
    }
  ],
  "warnings": [
    {
      "warning_id": "warn_001",
      "text": "Do not operate the pump above 1500 RPM without prior approval from the maintenance supervisor.",
      "severity": "high",
      "applies_to_entity": "asset_p101",
      "page": 5,
      "confidence": 0.96
    }
  ],
  "compliance_gaps": [
    {
      "gap_id": "comp_001",
      "description": "Fire extinguisher inspection certificate expired on 2025-12-31.",
      "regulation": "NFPA 10",
      "severity": "critical",
      "page": 3,
      "confidence": 0.98
    }
  ]
}
```

If no risks found, return:
```json
{"risks": [], "warnings": [], "compliance_gaps": []}
```

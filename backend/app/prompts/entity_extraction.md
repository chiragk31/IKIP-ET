# Entity Extraction Prompt

Version: 1.0
Last Updated: 2026-07-19
Author: IKIP Platform
Purpose: Extract industrial entities from parsed document text

---

## Instructions

Extract all industrial entities from the following document text.

For each entity, provide:
- A unique entity ID
- Entity type (from the allowed types below)
- Primary label (canonical name)
- Aliases (alternative names found in the document)
- Confidence score (0.0 to 1.0)
- Source page number (if available)

---

## Allowed Entity Types

- Asset (equipment, machinery, instruments)
- Person (engineer, operator, supervisor, inspector)
- Organization (plant, vendor, OEM, contractor, authority)
- Location (area, section, unit, building)
- Procedure (inspection, calibration, maintenance, shutdown, LOTO)
- Event (failure, shutdown, repair, alarm, incident)
- Measurement (temperature, pressure, flow, voltage, RPM)
- Risk (hazard, leak, explosion, corrosion, fire)
- Failure (breakdown, fault, root cause)
- Regulation (ISO, OSHA, factory act, standards)

---

## Rules

- Extract ONLY entities that are explicitly mentioned in the text.
- Do NOT invent entities.
- Preserve exact equipment codes (e.g., "Pump P101", "Valve V-12").
- Preserve exact measurement values with units (e.g., "150°C", "25 bar").
- If the same entity appears under multiple names, list all names as aliases.
- Assign lower confidence scores to ambiguous extractions.

---

## Input

Document Text:
{{document_text}}

Document ID: {{document_id}}

---

## Expected Output Format

```json
{
  "entities": [
    {
      "entity_id": "asset_p101",
      "entity_type": "Asset",
      "label": "Pump P101",
      "aliases": ["P101", "Main Feed Pump"],
      "confidence": 0.97,
      "page": 3,
      "properties": {
        "manufacturer": "Grundfos",
        "serial_number": "GF-2023-001"
      }
    }
  ]
}
```

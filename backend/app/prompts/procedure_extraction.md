# Procedure Extraction Prompt

Version: 1.1
Last Updated: 2026-07-20
Author: IKIP Platform
Purpose: Extract step-by-step procedures, maintenance workflows, and safety instructions from industrial documents

---

## Instructions

Extract all documented procedures from the following industrial document text.

For each procedure, provide:
- A unique procedure ID
- The procedure name/title
- The procedure type (maintenance, inspection, safety, startup, shutdown, calibration, emergency)
- The target equipment or system it applies to — use the entity_id from the Entity Registry below
- Ordered list of steps
- Required tools, materials, or PPE
- Applicable standards or regulations
- Warnings or cautions
- Estimated duration (if mentioned)
- The page number (if available)
- Confidence score (0.0 to 1.0)

---

## Procedure Types to Extract

- Maintenance procedures (scheduled, corrective, predictive)
- Inspection procedures (routine, safety, regulatory)
- Start-up procedures
- Shutdown procedures (normal, emergency)
- LOTO (Lock-Out/Tag-Out) procedures
- Calibration procedures
- Safety procedures
- Emergency response procedures
- Commissioning procedures
- Testing and verification procedures

---

## Entity Registry

The following entities were extracted in a previous stage.

When assigning `applies_to_entity`, you MUST use ONLY the `entity_id` values from this list.

Do NOT invent new entity IDs.

If a procedure cannot be matched to any entity in this registry, set `applies_to_entity` to `"unknown_entity"`.

```json
{{entity_registry}}
```

---

## Rules

- Extract ONLY procedures explicitly described in the document.
- Preserve the original step sequence exactly.
- Extract ALL steps — do not summarize or merge steps.
- Capture warnings/cautions alongside the relevant step.
- If steps reference other procedures, note the reference.
- Associate the procedure with the nearest named asset using the Entity Registry above.
- Never invent entity IDs. Only use IDs from the Entity Registry.

---

## Input

Document Text:
{{document_text}}

Document ID: {{document_id}}

---

## Expected Output Format

```json
{
  "procedures": [
    {
      "procedure_id": "proc_001",
      "name": "Pump P101 Bearing Replacement",
      "procedure_type": "maintenance",
      "applies_to_entity": "asset_p101",
      "applies_to_label": "Pump P101",
      "steps": [
        {
          "step_number": 1,
          "description": "Isolate the pump from the electrical panel using LOTO procedure.",
          "warning": "Ensure power is completely isolated before proceeding.",
          "tools": ["LOTO kit", "multimeter"]
        },
        {
          "step_number": 2,
          "description": "Drain the pump casing by opening the drain valve V-15.",
          "warning": null,
          "tools": ["drain pan", "wrench"]
        }
      ],
      "required_tools": ["LOTO kit", "bearing puller", "torque wrench"],
      "required_ppe": ["safety glasses", "gloves", "steel-toe boots"],
      "applicable_standards": ["ISO 4413", "OSHA 1910.147"],
      "estimated_duration_hours": 4.0,
      "page": 12,
      "confidence": 0.93
    }
  ]
}
```

If no procedures found, return:
```json
{"procedures": []}
```

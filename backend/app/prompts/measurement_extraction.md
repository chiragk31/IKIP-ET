# Measurement Extraction Prompt

Version: 1.0
Last Updated: 2026-07-20
Author: IKIP Platform
Purpose: Extract all numerical measurements, physical quantities, and engineering values from industrial documents

---

## Instructions

Extract all numerical measurements and physical quantities from the following industrial document text.

For each measurement, provide:
- A unique measurement ID
- The measurement name/parameter
- The numeric value
- The unit of measurement
- The entity it applies to (asset, equipment, system)
- The context in which it appears
- Whether it is a limit/threshold or an actual measured value
- The page number (if available)
- Confidence score (0.0 to 1.0)

---

## Measurement Categories to Extract

- Temperature (°C, °F, K)
- Pressure (bar, psi, Pa, kPa, MPa)
- Flow Rate (m³/h, L/min, GPM, SCFM)
- Electrical (V, A, kW, Hz, Ω)
- Mechanical (RPM, torque Nm, vibration mm/s)
- Dimensional (mm, cm, m, inch)
- Weight/Mass (kg, ton, lb)
- Humidity (%, g/m³)
- Time/Frequency (hours, cycles, days)
- Concentration/Chemical (ppm, %, pH)
- Tolerance/Range values (±, min–max)
- Calibration values

---

## Rules

- Extract ONLY measurements explicitly stated in the text.
- Do NOT estimate or infer measurements not clearly stated.
- Preserve exact values — never round or alter numbers.
- Always extract the unit with the value.
- If a range is given (e.g., 120–150 psi), extract both min and max.
- If a tolerance is given (e.g., 100 ± 5 bar), capture both.
- Associate each measurement with the nearest named asset or system.

---

## Input

Document Text:
{{document_text}}

Document ID: {{document_id}}

---

## Expected Output Format

```json
{
  "measurements": [
    {
      "measurement_id": "meas_001",
      "name": "Operating Pressure",
      "value": 120.0,
      "unit": "psi",
      "value_min": null,
      "value_max": null,
      "tolerance": null,
      "measurement_type": "operating",
      "applies_to_entity": "asset_p101",
      "applies_to_label": "Pump P101",
      "context": "Normal operating pressure of the main feed pump",
      "page": 4,
      "confidence": 0.95
    },
    {
      "measurement_id": "meas_002",
      "name": "Temperature Limit",
      "value": null,
      "unit": "°C",
      "value_min": 60.0,
      "value_max": 80.0,
      "tolerance": null,
      "measurement_type": "limit",
      "applies_to_entity": "asset_b01",
      "applies_to_label": "Boiler B-01",
      "context": "Acceptable operating temperature range",
      "page": 7,
      "confidence": 0.92
    }
  ]
}
```

If no measurements found, return:
```json
{"measurements": []}
```

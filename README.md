# Indian Lab Report → FHIR R4 Converter

Converts Indian pathology lab report PDFs into structured **FHIR R4** JSON bundles using the **Gemini API** for intelligent extraction.

Built to solve a real problem: Indian diagnostic labs (Niramaya, SRL, Thyrocare, Dr Lal Pathlabs, etc.) each produce PDFs in their own format with no standardization. This tool parses them all and outputs interoperable FHIR data aligned with **ABDM (Ayushman Bharat Digital Mission)** guidelines.

---

## How it works

```
PDF Lab Report
     │
     ▼
[pdfplumber]  ──  text extraction (layout-preserved)
     │
     ▼
[Gemini API]  ──  structured data extraction via LLM
     │             (patient info, test name, result, unit,
     │              reference range, method, interpretation)
     ▼
[FHIR Mapper] ──  maps to FHIR R4 resources
     │             with LOINC codes for common tests
     ▼
FHIR R4 Bundle (Patient + DiagnosticReport + N Observations)
```

---

## Output Structure

Each run produces a **FHIR R4 Bundle** containing:

| Resource | Count | Description |
|---|---|---|
| `Patient` | 1 | Patient demographics from report header |
| `DiagnosticReport` | 1 | Report metadata, lab info, date, references all Observations |
| `Observation` | N | One per test result, with LOINC code where available |

### Example Observation (Haemoglobin)

```json
{
  "resourceType": "Observation",
  "status": "final",
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "718-7",
      "display": "Hemoglobin [Mass/volume] in Blood"
    }],
    "text": "Haemoglobin"
  },
  "valueQuantity": {
    "value": 14.4,
    "unit": "g/dL"
  },
  "referenceRange": [{ "text": "13.0 - 17.0" }],
  "interpretation": [{
    "coding": [{ "code": "N", "display": "Normal" }]
  }],
  "method": { "text": "Photometry" },
  "specimen": { "display": "EDTA BLOOD" }
}
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your Gemini API key

```bash
export GEMINI_API_KEY="your_key_here"
```

Get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey)

### 3. Run

```bash
python main.py samples/input/your_report.pdf --output output.json
```

Or to print to stdout:

```bash
python main.py samples/input/your_report.pdf
```

---

## Project Structure

```
indian-lab-report-fhir/
├── main.py                   # CLI entry point
├── requirements.txt
├── src/
│   ├── extractor.py          # PDF → raw text (pdfplumber)
│   ├── parser.py             # raw text → structured dict (Gemini API)
│   └── mapper.py             # structured dict → FHIR R4 Bundle
├── samples/
│   ├── input/                # Put your PDFs here
│   └── output/
│       └── niramaya_sample_fhir.json   # Real example output
└── tests/
    └── test_mapper.py
```

---

## Supported Labs (tested)

| Lab | Format | Status |
|---|---|---|
| Niramaya Pathlabs | Columnar PDF | Tested |
| SRL Diagnostics | Columnar PDF | Planned |
| Thyrocare | Columnar PDF | Planned |
| Dr Lal Pathlabs | Columnar PDF | Planned |

---

## LOINC Coverage

LOINC codes are mapped for 50+ common Indian lab tests across:

- **Haematology**: CBC with differentials (Hb, WBC, RBC, platelets, MCV, MCH, MCHC, RDW, MPV, PCT...)
- **Biochemistry**: HbA1c, eAG, Lipid Profile (Total Cholesterol, TG, HDL, LDL, VLDL, ratios...)
- **Liver Function**: Bilirubin (Total/Direct/Indirect), AST, ALT, ALP, GGT, Total Protein, Albumin, Globulin
- **Kidney Function**: BUN, Creatinine, Uric Acid, eGFR, Urea
- **Thyroid**: T3, T4, TSH
- **Serology**: CRP

Tests without a LOINC mapping use a local code system (`urn:in:pathlabs:local-test-code`) so no data is lost.

---

## ABDM Alignment

This tool is designed to complement the [ABDM Health Data Management Policy](https://abdm.gov.in/) and the **NDHM Health Records** specification, which mandates FHIR R4 for health data exchange in India. The generated bundles can be submitted to ABHA-linked PHR applications.

---

## Limitations

- Handwritten or scanned (image-only) PDFs are not supported  reports must have selectable text
- Reference ranges with complex categorical rules (e.g., HbA1c) are stored as plain text strings, not structured FHIR ranges
- LOINC codes are best-effort; always validate before clinical use

---

## Contributing

PRs welcome. Most useful contributions:
- Testing against reports from new labs and documenting differences
- Adding LOINC codes for tests not yet mapped
- Handling edge cases (abnormal flags, multi-page reports, Hindi text)

---

## License

MIT
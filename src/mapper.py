"""
mapper.py
Maps structured lab data to FHIR R4 resources.
Produces a FHIR Bundle containing:
  - 1 Patient resource
  - 1 DiagnosticReport resource
  - N Observation resources (one per test)
"""

import uuid
from datetime import datetime
from typing import Optional


# LOINC codes for common Indian lab tests
# See: https://loinc.org/
LOINC_MAP = {
    # Haematology
    "haemoglobin": ("718-7", "Hemoglobin [Mass/volume] in Blood"),
    "total wbc count": ("6690-2", "Leukocytes [#/volume] in Blood"),
    "neutrophils": ("770-8", "Neutrophils/100 leukocytes in Blood"),
    "lymphocytes": ("736-9", "Lymphocytes/100 leukocytes in Blood"),
    "eosinophils": ("713-8", "Eosinophils/100 leukocytes in Blood"),
    "monocytes": ("5905-5", "Monocytes/100 leukocytes in Blood"),
    "basophils": ("706-2", "Basophils/100 leukocytes in Blood"),
    "pcv": ("20570-8", "Hematocrit [Volume Fraction] of Blood"),
    "red blood cell (rbc) count": ("789-8", "Erythrocytes [#/volume] in Blood"),
    "mcv": ("787-2", "MCV [Entitic volume]"),
    "mch": ("785-6", "MCH [Entitic mass]"),
    "mchc": ("786-4", "MCHC [Mass/volume]"),
    "platelet count": ("777-3", "Platelets [#/volume] in Blood"),
    "absolute neutrophils": ("753-4", "Neutrophils [#/volume] in Blood"),
    "absolute lymphocytes": ("731-0", "Lymphocytes [#/volume] in Blood"),
    "absolute eosinophils": ("711-2", "Eosinophils [#/volume] in Blood"),
    "absolute monocytes": ("742-7", "Monocytes [#/volume] in Blood"),
    "absolute basophils": ("704-7", "Basophils [#/volume] in Blood"),
    "rdw - cv": ("788-0", "Erythrocyte distribution width [Ratio]"),
    "rdw - sd": ("21000-5", "Erythrocyte distribution width [Entitic volume]"),
    "pdw": ("32207-3", "Platelet distribution width [Entitic volume]"),
    "mpv": ("32623-1", "Platelet mean volume [Entitic volume]"),
    "pct": ("51637-7", "Plateletcrit [Volume Fraction]"),

    # Biochemistry - HbA1c
    "glycosylated haemoglobin (hba1c)": ("4548-4", "Hemoglobin A1c/Hemoglobin.total in Blood"),
    "estimated average glucose (eag)": ("77145-1", "Glucose mean value [Mass/volume] in Blood Estimated from glycated hemoglobin"),

    # Lipid profile
    "cholesterol, total": ("2093-3", "Cholesterol [Mass/volume] in Serum or Plasma"),
    "triglycerides": ("2571-8", "Triglyceride [Mass/volume] in Serum or Plasma"),
    "cholesterol, hdl": ("2085-9", "Cholesterol in HDL [Mass/volume] in Serum or Plasma"),
    "cholesterol, ldl": ("13457-7", "Cholesterol in LDL [Mass/volume] in Serum or Plasma by calculation"),
    "cholesterol, vldl": ("13458-5", "Cholesterol in VLDL [Mass/volume] in Serum or Plasma"),
    "cholesterol/hdl ratio": ("9830-1", "Cholesterol.total/Cholesterol in HDL [Mass Ratio] in Serum or Plasma"),
    "ldl/hdl ratio": ("11054-4", "Cholesterol in LDL/Cholesterol in HDL [Mass Ratio] in Serum or Plasma"),
    "non - hdl cholesterol": ("43396-1", "Cholesterol non HDL [Mass/volume] in Serum or Plasma"),
    "hdl/ldl ratio": ("11054-4", "Cholesterol in LDL/Cholesterol in HDL [Mass Ratio] in Serum or Plasma"),

    # LFT
    "bilirubin, total": ("1975-2", "Bilirubin.total [Mass/volume] in Serum or Plasma"),
    "bilirubin, direct": ("1968-7", "Bilirubin.direct [Mass/volume] in Serum or Plasma"),
    "bilirubin, indirect": ("1971-1", "Bilirubin.indirect [Mass/volume] in Serum or Plasma"),
    "aspartate aminotransferase (ast/sgot)": ("1920-8", "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma"),
    "alanine aminotransferase (alt/sgpt)": ("1742-6", "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma"),
    "alkaline phosphatase": ("6768-6", "Alkaline phosphatase [Enzymatic activity/volume] in Serum or Plasma"),
    "gamma glutamyl-transferase (ggt)": ("2324-2", "Gamma glutamyl transferase [Enzymatic activity/volume] in Serum or Plasma"),
    "total protein.": ("2885-2", "Protein [Mass/volume] in Serum or Plasma"),
    "albumin.": ("1751-7", "Albumin [Mass/volume] in Serum or Plasma"),
    "globulin.": ("10834-0", "Globulin [Mass/volume] in Serum"),
    "albumin/globulin ratio": ("1759-0", "Albumin/Globulin [Mass Ratio] in Serum or Plasma"),

    # Kidney function
    "bun": ("3094-0", "Urea nitrogen [Mass/volume] in Serum or Plasma"),
    "creatinine.": ("2160-0", "Creatinine [Mass/volume] in Serum or Plasma"),
    "uric acid.": ("3084-1", "Urate [Mass/volume] in Serum or Plasma"),
    "est. glomerular filtration rate": ("62238-1", "Glomerular filtration rate/1.73 sq M.predicted [Volume Rate/Area] in Serum, Plasma or Blood by Creatinine-based formula (MDRD)"),
    "urea": ("22664-7", "Urea [Mass/volume] in Serum or Plasma"),

    # Thyroid
    "t3": ("3053-6", "Triiodothyronine (T3) [Mass/volume] in Serum or Plasma"),
    "t4": ("3026-2", "Thyroxine (T4) [Mass/volume] in Serum or Plasma"),
    "tsh": ("3016-3", "Thyrotropin [Units/volume] in Serum or Plasma"),

    # Serology
    "crp": ("1988-5", "C reactive protein [Mass/volume] in Serum or Plasma"),
}


def get_loinc(test_name: str) -> Optional[tuple]:
    """Look up LOINC code for a test name. Case-insensitive fuzzy match."""
    key = test_name.lower().strip()
    if key in LOINC_MAP:
        return LOINC_MAP[key]
    # Partial match fallback
    for loinc_key, value in LOINC_MAP.items():
        if loinc_key in key or key in loinc_key:
            return value
    return None


def parse_date_to_fhir(date_str: str) -> Optional[str]:
    """Convert DD/MM/YYYY HH:MM to FHIR dateTime format (YYYY-MM-DDTHH:MM:00+05:30)"""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%d/%m/%Y %H:%M")
        return dt.strftime("%Y-%m-%dT%H:%M:00+05:30")
    except ValueError:
        try:
            dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
            return dt.strftime("%Y-%m-%dT00:00:00+05:30")
        except ValueError:
            return None


def make_patient(patient_data: dict) -> dict:
    """Build a FHIR R4 Patient resource."""
    patient_id = str(uuid.uuid4())

    # Parse age as a rough birthDate (approximate)
    age_str = patient_data.get("age", "")
    age_num = None
    try:
        age_num = int(age_str.replace("Y", "").strip())
    except (ValueError, AttributeError):
        pass

    resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [
            {
                "system": "urn:in:pathlabs:patient-id",
                "value": patient_data.get("patient_id", "")
            }
        ],
        "name": [
            {
                "text": patient_data.get("name", ""),
                "use": "official"
            }
        ],
        "gender": patient_data.get("sex", "").lower() if patient_data.get("sex") else "unknown",
    }

    if age_num:
        birth_year = datetime.now().year - age_num
        resource["birthDate"] = str(birth_year)

    return resource, patient_id


def make_observation(test: dict, patient_id: str, report_date: str) -> tuple:
    """Build a FHIR R4 Observation resource for a single test result."""
    obs_id = str(uuid.uuid4())
    loinc = get_loinc(test["name"])

    # Build coding
    coding = []
    if loinc:
        coding.append({
            "system": "http://loinc.org",
            "code": loinc[0],
            "display": loinc[1]
        })
    # Always include local code as fallback
    coding.append({
        "system": "urn:in:pathlabs:local-test-code",
        "display": test["name"]
    })

    # Interpretation mapping
    interpretation_map = {
        "H": {"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"},
        "L": {"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "L", "display": "Low"},
        "N": {"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"},
    }

    obs = {
        "resourceType": "Observation",
        "id": obs_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "laboratory",
                        "display": "Laboratory"
                    }
                ]
            }
        ],
        "code": {
            "coding": coding,
            "text": test["name"]
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": report_date,
        "specimen": {
            "display": test.get("specimen", "")
        },
        "method": {
            "text": test.get("method", "")
        } if test.get("method") else None,
    }

    # Value
    try:
        obs["valueQuantity"] = {
            "value": float(test["result"]),
            "unit": test.get("unit", ""),
            "system": "http://unitsofmeasure.org"
        }
    except (ValueError, TypeError):
        obs["valueString"] = str(test.get("result", ""))

    # Reference range
    if test.get("reference_range"):
        obs["referenceRange"] = [{"text": test["reference_range"]}]

    # Interpretation
    interp = test.get("interpretation")
    if interp and interp in interpretation_map:
        obs["interpretation"] = [{"coding": [interpretation_map[interp]]}]

    # Extension: section/subsection for grouping
    extensions = []
    if test.get("section"):
        extensions.append({
            "url": "urn:in:pathlabs:section",
            "valueString": test["section"]
        })
    if test.get("subsection"):
        extensions.append({
            "url": "urn:in:pathlabs:subsection",
            "valueString": test["subsection"]
        })
    if extensions:
        obs["extension"] = extensions

    # Clean up null fields
    obs = {k: v for k, v in obs.items() if v is not None}

    return obs, obs_id


def make_diagnostic_report(parsed: dict, patient_id: str, observation_ids: list) -> dict:
    """Build a FHIR R4 DiagnosticReport resource."""
    report = parsed["report"]
    lab = parsed["lab"]

    reported_date = parse_date_to_fhir(report.get("reported_date"))
    collected_date = parse_date_to_fhir(report.get("collected_date"))

    dr = {
        "resourceType": "DiagnosticReport",
        "id": str(uuid.uuid4()),
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "LAB",
                        "display": "Laboratory"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "11502-2",
                    "display": "Laboratory report"
                }
            ],
            "text": "Final Test Report"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": collected_date,
        "issued": reported_date,
        "performer": [
            {
                "display": f"{lab.get('name', '')} - {lab.get('branch', '')}".strip(" -")
            }
        ],
        "result": [
            {"reference": f"Observation/{obs_id}"}
            for obs_id in observation_ids
        ],
        "identifier": [
            {
                "system": "urn:in:pathlabs:sid",
                "value": parsed["patient"].get("sid", "")
            }
        ],
    }

    if parsed.get("report", {}).get("referred_by"):
        dr["basedOn"] = [{"display": f"Referred by: {report['referred_by']}"}]

    return dr


def build_fhir_bundle(parsed: dict) -> dict:
    """
    Main entry point. Takes parsed lab data and returns a complete FHIR R4 Bundle.
    """
    entries = []

    # 1. Patient
    patient_resource, patient_id = make_patient(parsed["patient"])
    entries.append({"resource": patient_resource, "fullUrl": f"urn:uuid:{patient_id}"})

    # 2. Observations (one per test)
    observation_ids = []
    report_date = parse_date_to_fhir(parsed["report"].get("reported_date")) or datetime.now().isoformat()

    for test in parsed.get("tests", []):
        obs, obs_id = make_observation(test, patient_id, report_date)
        observation_ids.append(obs_id)
        entries.append({"resource": obs, "fullUrl": f"urn:uuid:{obs_id}"})

    # 3. DiagnosticReport
    dr = make_diagnostic_report(parsed, patient_id, observation_ids)
    entries.insert(1, {"resource": dr, "fullUrl": f"urn:uuid:{dr['id']}"})

    # 4. Wrap in Bundle
    bundle = {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "type": "collection",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        "entry": entries
    }

    return bundle

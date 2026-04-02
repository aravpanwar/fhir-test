"""
tests/test_mapper.py
Unit tests for the FHIR mapper. Run with: pytest tests/
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.mapper import (
    get_loinc,
    parse_date_to_fhir,
    make_patient,
    make_observation,
    build_fhir_bundle,
)


# --- LOINC lookup tests ---

def test_loinc_exact_match():
    result = get_loinc("haemoglobin")
    assert result is not None
    assert result[0] == "718-7"

def test_loinc_case_insensitive():
    result = get_loinc("HAEMOGLOBIN")
    assert result is not None

def test_loinc_partial_match():
    result = get_loinc("Glycosylated Haemoglobin (HbA1c)")
    assert result is not None
    assert result[0] == "4548-4"

def test_loinc_unknown_test():
    result = get_loinc("some random test xyz")
    assert result is None


# --- Date parsing tests ---

def test_parse_date_full():
    result = parse_date_to_fhir("22/03/2026 12:08")
    assert result == "2026-03-22T12:08:00+05:30"

def test_parse_date_date_only():
    result = parse_date_to_fhir("22/03/2026")
    assert result == "2026-03-22T00:00:00+05:30"

def test_parse_date_invalid():
    result = parse_date_to_fhir("not a date")
    assert result is None


# --- Patient resource tests ---

def test_make_patient_basic():
    data = {"name": "Mr. Test Patient", "age": "45 Y", "sex": "Male", "patient_id": "12345", "sid": "SID001"}
    resource, patient_id = make_patient(data)
    assert resource["resourceType"] == "Patient"
    assert resource["gender"] == "male"
    assert resource["name"][0]["text"] == "Mr. Test Patient"
    assert patient_id is not None

def test_make_patient_gender_female():
    data = {"name": "Ms. Test", "age": "30 Y", "sex": "Female", "patient_id": "999", "sid": "S1"}
    resource, _ = make_patient(data)
    assert resource["gender"] == "female"


# --- Observation resource tests ---

SAMPLE_TEST = {
    "name": "Haemoglobin",
    "section": "HAEMATOLOGY",
    "subsection": "Complete blood count",
    "specimen": "EDTA BLOOD",
    "result": "14.4",
    "unit": "g/dL",
    "reference_range": "13.0 - 17.0",
    "method": "Photometry",
    "interpretation": "N"
}

def test_make_observation_structure():
    obs, obs_id = make_observation(SAMPLE_TEST, "patient-001", "2026-03-22T12:08:00+05:30")
    assert obs["resourceType"] == "Observation"
    assert obs["status"] == "final"
    assert obs["valueQuantity"]["value"] == 14.4
    assert obs["valueQuantity"]["unit"] == "g/dL"
    assert obs["referenceRange"][0]["text"] == "13.0 - 17.0"

def test_make_observation_has_loinc():
    obs, _ = make_observation(SAMPLE_TEST, "patient-001", "2026-03-22T12:08:00+05:30")
    loinc_codes = [c["system"] for c in obs["code"]["coding"]]
    assert "http://loinc.org" in loinc_codes

def test_make_observation_interpretation():
    obs, _ = make_observation(SAMPLE_TEST, "patient-001", "2026-03-22T12:08:00+05:30")
    assert obs["interpretation"][0]["coding"][0]["code"] == "N"

def test_make_observation_high():
    test = {**SAMPLE_TEST, "result": "19.0", "interpretation": "H"}
    obs, _ = make_observation(test, "patient-001", "2026-03-22T12:08:00+05:30")
    assert obs["interpretation"][0]["coding"][0]["code"] == "H"


# --- Full bundle test ---

SAMPLE_PARSED = {
    "patient": {
        "name": "Mr. Test Patient",
        "age": "60 Y",
        "sex": "Male",
        "patient_id": "12345",
        "sid": "SID001"
    },
    "lab": {
        "name": "Test Pathlabs",
        "branch": "HYDERABAD",
        "phone": None,
        "email": None
    },
    "report": {
        "collected_date": "22/03/2026 10:06",
        "received_date": "22/03/2026 10:23",
        "reported_date": "22/03/2026 12:08",
        "referred_by": "MEDIBUDDY"
    },
    "tests": [SAMPLE_TEST]
}

def test_build_fhir_bundle():
    bundle = build_fhir_bundle(SAMPLE_PARSED)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    resource_types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert "Patient" in resource_types
    assert "DiagnosticReport" in resource_types
    assert "Observation" in resource_types

def test_bundle_observation_count():
    bundle = build_fhir_bundle(SAMPLE_PARSED)
    obs_count = sum(1 for e in bundle["entry"] if e["resource"]["resourceType"] == "Observation")
    assert obs_count == len(SAMPLE_PARSED["tests"])

def test_diagnostic_report_references_observations():
    bundle = build_fhir_bundle(SAMPLE_PARSED)
    dr = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "DiagnosticReport")
    assert len(dr["result"]) == len(SAMPLE_PARSED["tests"])

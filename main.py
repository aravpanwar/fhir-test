"""
main.py
CLI entry point for the Indian Lab Report → FHIR converter.

Usage:
    python main.py <path_to_pdf> [--output <output_path>]

Example:
    python main.py samples/input/report.pdf --output samples/output/report_fhir.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

from src.extractor import extract_text
from src.parser import parse_report
from src.mapper import build_fhir_bundle


def convert(pdf_path: str, output_path: str = None, verbose: bool = False) -> dict:
    """
    Full pipeline: PDF → text → structured data → FHIR Bundle.
    Returns the FHIR Bundle as a dict.
    """

    print(f"[1/3] Extracting text from: {pdf_path}")
    raw_text = extract_text(pdf_path)
    if verbose:
        print(f"      Extracted {len(raw_text)} characters across pages")

    print("[2/3] Parsing with Gemini...")
    parsed = parse_report(raw_text)
    patient = parsed.get("patient", {})
    tests = parsed.get("tests", [])
    print(f"      Found {len(tests)} test results for patient: {patient.get('name', 'Unknown')}")

    print("[3/3] Mapping to FHIR R4...")
    bundle = build_fhir_bundle(parsed)
    resource_count = len(bundle["entry"])
    print(f"      Created FHIR Bundle with {resource_count} resources")
    print(f"        - 1 Patient")
    print(f"        - 1 DiagnosticReport")
    print(f"        - {resource_count - 2} Observations")

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(bundle, f, indent=2)
        print(f"\n✓ FHIR Bundle saved to: {output_path}")
    else:
        print("\n--- FHIR Bundle (stdout) ---")
        print(json.dumps(bundle, indent=2))

    return bundle


def main():
    parser = argparse.ArgumentParser(
        description="Convert Indian lab report PDFs to FHIR R4 JSON"
    )
    parser.add_argument("pdf", help="Path to lab report PDF")
    parser.add_argument("--output", "-o", help="Output path for FHIR JSON (default: stdout)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"Error: File not found: {args.pdf}")
        sys.exit(1)

    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set")
        print("Get your key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)

    convert(args.pdf, args.output, args.verbose)


if __name__ == "__main__":
    main()

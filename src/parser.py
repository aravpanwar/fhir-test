"""
parser.py
Uses Gemini API to extract structured data from raw lab report text.
This is the core intelligence of the pipeline.
"""

import json
import re
import os
import google.generativeai as genai


# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")


EXTRACTION_PROMPT = """
You are a medical data extraction assistant. You will be given raw text extracted from an Indian lab report PDF.

Extract ALL information and return ONLY valid JSON — no markdown, no explanation, no preamble.

Return this exact structure:
{
  "patient": {
    "name": "string",
    "age": "string",
    "sex": "string",
    "patient_id": "string",
    "sid": "string"
  },
  "lab": {
    "name": "string",
    "branch": "string",
    "phone": "string",
    "email": "string"
  },
  "report": {
    "collected_date": "string",
    "received_date": "string",
    "reported_date": "string",
    "referred_by": "string"
  },
  "tests": [
    {
      "name": "string (full test name)",
      "section": "string",
      "subsection": "string",
      "specimen": "string",
      "result": "string (numeric value as string)",
      "unit": "string",
      "reference_range": "string",
      "method": "string",
      "interpretation": "string (H = high, L = low, N = normal)"
    }
  ]
}

CRITICAL RULES TO PREVENT TOKEN LIMITS:
1. Extract EVERY test result.
2. DO NOT include keys where the value is unknown, blank, or null. Completely omit that key from the object. This is critical to save space.
3. Do NOT include interpretive notes/paragraphs.

Lab report text:
{text}
"""


def parse_report(raw_text: str) -> dict:
    prompt = EXTRACTION_PROMPT.replace("{text}", raw_text)

    # Use a standard dictionary for config and remove JSON mode to prevent overrides
    response = model.generate_content(
        prompt,
        generation_config={
            "max_output_tokens": 8192
        }
    )

    raw_response = response.text.strip()

    # Clean up Markdown formatting
    cleaned_response = raw_response.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned_response)
    except json.decoder.JSONDecodeError as e:
        print(f"\n[!] Gemini output got cut off at {len(cleaned_response)} chars. Attempting auto-recovery...")
        
        # AUTO-RECOVERY LOGIC FOR TRUNCATED JSON
        # Find the last completely valid test object block
        last_brace_index = cleaned_response.rfind('}')
        
        if last_brace_index != -1:
            # Chop off the incomplete text (e.g., the half-written test name)
            recovered_str = cleaned_response[:last_brace_index + 1]
            
            # Close the tests array and the main JSON body
            recovered_str += '\n  ]\n}'
            
            try:
                recovered_data = json.loads(recovered_str)
                print(f"    ✓ Successfully recovered {len(recovered_data.get('tests', []))} tests from partial data!")
                return recovered_data
            except Exception:
                print("    x Auto-recovery failed.")

        # If it fully crashes, print out the text so we can see
        print("\n--- GEMINI OUTPUT THAT CAUSED THE CRASH ---")
        print(cleaned_response)
        print("-------------------------------------------\n")
        raise e


if __name__ == "__main__":
    import sys
    from extractor import extract_text

    if len(sys.argv) < 2:
        print("Usage: python parser.py <path_to_pdf>")
        sys.exit(1)

    text = extract_text(sys.argv[1])
    result = parse_report(text)
    print(json.dumps(result, indent=2))
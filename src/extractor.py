"""
extractor.py
Extracts raw text from lab report PDFs using pdfplumber.
Preserves layout so the columnar structure (Test | Result | Units | Range) is intact.
"""

import pdfplumber


def extract_text(pdf_path: str) -> str:
    """
    Extract all text from a PDF, page by page.
    Uses layout=True to preserve column spacing — critical for lab reports.
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if text:
                pages.append(text)
    return "\n\n".join(pages)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <path_to_pdf>")
        sys.exit(1)
    text = extract_text(sys.argv[1])
    print(text[:3000])  # preview first 3000 chars

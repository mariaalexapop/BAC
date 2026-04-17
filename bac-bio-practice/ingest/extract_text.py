"""
Extracts text from PDF files using pdfplumber.
"""

import pdfplumber
from typing import List


def extract_text(pdf_path: str) -> str:
    """
    Extract all text from a PDF, concatenating pages with newlines.
    Strips common footer/header noise.
    """
    pages: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    raw = "\n".join(pages)
    return _clean_text(raw)


def _clean_text(text: str) -> str:
    """Remove boilerplate headers/footers that appear on every page."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip common footer lines
        if stripped.startswith("Pagina ") and " din " in stripped:
            continue
        if stripped.startswith("Probă scrisă la"):
            continue
        if stripped.startswith("Ministerul Educaţ") or stripped.startswith("Ministerul Educației"):
            continue
        if stripped.startswith("Centrul Naţional") or stripped.startswith("Centrul National"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)

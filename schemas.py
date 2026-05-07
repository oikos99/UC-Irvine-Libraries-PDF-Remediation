from __future__ import annotations

from pydantic import BaseModel, Field


class PageAccessDraft(BaseModel):
    page_summary: str = Field(description="A concise 1-3 sentence summary of the page.")
    short_alt_text: str = Field(description="Short alt text for the full-page image.")
    long_description: str = Field(description="Detailed visual description of the page layout and meaningful visual content.")
    transcription: str = Field(description="Best-effort transcription of all readable text. Mark illegible text clearly.")
    language_detected: str = Field(description="Language or languages visible on the page.")
    math_or_formulas: str = Field(description="Any formulas, equations, tables, or symbolic notation visible on the page.")


DISPLAY_FIELDS = [
    "page_summary",
    "short_alt_text",
    "long_description",
    "transcription",
    "language_detected",
    "math_or_formulas",
]

FIELD_LABELS = {
    "page_summary": "Page summary",
    "short_alt_text": "Short alt text",
    "long_description": "Long description",
    "transcription": "Transcription",
    "language_detected": "Language detected",
    "math_or_formulas": "Math, formulas, tables, or symbols",
}


def make_empty_record(page_number: int) -> dict:
    return {
        "page_number": page_number,
        "page_summary": "",
        "short_alt_text": "Scanned archival PDF page. Description and text follow.",
        "long_description": "",
        "transcription": "",
        "language_detected": "",
        "math_or_formulas": "",
    }


def filtered_record(record: dict) -> dict:
    """Return only the fields that should appear in user-facing outputs."""
    page_number = record.get("page_number", "")
    clean = {"page_number": page_number}
    for field in DISPLAY_FIELDS:
        clean[field] = record.get(field, "")
    return clean

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Literal, Optional

from openai import OpenAI

from schemas import PageAccessDraft
from utils import image_to_data_url

ProviderName = Literal["OpenAI", "Gemini", "Test mode (no API)"]


JSON_SHAPE = """
{
  "page_summary": "A concise 1-3 sentence summary of the page.",
  "short_alt_text": "Short alt text for the full-page image.",
  "long_description": "Detailed visual description of the page layout and meaningful visual content.",
  "transcription": "Best-effort transcription of all readable text. Mark illegible text clearly.",
  "language_detected": "Language or languages visible on the page.",
  "math_or_formulas": "Any formulas, equations, tables, or symbolic notation visible on the page."
}
""".strip()


def build_prompt(page_number: int, total_pages: int, custom_instruction: str) -> str:
    return f"""
You are assisting with accessibility access-copy creation for a scanned archival PDF page.

Analyze original page {page_number} of {total_pages} from the page image.

Core rules:
- Do not invent missing information.
- If text is unclear, mark it as [illegible] or [uncertain: possible word].
- Preserve line breaks in the transcription when useful.
- If the page includes handwriting, describe the handwriting and transcribe what you can.
- If the page includes non-English text, identify the language when possible and transcribe it as written.
- If the page includes math, formulas, tables, diagrams, stamps, marginalia, or damage, describe them.
- Be useful to a screen reader user who cannot see the page image.
- The result is an AI draft for human review, not final archival metadata.

Additional local instruction from reviewer:
{custom_instruction}
""".strip()


def build_json_prompt(page_number: int, total_pages: int, custom_instruction: str) -> str:
    base_prompt = build_prompt(page_number, total_pages, custom_instruction)
    return f"""
Return ONLY valid JSON. Do not include markdown, code fences, explanations, or surrounding text.

Use this exact JSON structure and fill every field. Do not add extra fields:

{JSON_SHAPE}

{base_prompt}
""".strip()


def extract_json_from_text(text: str) -> dict:
    """Extract JSON from a raw provider text response."""
    if not text or not text.strip():
        raise ValueError("Provider returned an empty response.")

    cleaned = text.strip()

    # Remove common markdown code fences.
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: extract the first JSON object from surrounding text.
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find a JSON object in provider response. Raw response:\n\n{text[:4000]}")

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Found JSON-like text, but it could not be parsed. "
            f"Extracted text:\n\n{match.group(0)[:4000]}"
        ) from exc


def normalize_ai_result(parsed: object, page_number: int, provider: str, raw_response: str = "") -> dict:
    """Normalize provider output into the same dict shape expected by the UI."""
    if isinstance(parsed, PageAccessDraft):
        data = parsed.model_dump()
    elif isinstance(parsed, dict):
        data = parsed
    else:
        data = {}
        for field in PageAccessDraft.model_fields.keys():
            data[field] = getattr(parsed, field, "")

    return {
        "page_number": page_number,
        "page_summary": str(data.get("page_summary", "")),
        "short_alt_text": str(data.get("short_alt_text", "")),
        "long_description": str(data.get("long_description", "")),
        "transcription": str(data.get("transcription", "")),
        "language_detected": str(data.get("language_detected", "")),
        "math_or_formulas": str(data.get("math_or_formulas", "")),
        "ai_provider": provider,
        "_debug_raw_response": raw_response,
    }


def analyze_page_test_mode(page_number: int, total_pages: int) -> dict:
    return normalize_ai_result(
        {
            "page_summary": f"TEST DATA: This is a fake summary for original page {page_number} of {total_pages}.",
            "short_alt_text": f"TEST DATA: Scanned archival page {page_number}. Description and text follow.",
            "long_description": (
                "TEST DATA: This field proves that the long-description text area can populate. "
                "The page image appears on the left, and this generated text should appear on the right."
            ),
            "transcription": (
                "TEST DATA TRANSCRIPTION\n"
                "Line 1: This is not from the PDF.\n"
                "Line 2: This confirms the UI is working without spending API credits."
            ),
            "language_detected": "TEST DATA: English",
            "math_or_formulas": "TEST DATA: No formulas detected in test mode.",
        },
        page_number=page_number,
        provider="Test mode (no API)",
        raw_response="No API call was made. This is deterministic fake test data.",
    )


def analyze_page_with_openai(
    image_path: str,
    page_number: int,
    total_pages: int,
    model: str,
    api_key: Optional[str],
    custom_instruction: str,
) -> dict:
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    prompt = build_prompt(page_number, total_pages, custom_instruction)
    data_url = image_to_data_url(image_path)

    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": "You create structured accessibility descriptions and transcriptions for scanned archival materials.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url},
                ],
            },
        ],
        text_format=PageAccessDraft,
    )

    parsed = response.output_parsed
    raw_response = getattr(response, "output_text", "") or ""
    return normalize_ai_result(parsed, page_number, provider="OpenAI", raw_response=raw_response)


def analyze_page_with_gemini(
    image_path: str,
    page_number: int,
    total_pages: int,
    model: str,
    api_key: Optional[str],
    custom_instruction: str,
) -> dict:
    """
    Gemini adapter.

    Gemini can return parsed JSON in newer SDK versions, or text JSON in other cases.
    This function supports both and normalizes the result for the UI.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ImportError("Gemini support requires google-genai. Install it with: pip install google-genai") from exc

    gemini_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("Missing Gemini API key. Enter it in the sidebar or set GEMINI_API_KEY.")

    client = genai.Client(api_key=gemini_key)
    prompt = build_json_prompt(page_number, total_pages, custom_instruction)
    image_bytes = Path(image_path).read_bytes()

    response = client.models.generate_content(
        model=model,
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        ],
        config=types.GenerateContentConfig(
            system_instruction="You create structured accessibility descriptions and transcriptions for scanned archival materials.",
            response_mime_type="application/json",
        ),
    )

    raw_text = getattr(response, "text", "") or ""
    parsed = getattr(response, "parsed", None)

    if parsed is None:
        parsed = extract_json_from_text(raw_text)
    elif isinstance(parsed, str):
        parsed = extract_json_from_text(parsed)

    return normalize_ai_result(parsed, page_number, provider="Gemini", raw_response=raw_text)


def analyze_page(
    provider: str,
    image_path: str,
    page_number: int,
    total_pages: int,
    custom_instruction: str,
    # New named arguments used by the fixed app.py:
    openai_model: Optional[str] = None,
    gemini_model: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    # Backward-compatible arguments used by older app.py versions:
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """
    Main provider router used by app.py.

    This signature intentionally supports both the new provider-specific arguments
    and the older generic model/api_key arguments so app.py and ai_analysis.py do
    not fall out of sync during prototyping.
    """
    if provider == "Test mode (no API)":
        return analyze_page_test_mode(page_number, total_pages)

    if provider == "OpenAI":
        return analyze_page_with_openai(
            image_path=image_path,
            page_number=page_number,
            total_pages=total_pages,
            model=openai_model or model or os.environ.get("OPENAI_MODEL", "gpt-5.2"),
            api_key=openai_api_key or api_key,
            custom_instruction=custom_instruction,
        )

    if provider == "Gemini":
        return analyze_page_with_gemini(
            image_path=image_path,
            page_number=page_number,
            total_pages=total_pages,
            model=gemini_model or model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            api_key=gemini_api_key or api_key,
            custom_instruction=custom_instruction,
        )

    raise ValueError(f"Unknown AI provider: {provider}")

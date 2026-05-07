from __future__ import annotations

import html
import json
from typing import Dict, List, Tuple

import fitz  # PyMuPDF

from schemas import FIELD_LABELS, filtered_record
from utils import image_to_data_url, records_as_sorted_list


OUTPUT_FIELDS = [
    "page_summary",
    "short_alt_text",
    "long_description",
    "transcription",
    "language_detected",
    "math_or_formulas",
]


def page_description_title(page_number: int) -> str:
    return f"Page {page_number}: Description and Text:"


def html_page_title(page_number: int) -> str:
    return f"Page {page_number}:"


def export_json(records: Dict[int, dict]) -> bytes:
    clean_records = [filtered_record(record) for record in records_as_sorted_list(records)]
    return json.dumps(clean_records, indent=2, ensure_ascii=False).encode("utf-8")


def export_html(records: Dict[int, dict], page_meta: List[dict], title: str) -> bytes:
    meta_by_page = {m["page_number"]: m for m in page_meta}
    sections = []

    for raw_record in records_as_sorted_list(records):
        record = filtered_record(raw_record)
        page_number = record["page_number"]
        meta = meta_by_page.get(page_number)
        image_data_url = image_to_data_url(meta["image_path"]) if meta else ""

        field_html = []
        for field in OUTPUT_FIELDS:
            label = FIELD_LABELS[field]
            value = html.escape(str(record.get(field, ""))).replace(chr(10), "<br>")
            if field == "transcription":
                field_html.append(f"<h2>{html.escape(label)}:</h2>\n<pre>{html.escape(str(record.get(field, '')))}</pre>")
            else:
                field_html.append(f"<h2>{html.escape(label)}:</h2>\n<p>{value}</p>")

        sections.append(
            f"""
<section class="page-section" aria-labelledby="page-{page_number}-heading">
  <h1 id="page-{page_number}-heading">{html.escape(html_page_title(page_number))}</h1>
  <figure>
    <img src="{image_data_url}" alt="{html.escape(record.get('short_alt_text', 'Scanned archival PDF page. Description and text follow.'))}">
  </figure>
  {''.join(field_html)}
</section>
"""
        )

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; line-height: 1.55; margin: 2rem auto; max-width: 960px; padding: 0 1rem; }}
    img {{ max-width: 100%; height: auto; border: 1px solid #ccc; }}
    figure {{ margin: 1rem 0 2rem 0; }}
    h1 {{ font-size: 1.8rem; margin-top: 2rem; border-bottom: 3px solid #333; padding-bottom: .25rem; }}
    h2 {{ font-size: 1.25rem; margin-top: 1.5rem; }}
    pre {{ white-space: pre-wrap; background: #f7f7f7; padding: 1rem; border: 1px solid #ddd; }}
    .page-section {{ border-top: 3px solid #333; padding-top: 1.5rem; margin-top: 2rem; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p>This PDF was analyzed from its scanned page images. The output below provides a description and visible text transcription for each page.</p>
  {''.join(sections)}
</body>
</html>"""
    return document.encode("utf-8")


def _text_width(text: str, fontname: str, fontsize: float) -> float:
    return fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)


def _wrap_line(line: str, max_width: float, fontname: str, fontsize: float) -> List[str]:
    """Wrap a single logical line to fit max_width while preserving words when possible."""
    if line == "":
        return [""]

    words = line.split(" ")
    wrapped: List[str] = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        if _text_width(candidate, fontname, fontsize) <= max_width:
            current = candidate
            continue

        if current:
            wrapped.append(current)
            current = word
        else:
            # Very long token. Break by characters.
            chunk = ""
            for char in word:
                candidate_chunk = chunk + char
                if _text_width(candidate_chunk, fontname, fontsize) <= max_width:
                    chunk = candidate_chunk
                else:
                    if chunk:
                        wrapped.append(chunk)
                    chunk = char
            current = chunk

    if current:
        wrapped.append(current)

    return wrapped or [""]


def _wrap_text(text: str, max_width: float, fontname: str, fontsize: float) -> List[str]:
    lines: List[str] = []
    for raw_line in str(text).splitlines():
        lines.extend(_wrap_line(raw_line, max_width, fontname, fontsize))
    return lines or [""]


def _new_description_page(doc: fitz.Document, page_number: int, continued: bool = False) -> Tuple[fitz.Page, float]:
    width, height = 612, 792  # Letter size
    margin = 54
    title_font = "hebo"
    page = doc.new_page(width=width, height=height)

    title = page_description_title(page_number)
    if continued:
        title += " (continued)"

    y = margin
    page.insert_text((margin, y), title, fontname=title_font, fontsize=18)
    y += 18
    page.draw_line((margin, y + 6), (width - margin, y + 6), width=1.25)
    y += 28
    return page, y


def _draw_label_and_text(
    doc: fitz.Document,
    page: fitz.Page,
    y: float,
    page_number: int,
    label: str,
    value: str,
) -> Tuple[fitz.Page, float]:
    width, height = 612, 792
    margin = 54
    max_width = width - (2 * margin)
    bottom = height - margin
    label_font = "hebo"
    body_font = "helv"
    label_size = 13.5
    body_size = 10.5
    label_line_height = 18
    body_line_height = 14
    paragraph_gap = 12

    def ensure_space(current_page: fitz.Page, current_y: float, needed: float) -> Tuple[fitz.Page, float]:
        if current_y + needed <= bottom:
            return current_page, current_y
        return _new_description_page(doc, page_number, continued=True)

    page, y = ensure_space(page, y, label_line_height + body_line_height)
    page.insert_text((margin, y), f"{label}:", fontname=label_font, fontsize=label_size)
    y += label_line_height

    lines = _wrap_text(value or "", max_width=max_width, fontname=body_font, fontsize=body_size)
    if not lines:
        lines = [""]

    for line in lines:
        page, y = ensure_space(page, y, body_line_height)
        if line:
            page.insert_text((margin, y), line, fontname=body_font, fontsize=body_size)
        y += body_line_height

    y += paragraph_gap
    return page, y


def add_description_pages(doc: fitz.Document, record: dict) -> int:
    """Add visually formatted description/text pages after an image page. Returns the first page index added."""
    page_number = int(record.get("page_number", 0))
    clean = filtered_record(record)
    first_page_index = doc.page_count
    page, y = _new_description_page(doc, page_number, continued=False)

    for field in OUTPUT_FIELDS:
        label = FIELD_LABELS[field]
        value = clean.get(field, "")
        page, y = _draw_label_and_text(doc, page, y, page_number, label, value)

    return first_page_index


def export_basic_pdf(records: Dict[int, dict], page_meta: List[dict]) -> bytes:
    """Create a basic interleaved PDF: image page, then description/text page(s)."""
    out = fitz.open()
    meta_by_page = {m["page_number"]: m for m in page_meta}
    toc = []

    for raw_record in records_as_sorted_list(records):
        record = filtered_record(raw_record)
        page_number = record["page_number"]
        meta = meta_by_page.get(page_number)
        if not meta:
            continue

        image_page_number = out.page_count + 1
        image_page = out.new_page(width=meta["width"], height=meta["height"])
        image_page.insert_image(
            fitz.Rect(0, 0, meta["width"], meta["height"]),
            filename=meta["image_path"],
            keep_proportion=True,
        )
        toc.append([1, f"Original page {page_number}", image_page_number])

        description_page_index = add_description_pages(out, record)
        toc.append([1, page_description_title(page_number), description_page_index + 1])

    if toc:
        out.set_toc(toc)

    pdf_bytes = out.tobytes(garbage=4, deflate=True)
    out.close()
    return pdf_bytes

# UC Irvine Libraries PDF Scan Accessibility Remediation Tool

This is a Python/Streamlit prototype for creating AI-assisted descriptions and visible text transcriptions for scanned archival PDFs and other image-based documents that are difficult to process through OCR alone.

## What it does

This version supports **OpenAI**, **Gemini**, and **Test mode (no API)**. Use Test mode first to confirm the UI populates before spending API credits.

1. Upload a scanned PDF.
2. Render each page as a PNG image.
3. Choose OpenAI or Gemini and send selected page images to the selected provider.
4. Receive structured JSON with only these page fields:
   - page summary
   - short alt text
   - long description
   - transcription
   - language detected
   - math, formulas, tables, or symbols
5. Show each page image and generated text side by side.
6. Allow human editing.
7. Export:
   - JSON
   - accessible HTML access copy
   - basic interleaved PDF access copy

## Output changes in this version

The review UI and exports no longer include:

- uncertain items
- reviewer warning
- review status

The description page title is now:

```text
Page 1: Description and Text:
```

In the basic PDF export, this page title is visually styled as a large heading. Each field label is visually styled as a smaller heading:

```text
Page summary:
Short alt text:
Long description:
Transcription:
Language detected:
Math, formulas, tables, or symbols:
```

## Important PDF limitation

The exported PDF is a basic derivative with image pages and visible description/text pages. It uses visually pronounced headings and PDF bookmarks, but it is **not** a fully tagged PDF/UA-compliant PDF with true H1/H2 structure tags.

For early testing, use the HTML export as the primary accessible access copy. A true tagged PDF export should be added later with a dedicated tagged-PDF library or manual remediation workflow.

## AI provider options

The sidebar includes an **AI provider** dropdown with three choices:

- **Test mode (no API)** — inserts fake data without spending API credits.
- **OpenAI** — uses `OPENAI_API_KEY` or the OpenAI API key field in the sidebar.
- **Gemini** — uses `GEMINI_API_KEY` or the Gemini API key field in the sidebar.

All providers return the same page fields, so the review and export workflow stays the same.

## Project structure

- `app.py` — Streamlit entrypoint and workflow orchestration
- `render_pages.py` — render each PDF page to PNG
- `ai_analysis.py` — send page images to OpenAI or Gemini and receive structured JSON
- `review_ui.py` — show page image + editable AI text side by side
- `exports.py` — export JSON, HTML access copy, and basic PDF access copy
- `schemas.py` — Pydantic schema, field labels, and output field filtering
- `utils.py` — shared helpers for hashing, working directories, page parsing, and image encoding

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set your API keys, or paste them into the app sidebar.

Windows:

```bash
set OPENAI_API_KEY=your_openai_api_key_here
set GEMINI_API_KEY=your_gemini_api_key_here
```

macOS/Linux:

```bash
export OPENAI_API_KEY=your_openai_api_key_here
export GEMINI_API_KEY=your_gemini_api_key_here
```

Run the app:

```bash
streamlit run app.py
```

## Debug first before using API credits

Before choosing OpenAI or Gemini, choose **Test mode (no API)** in the sidebar and click **Generate AI drafts**. This inserts fake text into the review fields without spending any API credits.

- If the fake text appears, the Streamlit UI population is working.
- If the fake text does not appear, the issue is the UI/session-state layer.
- If fake text works but Gemini/OpenAI output is blank, open the **Debug** expander and inspect the raw provider response.

## Recommended first API test

Start with a small sample:

- 1 handwritten page
- 1 foreign-language page
- 1 page with formulas/tables
- 1 difficult scan

Run only page `1` first to control cost and review quality.


## Model selection

OpenAI and Gemini model fields are predefined dropdowns in the Settings sidebar. You can still override the default selected model by setting `OPENAI_MODEL` or `GEMINI_MODEL` before launching the app.

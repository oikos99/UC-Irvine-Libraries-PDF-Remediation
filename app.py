"""
UC Irvine Libraries PDF Scan Accessibility Remediation Tool

Workflow:
1. Upload PDF
2. Render pages as PNG
3. Send selected page images to OpenAI, Gemini, or Test mode
4. Receive structured JSON
5. Show image + AI text side by side
6. Human edits/corrects
7. Export HTML access copy
8. Export basic PDF with description pages
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Dict

import streamlit as st
from PIL import Image

from ai_analysis import analyze_page
from exports import export_basic_pdf, export_html, export_json
from render_pages import render_pdf_pages
from review_ui import render_review_editor
from schemas import make_empty_record
from utils import get_file_hash, get_work_dir, parse_page_selection


def get_favicon():
    favicon_path = Path(__file__).parent / "assets" / "uci_libraries_favicon.png"
    if favicon_path.exists():
        return Image.open(favicon_path)
    return None


def get_logo_data_url() -> str:
    logo_path = Path(__file__).parent / "assets" / "uci_libraries_logo.jpg"
    if not logo_path.exists():
        return ""
    mime_type = "image/jpeg"
    encoded = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def apply_custom_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --uci-blue: #00386c;
            --uci-blue-hover: #00508f;
            --uci-gold: #f6aa0d;
            --uci-light-blue: #78b9e6;
            --uci-control-border: #d9d9d9;
            --uci-control-text: #111111;
        }

        /* Sidebar shell. */
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] > div {
            background-color: var(--uci-blue) !important;
        }

        /* Plain sidebar text and labels. Do not set backgrounds here. */
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] small,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] .stMarkdown p {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--uci-gold) !important;
        }
        [data-testid="stSidebar"] label {
            font-weight: 600 !important;
        }

        /* Tooltip/help icons beside labels. Keep the icon outline visible without filling the circle. */
        [data-testid="stSidebar"] [data-testid="stTooltipIcon"],
        [data-testid="stSidebar"] [data-testid="stTooltipHoverTarget"],
        [data-testid="stSidebar"] label button[aria-label*="help"],
        [data-testid="stSidebar"] label button[title*="help"] {
            background: transparent !important;
            color: #ffffff !important;
            border: none !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] [data-testid="stTooltipIcon"] svg,
        [data-testid="stSidebar"] [data-testid="stTooltipHoverTarget"] svg,
        [data-testid="stSidebar"] label button[aria-label*="help"] svg,
        [data-testid="stSidebar"] label button[title*="help"] svg {
            color: #ffffff !important;
            fill: none !important;
            stroke: #ffffff !important;
        }
        [data-testid="stSidebar"] [data-testid="stTooltipIcon"] svg *,
        [data-testid="stSidebar"] [data-testid="stTooltipHoverTarget"] svg *,
        [data-testid="stSidebar"] label button[aria-label*="help"] svg *,
        [data-testid="stSidebar"] label button[title*="help"] svg * {
            fill: none !important;
            stroke: #ffffff !important;
        }
        [data-testid="stSidebar"] label button:focus-visible,
        [data-testid="stSidebar"] [data-testid="stTooltipHoverTarget"]:focus-visible {
            outline: 2px solid #ffffff !important;
            outline-offset: 2px !important;
            border-radius: 999px !important;
        }

        /* Dropdowns: white controls with dark text/icons in light and dark mode. */
        [data-testid="stSidebar"] [data-baseweb="select"],
        [data-testid="stSidebar"] [data-baseweb="select"] > div {
            background-color: #ffffff !important;
            border-color: var(--uci-control-border) !important;
            color: var(--uci-control-text) !important;
            border-radius: 14px !important;
            overflow: hidden !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] [role="button"],
        [data-testid="stSidebar"] [data-baseweb="select"] div[aria-haspopup="listbox"],
        [data-testid="stSidebar"] [data-baseweb="select"] div[class*="control"],
        [data-testid="stSidebar"] [data-baseweb="select"] div[class*="ValueContainer"] {
            background-color: #ffffff !important;
            border-radius: 14px !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] span,
        [data-testid="stSidebar"] [data-baseweb="select"] div,
        [data-testid="stSidebar"] [data-baseweb="select"] input {
            color: var(--uci-control-text) !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] svg,
        [data-testid="stSidebar"] [data-baseweb="select"] svg path {
            color: var(--uci-control-text) !important;
            fill: var(--uci-control-text) !important;
            stroke: var(--uci-control-text) !important;
        }

        /* Text/password inputs and textareas. Keep controls white even in dark mode. */
        [data-testid="stSidebar"] [data-baseweb="input"],
        [data-testid="stSidebar"] [data-baseweb="input"] > div,
        [data-testid="stSidebar"] [data-baseweb="base-input"],
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea {
            background-color: #ffffff !important;
            color: var(--uci-control-text) !important;
            border-color: var(--uci-control-border) !important;
            caret-color: var(--uci-control-text) !important;
        }
        [data-testid="stSidebar"] input::placeholder,
        [data-testid="stSidebar"] textarea::placeholder {
            color: #555555 !important;
            opacity: 1 !important;
        }

        /* Password eye icon button: always white button area with dark icon. */
        [data-testid="stSidebar"] [data-baseweb="input"] button,
        [data-testid="stSidebar"] [data-baseweb="input"] [role="button"] {
            background-color: #ffffff !important;
            color: var(--uci-control-text) !important;
            border-left: 1px solid var(--uci-control-border) !important;
        }
        [data-testid="stSidebar"] [data-baseweb="input"] button svg,
        [data-testid="stSidebar"] [data-baseweb="input"] button svg path,
        [data-testid="stSidebar"] [data-baseweb="input"] [role="button"] svg,
        [data-testid="stSidebar"] [data-baseweb="input"] [role="button"] svg path {
            color: var(--uci-control-text) !important;
            fill: var(--uci-control-text) !important;
            stroke: var(--uci-control-text) !important;
        }

        /* Slider: UCI gold. Override Streamlit's default red fill gradient. */
        [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] div[role="slider"] {
            background-color: var(--uci-gold) !important;
            border-color: #ffffff !important;
            box-shadow: 0 0 0 2px #ffffff !important;
        }
        /* Replace Streamlit's default red slider fill gradient with UCI gold. */
        [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] div[style*="linear-gradient"],
        [data-testid="stSidebar"] .stSlider div[style*="height: 0.25rem"],
        [data-testid="stSidebar"] .stSlider div[style*="rgb(255, 75, 75)"],
        [data-testid="stSidebar"] .stSlider div[style*="#ff4b4b"],
        [data-testid="stSidebar"] .stSlider .st-ed {
            background: linear-gradient(to right, var(--uci-gold) 0%, var(--uci-gold) 100%) !important;
            background-color: transparent !important;
            background-image: linear-gradient(to right, var(--uci-gold) 0%, var(--uci-gold) 100%) !important;
        }

        /* Do not add the extra semi-transparent white background on the tick bar. */
        [data-testid="stSidebar"] .stSlider [data-testid="stSliderTickBar"],
        [data-testid="stSidebar"] .stSlider [data-testid="stSliderTickBar"] > div,
        [data-testid="stSidebar"] .stSlider div[data-testid*="TickBar"] {
            background-color: transparent !important;
            background-image: none !important;
        }

        /* Primary action button: UCI blue instead of Streamlit red/light-blue. */
        div.stButton > button[kind="primary"],
        div.stButton > button[data-testid="baseButton-primary"] {
            background-color: var(--uci-blue) !important;
            color: #ffffff !important;
            border: 1px solid var(--uci-blue) !important;
            font-weight: 700 !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div.stButton > button[data-testid="baseButton-primary"]:hover {
            background-color: var(--uci-blue-hover) !important;
            border-color: var(--uci-blue-hover) !important;
            color: #ffffff !important;
        }
        div.stButton > button[kind="primary"]:focus,
        div.stButton > button[data-testid="baseButton-primary"]:focus {
            box-shadow: 0 0 0 0.2rem rgba(120, 185, 230, 0.75) !important;
        }

        .uci-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            width: 100%;
            max-width: 100%;
            margin-bottom: 0.75rem;
        }
        .uci-header img {
            width: clamp(82px, 9vw, 110px);
            height: clamp(82px, 9vw, 110px);
            flex: 0 0 auto;
            object-fit: cover;
            border-radius: 10px;
        }
        .uci-header-text {
            flex: 1 1 auto;
            min-width: 0;
        }
        .uci-header-text h1 {
            margin: 0;
            line-height: 1.08;
            font-size: clamp(1.55rem, 3vw, 2.6rem);
            max-width: 100%;
            display: inline-flex;
            align-items: flex-start;
            gap: 0.45rem;
            flex-wrap: nowrap;
        }
        .uci-header-text .title-lines {
            display: inline-flex;
            flex-direction: column;
            min-width: 0;
        }
        .uci-header-text .line-1,
        .uci-header-text .line-2 {
            display: block;
        }
        .uci-header-text h1 [data-testid="stHeaderActionElements"] {
            display: inline-flex !important;
            align-self: flex-start;
            flex: 0 0 auto;
            margin-top: 0.12em;
            white-space: nowrap;
        }
        .uci-header-text h1 [data-testid="stHeaderActionElements"] a {
            display: inline-flex;
            align-items: center;
            color: currentColor;
        }
        .uci-subtitle {
            margin-top: 0.25rem;
            margin-bottom: 0 !important;
            width: 100%;
            max-width: none;
        }
        .uci-subtitle p {
            margin-bottom: 0 !important;
        }
        [data-testid="stMarkdownContainer"]:has(.uci-header),
        [data-testid="stMarkdownContainer"]:has(.uci-subtitle) {
            margin-bottom: 0 !important;
        }
        @media (max-width: 900px) {
            .uci-header {
                align-items: flex-start;
            }
            .uci-header-text h1 {
                font-size: clamp(1.35rem, 4.8vw, 2rem);
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header() -> None:
    logo_data_url = get_logo_data_url()
    img_html = f'<img src="{logo_data_url}" alt="UC Irvine Libraries logo">' if logo_data_url else ""
    st.markdown(
        f"""
        <div class="uci-header">
            {img_html}
            <div class="uci-header-text">
                <h1><span class="title-lines"><span class="line-1">UC Irvine Libraries</span><span class="line-2">Scanned PDF Accessibility Remediation Tool</span></span></h1>
            </div>
        </div>
        <div class="uci-subtitle">
            This tool supports accessibility remediation for scanned archival PDFs and other image-based documents that are difficult to process through OCR alone. These may include handwritten materials, multilingual text, mathematical formulas, musical notation, poor-quality scans, or other visually complex content. The tool analyzes each PDF page as an image and uses generative AI to provide a detailed page-level description and visible text transcription. It is intended to provide a more useful automated baseline when OCR and full semantic remediation are not feasible.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[str, str, str, str, str, int, str]:
    with st.sidebar:
        st.header("Settings")
        provider = st.selectbox("AI provider", options=["Test mode (no API)", "OpenAI", "Gemini"])

        st.subheader("API keys")
        openai_api_key = st.text_input(
            "OpenAI API key",
            type="password",
            help="Optional if OPENAI_API_KEY is already set in your environment.",
        )
        gemini_api_key = st.text_input(
            "Gemini API key",
            type="password",
            help="Optional if GEMINI_API_KEY is already set in your environment.",
        )

        st.subheader("Models")
        openai_model_options = ["gpt-5.2", "gpt-5.2-mini"]
        default_openai_model = os.environ.get("OPENAI_MODEL", "gpt-5.2")
        if default_openai_model not in openai_model_options:
            openai_model_options.append(default_openai_model)
        openai_model = st.selectbox(
            "OpenAI model",
            options=openai_model_options,
            index=openai_model_options.index(default_openai_model),
        )

        gemini_model_options = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]
        default_gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        if default_gemini_model not in gemini_model_options:
            gemini_model_options.append(default_gemini_model)
        gemini_model = st.selectbox(
            "Gemini model",
            options=gemini_model_options,
            index=gemini_model_options.index(default_gemini_model),
        )

        dpi = st.slider("Render DPI", min_value=120, max_value=300, value=200, step=20)
        custom_instruction = st.text_area(
            "Local prompt instruction",
            value="Prioritize accessibility usefulness. Mark uncertainty clearly. Do not guess names, dates, or words.",
            height=120,
        )

    return provider, openai_api_key, gemini_api_key, openai_model, gemini_model, dpi, custom_instruction


def initialize_state(file_hash: str) -> None:
    if st.session_state.get("file_hash") != file_hash:
        st.session_state["file_hash"] = file_hash
        st.session_state["records"] = {}
        st.session_state["page_meta"] = []
        st.session_state["debug_generation_log"] = []


def ensure_records(records: Dict[int, dict], page_meta: list[dict]) -> Dict[int, dict]:
    for meta in page_meta:
        page_number = meta["page_number"]
        records.setdefault(page_number, make_empty_record(page_number))
    return records


def render_generation_panel(total_pages: int) -> tuple[bool, str]:
    st.subheader("Generate AI drafts")
    page_selection_default = "1" if total_pages == 1 else f"1-{min(total_pages, 3)}"
    page_selection = st.text_input(
        "Pages to analyze now",
        value=page_selection_default,
        help="Examples: 1, 1-3, 1,4,7-9. Start small to control cost and review quality.",
    )

    col_generate, col_note = st.columns([1, 3])
    with col_generate:
        generate = st.button("Generate AI drafts", type="primary")
    with col_note:
        st.write("The app only sends selected page images to the selected AI provider. Human review is still required.")
    return generate, page_selection


def validate_provider_key(provider: str, openai_api_key: str, gemini_api_key: str) -> bool:
    if provider == "Test mode (no API)":
        return True

    if provider == "OpenAI" and (openai_api_key or os.environ.get("OPENAI_API_KEY")):
        return True

    if provider == "Gemini" and (gemini_api_key or os.environ.get("GEMINI_API_KEY")):
        return True

    env_var = "OPENAI_API_KEY" if provider == "OpenAI" else "GEMINI_API_KEY"
    st.error(f"Please provide a {provider} API key in the sidebar or set {env_var} in your environment.")
    return False


def generate_ai_drafts(
    generate: bool,
    page_selection: str,
    total_pages: int,
    page_meta: list[dict],
    records: Dict[int, dict],
    provider: str,
    openai_model: str,
    gemini_model: str,
    openai_api_key: str,
    gemini_api_key: str,
    custom_instruction: str,
) -> Dict[int, dict]:
    if not generate:
        return records

    selected_pages = parse_page_selection(page_selection, total_pages)
    if not selected_pages:
        st.error("No valid pages selected.")
        return records

    if not validate_provider_key(provider, openai_api_key, gemini_api_key):
        return records

    successes = 0
    failures = 0
    progress = st.progress(0)

    for i, page_number in enumerate(selected_pages, start=1):
        meta = page_meta[page_number - 1]
        with st.spinner(f"Analyzing page {page_number} with {provider}..."):
            try:
                result = analyze_page(
                    provider=provider,
                    image_path=meta["image_path"],
                    page_number=page_number,
                    total_pages=total_pages,
                    openai_model=openai_model,
                    gemini_model=gemini_model,
                    openai_api_key=openai_api_key or None,
                    gemini_api_key=gemini_api_key or None,
                    custom_instruction=custom_instruction,
                )

                previous_revision = records.get(page_number, {}).get("_record_revision", 0)
                result["_record_revision"] = previous_revision + 1
                records[page_number] = result
                st.session_state["records"] = records
                st.session_state.setdefault("debug_generation_log", []).append(
                    {
                        "page_number": page_number,
                        "provider": provider,
                        "model": openai_model if provider == "OpenAI" else gemini_model if provider == "Gemini" else "test-mode",
                        "result_keys": sorted(result.keys()),
                        "page_summary_preview": result.get("page_summary", "")[:300],
                        "raw_response_preview": str(result.get("_debug_raw_response", ""))[:1000],
                    }
                )
                successes += 1
            except Exception as exc:
                failures += 1
                st.error(f"Page {page_number} failed: {exc}")

        progress.progress(i / len(selected_pages))

    if successes:
        st.success(f"AI draft generation finished for {successes} page(s).")
    if failures:
        st.warning(f"{failures} page(s) failed. Open the debug panel before spending more API credits.")

    return records


def render_debug_panel(records: Dict[int, dict], provider: str, openai_model: str, gemini_model: str) -> None:
    with st.expander("Debug: inspect generated data before spending more API credits"):
        st.write(
            "Use **Test mode (no API)** first. If fake text populates, the UI is working. "
            "If an API provider fails or stays blank, inspect the log and raw response preview here."
        )
        st.write(
            {
                "selected_provider": provider,
                "openai_model": openai_model,
                "gemini_model": gemini_model,
            }
        )
        st.write("Generation log:")
        st.json(st.session_state.get("debug_generation_log", []))
        st.write("Current records:")
        st.json(records)


def render_export_panel(uploaded_name: str, records: Dict[int, dict], page_meta: list[dict]) -> None:
    st.subheader("Export")
    base_name = Path(uploaded_name).stem
    html_title = f"Description and Visible Text for {uploaded_name}"

    json_bytes = export_json(records)
    html_bytes = export_html(records, page_meta, html_title)
    pdf_access_bytes = export_basic_pdf(records, page_meta)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "Download JSON",
            data=json_bytes,
            file_name=f"{base_name}_access_copy_draft.json",
            mime="application/json",
        )
    with col2:
        st.download_button(
            "Download HTML access copy",
            data=html_bytes,
            file_name=f"{base_name}_access_copy.html",
            mime="text/html",
        )
    with col3:
        st.download_button(
            "Download basic PDF access copy",
            data=pdf_access_bytes,
            file_name=f"{base_name}_basic_access_copy.pdf",
            mime="application/pdf",
        )

    st.warning(
        "Prototype limitation: the exported PDF uses visually styled headings, bookmarks, image pages, and visible text pages. "
        "It is not a fully tagged PDF/UA document with true H1/H2 structure tags. Use the HTML export as the primary accessible access copy for early testing."
    )


def main() -> None:
    st.set_page_config(
        page_title="UC Irvine Libraries Scanned PDF Accessibility Remediation Tool",
        page_icon=get_favicon(),
        layout="wide",
    )
    apply_custom_theme()
    render_page_header()

    provider, openai_api_key, gemini_api_key, openai_model, gemini_model, dpi, custom_instruction = render_sidebar()

    uploaded = st.file_uploader("Upload a scanned PDF", type=["pdf"])
    if not uploaded:
        st.info("Upload a PDF to begin.")
        st.stop()

    pdf_bytes = uploaded.getvalue()
    file_hash = get_file_hash(pdf_bytes)
    work_dir = get_work_dir(file_hash)
    pdf_path = work_dir / uploaded.name
    pdf_path.write_bytes(pdf_bytes)

    initialize_state(file_hash)

    with st.spinner("Rendering PDF pages as PNG images..."):
        page_meta = render_pdf_pages(pdf_bytes, work_dir, dpi=dpi)
        st.session_state["page_meta"] = page_meta

    records: Dict[int, dict] = st.session_state.setdefault("records", {})
    records = ensure_records(records, page_meta)
    total_pages = len(page_meta)

    st.success(f"Rendered {total_pages} page(s).")

    generate, page_selection = render_generation_panel(total_pages)
    records = generate_ai_drafts(
        generate=generate,
        page_selection=page_selection,
        total_pages=total_pages,
        page_meta=page_meta,
        records=records,
        provider=provider,
        openai_model=openai_model,
        gemini_model=gemini_model,
        openai_api_key=openai_api_key,
        gemini_api_key=gemini_api_key,
        custom_instruction=custom_instruction,
    )

    render_debug_panel(records, provider, openai_model, gemini_model)

    records = render_review_editor(records, page_meta, file_hash)
    st.session_state["records"] = records

    render_export_panel(uploaded.name, records, page_meta)


if __name__ == "__main__":
    main()

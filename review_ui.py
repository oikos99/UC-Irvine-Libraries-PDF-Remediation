from __future__ import annotations

from typing import Dict, List

import streamlit as st

from schemas import FIELD_LABELS


def render_review_editor(records: Dict[int, dict], page_meta: List[dict], file_hash: str) -> Dict[int, dict]:
    st.subheader("Review and edit")

    for meta in page_meta:
        page_number = meta["page_number"]
        record = records[page_number]
        revision = record.get("_record_revision", 0)
        key_base = f"{file_hash}_{page_number}_{revision}"

        with st.expander(f"Original page {page_number}", expanded=(page_number == 1)):
            left, right = st.columns([1, 1])
            with left:
                st.image(meta["image_path"], caption=f"Rendered original page {page_number}")
                provider = record.get("ai_provider")
                if provider:
                    st.caption(f"AI provider: {provider}")
            with right:
                record["page_summary"] = st.text_area(
                    FIELD_LABELS["page_summary"],
                    value=record.get("page_summary", ""),
                    key=f"summary_{key_base}",
                    height=100,
                )
                record["short_alt_text"] = st.text_area(
                    FIELD_LABELS["short_alt_text"],
                    value=record.get("short_alt_text", ""),
                    key=f"alt_{key_base}",
                    height=90,
                )
                record["long_description"] = st.text_area(
                    FIELD_LABELS["long_description"],
                    value=record.get("long_description", ""),
                    key=f"desc_{key_base}",
                    height=220,
                )
                record["transcription"] = st.text_area(
                    FIELD_LABELS["transcription"],
                    value=record.get("transcription", ""),
                    key=f"transcription_{key_base}",
                    height=220,
                )
                record["language_detected"] = st.text_input(
                    FIELD_LABELS["language_detected"],
                    value=record.get("language_detected", ""),
                    key=f"language_{key_base}",
                )
                record["math_or_formulas"] = st.text_area(
                    FIELD_LABELS["math_or_formulas"],
                    value=record.get("math_or_formulas", ""),
                    key=f"math_{key_base}",
                    height=90,
                )

        records[page_number] = record

    return records

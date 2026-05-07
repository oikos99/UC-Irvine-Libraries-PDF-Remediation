from __future__ import annotations

from pathlib import Path
from typing import List

import fitz  # PyMuPDF



def render_pdf_pages(pdf_bytes: bytes, output_dir: Path, dpi: int = 200) -> List[dict]:
    """Render each PDF page as a PNG and return page metadata."""
    pages_dir = output_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_meta: List[dict] = []

    for page_index, page in enumerate(doc):
        page_number = page_index + 1
        image_path = pages_dir / f"page_{page_number:04d}.png"

        if not image_path.exists():
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            pix.save(image_path)

        page_meta.append(
            {
                "page_number": page_number,
                "image_path": str(image_path),
                "width": float(page.rect.width),
                "height": float(page.rect.height),
            }
        )

    doc.close()
    return page_meta

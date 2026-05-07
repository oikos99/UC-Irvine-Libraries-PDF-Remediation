from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Dict, List


def get_file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]



def get_work_dir(file_hash: str) -> Path:
    path = Path("prototype_outputs") / file_hash
    path.mkdir(parents=True, exist_ok=True)
    return path



def image_to_data_url(image_path: str) -> str:
    data = Path(image_path).read_bytes()
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:image/png;base64,{encoded}"



def parse_page_selection(selection: str, max_page: int) -> List[int]:
    """Parse strings like '1,3-5,8' into page numbers."""
    selection = selection.strip()
    if not selection:
        return []

    pages = set()
    chunks = [chunk.strip() for chunk in selection.split(",") if chunk.strip()]

    for chunk in chunks:
        if "-" in chunk:
            start_s, end_s = chunk.split("-", 1)
            start, end = int(start_s), int(end_s)
            if start > end:
                start, end = end, start
            pages.update(range(start, end + 1))
        else:
            pages.add(int(chunk))

    return sorted(p for p in pages if 1 <= p <= max_page)



def records_as_sorted_list(records: Dict[int, dict]) -> List[dict]:
    return [records[k] for k in sorted(records.keys())]

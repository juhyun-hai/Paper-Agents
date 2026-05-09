"""
PDF figure & table extraction for HotPaper summaries.

Many academic PDFs render figures as vector graphics, so the embedded-image
list is empty. We instead:

1. Find every "Figure N:" / "Fig. N:" / "Table N:" caption line in the text.
2. For each caption, render the page region *above* the caption as a PNG.
3. Return up to N captioned figures, ordered by figure number.

This robustly captures both raster and vector figures.
"""

from __future__ import annotations
import base64
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import requests


CAPTION_RE = re.compile(
    r"\b(Figure|Fig\.?|Table|Tab\.?)\s*(\d+)\b[\.:\s]",
    re.IGNORECASE,
)
MAX_FIGURES = 5
RENDER_DPI = 150  # ~2x resolution for crisp display
PDF_CACHE = Path(tempfile.gettempdir()) / "hotpaper_pdf_cache"
PDF_CACHE.mkdir(exist_ok=True)


def _download_pdf(arxiv_id: str) -> Optional[Path]:
    target = PDF_CACHE / f"{arxiv_id}.pdf"
    if target.exists() and target.stat().st_size > 1024:
        return target
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    try:
        r = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "HotPaper/1.0 (https://hotpaper.ai)"},
        )
        if r.status_code != 200 or len(r.content) < 1024:
            return None
        target.write_bytes(r.content)
        return target
    except Exception:
        return None


def _find_caption_blocks(page) -> List[Tuple[fitz.Rect, str, str, int]]:
    """Return [(caption_rect, kind, caption_text, fig_num), ...] for each
    Figure/Table caption on the page, found via text-block matching."""
    out = []
    try:
        blocks = page.get_text("dict").get("blocks", [])
    except Exception:
        return out
    for block in blocks:
        if block.get("type", 0) != 0:  # text only
            continue
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", []))
            stripped = text.strip()
            if not stripped:
                continue
            m = CAPTION_RE.match(stripped)
            if not m:
                continue
            kind = "Table" if "Tab" in m.group(1) else "Figure"
            try:
                fig_num = int(m.group(2))
            except (ValueError, IndexError):
                fig_num = 0
            bbox = line.get("bbox") or block.get("bbox")
            if not bbox:
                continue
            rect = fitz.Rect(bbox)
            # Trim very long caption to ~250 chars
            out.append((rect, kind, stripped[:250], fig_num))
    return out


def _render_region(page, rect: fitz.Rect) -> Optional[bytes]:
    """Render the page region `rect` as a PNG."""
    try:
        zoom = RENDER_DPI / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=rect, alpha=False)
        return pix.tobytes("png")
    except Exception:
        return None


def extract_figures(arxiv_id: str, max_figures: int = MAX_FIGURES) -> List[Dict[str, Any]]:
    """Extract up to `max_figures` captioned figures/tables from the arXiv PDF.

    For each caption, render the area above the caption (figure body) on the
    same page. Page boundaries are respected and tables are rendered including
    their caption (since the table body sits *above* the caption already).
    """
    pdf_path = _download_pdf(arxiv_id)
    if pdf_path is None:
        return []

    try:
        doc = fitz.open(str(pdf_path))
    except Exception:
        return []

    candidates: List[Dict[str, Any]] = []
    try:
        for page_num in range(min(20, len(doc))):
            page = doc.load_page(page_num)
            page_rect = page.rect
            captions = _find_caption_blocks(page)
            if not captions:
                continue

            # Sort captions on the page top→bottom so we can compute per-caption
            # body regions that don't overlap.
            captions.sort(key=lambda c: c[0].y0)

            for idx, (cap_rect, kind, cap_text, fig_num) in enumerate(captions):
                # Body region: from previous caption bottom (or page top) to
                # this caption's top. Keep a small margin so text labels stay.
                top = page_rect.y0 + 40
                if idx > 0:
                    prev_bottom = captions[idx - 1][0].y1
                    top = max(top, prev_bottom + 8)
                bottom = cap_rect.y0 - 4
                if bottom - top < 80:  # too small, skip
                    continue
                body_rect = fitz.Rect(
                    page_rect.x0 + 30,
                    top,
                    page_rect.x1 - 30,
                    bottom,
                )

                # For tables the body is typically *above* the caption too in
                # academic PDFs (some venues put captions below tables).
                png = _render_region(page, body_rect)
                if not png or len(png) < 2000:  # tiny — likely blank
                    continue
                b64 = base64.b64encode(png).decode("utf-8")
                candidates.append({
                    "id": f"{kind.lower()}_{fig_num}_p{page_num + 1}",
                    "kind": kind,
                    "number": fig_num,
                    "page": page_num + 1,
                    "caption": cap_text,
                    "data": b64,
                    "mime": "image/png",
                    "byte_size": len(png),
                })
    finally:
        doc.close()

    # Prefer Figure 1 first (most likely the architecture diagram), then by
    # figure/table number ascending.
    def _sort_key(c):
        # Figure first, Table second
        kind_rank = 0 if c["kind"] == "Figure" else 1
        return (kind_rank, c["number"], c["page"])

    candidates.sort(key=_sort_key)

    # Dedup by (kind, number) — sometimes captions repeat in PDF (continued).
    seen, chosen = set(), []
    for c in candidates:
        key = (c["kind"], c["number"])
        if key in seen:
            continue
        seen.add(key)
        chosen.append(c)
        if len(chosen) >= max_figures:
            break

    # Strip helper field from response
    for c in chosen:
        c.pop("byte_size", None)
    return chosen


def get_pdf_full_text(arxiv_id: str, max_chars: int = 20000) -> str:
    """Return the first `max_chars` characters of plain text from the PDF."""
    pdf_path = _download_pdf(arxiv_id)
    if pdf_path is None:
        return ""
    try:
        doc = fitz.open(str(pdf_path))
        out = []
        total = 0
        for page in doc:
            t = page.get_text("text") or ""
            out.append(t)
            total += len(t)
            if total >= max_chars:
                break
        doc.close()
        return ("\n".join(out))[:max_chars]
    except Exception:
        return ""

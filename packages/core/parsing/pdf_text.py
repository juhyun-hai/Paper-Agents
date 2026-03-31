"""
PDF download and text extraction for deep summarization.

No OCR: text-layer only via PyMuPDF (fitz).
"""

import hashlib
import logging
import os
import re
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# Fallback chunk sizes when section splitting fails.
# Sum (3500 + 3500 + 2000 = 9000) matches the default max_chars budget in the
# summarizer so the combined fallback text never exceeds the section cap.
_FALLBACK_HEAD_CHARS = 3500
_FALLBACK_MID_WINDOW = 3500
_FALLBACK_TAIL_CHARS = 2000

# Hard limit on PDF download size (50 MB)
_MAX_PDF_BYTES = 50 * 1024 * 1024

# Regex to detect section header lines:
#   - Optional leading number (e.g. "1." or "2 ")
#   - One of the known section names
#   - Nothing else on the line (trailing whitespace OK)
_HEADER_RE = re.compile(
    r"^\s*(?:\d+\.?\s+)?"
    r"(Abstract|Introduction|Related\s+Work|Background|"
    r"Method(?:ology|s)?|Approach|Model|"
    r"Experiments?|Results?|Discussion|"
    r"Conclusion(?:s)?(?:\s+and\s+Future\s+Work)?|"
    r"Limitation(?:s)?)\s*$",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Sentence extraction constants (used by sentence_candidates and
# extract_evidence_candidates for deep_pdf evidence quality)
# ---------------------------------------------------------------------------

# Splits on sentence-ending punctuation followed by whitespace, and on
# paragraph breaks (two or more consecutive newlines).
_SENT_SEP_RE = re.compile(r"(?<=[.?!])\s+|\n{2,}")

# Patterns that mark a sentence as a high-value table/metric evidence line.
# Includes numeric result indicators and common ML metric names.
_METRIC_LINE_RE = re.compile(
    r"%|±"
    r"|\bTable\b|\bFig(?:ure)?\b"
    r"|\bBLEU\b|\bmAP\b|\bFID\b|\bAUROC\b|\baccuracy\b"
    r"|\btop-1\b|\btop1\b",
    re.IGNORECASE,
)

# Sections mined first when building evidence candidates (highest signal first).
_EVIDENCE_PRIORITY_SECTIONS = (
    "method",
    "experiments",
    "results",
    "conclusion",
    "discussion",
    "limitations",
)

# Sentence length bounds for evidence candidates
_CAND_MIN_LEN = 80
_CAND_MAX_LEN = 350

# Minimum ratio of alphabetic chars to total chars.
# Sentences below this are likely symbol-heavy lines (tables, formulas, etc.)
# that won't read as real sentences.
_CAND_MIN_ALPHA_RATIO = 0.5

# Candidate count limits
_CAND_PRIORITY_MAX = 80   # sentences from priority sections
_CAND_TOTAL_MAX = 120     # including numeric-pattern sentences from all sections

# Maps raw header text (lowercase, collapsed spaces) to canonical key
_CANON: dict[str, str] = {
    "abstract": "abstract",
    "introduction": "introduction",
    "related work": "related_work",
    "background": "background",
    "methodology": "method",
    "methods": "method",
    "method": "method",
    "approach": "method",
    "model": "method",
    "experiment": "experiments",
    "experiments": "experiments",
    "result": "results",
    "results": "results",
    "discussion": "discussion",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "conclusions and future work": "conclusion",
    "limitation": "limitations",
    "limitations": "limitations",
}


def sentence_candidates(text: str) -> list[str]:
    """
    Extract meaningful sentence candidates from *text*.

    Steps:
        1. Split on sentence-ending punctuation followed by whitespace,
           and on paragraph breaks (two or more consecutive newlines).
        2. Normalise internal whitespace (collapse all whitespace runs to
           a single space).
        3. Keep candidates whose character length is in
           [``_CAND_MIN_LEN``, ``_CAND_MAX_LEN``] (80–350 chars).
        4. Drop candidates where fewer than 50 % of characters are
           alphabetic (filters formula-heavy or symbol-only lines).
        5. Deduplicate exact duplicates, preserving first-occurrence order.

    Args:
        text: Raw text string (e.g. one section of a paper).

    Returns:
        List of deduplicated sentence strings, each 80–350 chars.
    """
    seen: set[str] = set()
    result: list[str] = []
    for raw in _SENT_SEP_RE.split(text):
        s = " ".join(raw.split())  # collapse all whitespace
        if not (_CAND_MIN_LEN <= len(s) <= _CAND_MAX_LEN):
            continue
        if sum(c.isalpha() for c in s) / len(s) < _CAND_MIN_ALPHA_RATIO:
            continue
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result


def evidence_candidates(sections: dict[str, str]) -> list[str]:
    """
    Build the evidence_candidates list for the deep_pdf extraction prompt.

    Algorithm:

        Source selection:
            If any of method / experiments / results / conclusion are present,
            mine those in that order (then any remaining sections).
            If none of the priority sections exist, fall back to
            first_chunk / middle_chunk / last_chunk (the positional fallbacks
            produced by extract_sections when header detection fails).

        Two buckets collected in source order:
            metric_lines  — sentences matching a table/metric pattern
                            (Table, Fig, %, ±, BLEU, mAP, FID, AUROC,
                             accuracy, top-1, top1).
            body_sents    — all other qualifying sentences.

        Result:
            metric_lines first, then body_sents; total capped at
            ``_CAND_TOTAL_MAX`` (120).  Prioritising metric lines first
            ensures numeric result sentences are always within the
            ``_MAX_PROMPT_CANDIDATES`` window shown to the model.

    Args:
        sections: Dict of section_name -> section_text from extract_sections().

    Returns:
        List of up to 120 sentence strings, each 80–350 chars with ≥ 50 %
        alphabetic characters.
    """
    _PRIORITY = ("method", "experiments", "results", "conclusion",
                 "discussion", "limitations")
    _FALLBACK_KEYS = ("first_chunk", "middle_chunk", "last_chunk")

    # Determine source key order
    has_priority = any(k in sections for k in _PRIORITY)
    if has_priority:
        source_keys = [k for k in _PRIORITY if k in sections]
        # Append any remaining sections that are not in _PRIORITY
        for k in sections:
            if k not in source_keys:
                source_keys.append(k)
    else:
        # Fall back to positional chunks; if those are also absent use whatever is there
        source_keys = [k for k in _FALLBACK_KEYS if k in sections] or list(sections.keys())

    seen: set[str] = set()
    metric_lines: list[str] = []
    body_sents: list[str] = []

    for key in source_keys:
        for s in sentence_candidates(sections[key]):
            if s in seen:
                continue
            seen.add(s)
            if _METRIC_LINE_RE.search(s):
                metric_lines.append(s)
            else:
                body_sents.append(s)

    combined = metric_lines + body_sents
    return combined[:_CAND_TOTAL_MAX]


# Backward-compatible alias kept for any callers that used the old name.
extract_evidence_candidates = evidence_candidates


def download_pdf(pdf_url: str, cache_dir: str) -> str:
    """
    Download PDF to cache_dir and return the local path.

    Uses a SHA-256 hash of the URL as the filename so that the same paper
    URL always maps to the same cache file (deterministic, avoids special
    characters in filenames).  Returns the cached path immediately if the
    file already exists.

    Args:
        pdf_url:   Full URL of the PDF to download.
        cache_dir: Directory to cache downloaded PDFs.

    Returns:
        Absolute path to the downloaded (or cached) PDF file.

    Raises:
        RuntimeError: If the download fails or the file exceeds the size limit.
    """
    os.makedirs(cache_dir, exist_ok=True)

    url_hash = hashlib.sha256(pdf_url.encode()).hexdigest()[:16]
    local_path = os.path.join(cache_dir, f"{url_hash}.pdf")

    if os.path.exists(local_path):
        logger.debug("PDF cache hit: %s", local_path)
        return local_path

    # Security: Only allow arXiv URLs to prevent SSRF
    parsed = urlparse(pdf_url)
    if not parsed.netloc.endswith('arxiv.org'):
        raise ValueError(f"Invalid PDF URL, only arXiv URLs allowed: {pdf_url}")

    logger.info("Downloading PDF: %s", pdf_url)
    try:
        response = requests.get(pdf_url, timeout=(10, 120), stream=True)
        response.raise_for_status()

        size = 0
        with open(local_path, "wb") as fh:
            for chunk in response.iter_content(chunk_size=65536):
                size += len(chunk)
                if size > _MAX_PDF_BYTES:
                    fh.close()
                    os.unlink(local_path)
                    raise RuntimeError(
                        f"PDF exceeds size limit "
                        f"(>{_MAX_PDF_BYTES // 1024 // 1024} MB): {pdf_url}"
                    )
                fh.write(chunk)

        logger.info("PDF saved: %s (%.1f KB)", local_path, size / 1024)
        return local_path

    except requests.exceptions.RequestException as exc:
        if os.path.exists(local_path):
            os.unlink(local_path)
        raise RuntimeError(f"PDF download failed for {pdf_url}: {exc}") from exc


def extract_text_pymupdf(local_path: str) -> str:
    """
    Extract full text from a PDF using PyMuPDF (fitz).

    Text-layer only — no OCR.  Pages with no extractable text are skipped.

    Args:
        local_path: Path to the local PDF file.

    Returns:
        Full extracted text string (may be empty for image-only PDFs).

    Raises:
        RuntimeError: If PyMuPDF is not installed or extraction fails.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError(
            "PyMuPDF not installed. Run: pip install pymupdf"
        )

    try:
        doc = fitz.open(local_path)
        pages: list[str] = []
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages.append(text)
        doc.close()

        full_text = "\n".join(pages)
        logger.debug(
            "Extracted %d chars across %d pages: %s",
            len(full_text),
            len(pages),
            local_path,
        )
        return full_text

    except Exception as exc:
        raise RuntimeError(
            f"PDF text extraction failed for {local_path}: {exc}"
        ) from exc


def extract_sections(full_text: str) -> dict[str, str]:
    """
    Split full_text into named sections using regex-based header detection.

    Recognises headers for: abstract, introduction, related work, background,
    method/methodology/approach/model, experiments, results, discussion,
    conclusion, limitations.

    Falls back to three positional chunks when fewer than two sections are
    detected (e.g. single-section or unrecognised layout):
        - ``first_chunk``  – start of the document
        - ``middle_chunk`` – region around the first "experiment" occurrence
        - ``last_chunk``   – end of the document

    Args:
        full_text: Full text extracted from the PDF.

    Returns:
        Dict mapping section name -> section text.
    """
    sections = _try_section_split(full_text)
    if len(sections) >= 2:
        return sections

    logger.debug("Section split yielded < 2 sections; using fallback chunks")
    return _fallback_chunks(full_text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _try_section_split(text: str) -> dict[str, str]:
    """Attempt regex-based section splitting; return dict of name -> text."""
    sections: dict[str, str] = {}
    current_name: Optional[str] = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        m = _HEADER_RE.match(line)
        if m:
            # Flush previous section
            if current_name and current_lines:
                sections[current_name] = "\n".join(current_lines).strip()
            raw = re.sub(r"\s+", " ", m.group(1).strip().lower())
            current_name = _CANON.get(raw, raw.replace(" ", "_"))
            current_lines = []
        else:
            if current_name is not None:
                current_lines.append(line)

    # Flush the last section
    if current_name and current_lines:
        sections[current_name] = "\n".join(current_lines).strip()

    return sections


def _fallback_chunks(text: str) -> dict[str, str]:
    """Return three position-based chunks when section splitting fails."""
    n = len(text)

    first = text[:_FALLBACK_HEAD_CHARS].strip()

    # Centre the middle chunk around the first "experiment" occurrence
    exp_pos = text.lower().find("experiment")
    if exp_pos == -1:
        mid_start = max(0, n // 2 - _FALLBACK_MID_WINDOW // 2)
    else:
        mid_start = max(0, exp_pos - 200)
    middle = text[mid_start : mid_start + _FALLBACK_MID_WINDOW].strip()

    last = text[max(0, n - _FALLBACK_TAIL_CHARS) :].strip()

    return {
        "first_chunk": first,
        "middle_chunk": middle,
        "last_chunk": last,
    }

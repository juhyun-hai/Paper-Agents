"""
HAI Lab (Hyperautonomy AI Lab, Seoul National University) configuration.

Used to:
- Score daily featured papers (keyword matching boost).
- Auto-tag papers authored by HAI Lab members.
- Power the "HAI Lab Picks" section on the site.
"""

from __future__ import annotations
from typing import List, Set
import re
import unicodedata


# ---------------------------------------------------------------------------
# Lab members (extend this list as needed)
# ---------------------------------------------------------------------------
HAI_LAB_MEMBERS: List[str] = [
    # Director
    "Byeng D. Youn",
    "Byeng Youn",
    "B. D. Youn",
]


# ---------------------------------------------------------------------------
# Lab research interest keywords (broad: manufacturing AI + LLM/Agent)
# ---------------------------------------------------------------------------
HAI_KEYWORDS: List[str] = [
    # Manufacturing / Industrial AI (per hai.snu.ac.kr)
    "manufacturing", "industrial ai", "smart factory",
    "physics-informed", "physics informed",
    "fault diagnosis", "anomaly detection",
    "remaining useful life", "rul prediction",
    "battery", "semiconductor reliability",
    "digital twin", "predictive maintenance",
    "condition monitoring", "prognostics",

    # Robotics / Embodied AI
    "embodied ai", "robotics", "quadruped",
    "manipulation", "navigation",
    "sim-to-real", "robot learning",

    # Foundation models / LLM / Agents
    "foundation model", "large language model", "llm",
    "agent", "agentic", "multi-agent",
    "reasoning", "chain-of-thought", "tool use",
    "rag", "retrieval-augmented",
    "alignment", "rlhf",

    # Multimodal / Vision-language
    "vision-language", "vlm", "multimodal",
    "image understanding", "video understanding",

    # Generative / Diffusion
    "diffusion model", "generative model", "text-to-image",
    "video generation", "world model",
]


# ---------------------------------------------------------------------------
# Matching utilities
# ---------------------------------------------------------------------------
def _normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


_MEMBER_SET: Set[str] = {_normalize(name) for name in HAI_LAB_MEMBERS}


def is_hai_author(authors) -> bool:
    """Check whether any author name matches a HAI Lab member."""
    if not authors:
        return False
    if isinstance(authors, str):
        authors = [authors]
    for raw in authors:
        if not raw:
            continue
        n = _normalize(raw)
        if n in _MEMBER_SET:
            return True
        # Fallback: substring match for cases with extra middle names.
        for member in _MEMBER_SET:
            if member in n or n in member:
                return True
    return False


def hai_keyword_score(title: str, abstract: str) -> int:
    """Count how many HAI keywords appear in title + abstract.

    Returns the number of distinct matched keywords. Title matches are weighted
    by adding a small boost (each title hit counts as 2).
    """
    if not title and not abstract:
        return 0
    blob_title = _normalize(title or "")
    blob_abs = _normalize(abstract or "")
    score = 0
    seen = set()
    for kw in HAI_KEYWORDS:
        k = _normalize(kw)
        if k in seen:
            continue
        if re.search(r"\b" + re.escape(k) + r"\b", blob_title):
            score += 2
            seen.add(k)
        elif re.search(r"\b" + re.escape(k) + r"\b", blob_abs):
            score += 1
            seen.add(k)
    return score


# ---------------------------------------------------------------------------
# Lab metadata for frontend display
# ---------------------------------------------------------------------------
HAI_LAB_INFO = {
    "name": "Hyperautonomy AI Lab",
    "short_name": "HAI Lab",
    "institution": "Seoul National University",
    "website": "https://hai.snu.ac.kr/",
    "director": "Prof. Byeng D. Youn",
    "tagline": "Intelligent Metrology · System Modeling · Decision Making",
    "description": (
        "We research AI-driven autonomous systems spanning manufacturing AI, "
        "physics-informed machine learning, embodied robotics, and foundation "
        "models. HotPaper.ai is curated by HAI Lab to surface the most "
        "impactful papers each day."
    ),
}

"""
HAI Lab (Hyperautonomy AI Lab, Seoul National University) configuration.

NOTE: This file is the *plugin copy* of ``backend.app.core.hai_config`` and is
the canonical location going forward. The original module is intentionally
left in place for backward compatibility (daily_cron, retag scripts, trending
routes). When the legacy import sites are migrated, ``core/hai_config.py`` can
become a thin re-export shim that does ``from backend.app.plugins.hai.config
import *``.

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
    # Industrial Foundation Models & Physical AI (lab strategic direction).
    # Multi-word terms only — single-word "llm"/"vlm" matched too many generic
    # arXiv papers and flooded HAI Picks.
    "industrial foundation model", "manufacturing foundation model",
    "industrial physical ai", "physical ai",
    "embodied ai", "world model",
    "foundation model for manufacturing", "foundation model for industrial",

    # Manufacturing / Industrial AI (HAI Lab core focus)
    "manufacturing", "manufacturing ai", "industrial ai", "industrial",
    "smart factory", "smart manufacturing",
    "physics-informed", "physics informed", "physics-based",
    "physics-informed neural", "pinn",
    "fault diagnosis", "fault detection", "fault prediction",
    "anomaly detection",
    "remaining useful life", "rul",
    "prognostics", "phm", "prognostics and health management",
    "predictive maintenance", "condition monitoring",
    "digital twin", "digital twins",

    # Signal processing
    "signal processing", "vibration", "spectral",
    "wavelet", "frequency domain", "time-frequency",

    # Specific hardware / process / domains
    "battery", "lithium-ion", "battery degradation",
    "semiconductor", "wafer", "lithography", "cmp",
    "bearing", "rotating machinery",
    "additive manufacturing", "3d printing",
    "structural health monitoring", "shm",

    # Reliability & robustness for engineering systems
    "reliability", "uncertainty quantification", "surrogate model",
    "engineering design", "design optimization",
    "model-based", "scientific machine learning",

    # Embodied / robotics for industrial use
    "industrial robot", "quadruped", "manipulation",
    "robot learning", "sim-to-real",
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
# Topic classification — group HAI papers into broader research themes for
# filtering on the /hai page.
# ---------------------------------------------------------------------------
HAI_TOPICS = {
    "foundation-models": [
        "industrial foundation model", "manufacturing foundation model",
        "foundation model for manufacturing", "foundation model for industrial",
    ],
    "physical-ai": [
        "physical ai", "industrial physical ai",
        "embodied ai", "world model", "sim-to-real", "robot learning",
    ],
    "physics-informed": [
        "physics-informed", "physics informed", "physics-based",
        "pinn", "scientific machine learning",
    ],
    "fault-diagnosis": [
        "fault diagnosis", "fault detection", "fault prediction",
        "anomaly detection", "condition monitoring",
    ],
    "rul-phm": [
        "remaining useful life", "rul", "prognostics", "phm",
        "predictive maintenance",
    ],
    "signal-processing": [
        "signal processing", "vibration", "spectral",
        "wavelet", "frequency domain", "time-frequency",
    ],
    "digital-twin": [
        "digital twin", "digital twins",
    ],
    "battery": [
        "battery", "lithium-ion", "battery degradation",
    ],
    "semiconductor": [
        "semiconductor", "wafer", "lithography", "cmp",
    ],
    "manufacturing": [
        "manufacturing", "manufacturing ai", "smart factory",
        "smart manufacturing", "additive manufacturing", "3d printing",
    ],
    "robotics": [
        "industrial robot", "quadruped", "manipulation",
    ],
    "reliability": [
        "reliability", "uncertainty quantification", "surrogate model",
        "structural health monitoring", "shm", "bearing",
        "rotating machinery",
    ],
}

TOPIC_DISPLAY = {
    "foundation-models": "Foundation Models",
    "physical-ai": "Physical AI",
    "physics-informed": "Physics-Informed ML",
    "fault-diagnosis": "Fault Diagnosis",
    "rul-phm": "RUL / Prognostics",
    "signal-processing": "Signal Processing",
    "digital-twin": "Digital Twin",
    "battery": "Battery",
    "semiconductor": "Semiconductor",
    "manufacturing": "Manufacturing AI",
    "robotics": "Industrial Robotics",
    "reliability": "Reliability / SHM",
}


def hai_topic(title: str, abstract: str) -> str:
    """Pick the best-matching HAI topic for a paper. Returns topic key or
    "other"."""
    blob = _normalize((title or "") + " " + (abstract or ""))
    best, best_score = None, 0
    for topic, keys in HAI_TOPICS.items():
        s = 0
        for k in keys:
            if re.search(r"\b" + re.escape(_normalize(k)) + r"\b", blob):
                s += 1
        if s > best_score:
            best, best_score = topic, s
    return best or "other"


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

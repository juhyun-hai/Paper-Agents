"""
Light summarization with backend routing.

Supports multiple backends:
- dummy: Simple heuristics (no LLM)
- vllm: vLLM via OpenAI-compatible API

Backend is selected via SUMMARY_BACKEND environment variable or CLI override.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def summarize_light(
    title: str,
    abstract: str,
    categories: List[str],
    backend: Optional[str] = None,
) -> tuple[Dict[str, Any], str, Optional[int]]:
    """
    Generate a light summary using the specified backend.

    Args:
        title: Paper title
        abstract: Paper abstract
        categories: List of arXiv categories
        backend: Backend to use ("dummy" or "vllm"). If None, uses SUMMARY_BACKEND env var.

    Returns:
        Tuple of (summary_dict, model_used, tokens_used)
        - summary_dict: Summary dictionary matching CLAUDE.md schema
        - model_used: Model identifier (e.g., "dummy" or model name)
        - tokens_used: Token count (None for dummy backend)

    Raises:
        ValueError: If backend is invalid
        RuntimeError: If vLLM backend fails
    """
    # Determine backend
    if backend is None:
        backend = os.getenv("SUMMARY_BACKEND", "dummy")

    backend = backend.lower()

    if backend == "dummy":
        summary = _summarize_light_dummy(title, abstract, categories)
        return summary, "dummy", None

    elif backend == "vllm":
        # Import here to avoid dependency if not using vllm
        from packages.core.summarizers.light_vllm import (
            summarize_light_vllm,
            get_vllm_config,
            get_token_count_estimate,
        )

        summary = summarize_light_vllm(title, abstract, categories)
        _, model_name = get_vllm_config()

        # Estimate tokens
        tokens = get_token_count_estimate(str(summary))

        return summary, model_name, tokens

    else:
        raise ValueError(
            f"Invalid backend: {backend}. Must be 'dummy' or 'vllm'."
        )


def _summarize_light_dummy(
    title: str, abstract: str, categories: List[str]
) -> Dict[str, Any]:
    """
    Generate a light summary using simple heuristics (dummy backend).

    No LLM is used. This is a fallback implementation.

    Args:
        title: Paper title
        abstract: Paper abstract
        categories: List of arXiv categories

    Returns:
        Summary dictionary matching CLAUDE.md schema
    """
    # Split abstract into sentences
    sentences = _split_sentences(abstract)

    # Extract one-liner (first sentence, truncated)
    one_liner = _extract_one_liner(sentences)

    # Extract problem statement (look for problem-related keywords)
    problem = _extract_problem(sentences)

    # Extract method (look for method-related keywords)
    method = _extract_method(sentences)

    # Extract keywords from title and categories
    keywords = _extract_keywords(title, categories)

    # Build summary matching schema
    summary = {
        "one_liner": one_liner,
        "problem": problem,
        "method": method,
        "model_info": {
            "backbone": "unknown",
            "foundation_model": "unknown",
            "parameters": "unknown",
            "training_objective": "unknown",
        },
        "datasets": [],
        "metrics": [],
        "results": [],
        "compute": {
            "gpus": "unknown",
            "steps": "unknown",
            "batch_size": "unknown",
            "training_time": "unknown",
        },
        "limitations": "unknown",
        "keywords": keywords,
        "relevance_tags": categories,
    }

    return summary


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences (simple heuristic)."""
    # Simple sentence splitting (not perfect, but good enough for Phase 1)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _extract_one_liner(sentences: List[str]) -> str:
    """Extract a one-line summary (first sentence, truncated)."""
    if not sentences:
        return "unknown"

    first = sentences[0]

    # Truncate to ~150 characters at word boundary
    if len(first) > 150:
        first = first[:147].rsplit(" ", 1)[0] + "..."

    return first


def _extract_problem(sentences: List[str]) -> str:
    """Extract problem statement using keyword heuristics."""
    if not sentences:
        return "unknown"

    # Look for sentences mentioning problem-related keywords
    problem_keywords = [
        "problem",
        "challenge",
        "issue",
        "limitation",
        "difficult",
        "gap",
        "lack",
        "bottleneck",
    ]

    for sentence in sentences:
        lower = sentence.lower()
        if any(kw in lower for kw in problem_keywords):
            return sentence

    # Fallback: use first sentence
    return sentences[0] if sentences else "unknown"


def _extract_method(sentences: List[str]) -> str:
    """Extract method description using keyword heuristics."""
    if not sentences:
        return "unknown"

    # Look for sentences mentioning method-related keywords
    method_keywords = [
        "propose",
        "introduce",
        "present",
        "develop",
        "method",
        "approach",
        "technique",
        "algorithm",
        "model",
        "framework",
    ]

    for sentence in sentences:
        lower = sentence.lower()
        if any(kw in lower for kw in method_keywords):
            return sentence

    # Fallback: use second sentence if available, else first
    if len(sentences) > 1:
        return sentences[1]
    elif sentences:
        return sentences[0]
    else:
        return "unknown"


def _extract_keywords(title: str, categories: List[str]) -> List[str]:
    """Extract keywords from title and categories."""
    keywords = []

    # Add category terms (e.g., "cs.LG" -> "machine learning")
    category_map = {
        "cs.LG": "machine learning",
        "cs.CV": "computer vision",
        "cs.CL": "natural language processing",
        "cs.AI": "artificial intelligence",
        "stat.ML": "statistical machine learning",
        "cs.RO": "robotics",
        "cs.NE": "neural networks",
    }

    for cat in categories:
        if cat in category_map:
            keywords.append(category_map[cat])

    # Extract significant words from title (simple approach)
    # Remove common words and keep capitalized or long words
    title_words = title.split()
    stopwords = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
    }

    for word in title_words:
        # Clean word (remove punctuation)
        clean = re.sub(r"[^\w\s-]", "", word.lower())

        # Add if not stopword and length > 4
        if clean and clean not in stopwords and len(clean) > 4:
            if clean not in keywords:
                keywords.append(clean)

    # Limit to 10 keywords
    return keywords[:10]


def validate_summary(summary: Dict[str, Any]) -> bool:
    """
    Validate that summary matches required schema.

    Args:
        summary: Summary dictionary

    Returns:
        True if valid, False otherwise

    Raises:
        ValueError: If validation fails with details
    """
    required_fields = ["one_liner", "problem", "method", "keywords"]

    # Check required top-level fields
    for field in required_fields:
        if field not in summary:
            raise ValueError(f"Missing required field: {field}")

    # Check model_info structure
    if "model_info" not in summary:
        raise ValueError("Missing required field: model_info")

    model_info_fields = [
        "backbone",
        "foundation_model",
        "parameters",
        "training_objective",
    ]
    for field in model_info_fields:
        if field not in summary["model_info"]:
            raise ValueError(f"Missing required field in model_info: {field}")

    # Check compute structure
    if "compute" not in summary:
        raise ValueError("Missing required field: compute")

    compute_fields = ["gpus", "steps", "batch_size", "training_time"]
    for field in compute_fields:
        if field not in summary["compute"]:
            raise ValueError(f"Missing required field in compute: {field}")

    # Check array fields exist
    array_fields = ["datasets", "metrics", "results", "relevance_tags"]
    for field in array_fields:
        if field not in summary:
            raise ValueError(f"Missing required field: {field}")
        if not isinstance(summary[field], list):
            raise ValueError(f"Field must be a list: {field}")

    return True

"""
Embedding utilities for paper recommendation.

Builds rich index text from paper metadata + summaries and wraps
SentenceTransformer to produce L2-normalised float32 vectors suitable
for cosine similarity via FAISS IndexFlatIP.
"""

import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "BAAI/bge-m3"
_DEFAULT_HF_CACHE = "data/cache/hf"


def build_index_text(
    pv_row: dict,
    summaries: dict[str, dict],
) -> str:
    """
    Build a rich text representation for embedding a paper version.

    Always includes title + abstract.  Enriches with structured fields
    from the best available summary (deep_pdf > deep > light):
        one_liner, problem, method, keywords (joined), datasets, metrics, results.

    Args:
        pv_row:    Row dict from paper_versions (must have 'title', 'abstract').
        summaries: Dict keyed by summary_type -> summary_data dict.

    Returns:
        A single string suitable for embedding.
    """
    parts: list[str] = []

    title = pv_row.get("title", "").strip()
    abstract = pv_row.get("abstract", "").strip()
    if title:
        parts.append(title)
    if abstract:
        parts.append(abstract)

    # Best available summary: prefer deep_pdf, then deep, then light
    summary: dict | None = (
        summaries.get("deep_pdf")
        or summaries.get("deep")
        or summaries.get("light")
    )

    if summary:
        for field in ("one_liner", "problem", "method"):
            val = summary.get(field, "")
            if val and val != "unknown":
                parts.append(val)

        kws = summary.get("keywords", [])
        if isinstance(kws, list) and kws:
            parts.append(" ".join(kws))

        # Factual enrichment from deep_pdf fields
        for ds in summary.get("datasets", []):
            name = ds.get("name", "")
            task = ds.get("task", "")
            if name and name != "unknown":
                parts.append(f"dataset: {name} {task}".strip())

        for metric in summary.get("metrics", []):
            if isinstance(metric, str) and metric != "unknown":
                parts.append(f"metric: {metric}")

        for r in summary.get("results", []):
            metric = r.get("metric", "")
            value = r.get("value", "")
            setting = r.get("setting", "")
            if metric and value and metric != "unknown":
                parts.append(f"{metric} {value} {setting}".strip())

    return "\n".join(parts)


def _suppress_hf_progress() -> None:
    """Best-effort suppression of HuggingFace download/load progress bars."""
    # huggingface_hub >= 0.14
    try:
        from huggingface_hub.utils import disable_progress_bars
        disable_progress_bars()
    except Exception:
        pass

    # transformers verbosity
    try:
        import transformers
        transformers.logging.set_verbosity_error()
    except Exception:
        pass

    # sentence_transformers internal logger
    try:
        logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
    except Exception:
        pass


def get_embedder(model_name: str = _DEFAULT_MODEL, cache_dir: str | None = None):
    """
    Load a SentenceTransformer model with a stable local cache.

    The cache directory is resolved in priority order:
        1. ``cache_dir`` argument
        2. ``HF_HOME`` environment variable
        3. ``data/cache/hf`` (project default)

    Progress bars from HuggingFace / transformers are suppressed before
    loading so that repeated invocations produce clean output.

    Args:
        model_name: HuggingFace model identifier (default: BAAI/bge-m3).
        cache_dir:  Override cache directory (optional).

    Returns:
        SentenceTransformer instance.

    Raises:
        RuntimeError: If sentence-transformers is not installed.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise RuntimeError(
            "sentence-transformers not installed. "
            "Run: pip install sentence-transformers"
        )

    resolved_cache = cache_dir or os.getenv("HF_HOME", _DEFAULT_HF_CACHE)
    os.makedirs(resolved_cache, exist_ok=True)

    _suppress_hf_progress()

    logger.info("Loading embedding model: %s (cache: %s)", model_name, resolved_cache)
    model = SentenceTransformer(model_name, cache_folder=resolved_cache)
    logger.info("Model loaded.")
    return model


def embed_texts(
    model,
    texts: list[str],
    batch_size: int = 32,
    show_progress: bool = False,
) -> np.ndarray:
    """
    Embed a list of texts and return L2-normalised float32 vectors.

    Using L2-normalised vectors with IndexFlatIP gives cosine similarity
    because inner-product on unit vectors equals cosine similarity.

    Args:
        model:         SentenceTransformer instance.
        texts:         List of strings to embed.
        batch_size:    Encoding batch size (default 32).
        show_progress: Show tqdm progress bar.

    Returns:
        numpy.ndarray of shape (len(texts), dim), dtype float32, L2-normalised.
    """
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return vectors.astype(np.float32)

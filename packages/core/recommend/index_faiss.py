"""
FAISS index management for paper similarity search.

Uses IndexFlatIP (inner product) with L2-normalised vectors — equivalent to
cosine similarity.  The companion id list maps FAISS integer positions to
database paper_version ids.
"""

import json
import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_INDEX_DIR = "data/index"
_INDEX_FILENAME = "papers.faiss"
_IDS_FILENAME = "papers_ids.json"


def build_faiss_index(vectors: np.ndarray):
    """
    Build a FAISS IndexFlatIP from pre-normalised float32 vectors.

    Args:
        vectors: (n, dim) float32 array, L2-normalised.

    Returns:
        faiss.IndexFlatIP populated with all vectors.

    Raises:
        RuntimeError: If faiss-cpu is not installed.
    """
    try:
        import faiss
    except ImportError:
        raise RuntimeError(
            "faiss-cpu not installed. Run: pip install faiss-cpu"
        )

    assert vectors.ndim == 2, "vectors must be 2-D"
    assert vectors.dtype == np.float32, "vectors must be float32"

    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    logger.info("Built IndexFlatIP: %d vectors, dim=%d", index.ntotal, dim)
    return index


def save_index(
    index,
    ids: list[int],
    index_dir: str = _DEFAULT_INDEX_DIR,
) -> None:
    """
    Save FAISS index and companion id list to disk.

    Args:
        index:     FAISS index populated with vectors.
        ids:       List of paper_version ids (one per vector, same order).
        index_dir: Directory to write files into.
    """
    import faiss

    os.makedirs(index_dir, exist_ok=True)
    index_path = os.path.join(index_dir, _INDEX_FILENAME)
    ids_path = os.path.join(index_dir, _IDS_FILENAME)

    faiss.write_index(index, index_path)
    with open(ids_path, "w") as f:
        json.dump(ids, f)

    logger.info("Saved FAISS index to %s (%d vectors)", index_path, index.ntotal)
    logger.info("Saved id list to %s", ids_path)


def load_index(
    index_dir: str = _DEFAULT_INDEX_DIR,
) -> tuple:
    """
    Load FAISS index and companion id list from disk.

    Args:
        index_dir: Directory containing the index files.

    Returns:
        (faiss.Index, list[int]) — index and paper_version ids.

    Raises:
        FileNotFoundError: If index files are not found.
    """
    import faiss

    index_path = os.path.join(index_dir, _INDEX_FILENAME)
    ids_path = os.path.join(index_dir, _IDS_FILENAME)

    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"FAISS index not found: {index_path}. "
            "Run scripts/build_embeddings.py first."
        )
    if not os.path.exists(ids_path):
        raise FileNotFoundError(
            f"ID list not found: {ids_path}. "
            "Run scripts/build_embeddings.py first."
        )

    index = faiss.read_index(index_path)
    with open(ids_path) as f:
        ids = json.load(f)

    logger.info("Loaded index from %s (%d vectors)", index_path, index.ntotal)
    return index, ids


def query_index(
    index,
    ids: list[int],
    query_vec: np.ndarray,
    topk: int = 10,
) -> list[tuple[int, float]]:
    """
    Query the FAISS index and return top-k paper_version ids with scores.

    Args:
        index:     FAISS index.
        ids:       Paper_version id list corresponding to index positions.
        query_vec: (1, dim) float32 L2-normalised query vector.
        topk:      Number of results to return.

    Returns:
        List of (paper_version_id, cosine_score) sorted by score descending.
    """
    assert query_vec.ndim == 2 and query_vec.shape[0] == 1, (
        "query_vec must have shape (1, dim)"
    )

    k = min(topk, index.ntotal)
    scores, positions = index.search(query_vec, k)

    results = []
    for pos, score in zip(positions[0], scores[0]):
        if pos < 0:  # FAISS pads with -1 when ntotal < k
            continue
        results.append((ids[pos], float(score)))

    return results

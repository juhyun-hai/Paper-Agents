"""
Priority scoring for deep_pdf candidate selection and recommendation re-ranking.

Three scoring components:
  recency    = exp(-days_since_publication / 7)
  centrality = mean cosine similarity to the top-N most recently indexed papers
  trending   = 1.0 if paper intersects today's top-K trending keywords, else 0.0

Deep_pdf candidate priority (select_deep_pdf_candidates.py):
  0.5 * recency + 0.3 * centrality + 0.2 * trending

Recommendation re-score (recommend.py):
  0.7 * embedding_similarity + 0.2 * recency + 0.1 * trending
"""

import logging
import math
from datetime import date, datetime
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Source weights consistent with show_trending.py
_TRENDING_SOURCE_WEIGHTS = {"llm": 3, "title": 2, "abstract": 1}


# ---------------------------------------------------------------------------
# Recency
# ---------------------------------------------------------------------------


def compute_recency_score(published_date) -> float:
    """
    Exponential decay based on days since publication.

        score = exp(-days_since / 7)

    A paper published today scores ~1.0; one published 7 days ago ~0.37;
    30 days ago ~0.013.

    Args:
        published_date: datetime.datetime (tz-aware or naive) or datetime.date.
                        Returns 0.0 for None or unrecognised types.
    """
    if published_date is None:
        return 0.0

    today = date.today()

    if isinstance(published_date, datetime):
        pub_date = published_date.date()
    elif isinstance(published_date, date):
        pub_date = published_date
    else:
        return 0.0

    days_since = max(0, (today - pub_date).days)
    return math.exp(-days_since / 7.0)


# ---------------------------------------------------------------------------
# Trending
# ---------------------------------------------------------------------------


def get_top_trending_keywords(conn, day: date, n: int = 20) -> set[str]:
    """
    Return the top-n keywords for *day* from keyword_stats, weighted by source.

    Weights: llm=3, title=2, abstract=1 (consistent with show_trending.py).
    Returns an empty set on failure or if the table has no rows for *day*.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT keyword,
                       SUM(count * CASE source
                               WHEN 'llm'   THEN 3
                               WHEN 'title' THEN 2
                               ELSE 1
                           END) AS weighted_count
                FROM keyword_stats
                WHERE day = %s
                GROUP BY keyword
                ORDER BY weighted_count DESC
                LIMIT %s
                """,
                (day, n),
            )
            rows = cur.fetchall()
        return {r["keyword"].lower() for r in rows}
    except Exception as exc:
        logger.warning("Could not fetch trending keywords: %s", exc)
        return set()


def compute_trending_boost(
    title: str,
    keywords: list[str],
    trending_kws: set[str],
) -> float:
    """
    Return 1.0 if the paper intersects today's trending keywords, else 0.0.

    Matching:
      - Any trending keyword appears as a *substring* of ``title.lower()``.
      - Any element of ``keywords`` (lowercased) is in ``trending_kws``.

    Args:
        title:        Paper title.
        keywords:     LLM-extracted or manual keyword list.
        trending_kws: Lowercase trending keyword set for the target day.
    """
    if not trending_kws:
        return 0.0

    title_lower = title.lower()
    kw_set = {k.lower() for k in keywords if isinstance(k, str)}

    for kw in trending_kws:
        if kw in title_lower or kw in kw_set:
            return 1.0

    return 0.0


# ---------------------------------------------------------------------------
# Embedding centrality
# ---------------------------------------------------------------------------


def build_id_to_pos(ids: list[int]) -> dict[int, int]:
    """Return a version_id → FAISS-position lookup built from the id list."""
    return {vid: i for i, vid in enumerate(ids)}


def load_recent_reference_vectors(
    conn,
    index,
    id_to_pos: dict[int, int],
    n: int = 20,
) -> Optional[np.ndarray]:
    """
    Retrieve embedding vectors for the n most recently published papers in the
    FAISS index.

    Queries paper_versions for the n most recent rows whose ids appear in
    id_to_pos, then reconstructs their vectors via ``index.reconstruct()``.

    Args:
        conn:       Active psycopg connection.
        index:      Loaded FAISS index (must support reconstruct).
        id_to_pos:  Mapping from version_id to FAISS position.
        n:          Number of recent reference papers.

    Returns:
        (n, dim) float32 array, or None if no indexed papers are available.
    """
    indexed_ids = list(id_to_pos.keys())
    if not indexed_ids:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM paper_versions
                WHERE id = ANY(%s)
                ORDER BY version_published_date DESC
                LIMIT %s
                """,
                (indexed_ids, n),
            )
            recent_ids = [row["id"] for row in cur.fetchall()]
    except Exception as exc:
        logger.warning("Could not fetch recent reference ids: %s", exc)
        return None

    if not recent_ids:
        return None

    dim = index.d
    vecs = np.empty((len(recent_ids), dim), dtype=np.float32)
    for i, vid in enumerate(recent_ids):
        index.reconstruct(id_to_pos[vid], vecs[i])

    logger.debug("Loaded %d reference vectors (dim=%d)", len(recent_ids), dim)
    return vecs


def compute_embedding_centrality(
    version_id: int,
    index,
    id_to_pos: dict[int, int],
    reference_vecs: np.ndarray,
) -> float:
    """
    Average cosine similarity between a candidate paper and the reference set.

    Since all vectors are L2-normalised, dot product equals cosine similarity.
    Returns 0.0 if the paper is not yet in the FAISS index.

    Args:
        version_id:     paper_versions.id to score.
        index:          Loaded FAISS index.
        id_to_pos:      version_id → FAISS position mapping.
        reference_vecs: (n_ref, dim) float32 reference matrix.

    Returns:
        float in [0.0, 1.0].
    """
    pos = id_to_pos.get(version_id)
    if pos is None:
        return 0.0

    vec = np.empty(index.d, dtype=np.float32)
    index.reconstruct(pos, vec)              # (dim,)
    sims = reference_vecs @ vec              # (n_ref,) cosine sims
    return float(np.clip(sims.mean(), 0.0, 1.0))


# ---------------------------------------------------------------------------
# Combined scores
# ---------------------------------------------------------------------------


def compute_priority_score(
    recency: float,
    centrality: float,
    trending: float,
) -> float:
    """
    Weighted priority for deep_pdf candidate selection.

        priority = 0.5 * recency + 0.3 * centrality + 0.2 * trending
    """
    return 0.5 * recency + 0.3 * centrality + 0.2 * trending


def compute_recommendation_score(
    embedding_sim: float,
    recency: float,
    trending: float,
) -> float:
    """
    Weighted final score for recommendation re-ranking.

        final = 0.7 * embedding_sim + 0.2 * recency + 0.1 * trending
    """
    return 0.7 * embedding_sim + 0.2 * recency + 0.1 * trending

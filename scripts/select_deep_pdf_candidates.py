#!/usr/bin/env python3
"""
Select paper_versions for deep_pdf summarization by hybrid priority score.

    priority = 0.5 * recency + 0.3 * centrality + 0.2 * trending

Candidates are paper_versions that have no deep_pdf summary yet.
Selected ids are written as a JSON array to stdout so the pipeline can
pipe them directly to run_deep_pdf_summary.py --ids.

Usage:
    python scripts/select_deep_pdf_candidates.py --limit 30
    python scripts/select_deep_pdf_candidates.py --limit 30 --day 2026-03-01

Environment:
    DATABASE_URL=postgresql://user:password@localhost:5432/paper_agent
"""

import argparse
import json
import logging
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from packages.core.recommend.priority import (
    build_id_to_pos,
    compute_embedding_centrality,
    compute_priority_score,
    compute_recency_score,
    compute_trending_boost,
    get_top_trending_keywords,
    load_recent_reference_vectors,
)
from packages.core.storage.db import get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 30
_DEFAULT_INDEX_DIR = "data/index"
_N_REFERENCE = 20   # recent papers used as centrality reference
_N_TRENDING = 20    # top trending keywords to consider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select deep_pdf candidates by hybrid priority score.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=_DEFAULT_LIMIT,
        help=f"Number of candidates to select (default: {_DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--index-dir",
        type=str,
        default=_DEFAULT_INDEX_DIR,
        help=f"FAISS index directory (default: {_DEFAULT_INDEX_DIR})",
    )
    parser.add_argument(
        "--day",
        type=str,
        default=str(date.today()),
        help="Date for trending keywords YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def _fetch_candidates(conn) -> list[dict]:
    """
    Fetch paper_versions that have no deep_pdf summary.

    Joins the light summary (if any) to pull LLM keywords used for
    trending matching.  Returns id, title, published_date, keywords.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                pv.id,
                pv.title,
                pv.version_published_date,
                s.summary_data
            FROM paper_versions pv
            LEFT JOIN summaries s
                ON s.paper_version_id = pv.id AND s.summary_type = 'light'
            WHERE NOT EXISTS (
                SELECT 1 FROM summaries ds
                WHERE ds.paper_version_id = pv.id
                  AND ds.summary_type = 'deep_pdf'
            )
            ORDER BY pv.version_published_date DESC
            """
        )
        rows = cur.fetchall()

    candidates = []
    for r in rows:
        summary_data = r["summary_data"] or {}
        if isinstance(summary_data, str):
            summary_data = json.loads(summary_data)
        keywords = summary_data.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []
        candidates.append(
            {
                "id": r["id"],
                "title": r["title"] or "",
                "published_date": r["version_published_date"],
                "keywords": keywords,
            }
        )

    return candidates


def _try_load_index(index_dir: str):
    """
    Attempt to load the FAISS index.

    Returns (index, ids, id_to_pos) on success, or (None, [], {}) when the
    index is unavailable — centrality will default to 0.0 in that case.
    """
    try:
        from packages.core.recommend.index_faiss import load_index

        index, ids = load_index(index_dir)
        id_to_pos = build_id_to_pos(ids)
        return index, ids, id_to_pos
    except Exception as exc:
        logger.warning("FAISS index unavailable (%s) — centrality = 0.0", exc)
        return None, [], {}


def main() -> None:
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        target_day = date.fromisoformat(args.day)
    except ValueError:
        logger.error("Invalid --day: %r (expected YYYY-MM-DD)", args.day)
        sys.exit(1)

    logger.info("=" * 65)
    logger.info(
        "Selecting up to %d deep_pdf candidates  day=%s", args.limit, target_day
    )
    logger.info("=" * 65)

    try:
        with get_connection() as conn:

            # 1. Candidates without deep_pdf
            candidates = _fetch_candidates(conn)
            if not candidates:
                logger.info("No candidates found — all versions have deep_pdf.")
                print(json.dumps([]))
                sys.exit(0)

            logger.info("Candidates (no deep_pdf): %d", len(candidates))

            # 2. FAISS index (best-effort)
            index, ids, id_to_pos = _try_load_index(args.index_dir)

            # 3. Reference vectors for centrality
            reference_vecs = None
            if index is not None:
                reference_vecs = load_recent_reference_vectors(
                    conn, index, id_to_pos, n=_N_REFERENCE
                )

            # 4. Trending keywords for the target day
            trending_kws = get_top_trending_keywords(conn, target_day, n=_N_TRENDING)
            if trending_kws:
                preview = ", ".join(sorted(trending_kws)[:8])
                logger.info(
                    "Trending keywords (%d): %s%s",
                    len(trending_kws),
                    preview,
                    "..." if len(trending_kws) > 8 else "",
                )
            else:
                logger.info("No trending keywords for %s — trending boost = 0.0", target_day)

            # 5. Score every candidate
            scored: list[tuple[float, int]] = []
            for c in candidates:
                recency = compute_recency_score(c["published_date"])

                centrality = 0.0
                if index is not None and reference_vecs is not None:
                    centrality = compute_embedding_centrality(
                        c["id"], index, id_to_pos, reference_vecs
                    )

                trending = compute_trending_boost(
                    c["title"], c["keywords"], trending_kws
                )
                priority = compute_priority_score(recency, centrality, trending)
                scored.append((priority, c["id"]))

                logger.debug(
                    "  id=%d  rec=%.3f  cen=%.3f  trd=%.1f  pri=%.3f  %s",
                    c["id"],
                    recency,
                    centrality,
                    trending,
                    priority,
                    c["title"][:55],
                )

            # 6. Sort descending, take top-limit
            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[: args.limit]
            selected_ids = [vid for _score, vid in top]

            logger.info(
                "Selected %d  (top scores: %s)",
                len(selected_ids),
                "  ".join(f"{s:.3f}" for s, _ in top[:5]),
            )

            # 7. Emit JSON to stdout
            print(json.dumps(selected_ids))

    except Exception as exc:
        logger.error("Candidate selection failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Build FAISS embedding index for paper recommendation.

Fetches all paper_versions with their summaries, builds rich index texts,
embeds them with SentenceTransformer (BAAI/bge-m3 by default), and saves
a FAISS IndexFlatIP + companion paper_version id list to disk.

Usage:
    python scripts/build_embeddings.py
    python scripts/build_embeddings.py --model BAAI/bge-m3 --limit 1000
    python scripts/build_embeddings.py --index-dir /tmp/idx

Environment:
    DATABASE_URL=postgresql://user:password@localhost:5432/paper_agent
"""

import argparse
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from packages.core.recommend.embeddings import build_index_text, embed_texts, get_embedder
from packages.core.recommend.index_faiss import build_faiss_index, save_index
from packages.core.storage.db import get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_DEFAULT_INDEX_DIR = "data/index"
_DEFAULT_MODEL = "BAAI/bge-m3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build FAISS embedding index for paper recommendation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--model",
        type=str,
        default=_DEFAULT_MODEL,
        help=f"SentenceTransformer model name (default: {_DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--index-dir",
        type=str,
        default=_DEFAULT_INDEX_DIR,
        help=f"Output directory for FAISS index files (default: {_DEFAULT_INDEX_DIR})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of paper versions to index (default: all)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Embedding batch size (default: 64)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def _fetch_papers_with_summaries(conn, limit: int | None) -> list[dict]:
    """
    Fetch paper_versions with all their summaries in two queries.

    Returns list of dicts with keys: id, arxiv_id, version, title, abstract,
    summaries (dict keyed by summary_type -> summary_data).
    """
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT
                pv.id,
                pv.arxiv_id,
                pv.version,
                pv.title,
                pv.abstract
            FROM paper_versions pv
            ORDER BY pv.version_published_date DESC
            {limit_clause}
            """
        )
        rows = cur.fetchall()

    if not rows:
        return []

    version_ids = [r["id"] for r in rows]

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT paper_version_id, summary_type, summary_data
            FROM summaries
            WHERE paper_version_id = ANY(%s)
            """,
            (version_ids,),
        )
        summary_rows = cur.fetchall()

    summaries_by_id: dict[int, dict] = {}
    for s in summary_rows:
        vid = s["paper_version_id"]
        if vid not in summaries_by_id:
            summaries_by_id[vid] = {}
        data = s["summary_data"]
        if isinstance(data, str):
            data = json.loads(data)
        summaries_by_id[vid][s["summary_type"]] = data

    result = []
    for row in rows:
        d = dict(row)
        d["summaries"] = summaries_by_id.get(row["id"], {})
        result.append(d)

    return result


def main() -> None:
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 70)
    logger.info("Build Embeddings  model=%s", args.model)
    logger.info("=" * 70)

    t0 = time.monotonic()

    try:
        with get_connection() as conn:
            logger.info(
                "Fetching paper versions%s...",
                f" (limit={args.limit})" if args.limit else "",
            )
            papers = _fetch_papers_with_summaries(conn, limit=args.limit)

        if not papers:
            logger.warning("No paper versions found in database.")
            sys.exit(0)

        logger.info("Fetched %d paper versions", len(papers))

        # Build index texts (skip versions with no meaningful text)
        ids: list[int] = []
        texts: list[str] = []
        skipped = 0
        for paper in papers:
            text = build_index_text(paper, paper["summaries"])
            if text.strip():
                ids.append(paper["id"])
                texts.append(text)
            else:
                skipped += 1
                logger.debug(
                    "Empty index text for version_id=%d, skipping", paper["id"]
                )

        if skipped:
            logger.warning("Skipped %d versions with empty index text", skipped)
        logger.info("Index texts ready: %d", len(texts))

        # Load model and embed
        model = get_embedder(args.model)
        logger.info(
            "Embedding %d texts (batch_size=%d)...", len(texts), args.batch_size
        )
        vectors = embed_texts(
            model, texts, batch_size=args.batch_size, show_progress=True
        )
        logger.info("Embedding done: shape=%s dtype=%s", vectors.shape, vectors.dtype)

        # Build FAISS index and save
        index = build_faiss_index(vectors)
        save_index(index, ids, index_dir=args.index_dir)

        elapsed = time.monotonic() - t0
        logger.info("=" * 70)
        logger.info("Done in %.1fs — indexed %d papers", elapsed, len(ids))
        logger.info("Index dir: %s", os.path.abspath(args.index_dir))
        logger.info("=" * 70)

    except Exception as exc:
        logger.error("Build failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()

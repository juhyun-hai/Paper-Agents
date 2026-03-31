#!/usr/bin/env python3
"""
Build keyword_stats from paper_versions and optional deep summaries.

Scans all paper_versions, extracts keywords from title / abstract / LLM-generated
keywords, aggregates counts, and upserts them into keyword_stats for the given day.

Running this script multiple times for the same day produces the same result (idempotent).

Usage:
    python scripts/build_keyword_stats.py
    python scripts/build_keyword_stats.py --day 2024-01-15
    python scripts/build_keyword_stats.py --use title
    python scripts/build_keyword_stats.py --use abstract
    python scripts/build_keyword_stats.py --use llm
    python scripts/build_keyword_stats.py --use all
"""

import sys
import os
import argparse
import logging
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from packages.core.storage.db import get_connection
from packages.core.trending.extract import extract_keywords
from packages.core.trending.repo import upsert_keyword_counts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build keyword stats for a given day.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--day",
        type=str,
        default=str(date.today()),
        help="Date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--use",
        type=str,
        default="all",
        choices=["title", "abstract", "llm", "all"],
        help="Which source(s) to extract keywords from (default: all)",
    )
    return parser.parse_args()


def resolve_sources(use: str) -> list[str]:
    """Expand 'all' to the full source list."""
    if use == "all":
        return ["title", "abstract", "llm"]
    return [use]


def fetch_paper_versions(conn) -> list:
    """Return id, title, abstract for every paper_version row."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, title, abstract FROM paper_versions ORDER BY id")
        return cur.fetchall()


def fetch_deep_summary_keywords(conn) -> dict[int, list[str]]:
    """
    Return a mapping of paper_version_id -> list[keyword] from deep summaries.

    Only deep summaries whose 'keywords' field is a non-empty JSON array are included.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT paper_version_id, summary_data -> 'keywords' AS keywords
            FROM summaries
            WHERE summary_type = 'deep'
              AND jsonb_typeof(summary_data -> 'keywords') = 'array'
            """
        )
        result: dict[int, list[str]] = {}
        for row in cur.fetchall():
            kws = row["keywords"]
            if isinstance(kws, list) and kws:
                result[row["paper_version_id"]] = kws
    return result


def main() -> None:
    args = parse_args()

    try:
        day = date.fromisoformat(args.day)
    except ValueError:
        logger.error("Invalid date %r – use YYYY-MM-DD.", args.day)
        sys.exit(1)

    sources = resolve_sources(args.use)

    logger.info("=" * 60)
    logger.info("Build Keyword Stats")
    logger.info("=" * 60)
    logger.info("Day:     %s", day)
    logger.info("Sources: %s", sources)
    logger.info("=" * 60)

    with get_connection() as conn:
        versions = fetch_paper_versions(conn)
        logger.info("Paper versions found: %d", len(versions))

        deep_kws: dict[int, list[str]] = {}
        if "llm" in sources:
            deep_kws = fetch_deep_summary_keywords(conn)
            logger.info("Deep summaries with keywords: %d", len(deep_kws))

        # Accumulate counts per source
        counts: dict[str, dict[str, int]] = {
            src: defaultdict(int) for src in sources
        }

        for version in versions:
            vid: int = version["id"]
            title: str = version["title"] or ""
            abstract: str = version["abstract"] or ""
            llm_kws = deep_kws.get(vid)

            extracted = extract_keywords(title, abstract, llm_kws)

            for src in sources:
                for kw in extracted.get(src, []):
                    counts[src][kw] += 1

        # Replace keyword_stats for each source: delete stale rows first,
        # then upsert fresh counts. This makes the operation idempotent.
        total_rows = 0
        for src in sources:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM keyword_stats WHERE day = %s AND source = %s",
                    (day, src),
                )
            n = upsert_keyword_counts(conn, day, src, dict(counts[src]))
            logger.info("Upserted %6d rows  source=%s", n, src)
            total_rows += n

    logger.info("=" * 60)
    logger.info("Done. Total rows upserted: %d", total_rows)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

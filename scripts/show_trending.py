#!/usr/bin/env python3
"""
Show top keywords and their trending scores for a given day.

Trending score formula:
    score = (freq_7d + 1) / (avg_prev_30d + 1)

Where:
    freq_7d      = total keyword occurrences in the 7-day window ending on --day
    avg_prev_30d = average daily occurrences in the 30-day window before that

If no prior baseline exists the score is still computed via smoothing
(avg_prev_30d treated as 0), and the keyword is marked "new".

Usage:
    python scripts/show_trending.py
    python scripts/show_trending.py --day 2024-01-15
    python scripts/show_trending.py --top 20 --source title
    python scripts/show_trending.py --source llm --top 50
"""

import sys
import os
import argparse
import logging
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from packages.core.storage.db import get_connection

# Source weights applied when aggregating raw counts from keyword_stats.
# The storage layer always holds raw per-source counts; weighting is display-only.
SOURCE_WEIGHTS: dict[str, float] = {"llm": 3.0, "title": 2.0, "abstract": 0.7}

# Multiplicative boost applied to multi-word keywords during ranking only.
# Raw and weighted counts shown in the table are never boosted.
PHRASE_BOOST: float = 1.4

# Minimum raw count (across all sources) required to show a keyword.
MIN_RAW_FREQ: int = 3

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show trending keywords for a day.",
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
        "--top",
        type=int,
        default=30,
        help="Number of top keywords to show (default: 30)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="all",
        choices=["title", "abstract", "llm", "all"],
        help="Filter by keyword source (default: all)",
    )
    parser.add_argument(
        "--min-freq",
        type=int,
        default=None,
        help="Minimum raw count to show a keyword (default: 1 for llm, 3 otherwise)",
    )
    return parser.parse_args()


def _aggregate_weighted(rows) -> tuple[dict[str, int], dict[str, float]]:
    """
    Accumulate per-source rows into raw and source-weighted totals per keyword.

    Each row must have 'keyword', 'source', and 'total' keys.
    Raw total: simple sum of counts across sources.
    Weighted total: sum of (count * SOURCE_WEIGHTS[source]).
    """
    raw: dict[str, int] = {}
    weighted: dict[str, float] = {}
    for row in rows:
        kw, src, cnt = row["keyword"], row["source"], int(row["total"])
        raw[kw] = raw.get(kw, 0) + cnt
        weighted[kw] = weighted.get(kw, 0.0) + cnt * SOURCE_WEIGHTS.get(src, 1.0)
    return raw, weighted


def get_day_totals(
    conn, day: date, source: str
) -> tuple[dict[str, int], dict[str, float]]:
    """
    Return (raw_counts, weighted_counts) per keyword for the given day.

    raw_counts:     simple sum of keyword_stats.count across requested sources.
    weighted_counts: sum weighted by SOURCE_WEIGHTS per source.
    """
    with conn.cursor() as cur:
        if source == "all":
            cur.execute(
                "SELECT keyword, source, SUM(count) AS total"
                " FROM keyword_stats WHERE day = %s"
                " GROUP BY keyword, source",
                (day,),
            )
        else:
            cur.execute(
                "SELECT keyword, source, SUM(count) AS total"
                " FROM keyword_stats WHERE day = %s AND source = %s"
                " GROUP BY keyword, source",
                (day, source),
            )
        return _aggregate_weighted(cur.fetchall())


def get_window_weighted_totals(
    conn, from_date: date, to_date: date, source: str
) -> dict[str, float]:
    """Return keyword -> source-weighted total count over a date window (for freq_7d)."""
    with conn.cursor() as cur:
        if source == "all":
            cur.execute(
                "SELECT keyword, source, SUM(count) AS total"
                " FROM keyword_stats WHERE day >= %s AND day <= %s"
                " GROUP BY keyword, source",
                (from_date, to_date),
            )
        else:
            cur.execute(
                "SELECT keyword, source, SUM(count) AS total"
                " FROM keyword_stats WHERE day >= %s AND day <= %s AND source = %s"
                " GROUP BY keyword, source",
                (from_date, to_date, source),
            )
        _, weighted = _aggregate_weighted(cur.fetchall())
        return weighted


def get_window_weighted_avg_daily(
    conn, from_date: date, to_date: date, source: str
) -> dict[str, float]:
    """
    Return keyword -> source-weighted average daily count over a date window.

    avg_daily is computed per (keyword, source) as total / DISTINCT days,
    then summed with source weights to get a single weighted baseline per keyword.
    """
    with conn.cursor() as cur:
        if source == "all":
            cur.execute(
                "SELECT keyword, source,"
                "       SUM(count)::float / GREATEST(COUNT(DISTINCT day), 1) AS total"
                " FROM keyword_stats WHERE day >= %s AND day <= %s"
                " GROUP BY keyword, source",
                (from_date, to_date),
            )
        else:
            cur.execute(
                "SELECT keyword, source,"
                "       SUM(count)::float / GREATEST(COUNT(DISTINCT day), 1) AS total"
                " FROM keyword_stats WHERE day >= %s AND day <= %s AND source = %s"
                " GROUP BY keyword, source",
                (from_date, to_date, source),
            )
        _, weighted_avg = _aggregate_weighted(cur.fetchall())
        return weighted_avg


def trending_score(freq_7d: float, avg_prev_30d: float) -> float:
    """score = (freq_7d + 1) / (avg_prev_30d + 1)"""
    return (freq_7d + 1.0) / (avg_prev_30d + 1.0)


def main() -> None:
    args = parse_args()

    try:
        day = date.fromisoformat(args.day)
    except ValueError:
        print(f"Error: invalid date {args.day!r} – use YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

    source = args.source
    top_n = args.top
    min_freq = args.min_freq if args.min_freq is not None else (1 if source == "llm" else MIN_RAW_FREQ)

    with get_connection() as conn:
        # Raw and weighted counts for the target day
        raw_day, weighted_day = get_day_totals(conn, day, source)
        if not raw_day:
            print(f"\nNo keyword stats found for {day}.")
            print("Run scripts/build_keyword_stats.py first.\n")
            return

        # 7-day window ending on `day`: [day-6 .. day] — weighted total
        w7_start = day - timedelta(days=6)
        freq_7d_w = get_window_weighted_totals(conn, w7_start, day, source)

        # Previous 30-day baseline: [day-36 .. day-7] — weighted avg daily
        p30_start = day - timedelta(days=36)
        p30_end = day - timedelta(days=7)
        avg_prev_30d_w = get_window_weighted_avg_daily(conn, p30_start, p30_end, source)

    # Build ranking rows.
    # rank_score = weighted_count * phrase_boost  (ranking only; not displayed)
    # Displayed columns: keyword, raw_count, weighted_count, score
    rows: list[tuple] = []
    for kw, raw_count in raw_day.items():
        if raw_count < min_freq:
            continue
        w_count = weighted_day.get(kw, float(raw_count))
        f7_w = freq_7d_w.get(kw, 0.0)
        p30_w = avg_prev_30d_w.get(kw, 0.0)
        score = trending_score(f7_w, p30_w)
        boost = PHRASE_BOOST if " " in kw else 1.0
        rank_score = w_count * boost
        rows.append((kw, raw_count, w_count, score, rank_score))

    # Primary sort: rank_score (weighted_count × phrase_boost) descending.
    # Secondary: trending score descending.
    rows.sort(key=lambda x: (-x[4], -x[3]))
    top = rows[:top_n]

    # Display
    src_label = source if source != "all" else "all sources"
    weights_desc = "llm×3 title×2 abstract×0.7"
    print(
        f"\nTop {top_n} keywords  day={day}  source={src_label}"
        f"  ({weights_desc}  phrase_boost×{PHRASE_BOOST}  min_freq={min_freq})\n"
    )
    print(f"{'#':<5}  {'Keyword':<42}  {'Count':>7}  {'Weighted':>9}  {'Score':>7}")
    print("-" * 76)
    for rank, (kw, raw_count, w_count, score, _) in enumerate(top, 1):
        print(f"{rank:<5}  {kw:<42}  {raw_count:>7}  {w_count:>9.1f}  {score:>7.2f}")
    print()


if __name__ == "__main__":
    main()

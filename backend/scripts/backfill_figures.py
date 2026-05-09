#!/usr/bin/env python3
"""Backfill PDF figures for already-summarized papers.

Default target: papers featured in the last `days` days that have a summary
but no figures stored. The figure extraction uses the same path as
/api/summary/extract-figures (PyMuPDF caption-based rendering).

Usage:
    python backfill_figures.py [--days 14] [--limit 100] [--all]
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time

import asyncpg
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('HF_HOME', os.path.join(os.path.dirname(__file__), '..', 'hf_cache'))


DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'


async def fetch_targets(conn, days: int, limit: int, mode: str):
    """Pick paper rows to backfill."""
    if mode == 'all':
        rows = await conn.fetch("""
            SELECT ps.arxiv_id
            FROM paper_summaries ps
            WHERE COALESCE(ps.figure_count, 0) = 0
            ORDER BY ps.id DESC
            LIMIT $1
        """, limit)
    else:
        # featured-only mode
        rows = await conn.fetch("""
            SELECT DISTINCT ps.arxiv_id
            FROM paper_summaries ps
            JOIN trending_papers tp ON ps.arxiv_id = tp.arxiv_id
            WHERE tp.is_featured = TRUE
              AND tp.date >= CURRENT_DATE - $1::int
              AND COALESCE(ps.figure_count, 0) = 0
            ORDER BY ps.arxiv_id DESC
            LIMIT $2
        """, days, limit)
    return [r['arxiv_id'] for r in rows]


async def update_figures(conn, arxiv_id: str, figures: list) -> bool:
    if not figures:
        return False
    await conn.execute("""
        UPDATE paper_summaries
        SET figures = $1::jsonb,
            figure_count = $2,
            updated_at = NOW()
        WHERE arxiv_id = $3
    """, json.dumps(figures), len(figures), arxiv_id)
    return True


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=14,
                        help='Look-back window for featured papers (ignored with --all)')
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--all', action='store_true',
                        help='Backfill ALL summaries without figures (not just featured)')
    parser.add_argument('--max-figures', type=int, default=5)
    args = parser.parse_args()

    # Local import; loads PyMuPDF on first call.
    from app.services.figure_extractor import extract_figures

    conn = await asyncpg.connect(DB_URL)
    try:
        mode = 'all' if args.all else 'featured'
        targets = await fetch_targets(conn, args.days, args.limit, mode)
        print(f'🎯 {len(targets)} papers to backfill (mode={mode})')

        ok, skipped, failed = 0, 0, 0
        for i, aid in enumerate(targets, 1):
            t0 = time.time()
            try:
                figs = extract_figures(aid, max_figures=args.max_figures)
            except Exception as e:
                print(f'  [{i}/{len(targets)}] {aid} extract error: {e}')
                failed += 1
                continue
            if not figs:
                print(f'  [{i}/{len(targets)}] {aid} no figures found ({time.time()-t0:.1f}s)')
                skipped += 1
                continue
            await update_figures(conn, aid, figs)
            ok += 1
            print(f'  [{i}/{len(targets)}] {aid} ✅ {len(figs)} figs ({time.time()-t0:.1f}s)')

        print(f'\nDone — saved figures for {ok}, skipped {skipped}, failed {failed}')
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())

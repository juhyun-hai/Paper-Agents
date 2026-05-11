#!/usr/bin/env python3
"""Re-extract figures for lab papers that have a pdf_url, after we previously
stripped them all out conservatively. Lab papers that publishers block will
just return 0 figures — that's fine.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import time

import asyncpg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('HF_HOME', os.path.join(os.path.dirname(__file__), '..', 'hf_cache'))

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'


async def main():
    from app.services.figure_extractor import extract_figures

    conn = await asyncpg.connect(DB_URL)
    try:
        rows = await conn.fetch("""
            SELECT p.id, p.arxiv_id, p.pdf_url, ps.id as sum_id
            FROM papers p
            JOIN paper_summaries ps ON p.arxiv_id = ps.arxiv_id
            WHERE p.arxiv_id LIKE 'hai:%'
              AND p.pdf_url IS NOT NULL AND p.pdf_url != ''
              AND (ps.figure_count = 0 OR ps.figure_count IS NULL)
        """)
        print(f'Targets: {len(rows)} lab papers with pdf_url and no figures')

        ok, none, fail = 0, 0, 0
        for i, row in enumerate(rows, 1):
            try:
                figs = extract_figures(row['arxiv_id'], max_figures=5, pdf_url=row['pdf_url'])
            except Exception as e:
                fail += 1
                continue
            if not figs:
                none += 1
                continue
            await conn.execute(
                "UPDATE paper_summaries SET figures = $1::jsonb, figure_count = $2, updated_at = NOW() WHERE id = $3",
                json.dumps(figs), len(figs), row['sum_id'],
            )
            ok += 1
            if ok % 5 == 0:
                print(f'  [{i}/{len(rows)}] +{len(figs)} figs for {row["arxiv_id"]}')
            time.sleep(0.2)

        print(f'\nWith figures: {ok}, no figures available: {none}, errored: {fail}')
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())

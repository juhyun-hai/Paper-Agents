#!/usr/bin/env python3
"""Re-evaluate the is_hai / hai_score columns on existing trending_papers
using the current HAI keyword list.

Use after editing app/core/hai_config.py to refresh historical tagging.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys

import asyncpg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.core.hai_config import is_hai_author, hai_keyword_score

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'


async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        rows = await conn.fetch("""
            SELECT tp.id, tp.arxiv_id, tp.title, p.abstract, p.authors
            FROM trending_papers tp
            LEFT JOIN papers p ON tp.arxiv_id = p.arxiv_id
        """)
        print(f'Re-tagging {len(rows)} trending entries...')

        updated, hai_count = 0, 0
        for row in rows:
            authors = []
            if row['authors']:
                try:
                    authors = (
                        json.loads(row['authors'])
                        if isinstance(row['authors'], str) else row['authors']
                    )
                except Exception:
                    authors = []
            kw = hai_keyword_score(row['title'] or '', row['abstract'] or '')
            is_hai = is_hai_author(authors) or kw >= 2
            score = kw + (10 if is_hai_author(authors) else 0)
            await conn.execute(
                "UPDATE trending_papers SET is_hai = $1, hai_score = $2 WHERE id = $3",
                is_hai, score, row['id'],
            )
            updated += 1
            if is_hai:
                hai_count += 1

        print(f'Updated: {updated}, HAI-tagged: {hai_count}')
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())

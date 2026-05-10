#!/usr/bin/env python3
"""Fetch HAI Lab publications from OpenAlex (papers by Prof. Byeng D. Youn).

Inserts into the `papers` table marked as is_lab_publication=true and is_hai=true.
Uses `openalex:WID` as the arxiv_id slot (the column is a generic string identifier).
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
from datetime import datetime

import asyncpg
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.core.hai_config import hai_topic

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
AUTHOR_ID = 'A5084771659'  # Byeng D. Youn (HAI Lab director)
OPENALEX = 'https://api.openalex.org'
HEADERS = {'User-Agent': 'HotPaper/1.0 (mailto:contact@hotpaper.ai)'}


def reconstruct_abstract(inv_index):
    """OpenAlex returns abstracts as inverted indexes. Reconstruct plain text."""
    if not inv_index:
        return ''
    pairs = []
    for word, positions in inv_index.items():
        for p in positions:
            pairs.append((p, word))
    pairs.sort()
    return ' '.join(w for _, w in pairs)


def fetch_works(per_page=200, max_works=300):
    """Fetch up to max_works recent papers, sorted by publication date desc."""
    works = []
    cursor = '*'
    while len(works) < max_works:
        url = (
            f"{OPENALEX}/works"
            f"?filter=author.id:{AUTHOR_ID}"
            f"&sort=publication_date:desc"
            f"&per-page={per_page}"
            f"&cursor={cursor}"
        )
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f'Failed: HTTP {r.status_code}')
            break
        data = r.json()
        results = data.get('results', [])
        if not results:
            break
        works.extend(results)
        cursor = data.get('meta', {}).get('next_cursor')
        if not cursor:
            break
    return works[:max_works]


async def main():
    print(f'Fetching publications for author {AUTHOR_ID}...')
    works = fetch_works(max_works=300)
    print(f'Got {len(works)} works')

    conn = await asyncpg.connect(DB_URL)
    try:
        added, updated, skipped = 0, 0, 0
        for w in works:
            wid = w.get('id', '').split('/')[-1]  # extract Wxxxxxxx
            if not wid:
                skipped += 1
                continue

            # Use openalex:WID as our identifier
            ext_id = f"openalex:{wid}"

            title = (w.get('title') or '').strip()
            abstract = reconstruct_abstract(w.get('abstract_inverted_index') or {}).strip()
            if not title:
                skipped += 1
                continue

            authors = []
            for au in (w.get('authorships') or []):
                a = au.get('author', {})
                name = a.get('display_name')
                if name:
                    authors.append(name)

            # Year & published date
            pub_date = w.get('publication_date')  # 'YYYY-MM-DD'
            year = w.get('publication_year')

            # Venue / journal
            venue = None
            host_venue = w.get('host_venue') or {}
            primary_loc = w.get('primary_location') or {}
            if isinstance(primary_loc.get('source'), dict):
                venue = primary_loc['source'].get('display_name')
            venue = venue or host_venue.get('display_name')

            doi = (w.get('doi') or '').replace('https://doi.org/', '')
            pdf_url = primary_loc.get('pdf_url') if isinstance(primary_loc, dict) else None
            html_url = (
                primary_loc.get('landing_page_url') if isinstance(primary_loc, dict) else None
            ) or (f'https://doi.org/{doi}' if doi else None)

            citations = int(w.get('cited_by_count') or 0)
            categories = []  # OpenAlex 'concepts' could go here later

            topic = hai_topic(title, abstract)

            # Upsert into papers table
            existing = await conn.fetchrow(
                "SELECT id FROM papers WHERE arxiv_id = $1", ext_id
            )
            try:
                if existing:
                    await conn.execute("""
                        UPDATE papers
                        SET title = $2, abstract = $3, authors = $4, venue = $5,
                            year = $6, citation_count = $7,
                            published_date = $8, pdf_url = $9, html_url = $10,
                            is_hai = TRUE, hai_score = 100, hai_topic = $11,
                            is_lab_publication = TRUE,
                            updated_at = NOW()
                        WHERE id = $1
                    """,
                        existing['id'], title, abstract, json.dumps(authors), venue,
                        year, citations,
                        datetime.fromisoformat(pub_date) if pub_date else None,
                        pdf_url, html_url, topic,
                    )
                    updated += 1
                else:
                    await conn.execute("""
                        INSERT INTO papers
                          (arxiv_id, title, abstract, authors, categories, venue, year,
                           citation_count, pdf_url, html_url, published_date,
                           is_hai, hai_score, hai_topic, is_lab_publication,
                           created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                                TRUE, 100, $12, TRUE, NOW(), NOW())
                    """,
                        ext_id, title, abstract, json.dumps(authors),
                        json.dumps(categories), venue, year,
                        citations, pdf_url, html_url,
                        datetime.fromisoformat(pub_date) if pub_date else None,
                        topic,
                    )
                    added += 1
            except Exception as e:
                print(f'  Failed {ext_id}: {e}')
                skipped += 1

        print(f'Added: {added}, Updated: {updated}, Skipped: {skipped}')
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())

#!/usr/bin/env python3
"""Backfill missing authors for arXiv papers using the arXiv API.

Papers that came from HuggingFace/RSS trending feeds were inserted with
empty author arrays because those feeds don't expose authors. This script
fetches the canonical author list from arxiv.org/abs/<id> in batches.
"""
from __future__ import annotations
import asyncio
import json
import re
import time
import xml.etree.ElementTree as ET

import asyncpg
import requests

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
ARXIV = 'http://export.arxiv.org/api/query'
NS = {'a': 'http://www.w3.org/2005/Atom'}
UA = 'HotPaper/1.0 (https://hotpaper.ai; mailto:contact@hotpaper.ai)'


def fetch_authors_for(arxiv_ids: list[str]) -> dict[str, list[str]]:
    """Hit arXiv API for a batch (up to ~200 ids) and return arxiv_id -> authors."""
    if not arxiv_ids:
        return {}
    # `id_list` accepts comma-separated arXiv IDs.
    url = f"{ARXIV}?id_list={','.join(arxiv_ids)}&max_results={len(arxiv_ids)}"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        if r.status_code != 200:
            return {}
        root = ET.fromstring(r.text)
        result = {}
        for entry in root.findall('a:entry', NS):
            entry_id_el = entry.find('a:id', NS)
            if entry_id_el is None:
                continue
            # entry.id is "http://arxiv.org/abs/2604.12345v1" — extract bare id.
            m = re.search(r'/abs/([0-9]{4}\.[0-9]{4,5})', entry_id_el.text or '')
            if not m:
                continue
            arxiv_id = m.group(1)
            authors = []
            for a in entry.findall('a:author', NS):
                name_el = a.find('a:name', NS)
                if name_el is not None and name_el.text:
                    authors.append(name_el.text.strip())
            if authors:
                result[arxiv_id] = authors
        return result
    except Exception as e:
        print(f"  fetch error: {e}")
        return {}


async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        rows = await conn.fetch("""
            SELECT id, arxiv_id FROM papers
            WHERE arxiv_id NOT LIKE 'hai:%'
              AND arxiv_id NOT LIKE 'openalex:%'
              AND (authors IS NULL OR jsonb_array_length(authors) = 0)
              AND arxiv_id ~ '^[0-9]{4}\\.[0-9]{4,5}$'
            ORDER BY id DESC
        """)
        print(f"Backfilling authors for {len(rows)} arxiv papers...")

        BATCH = 100  # arXiv recommends <= 100 per request, with 3s spacing
        enriched, no_match = 0, 0
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            ids = [r['arxiv_id'] for r in chunk]
            authors_map = fetch_authors_for(ids)

            for r in chunk:
                authors = authors_map.get(r['arxiv_id'])
                if not authors:
                    no_match += 1
                    continue
                try:
                    await conn.execute(
                        "UPDATE papers SET authors = $1::jsonb, updated_at = NOW() WHERE id = $2",
                        json.dumps(authors), r['id'],
                    )
                    enriched += 1
                except Exception as e:
                    print(f"  DB err {r['arxiv_id']}: {e}")
                    no_match += 1

            print(f"  [{i + len(chunk)}/{len(rows)}] +{len(authors_map)} this batch")
            # arxiv asks 3-second spacing between API calls
            time.sleep(3.5)

        print(f"\nEnriched: {enriched}, No match: {no_match}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

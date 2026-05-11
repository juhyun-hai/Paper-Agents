#!/usr/bin/env python3
"""Better enrichment: fetch all of Prof. Youn's papers from OpenAlex once,
then match against scraped lab papers by normalized title locally.
"""
from __future__ import annotations
import asyncio
import json
import os
import re
import sys
import time

import asyncpg
import requests

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
AUTHOR_ID = 'A5084771659'  # Byeng D. Youn
OPENALEX = 'https://api.openalex.org/works'
HEADERS = {'User-Agent': 'HotPaper/1.0 (mailto:contact@hotpaper.ai)'}


def reconstruct_abstract(inv_index):
    if not inv_index:
        return ''
    pairs = []
    for word, positions in inv_index.items():
        for p in positions:
            pairs.append((p, word))
    pairs.sort()
    return ' '.join(w for _, w in pairs)


def normalize_title(t: str) -> str:
    t = re.sub(r"[^\w\s]", " ", (t or "").lower())
    return re.sub(r"\s+", " ", t).strip()


def fetch_all_youn_papers():
    """Page through every paper authored by Prof. Youn (~400)."""
    papers = []
    cursor = "*"
    fields = (
        "id,title,abstract_inverted_index,doi,authorships,"
        "primary_location,publication_year,publication_date,"
        "cited_by_count"
    )
    while True:
        # `filter=author.id:Axxx` must NOT be URL-encoded (`:`), so build the
        # URL string by hand instead of letting requests encode params.
        url = (
            f"{OPENALEX}"
            f"?filter=author.id:{AUTHOR_ID}"
            f"&sort=publication_date:desc"
            f"&per-page=200"
            f"&cursor={cursor}"
            f"&select={fields}"
        )
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}: {r.text[:200]}")
            break
        data = r.json()
        results = data.get("results", [])
        if not results:
            break
        papers.extend(results)
        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.4)
    return papers


async def main():
    print("Fetching Prof. Youn's papers from OpenAlex (one-shot)...")
    youn_papers = fetch_all_youn_papers()
    print(f"Got {len(youn_papers)} papers from OpenAlex")

    # Build lookup by normalized title
    by_title = {}
    for w in youn_papers:
        title = (w.get("title") or "").strip()
        if not title:
            continue
        by_title[normalize_title(title)] = w

    print(f"Built title index ({len(by_title)} unique titles)")

    conn = await asyncpg.connect(DB_URL)
    try:
        rows = await conn.fetch("""
            SELECT id, arxiv_id, title FROM papers
            WHERE arxiv_id LIKE 'hai:%'
              AND (abstract IS NULL OR abstract = '')
        """)
        print(f"Matching {len(rows)} lab papers...")

        enriched, no_match = 0, 0
        for row in rows:
            nt = normalize_title(row["title"])
            w = by_title.get(nt)

            # Fallback: try fuzzy match via token-set Jaccard
            if not w:
                src_tokens = set(nt.split())
                if len(src_tokens) >= 4:
                    best, best_jacc = None, 0.0
                    for k, v in by_title.items():
                        kt = set(k.split())
                        inter = src_tokens & kt
                        if len(inter) < 4:
                            continue
                        jacc = len(inter) / len(src_tokens | kt)
                        if jacc > best_jacc:
                            best, best_jacc = v, jacc
                    if best_jacc >= 0.6:
                        w = best

            if not w:
                no_match += 1
                continue

            abstract = reconstruct_abstract(w.get("abstract_inverted_index") or {}).strip()
            doi = (w.get("doi") or "").replace("https://doi.org/", "")
            primary_loc = w.get("primary_location") or {}
            pdf_url = primary_loc.get("pdf_url") if isinstance(primary_loc, dict) else None
            citations = int(w.get("cited_by_count") or 0)
            year = w.get("publication_year")

            try:
                await conn.execute("""
                    UPDATE papers SET
                      abstract = COALESCE(NULLIF($2,''), abstract),
                      pdf_url = COALESCE(NULLIF($3,''), pdf_url),
                      citation_count = GREATEST(citation_count, $4),
                      year = COALESCE(year, $5),
                      updated_at = NOW()
                    WHERE id = $1
                """, row["id"], abstract, pdf_url, citations, year)
                if abstract:
                    enriched += 1
                else:
                    no_match += 1
            except Exception as e:
                print(f"  DB err {row['arxiv_id']}: {e}")
                no_match += 1

        print(f"\nEnriched (with abstract): {enriched}, No match / no abstract: {no_match}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

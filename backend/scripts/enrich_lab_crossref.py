#!/usr/bin/env python3
"""Final-pass enrichment using Crossref (and S2 fallback) for lab papers
that OpenAlex couldn't match.
"""
from __future__ import annotations
import asyncio
import re
import time
from html import unescape

import asyncpg
import requests

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
CROSSREF = 'https://api.crossref.org/works'
SEM_SCH = 'https://api.semanticscholar.org/graph/v1/paper/search'
UA = 'HotPaper/1.0 (mailto:contact@hotpaper.ai)'


def normalize_title(t: str) -> str:
    t = re.sub(r"[^\w\s]", " ", (t or "").lower())
    return re.sub(r"\s+", " ", t).strip()


def jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def crossref_lookup(title: str) -> dict | None:
    """Try Crossref by title. Returns {abstract, doi, citations, year, pdf_url}."""
    try:
        r = requests.get(
            CROSSREF,
            params={
                "query.bibliographic": title[:200],
                "rows": 5,
                "select": "DOI,title,abstract,issued,is-referenced-by-count,link",
            },
            headers={"User-Agent": UA},
            timeout=20,
        )
        if r.status_code != 200:
            return None
        items = r.json().get("message", {}).get("items", [])
        nt = normalize_title(title)
        best, best_j = None, 0.0
        for it in items:
            cand = (it.get("title") or [""])[0]
            j = jaccard(nt, normalize_title(cand))
            if j > best_j:
                best, best_j = it, j
        if not best or best_j < 0.55:
            return None
        abstract = best.get("abstract") or ""
        # Crossref returns JATS XML — strip tags & jats prefixes.
        abstract = re.sub(r"<[^>]+>", " ", abstract)
        abstract = unescape(re.sub(r"\s+", " ", abstract)).strip()
        # Drop "Abstract" lead word if present.
        abstract = re.sub(r"^abstract[\.:]?\s*", "", abstract, flags=re.IGNORECASE)
        year_parts = best.get("issued", {}).get("date-parts", [[None]])
        year = year_parts[0][0] if year_parts and year_parts[0] else None
        return {
            "abstract": abstract,
            "doi": best.get("DOI"),
            "citations": int(best.get("is-referenced-by-count") or 0),
            "year": year,
            "pdf_url": None,
        }
    except Exception:
        return None


def s2_lookup(title: str) -> dict | None:
    """Semantic Scholar fallback. May be rate-limited."""
    try:
        r = requests.get(
            SEM_SCH,
            params={"query": title[:120], "limit": 5,
                    "fields": "title,abstract,year,citationCount,externalIds"},
            headers={"User-Agent": UA},
            timeout=20,
        )
        if r.status_code != 200:
            return None
        items = r.json().get("data", []) or []
        nt = normalize_title(title)
        best, best_j = None, 0.0
        for it in items:
            cand = it.get("title") or ""
            j = jaccard(nt, normalize_title(cand))
            if j > best_j:
                best, best_j = it, j
        if not best or best_j < 0.6:
            return None
        return {
            "abstract": best.get("abstract") or "",
            "doi": (best.get("externalIds") or {}).get("DOI"),
            "citations": int(best.get("citationCount") or 0),
            "year": best.get("year"),
            "pdf_url": None,
        }
    except Exception:
        return None


async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        rows = await conn.fetch("""
            SELECT id, arxiv_id, title FROM papers
            WHERE arxiv_id LIKE 'hai:%'
              AND (abstract IS NULL OR abstract = '')
            ORDER BY id DESC
        """)
        print(f"Trying Crossref/S2 for {len(rows)} lab papers without abstracts...")

        enriched, no_match = 0, 0
        for i, row in enumerate(rows, 1):
            info = crossref_lookup(row["title"])
            if not info or not info["abstract"]:
                info_s2 = s2_lookup(row["title"])
                time.sleep(1.0)  # S2 rate limit is strict
                if info_s2 and info_s2.get("abstract"):
                    info = info_s2

            if not info or not info.get("abstract"):
                no_match += 1
                time.sleep(0.5)
                continue

            try:
                await conn.execute("""
                    UPDATE papers SET
                      abstract = $2,
                      citation_count = GREATEST(citation_count, $3),
                      year = COALESCE(year, $4),
                      updated_at = NOW()
                    WHERE id = $1
                """, row["id"], info["abstract"], info.get("citations", 0), info.get("year"))
                enriched += 1
                if i % 10 == 0:
                    print(f"  [{i}/{len(rows)}] enriched {row['arxiv_id']}")
            except Exception as e:
                print(f"  [{i}/{len(rows)}] DB error: {e}")
                no_match += 1
            time.sleep(0.5)

        print(f"\nEnriched: {enriched}, Still no abstract: {no_match}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Scrape HAI Lab International Journals publications from
https://hai.snu.ac.kr/bbs/board.php?bo_table=sub4_1_a

This is the authoritative list maintained by the lab. Replaces the OpenAlex-
sourced lab publications.

For each entry, parses:
  - title
  - authors (string)
  - venue / journal
  - citation index info (SCIE / IF)
  - status / date
  - lab page URL (so we can deep-link from the site)

Inserts into the `papers` table marked is_lab_publication=true.
"""
from __future__ import annotations
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from html import unescape

import asyncpg
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.core.hai_config import hai_topic

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
BASE = 'https://hai.snu.ac.kr/bbs/board.php?bo_table=sub4_1_a'
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
}

# Match a single publication block.
ENTRY_RE = re.compile(
    r'<a\s+href="(?P<url>[^"]*wr_id=(?P<wid>\d+)[^"]*)">\s*'
    r'<p[^>]*class="txtTitle"[^>]*>(?P<title>.+?)</p>\s*'
    r'<p[^>]*class="txtInfo"[^>]*>(?P<info>.+?)</p>',
    re.DOTALL,
)


def _strip_tags(s: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", s)).strip()


def _extract_span(info_html: str, klass: str) -> str:
    m = re.search(
        rf'<span[^>]*class="{klass}"[^>]*>(.+?)</span>',
        info_html, re.DOTALL,
    )
    return _strip_tags(m.group(1)) if m else ''


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _parse_year(date_str: str) -> int | None:
    m = re.search(r"(20\d{2})", date_str)
    return int(m.group(1)) if m else None


def fetch_page(page: int) -> str:
    r = requests.get(f"{BASE}&page={page}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def parse_entries(html: str):
    out = []
    for m in ENTRY_RE.finditer(html):
        url = unescape(m.group("url"))
        wid = m.group("wid")
        title = _normalize_ws(_strip_tags(m.group("title")))
        info_html = m.group("info")

        authors = _normalize_ws(_extract_span(info_html, "txtAuthor"))
        # Strip trailing comma/asterisks/footnotes: "Authors*, A*, B"
        venue = _normalize_ws(_extract_span(info_html, "txtJournal"))
        citation = _normalize_ws(_extract_span(info_html, "txtCitationIndex"))
        date_str = _normalize_ws(_extract_span(info_html, "txtDate"))

        year = _parse_year(date_str)

        out.append({
            "wid": wid,
            "url": url,
            "title": title,
            "authors_str": authors,
            "venue": venue,
            "citation": citation,
            "date_str": date_str,
            "year": year,
        })
    return out


def split_authors(s: str) -> list[str]:
    if not s:
        return []
    # Replace "and" with comma, remove trailing/inline asterisks/markers.
    s = re.sub(r"\s+and\s+", ", ", s)
    s = re.sub(r"\*+", "", s)
    parts = [p.strip(" ,.; ") for p in s.split(",")]
    return [p for p in parts if p]


def is_published(date_str: str) -> bool:
    if not date_str:
        return False
    low = date_str.lower()
    return not any(k in low for k in ("under revision", "submitted", "in review"))


def normalize_title(t: str) -> str:
    t = re.sub(r"[^\w\s]", " ", (t or "").lower())
    return re.sub(r"\s+", " ", t).strip()


async def main():
    print("Fetching all 15 pages of HAI Lab publications...")
    all_entries = []
    seen_wids = set()
    page = 1
    while True:
        try:
            html = fetch_page(page)
        except Exception as e:
            print(f"Page {page} fetch failed: {e}")
            break
        entries = parse_entries(html)
        if not entries:
            print(f"No entries on page {page} — stopping.")
            break
        new_entries = [e for e in entries if e["wid"] not in seen_wids]
        for e in new_entries:
            seen_wids.add(e["wid"])
        all_entries.extend(new_entries)
        print(f"Page {page}: {len(entries)} entries ({len(new_entries)} new). Total: {len(all_entries)}")
        if len(new_entries) == 0:
            break
        page += 1
        if page > 25:  # safety
            break
        time.sleep(0.5)

    print(f"\nTotal scraped: {len(all_entries)}")

    if not all_entries:
        print("Nothing scraped — aborting.")
        return

    conn = await asyncpg.connect(DB_URL)
    try:
        # 1) Wipe old OpenAlex-sourced lab publications + their summaries
        old_ids = await conn.fetch(
            "SELECT id, arxiv_id FROM papers WHERE is_lab_publication AND arxiv_id LIKE 'openalex:%'"
        )
        if old_ids:
            print(f"Removing {len(old_ids)} existing OpenAlex lab entries...")
            ids = [r['arxiv_id'] for r in old_ids]
            await conn.execute(
                "DELETE FROM paper_summaries WHERE arxiv_id = ANY($1::varchar[])",
                ids,
            )
            await conn.execute(
                "DELETE FROM papers WHERE arxiv_id = ANY($1::varchar[])",
                ids,
            )

        # 2) Pre-build a normalized-title index of existing arXiv papers so we
        #    can detect duplicates and tag the arXiv row as is_lab_publication
        #    instead of creating a separate hai:NNN row.
        existing_arxiv = await conn.fetch("""
            SELECT id, title FROM papers
            WHERE arxiv_id NOT LIKE 'hai:%' AND arxiv_id NOT LIKE 'openalex:%'
        """)
        title_idx = {normalize_title(r['title']): r['id'] for r in existing_arxiv}

        # 3) Insert current scraped entries (skip non-published)
        added, updated, deduped, skipped_unpub = 0, 0, 0, 0
        for e in all_entries:
            if not is_published(e["date_str"]):
                skipped_unpub += 1
                continue
            ext_id = f"hai:{e['wid']}"
            authors_list = split_authors(e["authors_str"])
            if not e["title"]:
                continue
            topic = hai_topic(e["title"], "")
            published_date = (
                datetime(e["year"], 1, 1) if e["year"] else None
            )

            citation_note = e["citation"] or ""
            full_venue = (
                f"{e['venue']} — {citation_note}" if citation_note else e["venue"]
            )
            if e["date_str"]:
                full_venue = f"{full_venue} ({e['date_str']})"

            try:
                # 3a) Title dedup against existing arXiv papers.
                arxiv_match = title_idx.get(normalize_title(e["title"]))
                if arxiv_match:
                    await conn.execute("""
                        UPDATE papers SET
                          venue = COALESCE(NULLIF(venue, ''), $2),
                          html_url = COALESCE(NULLIF(html_url, ''), $3),
                          is_hai = TRUE, hai_score = GREATEST(hai_score, 100),
                          hai_topic = COALESCE(hai_topic, $4),
                          is_lab_publication = TRUE,
                          updated_at = NOW()
                        WHERE id = $1
                    """, arxiv_match, full_venue, e["url"], topic)
                    deduped += 1
                    continue

                # 3b) Otherwise insert / update hai:NNN row.
                existing = await conn.fetchrow(
                    "SELECT id FROM papers WHERE arxiv_id = $1", ext_id
                )
                if existing:
                    await conn.execute("""
                        UPDATE papers SET
                          title = $2, authors = $3, venue = $4, year = $5,
                          published_date = $6, html_url = $7,
                          is_hai = TRUE, hai_score = 100, hai_topic = $8,
                          is_lab_publication = TRUE, updated_at = NOW()
                        WHERE id = $1
                    """,
                        existing['id'], e["title"], json.dumps(authors_list),
                        full_venue, e["year"], published_date, e["url"], topic,
                    )
                    updated += 1
                else:
                    await conn.execute("""
                        INSERT INTO papers
                          (arxiv_id, title, abstract, authors, categories,
                           venue, year, citation_count, html_url, published_date,
                           is_hai, hai_score, hai_topic, is_lab_publication,
                           created_at, updated_at)
                        VALUES ($1, $2, '', $3, '[]'::jsonb, $4, $5, 0,
                                $6, $7, TRUE, 100, $8, TRUE, NOW(), NOW())
                    """,
                        ext_id, e["title"], json.dumps(authors_list),
                        full_venue, e["year"], e["url"], published_date, topic,
                    )
                    added += 1
            except Exception as ex:
                print(f"  Failed {ext_id}: {ex}")

        print(
            f"\nAdded: {added}, Updated: {updated}, "
            f"Deduped (matched arXiv): {deduped}, Skipped (unpublished): {skipped_unpub}"
        )
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())

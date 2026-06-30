#!/usr/bin/env python3
"""
Top-venue paper fetcher (OpenReview + Semantic Scholar).

Used by daily_cron.py to add an "acceptance" signal (venue_bonus) and a
"citation" signal (citation_bonus) to the featured_score v4 formula.

Sources:
  • OpenReview API v2 — ICLR / NeurIPS / COLM / TMLR / AISTATS / RLC
    (provides decision + track: Oral/Spotlight/Poster/Reject/Withdrawn)
  • Semantic Scholar Graph API — CVPR / ICCV / ECCV / ICML / ACL / EMNLP /
    AAAI / KDD + citation_count enrichment for every paper.

Run modes:
  python scripts/fetch_top_venues.py --mode=openreview --venue=ICLR.cc/2026/Conference
  python scripts/fetch_top_venues.py --mode=s2 --venue=CVPR --year=2025
  python scripts/fetch_top_venues.py --mode=enrich-citations --since-days=30
  python scripts/fetch_top_venues.py --mode=daily-rotation   # used by cron

Rate limits:
  OpenReview: 0.5 req/sec (conservative).
  Semantic Scholar: 1 req/sec sustained, exp backoff (2/4/8s) on 429/5xx.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import asyncpg
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
HEADERS = {'User-Agent': 'HotPaper/1.0 (https://hotpaper.ai)'}

OPENREVIEW_API = 'https://api2.openreview.net/notes'
S2_BULK_API = 'https://api.semanticscholar.org/graph/v1/paper/search/bulk'
S2_BATCH_API = 'https://api.semanticscholar.org/graph/v1/paper/batch'
S2_API_KEY = os.environ.get('S2_API_KEY', '').strip()  # optional, raises rate limit


# ──────────────────────────────────────────
# Venue normalization / tier definitions
# ──────────────────────────────────────────
VENUE_ALIASES = {
    'nips': 'NeurIPS',
    'neurips': 'NeurIPS',
    'advances in neural information processing systems': 'NeurIPS',
    'iclr': 'ICLR',
    'international conference on learning representations': 'ICLR',
    'icml': 'ICML',
    'international conference on machine learning': 'ICML',
    'cvpr': 'CVPR',
    'iccv': 'ICCV',
    'eccv': 'ECCV',
    'acl': 'ACL',
    'emnlp': 'EMNLP',
    'naacl': 'NAACL',
    'aaai': 'AAAI',
    'kdd': 'KDD',
    'aistats': 'AISTATS',
    'colm': 'COLM',
    'tmlr': 'TMLR',
    'rlc': 'RLC',
    'findings of the association for computational linguistics': 'ACL-Findings',
}

# venue_tier_mul (matches featured_score v4 spec)
VENUE_TIER_MUL = {
    'ICLR': 1.0, 'NeurIPS': 1.0, 'ICML': 1.0,
    'CVPR': 1.0, 'ICCV': 1.0, 'ECCV': 1.0,
    'ACL': 1.0, 'EMNLP': 1.0,
    'AAAI': 0.85, 'KDD': 0.85,
    'AISTATS': 0.8, 'COLM': 0.9, 'TMLR': 0.85,
    'NAACL': 0.9, 'RLC': 0.85,
    'ACL-Findings': 0.85,
}

# track-name → base bonus
TRACK_BASE_BONUS = {
    'Oral': 8.0,
    'Spotlight': 5.0,
    'Poster': 3.0,
    'Findings': 2.0,
    'Workshop': 1.0,
}

# venues to rotate through for S2 daily collection
S2_VENUES_BY_WEEKDAY = {
    0: ['CVPR', 'ICCV'],     # Monday
    1: ['ECCV', 'ICML'],     # Tuesday
    2: ['ACL', 'EMNLP'],     # Wednesday
    3: ['AAAI', 'KDD'],      # Thursday
    4: ['NAACL', 'AISTATS'], # Friday
    5: ['NeurIPS'],          # Saturday (also covered by OpenReview if not yet)
    6: ['ICLR'],             # Sunday
}

# OpenReview venue ids — extend each year
OPENREVIEW_VENUES = [
    ('ICLR', 'ICLR.cc', 2026),
    ('ICLR', 'ICLR.cc', 2025),
    ('NeurIPS', 'NeurIPS.cc', 2025),
    ('NeurIPS', 'NeurIPS.cc', 2024),
    ('COLM', 'colmweb.org', 2025),
    ('TMLR', 'TMLR', None),       # rolling — handled separately
    ('AISTATS', 'AISTATS.org', 2025),
    ('RLC', 'rl-conference.cc', 2025),
]


def normalize_venue(raw: str) -> str:
    if not raw:
        return ''
    key = raw.strip().lower()
    if key in VENUE_ALIASES:
        return VENUE_ALIASES[key]
    # try exact uppercase first token
    first = key.split()[0] if key else ''
    if first in VENUE_ALIASES:
        return VENUE_ALIASES[first]
    return raw.strip()


def title_key(title: str, authors: List[str] | None) -> str:
    """Stable fuzzy key for title-only dedup.

    norm_title = lower → strip non-alnum → collapse spaces.
    Combined with first-author-last-name.
    """
    t = (title or '').lower()
    t = re.sub(r'[^a-z0-9]+', ' ', t).strip()
    t = re.sub(r'\s+', ' ', t)
    fa = ''
    if authors:
        first = authors[0] if isinstance(authors, list) else str(authors).split(',')[0]
        fa = (first or '').strip().split()[-1].lower() if first else ''
    return hashlib.sha1(f'{t}|{fa}'.encode()).hexdigest()


# ──────────────────────────────────────────
# Schema migration (idempotent)
# ──────────────────────────────────────────
async def ensure_schema(conn: asyncpg.Connection) -> None:
    await conn.execute("""
        ALTER TABLE papers
          ADD COLUMN IF NOT EXISTS source_type VARCHAR(32) DEFAULT 'arxiv',
          ADD COLUMN IF NOT EXISTS source_id VARCHAR(128),
          ADD COLUMN IF NOT EXISTS s2_paper_id VARCHAR(64),
          ADD COLUMN IF NOT EXISTS citation_count_updated_at TIMESTAMPTZ,
          ADD COLUMN IF NOT EXISTS title_key VARCHAR(64);
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS papers_title_key_idx ON papers (title_key);
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS papers_source_idx ON papers (source_type, source_id);
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS venue_acceptances (
            id           BIGSERIAL PRIMARY KEY,
            paper_id     BIGINT REFERENCES papers(id) ON DELETE CASCADE,
            venue        VARCHAR(64) NOT NULL,
            year         INT,
            track        VARCHAR(32),
            decision     VARCHAR(64),
            source       VARCHAR(32),
            fetched_at   TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (paper_id, venue, year)
        );
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS venue_acceptances_paper_idx
          ON venue_acceptances (paper_id);
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS venue_acceptances_venue_year_idx
          ON venue_acceptances (venue, year);
    """)


# ──────────────────────────────────────────
# 1) OpenReview fetcher
# ──────────────────────────────────────────
def _extract_arxiv_from_text(*texts: str) -> Optional[str]:
    for t in texts:
        if not t:
            continue
        m = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', t, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'(?:arxiv:)\s*(\d{4}\.\d{4,5})', t, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _content_value(content: dict, key: str) -> Any:
    v = content.get(key)
    if isinstance(v, dict):
        return v.get('value')
    return v


def fetch_openreview_venue(venue_slug: str, year: int,
                            since_days: int = 0) -> List[Dict[str, Any]]:
    """Fetch submissions for an OpenReview venue.

    venue_slug examples: 'ICLR.cc', 'NeurIPS.cc', 'colmweb.org'.
    Builds invitation as: f'{venue_slug}/{year}/Conference/-/Submission'.
    """
    invitation = f'{venue_slug}/{year}/Conference/-/Submission'
    print(f'  📥 OpenReview: {invitation}')

    since_ts_ms: Optional[int] = None
    if since_days > 0:
        since_ts_ms = int((datetime.utcnow() - timedelta(days=since_days)).timestamp() * 1000)

    out: List[Dict[str, Any]] = []
    offset = 0
    page = 1000
    venue_simple = invitation.split('.')[0].split('/')[0].upper()  # 'ICLR'

    while True:
        params = {
            'invitation': invitation,
            'details': 'replies,original',
            'limit': page,
            'offset': offset,
            'sort': 'cdate:desc',
        }
        try:
            resp = requests.get(OPENREVIEW_API, params=params,
                                headers=HEADERS, timeout=30)
            time.sleep(2.0)  # 0.5 req/sec
        except Exception as e:
            print(f'    ⚠️ OpenReview HTTP error: {e}')
            break
        if resp.status_code != 200:
            # 400 commonly means invitation doesn't exist yet (year mismatch).
            if resp.status_code != 400:
                print(f'    ⚠️ OpenReview {resp.status_code}: {resp.text[:200]}')
            break
        data = resp.json()
        notes = data.get('notes', [])
        if not notes:
            break
        for note in notes:
            cdate = note.get('cdate', 0) or 0
            if since_ts_ms is not None and cdate < since_ts_ms:
                continue
            content = note.get('content', {}) or {}
            title = _content_value(content, 'title') or ''
            if not title:
                continue
            abstract = _content_value(content, 'abstract') or ''
            authors_raw = _content_value(content, 'authors') or []
            if isinstance(authors_raw, str):
                authors_raw = [a.strip() for a in authors_raw.split(',') if a.strip()]
            pdf_url_explicit = _content_value(content, 'pdf') or ''
            html_link = _content_value(content, 'html') or ''
            forum_id = note.get('id') or note.get('forum') or ''

            # Try to extract arxiv id from any URL field
            arxiv_id = _extract_arxiv_from_text(
                pdf_url_explicit if isinstance(pdf_url_explicit, str) else '',
                html_link if isinstance(html_link, str) else '',
                abstract,
            )

            # Decision / track from replies
            decision_text = ''
            track = ''
            details = note.get('details') or {}
            replies = details.get('replies') or []
            for r in replies:
                inv = r.get('invitation') or ''
                if 'Decision' in inv or '/Decision' in inv:
                    rc = r.get('content') or {}
                    decision_text = _content_value(rc, 'decision') or ''
                    break
            if decision_text:
                low = decision_text.lower()
                if 'oral' in low:
                    track = 'Oral'
                elif 'spotlight' in low:
                    track = 'Spotlight'
                elif 'accept' in low:
                    track = 'Poster'
                elif 'reject' in low:
                    track = 'Reject'
                elif 'withdraw' in low:
                    track = 'Withdrawn'

            out.append({
                'source_type': 'openreview',
                'source_id': forum_id,
                'arxiv_id': arxiv_id,
                'title': title.strip().replace('\n', ' '),
                'abstract': (abstract or '').strip().replace('\n', ' ')[:2000],
                'authors': authors_raw,
                'pdf_url': f'https://openreview.net/pdf?id={forum_id}',
                'html_url': f'https://openreview.net/forum?id={forum_id}',
                'venue': venue_simple,
                'year': year,
                'decision': decision_text,
                'track': track,
                'upvotes': 0,
                'citation_count': None,
            })
        if len(notes) < page:
            break
        offset += page

    print(f'    ✅ {len(out)} notes from {venue_slug}/{year}')
    return out


# ──────────────────────────────────────────
# 2) Semantic Scholar fetchers
# ──────────────────────────────────────────
def _s2_headers() -> Dict[str, str]:
    h = dict(HEADERS)
    if S2_API_KEY:
        h['x-api-key'] = S2_API_KEY
    return h


def _s2_request(url: str, params: Dict[str, Any] | None = None,
                method: str = 'GET', body: Any = None,
                max_attempts: int = 3) -> Optional[dict]:
    """Wrapper around S2 API with exponential backoff (2/4/8s)."""
    delay = 2.0
    for attempt in range(1, max_attempts + 1):
        try:
            if method == 'GET':
                resp = requests.get(url, params=params,
                                    headers=_s2_headers(), timeout=30)
            else:
                resp = requests.post(url, params=params, json=body,
                                     headers=_s2_headers(), timeout=30)
        except Exception as e:
            print(f'    ⚠️ S2 HTTP error: {e}')
            time.sleep(delay)
            delay *= 2
            continue
        if resp.status_code == 200:
            time.sleep(1.0)  # 1 req/sec sustained
            return resp.json()
        if resp.status_code == 429 or resp.status_code >= 500:
            print(f'    ⚠️ S2 {resp.status_code}, retry in {delay}s')
            time.sleep(delay)
            delay *= 2
            continue
        # Other 4xx — fatal
        print(f'    ⚠️ S2 {resp.status_code}: {resp.text[:200]}')
        return None
    return None


def fetch_s2_venue(venue: str, year: int,
                   recent_days: int = 60,
                   max_pages: int = 5) -> List[Dict[str, Any]]:
    """Fetch papers from Semantic Scholar for a given venue+year."""
    print(f'  📥 S2: venue={venue} year>={year}')
    fields = (
        'paperId,title,abstract,authors,year,venue,externalIds,'
        'citationCount,influentialCitationCount,publicationDate'
    )
    base_params = {
        'venue': venue,
        'year': f'{year}-',
        'fields': fields,
        'limit': 1000,
    }

    out: List[Dict[str, Any]] = []
    token: Optional[str] = None
    for _ in range(max_pages):
        params = dict(base_params)
        if token:
            params['token'] = token
        data = _s2_request(S2_BULK_API, params=params)
        if not data:
            break
        items = data.get('data') or []
        if not items:
            break
        cutoff = None
        if recent_days > 0:
            cutoff = (datetime.utcnow() - timedelta(days=recent_days)).date()
        for item in items:
            ext = item.get('externalIds') or {}
            arxiv_id = ext.get('ArXiv') or ext.get('arXiv')
            pub_date = item.get('publicationDate')
            if cutoff and pub_date:
                try:
                    d = datetime.fromisoformat(pub_date).date()
                    if d < cutoff:
                        continue
                except Exception:
                    pass
            authors = [a.get('name', '') for a in (item.get('authors') or []) if a.get('name')]
            title = (item.get('title') or '').strip().replace('\n', ' ')
            if not title:
                continue
            out.append({
                'source_type': 's2',
                'source_id': item.get('paperId') or '',
                's2_paper_id': item.get('paperId') or '',
                'arxiv_id': arxiv_id,
                'title': title,
                'abstract': (item.get('abstract') or '').strip().replace('\n', ' ')[:2000],
                'authors': authors,
                'pdf_url': f'https://arxiv.org/pdf/{arxiv_id}.pdf' if arxiv_id else '',
                'html_url': f'https://www.semanticscholar.org/paper/{item.get("paperId", "")}',
                'venue': normalize_venue(item.get('venue') or venue),
                'year': item.get('year') or year,
                'decision': 'Accept-Poster',
                'track': 'Poster',
                'upvotes': 0,
                'citation_count': item.get('citationCount') or 0,
            })
        token = data.get('token')
        if not token:
            break

    print(f'    ✅ {len(out)} papers from S2/{venue}/{year}')
    return out


def enrich_citations(arxiv_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Refresh citationCount for a batch of arxiv ids via S2 batch endpoint."""
    if not arxiv_ids:
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    fields = 'citationCount,influentialCitationCount,externalIds,venue'
    for i in range(0, len(arxiv_ids), 100):
        chunk = arxiv_ids[i:i + 100]
        body = {'ids': [f'ARXIV:{aid}' for aid in chunk]}
        data = _s2_request(S2_BATCH_API, params={'fields': fields},
                           method='POST', body=body)
        if not data:
            continue
        for j, item in enumerate(data):
            if not item or not isinstance(item, dict):
                continue
            aid = chunk[j]
            out[aid] = {
                's2_paper_id': item.get('paperId'),
                'citation_count': item.get('citationCount') or 0,
                'influential_citation_count': item.get('influentialCitationCount') or 0,
                'venue': normalize_venue(item.get('venue') or ''),
            }
    return out


# ──────────────────────────────────────────
# DB upsert with 3-stage dedup
# ──────────────────────────────────────────
async def _find_paper_id(conn: asyncpg.Connection,
                          rec: Dict[str, Any]) -> Optional[int]:
    """3-stage matching: arxiv_id → (source_type, source_id) → title_key."""
    aid = rec.get('arxiv_id')
    if aid:
        row = await conn.fetchrow(
            "SELECT id FROM papers WHERE arxiv_id = $1", aid)
        if row:
            return row['id']
    src_type = rec.get('source_type')
    src_id = rec.get('source_id')
    if src_type and src_id:
        row = await conn.fetchrow(
            "SELECT id FROM papers WHERE source_type = $1 AND source_id = $2",
            src_type, src_id)
        if row:
            return row['id']
    tk = title_key(rec.get('title', ''), rec.get('authors') or [])
    if tk:
        row = await conn.fetchrow(
            "SELECT id FROM papers WHERE title_key = $1", tk)
        if row:
            return row['id']
    return None


async def upsert_paper(conn: asyncpg.Connection,
                        rec: Dict[str, Any]) -> Tuple[Optional[int], str]:
    """Insert or update a paper. Returns (paper_id, action)."""
    pid = await _find_paper_id(conn, rec)
    tk = title_key(rec.get('title', ''), rec.get('authors') or [])
    authors_json = json.dumps(rec.get('authors') or [])

    if pid:
        # ENRICH: pick longer abstract, fill missing arxiv/s2 ids
        existing = await conn.fetchrow("""
            SELECT abstract, arxiv_id, s2_paper_id, source_type, source_id,
                   citation_count, venue, year
              FROM papers WHERE id = $1
        """, pid)
        new_abs = rec.get('abstract') or ''
        old_abs = existing['abstract'] or ''
        better_abs = new_abs if len(new_abs) > len(old_abs) else old_abs
        new_arxiv = rec.get('arxiv_id') or existing['arxiv_id']
        new_s2 = rec.get('s2_paper_id') or existing['s2_paper_id']
        new_venue = rec.get('venue') or existing['venue']
        new_year = rec.get('year') or existing['year']
        cite_new = rec.get('citation_count')
        new_cite = cite_new if cite_new is not None else (existing['citation_count'] or 0)
        cite_ts = "NOW()" if cite_new is not None else "citation_count_updated_at"
        try:
            await conn.execute(f"""
                UPDATE papers
                   SET abstract = $1,
                       arxiv_id = COALESCE($2, arxiv_id),
                       s2_paper_id = COALESCE($3, s2_paper_id),
                       venue = COALESCE($4, venue),
                       year = COALESCE($5, year),
                       citation_count = $6,
                       citation_count_updated_at = {cite_ts},
                       title_key = COALESCE(title_key, $7),
                       updated_at = NOW()
                 WHERE id = $8
            """, better_abs, new_arxiv, new_s2, new_venue, new_year,
                 new_cite, tk, pid)
        except Exception as e:
            print(f'    ⚠️ update paper id={pid}: {e}')
        return pid, 'updated'

    # INSERT — papers.arxiv_id NOT NULL 제약. S2 paper 중 arxiv 없는 건 skip.
    if not rec.get('arxiv_id'):
        return None, 'skipped-no-arxiv'

    try:
        pub_date = datetime.utcnow()
        new_id = await conn.fetchval("""
            INSERT INTO papers (arxiv_id, title, abstract, authors, categories,
                                venue, year, citation_count,
                                citation_count_updated_at,
                                pdf_url, html_url, published_date,
                                source_type, source_id, s2_paper_id, title_key,
                                created_at, updated_at)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb,
                    $6, $7::int, $8::int,
                    CASE WHEN $8::int IS NOT NULL THEN NOW() ELSE NULL END,
                    $9, $10, $11, $12, $13, $14, $15, NOW(), NOW())
            RETURNING id
        """,
            rec.get('arxiv_id'),
            rec.get('title', '')[:2000],
            rec.get('abstract', ''),
            authors_json,
            json.dumps(rec.get('categories') or []),
            rec.get('venue'),
            rec.get('year'),
            rec.get('citation_count'),
            rec.get('pdf_url', ''),
            rec.get('html_url', ''),
            pub_date,
            rec.get('source_type'),
            rec.get('source_id'),
            rec.get('s2_paper_id'),
            tk,
        )
        return new_id, 'inserted'
    except asyncpg.UniqueViolationError:
        # race condition on arxiv_id — re-find
        pid = await _find_paper_id(conn, rec)
        return pid, 'race-skipped'
    except Exception as e:
        print(f'    ⚠️ insert error ({rec.get("source_type")}/{rec.get("source_id")}): {e}')
        return None, 'error'


async def upsert_venue_acceptance(conn: asyncpg.Connection,
                                   paper_id: int,
                                   venue: str, year: Optional[int],
                                   track: str, decision: str,
                                   source: str) -> None:
    if not venue or paper_id is None:
        return
    # Withdrawn → remove any prior acceptance for this venue/year
    if track == 'Withdrawn' or (decision and 'withdraw' in decision.lower()):
        await conn.execute("""
            DELETE FROM venue_acceptances
             WHERE paper_id = $1 AND venue = $2 AND year = $3
        """, paper_id, venue, year)
        return
    # Reject → don't record (we only keep acceptances)
    if track == 'Reject':
        return
    try:
        await conn.execute("""
            INSERT INTO venue_acceptances (paper_id, venue, year, track, decision, source)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (paper_id, venue, year) DO UPDATE
              SET track = EXCLUDED.track,
                  decision = EXCLUDED.decision,
                  source = EXCLUDED.source,
                  fetched_at = NOW()
        """, paper_id, venue, year, track or 'Poster', decision or '', source)
    except Exception as e:
        print(f'    ⚠️ venue_acceptance: {e}')


async def ingest_records(conn: asyncpg.Connection,
                          records: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counters = {'inserted': 0, 'updated': 0, 'error': 0,
                'accepted': 0, 'skipped': 0}
    for rec in records:
        pid, action = await upsert_paper(conn, rec)
        counters[action if action in counters else 'skipped'] = \
            counters.get(action if action in counters else 'skipped', 0) + 1
        if pid is None:
            continue
        venue = rec.get('venue')
        track = rec.get('track') or ''
        decision = rec.get('decision') or ''
        source = rec.get('source_type') or ''
        if venue and (track or decision):
            await upsert_venue_acceptance(
                conn, pid, venue, rec.get('year'),
                track, decision, source,
            )
            if track and track not in ('Reject', 'Withdrawn'):
                counters['accepted'] += 1
    return counters


# ──────────────────────────────────────────
# Public entry points used by daily_cron
# ──────────────────────────────────────────
async def run_openreview_weekly(conn: asyncpg.Connection,
                                 since_days: int = 7) -> Dict[str, int]:
    """Iterate all configured OpenReview venues. Cheap when no new replies."""
    await ensure_schema(conn)
    all_records: List[Dict[str, Any]] = []
    for venue_name, venue_slug, year in OPENREVIEW_VENUES:
        if year is None:
            continue  # TMLR rolling — TODO: separate fetcher
        try:
            recs = fetch_openreview_venue(venue_slug, year, since_days=since_days)
        except Exception as e:
            print(f'  ⚠️ openreview {venue_slug}/{year}: {e}')
            continue
        all_records.extend(recs)
    counters = await ingest_records(conn, all_records)
    print(f'  📊 openreview ingest: {counters}')
    return counters


async def run_s2_daily(conn: asyncpg.Connection,
                        weekday: Optional[int] = None,
                        year: Optional[int] = None,
                        recent_days: int = 60) -> Dict[str, int]:
    """Fetch the venues scheduled for today's weekday."""
    await ensure_schema(conn)
    wd = weekday if weekday is not None else datetime.utcnow().weekday()
    venues = S2_VENUES_BY_WEEKDAY.get(wd, [])
    yr = year or datetime.utcnow().year
    all_records: List[Dict[str, Any]] = []
    for v in venues:
        try:
            recs = fetch_s2_venue(v, yr, recent_days=recent_days)
        except Exception as e:
            print(f'  ⚠️ s2 {v}/{yr}: {e}')
            continue
        all_records.extend(recs)
    counters = await ingest_records(conn, all_records)
    print(f'  📊 s2 ingest ({venues}): {counters}')
    return counters


async def run_citation_refresh(conn: asyncpg.Connection,
                                since_days: int = 30,
                                limit: int = 500) -> int:
    """Refresh citation_count for recent papers that have an arxiv_id."""
    await ensure_schema(conn)
    rows = await conn.fetch("""
        SELECT arxiv_id FROM papers
         WHERE arxiv_id IS NOT NULL
           AND (citation_count_updated_at IS NULL
                OR citation_count_updated_at < NOW() - INTERVAL '7 days')
           AND (created_at >= NOW() - ($1::int * INTERVAL '1 day')
                OR published_date >= NOW() - ($1::int * INTERVAL '1 day'))
         ORDER BY created_at DESC
         LIMIT $2
    """, since_days, limit)
    arxiv_ids = [r['arxiv_id'] for r in rows]
    if not arxiv_ids:
        print('  📊 citation refresh: no candidates')
        return 0
    print(f'  🔄 citation refresh: {len(arxiv_ids)} papers')
    enrich = enrich_citations(arxiv_ids)
    updated = 0
    for aid, info in enrich.items():
        try:
            await conn.execute("""
                UPDATE papers
                   SET citation_count = $1,
                       s2_paper_id = COALESCE(s2_paper_id, $2),
                       venue = COALESCE(NULLIF($3, ''), venue),
                       citation_count_updated_at = NOW()
                 WHERE arxiv_id = $4
            """, info.get('citation_count') or 0,
                 info.get('s2_paper_id'),
                 info.get('venue') or '',
                 aid)
            updated += 1
        except Exception as e:
            print(f'    ⚠️ update {aid}: {e}')
    print(f'  📊 citation refresh: {updated} updated')
    return updated


# ──────────────────────────────────────────
# Helpers consumed by daily_cron for v4 scoring
# ──────────────────────────────────────────
async def load_acceptance_lookup(conn: asyncpg.Connection,
                                  arxiv_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Return {arxiv_id: [{venue, track, year}, ...]} for given arxiv ids."""
    if not arxiv_ids:
        return {}
    rows = await conn.fetch("""
        SELECT p.arxiv_id, va.venue, va.track, va.year
          FROM venue_acceptances va
          JOIN papers p ON p.id = va.paper_id
         WHERE p.arxiv_id = ANY($1::text[])
    """, arxiv_ids)
    out: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        out.setdefault(r['arxiv_id'], []).append({
            'venue': r['venue'],
            'track': r['track'] or 'Poster',
            'year': r['year'],
        })
    return out


async def load_citation_lookup(conn: asyncpg.Connection,
                                arxiv_ids: List[str]) -> Dict[str, int]:
    if not arxiv_ids:
        return {}
    rows = await conn.fetch("""
        SELECT arxiv_id, citation_count
          FROM papers WHERE arxiv_id = ANY($1::text[])
    """, arxiv_ids)
    return {r['arxiv_id']: (r['citation_count'] or 0) for r in rows}


def compute_venue_bonus(acceptances: List[Dict[str, Any]]) -> Tuple[float, str]:
    """Pick the max venue_bonus across accepted venues. Returns (bonus, label)."""
    best = 0.0
    label = ''
    for a in acceptances or []:
        track = a.get('track') or 'Poster'
        base = TRACK_BASE_BONUS.get(track, 0.0)
        mul = VENUE_TIER_MUL.get(a.get('venue') or '', 0.8)
        b = base * mul
        if b > best:
            best = b
            label = f"{a.get('venue')} {track}"
    return min(best, 10.0), label


def compute_citation_bonus(citation_count: int) -> float:
    import math
    if not citation_count or citation_count <= 0:
        return 0.0
    return min(math.log10(1 + citation_count) * 1.5, 6.0)


# ──────────────────────────────────────────
# CLI
# ──────────────────────────────────────────
async def _cli() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=[
        'openreview', 's2', 'enrich-citations', 'daily-rotation', 'migrate',
    ], default='daily-rotation')
    p.add_argument('--venue', help='ICLR.cc/2026/Conference or CVPR (s2)')
    p.add_argument('--year', type=int, default=datetime.utcnow().year)
    p.add_argument('--since-days', type=int, default=7)
    p.add_argument('--recent-days', type=int, default=60)
    p.add_argument('--limit', type=int, default=500)
    args = p.parse_args()

    conn = await asyncpg.connect(DB_URL)
    try:
        await ensure_schema(conn)

        if args.mode == 'migrate':
            print('✅ schema ensured')
            return

        if args.mode == 'openreview':
            if args.venue:
                # accept either 'ICLR.cc/2026/Conference' or 'ICLR.cc'
                parts = args.venue.split('/')
                slug = parts[0]
                yr = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else args.year
                recs = fetch_openreview_venue(slug, yr, since_days=args.since_days)
                counters = await ingest_records(conn, recs)
                print(f'  📊 ingest: {counters}')
            else:
                await run_openreview_weekly(conn, since_days=args.since_days)
            return

        if args.mode == 's2':
            if args.venue:
                recs = fetch_s2_venue(args.venue, args.year,
                                      recent_days=args.recent_days)
                counters = await ingest_records(conn, recs)
                print(f'  📊 ingest: {counters}')
            else:
                await run_s2_daily(conn, year=args.year,
                                   recent_days=args.recent_days)
            return

        if args.mode == 'enrich-citations':
            await run_citation_refresh(conn,
                                       since_days=args.since_days or 30,
                                       limit=args.limit)
            return

        if args.mode == 'daily-rotation':
            await run_s2_daily(conn, recent_days=args.recent_days)
            await run_citation_refresh(conn, since_days=30, limit=args.limit)
            return
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(_cli())

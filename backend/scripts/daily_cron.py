#!/usr/bin/env python3
"""
Daily Paper + Trending Collector (cron용)
매일 새벽 3시 실행: 최신 논문 100개 수집 + 다중 소스 trending 업데이트
소스: arXiv, HuggingFace, Semantic Scholar, Papers With Code
"""
import asyncio
import math
import sys
import os
import json
import re
import requests
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('HF_HOME', '/home/juhyun/hf_cache')

import asyncpg

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
ARXIV_API = 'http://export.arxiv.org/api/query'
HEADERS = {'User-Agent': 'HotPaper/1.0 (https://hotpaper.ai)'}

CATEGORIES = [
    'cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.IR',
    'cs.HC', 'cs.RO', 'cs.NE', 'stat.ML',
]

SOURCE_WEIGHTS = {
    'huggingface': 1.8,
    'arxiv_rss': 1.2,
    'crossref': 1.5,
    'openreview': 2.0,
    's2': 1.6,
}

# Sibling-module imports: ensure scripts/ is importable.
sys.path.insert(0, os.path.dirname(__file__))

# Top-venue helpers (OpenReview + S2). Wrapped in try so that an environment
# missing requests still loads the legacy collector.
try:
    from fetch_top_venues import (
        ensure_schema as _tv_ensure_schema,
        run_openreview_weekly as _tv_run_openreview,
        run_s2_daily as _tv_run_s2,
        run_citation_refresh as _tv_run_citations,
        load_acceptance_lookup as _tv_load_acceptances,
        load_citation_lookup as _tv_load_citations,
        compute_venue_bonus as _tv_venue_bonus,
        compute_citation_bonus as _tv_citation_bonus,
    )
    _TOP_VENUES_AVAILABLE = True
except Exception as _e:  # pragma: no cover
    print(f'⚠️ fetch_top_venues import failed: {_e}')
    _TOP_VENUES_AVAILABLE = False


# ──────────────────────────────────────────
# 1. arXiv 최신 논문 수집
# ──────────────────────────────────────────
async def fetch_arxiv_papers(max_results=100):
    cat_query = '+OR+'.join(f'cat:{c}' for c in CATEGORIES)
    url = f'{ARXIV_API}?search_query={cat_query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}'
    try:
        resp = requests.get(url, timeout=60, headers=HEADERS)
        if resp.status_code != 200:
            print(f'❌ arXiv API 실패: {resp.status_code}')
            return []

        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        papers = []
        for entry in root.findall('atom:entry', ns):
            arxiv_id = entry.find('atom:id', ns).text.split('/abs/')[-1].split('v')[0]
            title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
            abstract = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
            published = entry.find('atom:published', ns).text[:10]
            authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)]
            categories = [c.get('term') for c in entry.findall('atom:category', ns)]

            papers.append({
                'arxiv_id': arxiv_id, 'title': title, 'abstract': abstract[:2000],
                'authors': authors, 'categories': categories,
                'published_date': published,
                'pdf_url': f'https://arxiv.org/pdf/{arxiv_id}.pdf',
                'arxiv_url': f'https://arxiv.org/abs/{arxiv_id}',
            })

        print(f'✅ arXiv: {len(papers)}개 논문 수집')
        return papers
    except Exception as e:
        print(f'❌ arXiv 수집 실패: {e}')
        return []


# ──────────────────────────────────────────
# 2. HuggingFace Daily Papers
# ──────────────────────────────────────────
async def fetch_hf_trending():
    try:
        resp = requests.get('https://huggingface.co/api/daily_papers', timeout=15, headers=HEADERS)
        if resp.status_code != 200:
            return []

        data = resp.json()
        papers = []
        for item in (data if isinstance(data, list) else data.get('papers', [])):
            paper_info = item.get('paper', item)
            arxiv_id = str(paper_info.get('id', '')).replace('arXiv:', '').strip()
            if not arxiv_id or len(arxiv_id) < 5:
                continue
            # HF API: upvotes는 paper 객체 내부에 중첩돼 있음
            upvotes = paper_info.get('upvotes', item.get('upvotes', 0)) or 0
            papers.append({
                'arxiv_id': arxiv_id,
                'title': paper_info.get('title', ''),
                'abstract': paper_info.get('summary', '')[:2000],
                'upvotes': upvotes,
                'source': 'huggingface',
            })

        print(f'✅ HuggingFace: {len(papers)}개')
        return papers
    except Exception as e:
        print(f'❌ HuggingFace 실패: {e}')
        return []


# ──────────────────────────────────────────
# 3. arXiv RSS - 카테고리별 최신 논문
# ──────────────────────────────────────────
async def fetch_arxiv_rss():
    import xml.etree.ElementTree as ET
    papers = []
    rss_cats = ['cs.AI', 'cs.LG', 'cs.CL', 'cs.CV']

    for cat in rss_cats:
        try:
            resp = requests.get(f'https://rss.arxiv.org/rss/{cat}', timeout=15, headers=HEADERS)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.text)
            items = root.findall('.//item')

            for item in items[:20]:
                title = item.find('title').text or ''
                link = item.find('link').text or ''
                desc = item.find('description').text or ''

                arxiv_id = link.split('/')[-1] if link else ''
                if not arxiv_id or len(arxiv_id) < 5:
                    continue

                # 중복 체크
                if any(p['arxiv_id'] == arxiv_id for p in papers):
                    continue

                papers.append({
                    'arxiv_id': arxiv_id,
                    'title': title.replace('\n', ' ').strip(),
                    'abstract': desc[:2000],
                    'upvotes': 0,  # RSS는 인기 신호 없음 — cross-platform 카운트용
                    'source': 'arxiv_rss',
                })

            await asyncio.sleep(0.5)  # rate limit
        except Exception as e:
            print(f'  ⚠️ arXiv RSS {cat}: {e}')

    print(f'✅ arXiv RSS: {len(papers)}개')
    return papers


# ──────────────────────────────────────────
# 4. Crossref - 최근 인용 급증 AI 논문
# ──────────────────────────────────────────
async def fetch_crossref_trending():
    try:
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m')
        resp = requests.get(
            'https://api.crossref.org/works',
            params={
                'query': 'artificial intelligence machine learning deep learning',
                'filter': f'from-pub-date:{month_ago},type:journal-article',
                'sort': 'is-referenced-by-count',
                'order': 'desc',
                'rows': 30,
                'select': 'DOI,title,is-referenced-by-count,abstract',
            },
            timeout=20, headers=HEADERS
        )
        if resp.status_code != 200:
            print(f'❌ Crossref API: {resp.status_code}')
            return []

        data = resp.json()
        items = data.get('message', {}).get('items', [])

        papers = []
        for item in items:
            doi = item.get('DOI', '')
            titles = item.get('title', [])
            title = titles[0] if titles else ''
            citations = item.get('is-referenced-by-count', 0)
            abstract = item.get('abstract', '')

            # DOI에서 arXiv ID 추출 시도
            arxiv_id = ''
            if '10.48550/arxiv.' in doi.lower():
                arxiv_id = doi.split('.')[-1]
            elif 'arxiv' in doi.lower():
                match = re.search(r'(\d{4}\.\d{4,5})', doi)
                if match:
                    arxiv_id = match.group(1)

            if not arxiv_id or len(arxiv_id) < 5:
                continue

            papers.append({
                'arxiv_id': arxiv_id,
                'title': title,
                'abstract': abstract[:2000] if abstract else '',
                'upvotes': min(citations * 2, 200),  # 인용수 기반
                'source': 'crossref',
            })

        print(f'✅ Crossref: {len(papers)}개')
        return papers
    except Exception as e:
        print(f'❌ Crossref 실패: {e}')
        return []


# ──────────────────────────────────────────
# DB 저장
# ──────────────────────────────────────────
async def save_papers(conn, papers):
    saved, skipped = 0, 0
    for p in papers:
        existing = await conn.fetchrow("SELECT id FROM papers WHERE arxiv_id = $1", p['arxiv_id'])
        if existing:
            skipped += 1
            continue
        try:
            await conn.execute("""
                INSERT INTO papers (arxiv_id, title, abstract, authors, categories,
                                    published_date, pdf_url, html_url, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
            """,
                p['arxiv_id'], p['title'], p['abstract'],
                json.dumps(p.get('authors', [])), json.dumps(p.get('categories', [])),
                datetime.strptime(p['published_date'], '%Y-%m-%d') if p.get('published_date') else datetime.now(),
                p.get('pdf_url', ''), p.get('arxiv_url', ''),
            )
            saved += 1
        except Exception as e:
            print(f'  ⚠️ {p["arxiv_id"]} 저장 실패: {e}')

    print(f'📊 논문 저장: {saved}개 신규, {skipped}개 중복')
    return saved


async def save_trending(conn, all_source_papers, featured_top_n=25,
                         authors_lookup=None,
                         acceptance_lookup=None,
                         citation_lookup=None):
    """다중 소스 통합 trending 저장 + featured 큐레이션 (v4 scoring)."""
    authors_lookup = authors_lookup or {}
    acceptance_lookup = acceptance_lookup or {}
    citation_lookup = citation_lookup or {}
    # HAI scoring (lazy import to keep this script standalone-runnable)
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from app.core.hai_config import is_hai_author, hai_keyword_score
    except Exception:
        is_hai_author = lambda _a: False
        hai_keyword_score = lambda _t, _a: 0

    today = datetime.now().date()

    # 오늘 trending 초기화
    await conn.execute("DELETE FROM trending_papers WHERE DATE(created_at) = $1", today)

    # 논문별 점수 통합
    paper_scores = defaultdict(lambda: {
        'title': '', 'sources': [], 'total_score': 0.0, 'abstract': '',
        'upvotes': 0,
    })

    for p in all_source_papers:
        aid = p['arxiv_id']
        source = p['source']
        weight = SOURCE_WEIGHTS.get(source, 1.0)
        upvotes = max(0, p.get('upvotes', 0))
        score = max(0.1, upvotes) * weight

        paper_scores[aid]['total_score'] += score
        paper_scores[aid]['upvotes'] = max(paper_scores[aid]['upvotes'], upvotes)
        if source not in paper_scores[aid]['sources']:
            paper_scores[aid]['sources'].append(source)
        if len(p.get('title', '')) > len(paper_scores[aid]['title']):
            paper_scores[aid]['title'] = p['title']
        if len(p.get('abstract', '')) > len(paper_scores[aid]['abstract']):
            paper_scores[aid]['abstract'] = p['abstract']

    # 크로스 플랫폼 보너스 (total_score는 trending_papers 컬럼용 — 기존 호환)
    for aid, data in paper_scores.items():
        if len(data['sources']) >= 3:
            data['total_score'] *= 1.5
        elif len(data['sources']) >= 2:
            data['total_score'] *= 1.3

    # ─────────────────────────────────────────────────────────────
    # Featured 선정 점수 (v4 — venue + citation 추가)
    # ─────────────────────────────────────────────────────────────
    # featured_score = base + lab_bonus + venue_bonus + citation_bonus
    #   popularity   = log10(1 + upvotes) * 2.0
    #   cross_mul    = {1:1.0, 2:1.8, 3:2.6, 4:3.2, 5:3.6}  (5 src 대비)
    #   hf_bonus     = 1.0 if 'huggingface' in sources else 0
    #   base         = (popularity + 1.0) * cross_mul + hf_bonus
    #
    #   lab_bonus    = (5 if 회원) + min(kw, 5) * 1.5         # ≤ 12.5
    #   venue_bonus  = max venue track bonus * tier_mul       # ≤ 10
    #                  Oral 8 / Spotlight 5 / Poster 3 / Findings 2 / Workshop 1
    #   citation_bonus = min(log10(1 + s2_citation) * 1.5, 6) # ≤ 6
    #
    # 캘리브레이션 예시:
    #   ICLR Oral + HF 300 + 4-source: 7.0 + 8.0 + 0 ≈ 22  → top
    #   HF 2000 upvote, acceptance 없음: 8.6 + 0 + 0  ≈ 8.6 → 인기로 살아남음
    #   arxiv-only, citation 5000:       1.0 + 0 + 5.6 ≈ 6.6 → mid-tier rescued
    # ─────────────────────────────────────────────────────────────
    for aid, data in paper_scores.items():
        # 저자 정보는 in-memory lookup 우선 (papers 테이블에 아직 없을 수 있음)
        authors = authors_lookup.get(aid, [])
        if not authors:
            row = await conn.fetchrow(
                "SELECT authors FROM papers WHERE arxiv_id = $1", aid
            )
            if row and row['authors']:
                try:
                    authors = (
                        json.loads(row['authors'])
                        if isinstance(row['authors'], str)
                        else row['authors']
                    )
                except Exception:
                    authors = []
        data['authors'] = authors

        hai_kw = hai_keyword_score(data['title'], data['abstract'])
        is_member = is_hai_author(authors)
        is_hai = is_member or hai_kw >= 2
        data['hai_score'] = hai_kw + (10 if is_member else 0)
        data['is_hai'] = is_hai

        # 1) 인기 신호 (log 정규화 — outlier 완화)
        upvotes = max(0, data['upvotes'])
        popularity = math.log10(1 + upvotes) * 2.0  # 0→0, 10→2.1, 100→4.0, 500→5.4

        # 2) 크로스 플랫폼 multiplier (consensus = 최강 신호)
        n_src = len(set(data['sources']))
        cross_mul = {1: 1.0, 2: 1.8, 3: 2.6, 4: 3.2, 5: 3.6}.get(n_src, 3.6)

        # 3) HF Daily Papers 큐레이션 보너스 (사람이 픽한 신호)
        hf_bonus = 1.0 if 'huggingface' in data['sources'] else 0.0

        # 4) base = (인기 + 1.0 floor) × consensus + HF 큐레이션
        base = (popularity + 1.0) * cross_mul + hf_bonus

        # 5) Lab 보너스 (회원 floor + 키워드 비례, 캡 12.5)
        lab_bonus = 0.0
        if is_member:
            lab_bonus += 5.0
        lab_bonus += min(hai_kw, 5) * 1.5  # 키워드 최대 +7.5
        lab_bonus = min(lab_bonus, 12.5)

        # 6) Venue acceptance 보너스 (OpenReview/S2 신호, 캡 10)
        acceptances = acceptance_lookup.get(aid, [])
        if _TOP_VENUES_AVAILABLE and acceptances:
            venue_bonus, venue_label = _tv_venue_bonus(acceptances)
        else:
            venue_bonus, venue_label = 0.0, ''
        data['venue_bonus'] = venue_bonus
        data['venue_label'] = venue_label

        # 7) Citation 보너스 (S2 citation_count, 캡 6)
        cite = citation_lookup.get(aid, 0) or 0
        if _TOP_VENUES_AVAILABLE:
            citation_bonus = _tv_citation_bonus(cite)
        else:
            citation_bonus = 0.0
        data['citation_count'] = cite
        data['citation_bonus'] = citation_bonus

        data['featured_score'] = base + lab_bonus + venue_bonus + citation_bonus

    # 정렬 및 저장
    ranked = sorted(
        paper_scores.items(),
        key=lambda x: x[1]['featured_score'],
        reverse=True,
    )

    saved = 0
    featured_ids = set()
    for rank, (aid, data) in enumerate(ranked[:100], 1):
        is_featured = rank <= featured_top_n
        if is_featured:
            featured_ids.add(aid)
        try:
            await conn.execute("""
                INSERT INTO trending_papers (arxiv_id, title, sources,
                                              trending_score, final_score, rank,
                                              multi_source_bonus, date, created_at,
                                              featured_score, is_featured, is_hai,
                                              hai_score, upvotes)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(),
                        $9, $10, $11, $12, $13)
            """,
                aid, data['title'], json.dumps(data['sources']),
                data['total_score'], data['total_score'], rank,
                1.5 if len(data['sources']) >= 3 else (1.3 if len(data['sources']) >= 2 else 1.0),
                today,
                data['featured_score'], is_featured, data['is_hai'],
                data['hai_score'], data['upvotes'],
            )
            saved += 1
        except Exception as e:
            print(f'  ⚠️ trending {aid} 저장 실패: {e}')

    source_counts = defaultdict(int)
    for data in paper_scores.values():
        for s in data['sources']:
            source_counts[s] += 1

    print(f'🔥 Trending 저장: {saved}개 (featured: {len(featured_ids)})')
    print(f'   소스별: {dict(source_counts)}')
    multi = sum(1 for d in paper_scores.values() if len(d['sources']) >= 2)
    print(f'   크로스 플랫폼: {multi}개 논문')
    hai_count = sum(1 for d in paper_scores.values() if d.get('is_hai'))
    print(f'   HAI 매칭: {hai_count}개 논문')
    return saved, featured_ids, paper_scores


# ──────────────────────────────────────────
# Main
# ──────────────────────────────────────────
def fetch_authors_batch(arxiv_ids):
    """Batch-fetch authors from arXiv API. Returns dict[arxiv_id] -> list[str]."""
    if not arxiv_ids:
        return {}
    import xml.etree.ElementTree as ET
    import time as _t
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    lookup = {}
    for i in range(0, len(arxiv_ids), 100):
        chunk = arxiv_ids[i:i + 100]
        url = f"{ARXIV_API}?id_list={','.join(chunk)}&max_results={len(chunk)}"
        try:
            resp = requests.get(url, timeout=30, headers=HEADERS)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.text)
            for entry in root.findall('a:entry', ns):
                id_el = entry.find('a:id', ns)
                if id_el is None:
                    continue
                m = re.search(r'/abs/([0-9]{4}\.[0-9]{4,5})', id_el.text or '')
                if not m:
                    continue
                aid = m.group(1)
                names = [
                    a.find('a:name', ns).text.strip()
                    for a in entry.findall('a:author', ns)
                    if a.find('a:name', ns) is not None
                ]
                if names:
                    lookup[aid] = names
            _t.sleep(3.5)
        except Exception as e:
            print(f'  ⚠️ author batch fetch error: {e}')
    return lookup


async def main():
    start = datetime.now()
    print(f'{"="*60}')
    print(f'🚀 Hot Paper Daily Collector (Top-25 only) - {start.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"="*60}')

    conn = await asyncpg.connect(DB_URL)

    # 0. Schema migration (idempotent — adds source_type/title_key/venue_acceptances)
    if _TOP_VENUES_AVAILABLE:
        try:
            await _tv_ensure_schema(conn)
        except Exception as e:
            print(f'⚠️ schema ensure failed: {e}')

    # 1. 다중 소스 Trending feeds 수집 (랭킹 풀)
    print('\n🔥 Step 1: 다중 소스 Trending feeds 수집 (랭킹용)...')
    hf_papers, rss_papers, crossref_papers = await asyncio.gather(
        fetch_hf_trending(),
        fetch_arxiv_rss(),
        fetch_crossref_trending(),
    )
    all_trending = hf_papers + rss_papers + crossref_papers

    # 1b. Top-venue fetchers (daily S2 rotation + citation refresh; OpenReview
    #     Monday-only by default to respect the conservative weekly cadence).
    conf_seed_before = 0
    conf_seed_after = 0
    if _TOP_VENUES_AVAILABLE:
        try:
            conf_seed_before = await conn.fetchval(
                "SELECT count(*) FROM venue_acceptances"
            ) or 0
        except Exception as e:
            print(f'  ⚠️ conf seed count (before): {e}')
        weekday = datetime.now().weekday()
        try:
            print('\n🏛  Step 1b: S2 venue rotation (weekday-scheduled)...')
            await _tv_run_s2(conn)
        except Exception as e:
            print(f'  ⚠️ s2 rotation: {e}')
        try:
            print('  🔄 Citation refresh (recent papers)...')
            await _tv_run_citations(conn, since_days=30, limit=300)
        except Exception as e:
            print(f'  ⚠️ citation refresh: {e}')
        # OpenReview weekly on Mondays (weekday == 0)
        if weekday == 0 or os.environ.get('FORCE_OPENREVIEW') == '1':
            try:
                print('\n📜 Step 1c: OpenReview weekly sweep...')
                await _tv_run_openreview(conn, since_days=14)
            except Exception as e:
                print(f'  ⚠️ openreview sweep: {e}')
        try:
            conf_seed_after = await conn.fetchval(
                "SELECT count(*) FROM venue_acceptances"
            ) or 0
        except Exception as e:
            print(f'  ⚠️ conf seed count (after): {e}')
        new_conf = max(0, conf_seed_after - conf_seed_before)
        print(f'   📊 venue_acceptances: {conf_seed_after} total '
              f'(+{new_conf} this run)')

    # 2. 랭킹 풀의 모든 arxiv id에 대해 저자 batch fetch (HAI 스코어링용)
    candidate_ids = sorted({
        p['arxiv_id'] for p in all_trending
        if p.get('title') and p.get('abstract')
        and re.match(r'^[0-9]{4}\.[0-9]{4,5}$', p.get('arxiv_id') or '')
    })
    print(f'\n📖 Step 2: 후보 {len(candidate_ids)}편의 저자 정보 batch fetch...')
    authors_lookup = fetch_authors_batch(candidate_ids)
    print(f'   ✅ 저자 매칭: {len(authors_lookup)}/{len(candidate_ids)}')

    # 2b. Acceptance + citation lookups for v4 scoring
    acceptance_lookup = {}
    citation_lookup = {}
    if _TOP_VENUES_AVAILABLE and candidate_ids:
        try:
            acceptance_lookup = await _tv_load_acceptances(conn, candidate_ids)
            citation_lookup = await _tv_load_citations(conn, candidate_ids)
            print(f'   ✅ acceptance hits: {len(acceptance_lookup)}, '
                  f'citation hits: {sum(1 for v in citation_lookup.values() if v > 0)}')
        except Exception as e:
            print(f'  ⚠️ acceptance/citation lookup: {e}')

    # 3. Featured Top 25 선정 (papers 저장 전에 랭킹)
    print('\n📊 Step 3: 통합 점수 계산 + Featured Top 25 선정 (v4)...')
    _, featured_ids, paper_scores = await save_trending(
        conn, all_trending, featured_top_n=25,
        authors_lookup=authors_lookup,
        acceptance_lookup=acceptance_lookup,
        citation_lookup=citation_lookup,
    )

    # 4. Top 25만 papers 테이블에 저장
    print(f'\n💾 Step 4: Featured Top {len(featured_ids)}편만 papers DB에 저장...')
    today_str = datetime.now().strftime('%Y-%m-%d')
    to_save = []
    for aid in featured_ids:
        data = paper_scores.get(aid, {})
        to_save.append({
            'arxiv_id': aid,
            'title': data.get('title', ''),
            'abstract': data.get('abstract', '')[:2000],
            'authors': authors_lookup.get(aid, data.get('authors', [])),
            'categories': [],
            'published_date': today_str,
            'pdf_url': f'https://arxiv.org/pdf/{aid}.pdf',
            'arxiv_url': f'https://arxiv.org/abs/{aid}',
        })
    new_count = await save_papers(conn, to_save)

    # 4a. P4 — Dynamic tag extraction (LLM keyword): featured Top 25에 적용.
    #     concepts/paper_concepts 테이블 활용. hai_topic hardcoded 점진 폐기.
    #     14B 모델이라 빠름 (편당 ~5초).
    try:
        os.environ.setdefault('TAG_MODEL', 'qwen3:14b')
        from extract_tags import extract_tags_for_paper
        tag_ok = 0
        for aid in featured_ids:
            try:
                tags = await extract_tags_for_paper(conn, aid)
                if tags:
                    tag_ok += 1
            except Exception as e:
                print(f'  tag {aid} err: {e}')
        print(f'  🏷  tags: {tag_ok}/{len(featured_ids)} featured papers tagged')
    except Exception as e:
        print(f'  ⚠️ tag extraction: {e}')

    # 4b. Semantic bridge — featured/conf seed centroid로 최근 arXiv 의미 검색.
    #     이상한 paper 거의 사라짐: 광범위 cs.* RSS 대신 의미적으로 가까운 신선분만.
    #     별도 source='semantic_bridge'로 trending_papers에 추가 (featured에 영향 X).
    bridge_added = 0
    try:
        from arxiv_semantic_bridge import run_semantic_bridge
        bridge_results = await run_semantic_bridge(
            conn, fresh_days=7, top_k=15, min_similarity=0.55,
        )
        if bridge_results:
            # papers 테이블에 이미 있는 것만 inject (없는 건 별도 fetch 필요 — 다음 단계)
            today = datetime.now().date()
            for aid, title, sim in bridge_results:
                exists = await conn.fetchrow(
                    "SELECT id FROM papers WHERE arxiv_id = $1", aid
                )
                if not exists:
                    continue
                # 중복 방지: 이미 오늘 trending에 있는지
                already = await conn.fetchrow(
                    "SELECT id FROM trending_papers WHERE arxiv_id=$1 AND date=$2",
                    aid, today
                )
                if already:
                    continue
                await conn.execute("""
                    INSERT INTO trending_papers (
                        arxiv_id, title, sources, trending_score, final_score,
                        rank, multi_source_bonus, date, created_at,
                        featured_score, is_featured, upvotes
                    ) VALUES ($1, $2, $3, $4, $5, $6, 1.0, $7, NOW(),
                              $8, FALSE, 0)
                """, aid, title, json.dumps(['semantic_bridge']),
                     sim * 10, sim * 10, 100 + bridge_added, today, sim * 10)
                bridge_added += 1
            print(f'  ✅ semantic_bridge inject: {bridge_added}편 (rank 100+)')
    except Exception as e:
        print(f'  ⚠️ semantic_bridge: {e}')

    # 5. 통계
    total = await conn.fetchval('SELECT count(*) FROM papers')
    trending_count = await conn.fetchval(
        "SELECT count(*) FROM trending_papers WHERE DATE(created_at) = $1",
        datetime.now().date()
    )

    # Conf-first quota stats (P1 visibility — no pipeline change yet).
    conf_in_featured = len(featured_ids & set(acceptance_lookup.keys())) \
        if acceptance_lookup else 0
    arxiv_pool = len(candidate_ids)
    new_conf_this_run = max(0, conf_seed_after - conf_seed_before)

    elapsed = (datetime.now() - start).total_seconds()
    print(f'\n{"="*60}')
    print(f'✅ 완료! ({elapsed:.1f}초)')
    print(f'   전체 논문: {total}개')
    print(f'   신규 추가: {new_count}개 (Top 25 only)')
    print(f'   오늘 Trending: {trending_count}개')
    print(f'   Active Sources: HuggingFace({len(hf_papers)}), arXiv RSS({len(rss_papers)}), Crossref({len(crossref_papers)})')
    print(f'✅ Conf seed: {new_conf_this_run} (total {conf_seed_after}) / '
          f'arXiv pool: {arxiv_pool} / '
          f'featured: {len(featured_ids)} (conf: {conf_in_featured}) / '
          f'semantic_bridge: {bridge_added}')
    print(f'{"="*60}')

    await conn.close()


if __name__ == '__main__':
    asyncio.run(main())

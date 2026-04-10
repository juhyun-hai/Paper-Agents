#!/usr/bin/env python3
"""
Daily Paper + Trending Collector (cron용)
매일 새벽 3시 실행: 최신 논문 100개 수집 + 다중 소스 trending 업데이트
소스: arXiv, HuggingFace, Semantic Scholar, Papers With Code
"""
import asyncio
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
}


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
            papers.append({
                'arxiv_id': arxiv_id,
                'title': paper_info.get('title', ''),
                'abstract': paper_info.get('summary', '')[:2000],
                'upvotes': item.get('upvotes', 0),
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
                    'upvotes': 5,  # RSS는 기본 점수
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


async def save_trending(conn, all_source_papers):
    """다중 소스 통합 trending 저장."""
    today = datetime.now().date()

    # 오늘 trending 초기화
    await conn.execute("DELETE FROM trending_papers WHERE DATE(created_at) = $1", today)

    # 논문별 점수 통합
    paper_scores = defaultdict(lambda: {
        'title': '', 'sources': [], 'total_score': 0.0, 'abstract': ''
    })

    for p in all_source_papers:
        aid = p['arxiv_id']
        source = p['source']
        weight = SOURCE_WEIGHTS.get(source, 1.0)
        score = max(0.1, p.get('upvotes', 0)) * weight

        paper_scores[aid]['total_score'] += score
        if source not in paper_scores[aid]['sources']:
            paper_scores[aid]['sources'].append(source)
        if len(p.get('title', '')) > len(paper_scores[aid]['title']):
            paper_scores[aid]['title'] = p['title']
        if len(p.get('abstract', '')) > len(paper_scores[aid]['abstract']):
            paper_scores[aid]['abstract'] = p['abstract']

    # 크로스 플랫폼 보너스
    for aid, data in paper_scores.items():
        if len(data['sources']) >= 3:
            data['total_score'] *= 1.5
        elif len(data['sources']) >= 2:
            data['total_score'] *= 1.3

    # 정렬 및 저장
    ranked = sorted(paper_scores.items(), key=lambda x: x[1]['total_score'], reverse=True)

    saved = 0
    for rank, (aid, data) in enumerate(ranked[:100], 1):
        try:
            await conn.execute("""
                INSERT INTO trending_papers (arxiv_id, title, sources,
                                              trending_score, final_score, rank,
                                              multi_source_bonus, date, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            """,
                aid, data['title'], json.dumps(data['sources']),
                data['total_score'], data['total_score'], rank,
                1.5 if len(data['sources']) >= 3 else (1.3 if len(data['sources']) >= 2 else 1.0),
                today
            )
            saved += 1
        except Exception as e:
            print(f'  ⚠️ trending {aid} 저장 실패: {e}')

    source_counts = defaultdict(int)
    for data in paper_scores.values():
        for s in data['sources']:
            source_counts[s] += 1

    print(f'🔥 Trending 저장: {saved}개')
    print(f'   소스별: {dict(source_counts)}')
    multi = sum(1 for d in paper_scores.values() if len(d['sources']) >= 2)
    print(f'   크로스 플랫폼: {multi}개 논문')
    return saved


# ──────────────────────────────────────────
# Main
# ──────────────────────────────────────────
async def main():
    start = datetime.now()
    print(f'{"="*60}')
    print(f'🚀 Hot Paper Daily Collector - {start.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"="*60}')

    conn = await asyncpg.connect(DB_URL)

    # 1. arXiv 최신 논문
    print('\n📚 Step 1: arXiv 논문 수집...')
    arxiv_papers = await fetch_arxiv_papers(100)
    new_count = await save_papers(conn, arxiv_papers)

    # 2. 다중 소스 trending 수집 (병렬)
    print('\n🔥 Step 2: 다중 소스 Trending 수집...')
    hf_papers, rss_papers, crossref_papers = await asyncio.gather(
        fetch_hf_trending(),
        fetch_arxiv_rss(),
        fetch_crossref_trending(),
    )

    all_trending = hf_papers + rss_papers + crossref_papers

    # trending 논문 중 DB에 없는 것 저장
    for p in all_trending:
        if p.get('title') and p.get('abstract'):
            await save_papers(conn, [{
                'arxiv_id': p['arxiv_id'], 'title': p['title'],
                'abstract': p['abstract'], 'authors': [], 'categories': [],
                'published_date': datetime.now().strftime('%Y-%m-%d'),
                'pdf_url': f'https://arxiv.org/pdf/{p["arxiv_id"]}.pdf',
                'arxiv_url': f'https://arxiv.org/abs/{p["arxiv_id"]}',
            }])

    # 3. 통합 trending 저장
    print('\n📊 Step 3: 통합 Trending 점수 계산...')
    await save_trending(conn, all_trending)

    # 4. 통계
    total = await conn.fetchval('SELECT count(*) FROM papers')
    trending_count = await conn.fetchval(
        "SELECT count(*) FROM trending_papers WHERE DATE(created_at) = $1",
        datetime.now().date()
    )

    elapsed = (datetime.now() - start).total_seconds()
    print(f'\n{"="*60}')
    print(f'✅ 완료! ({elapsed:.1f}초)')
    print(f'   전체 논문: {total}개')
    print(f'   신규 추가: {new_count}개')
    print(f'   오늘 Trending: {trending_count}개')
    print(f'   Active Sources: HuggingFace({len(hf_papers)}), arXiv RSS({len(rss_papers)}), Crossref({len(crossref_papers)})')
    print(f'{"="*60}')

    await conn.close()


if __name__ == '__main__':
    asyncio.run(main())

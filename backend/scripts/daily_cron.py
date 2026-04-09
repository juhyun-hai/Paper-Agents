#!/usr/bin/env python3
"""
Daily Paper + Trending Collector (cron용)
매일 새벽 3시 실행: 최신 논문 100개 수집 + trending 업데이트
"""
import asyncio
import sys
import os
import json
import requests
import re
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('HF_HOME', '/home/juhyun/hf_cache')

import asyncpg

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
ARXIV_API = 'http://export.arxiv.org/api/query'
HF_API = 'https://huggingface.co/api/daily_papers'

CATEGORIES = [
    'cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.IR',
    'cs.HC', 'cs.RO', 'cs.NE', 'stat.ML',
]


async def fetch_arxiv_papers(max_results=100):
    """arXiv에서 최신 논문 수집."""
    cat_query = '+OR+'.join(f'cat:{c}' for c in CATEGORIES)
    url = f'{ARXIV_API}?search_query={cat_query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}'

    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            print(f'❌ arXiv API 실패: {resp.status_code}')
            return []

        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}

        papers = []
        for entry in root.findall('atom:entry', ns):
            arxiv_id_raw = entry.find('atom:id', ns).text
            arxiv_id = arxiv_id_raw.split('/abs/')[-1].split('v')[0]

            title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
            abstract = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
            published = entry.find('atom:published', ns).text[:10]

            authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)]
            categories = [c.get('term') for c in entry.findall('atom:category', ns)]

            papers.append({
                'arxiv_id': arxiv_id,
                'title': title,
                'abstract': abstract[:2000],
                'authors': authors,
                'categories': categories,
                'published_date': published,
                'pdf_url': f'https://arxiv.org/pdf/{arxiv_id}.pdf',
                'arxiv_url': f'https://arxiv.org/abs/{arxiv_id}',
            })

        print(f'✅ arXiv: {len(papers)}개 논문 수집')
        return papers
    except Exception as e:
        print(f'❌ arXiv 수집 실패: {e}')
        return []


async def fetch_hf_trending():
    """HuggingFace에서 trending 논문 수집."""
    try:
        resp = requests.get(HF_API, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0'
        })
        if resp.status_code != 200:
            print(f'❌ HF API 실패: {resp.status_code}')
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

        print(f'✅ HuggingFace: {len(papers)}개 trending 수집')
        return papers
    except Exception as e:
        print(f'❌ HF 수집 실패: {e}')
        return []


async def save_papers(conn, papers):
    """논문을 DB에 저장 (중복 건너뛰기)."""
    saved = 0
    skipped = 0
    for p in papers:
        existing = await conn.fetchrow(
            "SELECT id FROM papers WHERE arxiv_id = $1", p['arxiv_id']
        )
        if existing:
            skipped += 1
            continue

        try:
            await conn.execute("""
                INSERT INTO papers (arxiv_id, title, abstract, authors, categories,
                                    published_date, pdf_url, html_url, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
            """,
                p['arxiv_id'],
                p['title'],
                p['abstract'],
                json.dumps(p.get('authors', [])),
                json.dumps(p.get('categories', [])),
                datetime.strptime(p['published_date'], '%Y-%m-%d') if p.get('published_date') else datetime.now(),
                p.get('pdf_url', ''),
                p.get('arxiv_url', ''),
            )
            saved += 1
        except Exception as e:
            print(f'  ⚠️ {p["arxiv_id"]} 저장 실패: {e}')

    print(f'📊 논문 저장: {saved}개 신규, {skipped}개 중복')
    return saved


async def save_trending(conn, hf_papers):
    """Trending 논문 저장."""
    today = datetime.now().date()

    # 오늘 trending 초기화
    await conn.execute(
        "DELETE FROM trending_papers WHERE DATE(created_at) = $1", today
    )

    saved = 0
    for i, p in enumerate(hf_papers):
        score = max(0.1, (p.get('upvotes', 0) * 1.8))
        final_score = score * (1.3 if i < 10 else 1.0)

        try:
            await conn.execute("""
                INSERT INTO trending_papers (arxiv_id, title, sources,
                                              trending_score, final_score, rank,
                                              date, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            """,
                p['arxiv_id'], p['title'], json.dumps(['huggingface']),
                score, final_score, i + 1, today
            )
            saved += 1
        except Exception as e:
            print(f'  ⚠️ trending {p["arxiv_id"]} 저장 실패: {e}')

    print(f'🔥 Trending 저장: {saved}개')
    return saved


async def main():
    start = datetime.now()
    print(f'{"="*60}')
    print(f'🚀 Daily Paper Collector - {start.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"="*60}')

    conn = await asyncpg.connect(DB_URL)

    # 1. arXiv 최신 논문 수집
    print('\n📚 Step 1: arXiv 논문 수집...')
    arxiv_papers = await fetch_arxiv_papers(100)
    new_count = await save_papers(conn, arxiv_papers)

    # 2. HuggingFace trending 수집
    print('\n🔥 Step 2: HuggingFace trending 수집...')
    hf_papers = await fetch_hf_trending()

    # HF 논문 중 DB에 없는 것도 저장
    hf_as_papers = []
    for p in hf_papers:
        if p.get('title') and p.get('abstract'):
            hf_as_papers.append({
                'arxiv_id': p['arxiv_id'],
                'title': p['title'],
                'abstract': p['abstract'],
                'authors': [],
                'categories': [],
                'published_date': datetime.now().strftime('%Y-%m-%d'),
                'pdf_url': f'https://arxiv.org/pdf/{p["arxiv_id"]}.pdf',
                'arxiv_url': f'https://arxiv.org/abs/{p["arxiv_id"]}',
            })
    await save_papers(conn, hf_as_papers)
    await save_trending(conn, hf_papers)

    # 3. 통계
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
    print(f'{"="*60}')

    await conn.close()


if __name__ == '__main__':
    asyncio.run(main())

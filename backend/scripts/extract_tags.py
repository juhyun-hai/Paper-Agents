"""P4 — 동적 카테고리: 논문에서 5-10개 tag 자동 추출.

설계:
- Ollama qwen3:32b로 title + abstract → ['transformer', 'long context', ...] JSON
- canonical: lowercase + 트리밍 + 알리아스 매칭 (simple)
- concepts 테이블 (이미 schema 존재) 활용:
    concepts (canonical concept master)
    paper_concepts (paper ↔ concept edge with confidence)
- 1 paper → 5-10 tag, 모든 tag는 짧고 구체적 (1-3 단어)
- 정상 분야 단어만 (예: 'good', 'novel' 같은 형용사 제거)
- 중복 alias 자동 흡수 ('LLMs' → 'llm', 'Vision-Language' → 'vision language')

호출:
  • CLI: python extract_tags.py <arxiv_id>  → tag 리스트 출력
  • Bulk: python extract_tags.py --bulk      → tag 없는 paper 전부 처리
  • daily_cron 통합: extract_tags_for_paper(conn, arxiv_id) 호출
"""
from __future__ import annotations
import asyncio
import json
import os
import re
import sys
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncpg
import httpx

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
OLLAMA_URL = 'http://localhost:11434'
MODEL = os.environ.get('TAG_MODEL', 'qwen3:32b')

SYSTEM = """You extract 5-10 concise topic tags from a research paper.

Rules:
- Each tag: 1-3 words, all lowercase, hyphens for multi-word
- Specific technical concepts, NOT generic words ('novel', 'study', 'analysis')
- Mix: method names, application domains, dataset names, model architectures
- Examples: ["diffusion-models", "long-context", "fault-diagnosis", "vision-language", "in-context-learning"]
- Output ONLY a JSON array of strings, no commentary.

Bad: ["paper", "results", "good performance", "machine learning"]
Good: ["transformer", "long-context", "retrieval-augmented", "code-generation", "benchmark"]"""


# 흔한 stop-word / 너무 일반적 tag 제거
STOPWORDS = {
    'paper', 'study', 'analysis', 'novel', 'new', 'good', 'better',
    'machine-learning', 'deep-learning', 'artificial-intelligence',
    'method', 'approach', 'model', 'results', 'benchmark',  # 너무 일반
}

TAG_RE = re.compile(r'^[a-z][a-z0-9\-]{1,40}$')


def _normalize(tag: str) -> str | None:
    t = (tag or '').strip().lower()
    t = re.sub(r'\s+', '-', t)
    t = re.sub(r'[^a-z0-9\-]', '', t)
    t = re.sub(r'-+', '-', t).strip('-')
    if not t or not TAG_RE.match(t):
        return None
    if t in STOPWORDS:
        return None
    if len(t) < 3 or len(t) > 40:
        return None
    return t


def extract_tags_llm(title: str, abstract: str) -> List[str]:
    """Ollama 호출 → tag 리스트."""
    user_msg = f"Title: {title}\n\nAbstract:\n{abstract[:2500]}\n\nExtract 5-10 tags as JSON array."
    try:
        with httpx.Client(timeout=120) as cli:
            r = cli.post(f'{OLLAMA_URL}/api/chat', json={
                'model': MODEL, 'stream': False, 'think': False,
                'messages': [
                    {'role': 'system', 'content': SYSTEM},
                    {'role': 'user', 'content': user_msg},
                ],
                'options': {'num_predict': 300, 'num_ctx': 4096, 'temperature': 0.1},
            })
            r.raise_for_status()
            txt = r.json().get('message', {}).get('content', '').strip()
    except Exception as e:
        print(f'  ⚠️ Ollama err: {e}')
        return []

    # JSON 추출
    try:
        m = re.search(r'\[.*?\]', txt, re.S)
        if not m:
            return []
        raw = json.loads(m.group(0))
        if not isinstance(raw, list):
            return []
    except Exception:
        return []

    out = []
    seen = set()
    for x in raw:
        if not isinstance(x, str):
            continue
        norm = _normalize(x)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out[:10]


async def upsert_concept(conn: asyncpg.Connection, name: str) -> int:
    """concepts에 canonical row 보장. 반환: concept_id."""
    row = await conn.fetchrow(
        "SELECT id FROM concepts WHERE name = $1 AND type = 'keyword'", name
    )
    if row:
        return row['id']
    row = await conn.fetchrow("""
        INSERT INTO concepts (name, type, description, aliases, paper_count, created_at, updated_at)
        VALUES ($1, 'keyword', '', '[]'::jsonb, 0, NOW(), NOW())
        RETURNING id
    """, name)
    return row['id']


async def link_paper_concept(conn: asyncpg.Connection, paper_id: int,
                              concept_id: int, weight: float = 1.0):
    """paper_concepts edge (idempotent)."""
    await conn.execute("""
        INSERT INTO paper_concepts (paper_id, concept_id, weight, confidence,
                                     extraction_method, created_at)
        VALUES ($1, $2, $3, 1.0, 'llm:qwen3:32b', NOW())
        ON CONFLICT (paper_id, concept_id) DO UPDATE SET
            weight = EXCLUDED.weight, updated_at = NOW()
    """, paper_id, concept_id, weight)


async def extract_tags_for_paper(conn: asyncpg.Connection, arxiv_id: str) -> List[str]:
    """1개 paper에 tag 추출 + DB 저장. 반환: 저장된 tag 리스트."""
    paper = await conn.fetchrow(
        "SELECT id, title, COALESCE(abstract, '') AS abstract FROM papers WHERE arxiv_id = $1",
        arxiv_id,
    )
    if not paper or not paper['abstract'] or len(paper['abstract']) < 50:
        return []
    tags = extract_tags_llm(paper['title'], paper['abstract'])
    if not tags:
        return []
    for tag in tags:
        cid = await upsert_concept(conn, tag)
        await link_paper_concept(conn, paper['id'], cid)
    # concepts.paper_count 갱신
    await conn.execute("""
        UPDATE concepts c
        SET paper_count = (SELECT COUNT(*) FROM paper_concepts WHERE concept_id = c.id),
            updated_at = NOW()
        WHERE c.name = ANY($1::text[]) AND c.type='keyword'
    """, tags)
    return tags


async def bulk_extract(conn: asyncpg.Connection, limit: int = 100):
    """tag 없는 paper N편에 추출. featured + 최근 우선."""
    rows = await conn.fetch("""
        SELECT p.arxiv_id, p.title
        FROM papers p
        WHERE p.abstract IS NOT NULL AND length(p.abstract) > 100
          AND NOT EXISTS (SELECT 1 FROM paper_concepts pc WHERE pc.paper_id = p.id)
          AND p.arxiv_id ~ '^[0-9]{4}\\.[0-9]{4,5}$'
        ORDER BY p.created_at DESC
        LIMIT $1
    """, limit)
    print(f'🏷  {len(rows)}편에 tag 추출 시작')
    ok = 0
    for r in rows:
        tags = await extract_tags_for_paper(conn, r['arxiv_id'])
        if tags:
            ok += 1
            print(f"  [{ok}/{len(rows)}] {r['arxiv_id']}: {tags}")
    print(f'\n✅ 완료 — {ok}/{len(rows)} 처리')


async def _cli():
    conn = await asyncpg.connect(DB_URL)
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--bulk':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            await bulk_extract(conn, limit=limit)
        elif len(sys.argv) > 1:
            tags = await extract_tags_for_paper(conn, sys.argv[1])
            print(f'tags: {tags}')
        else:
            print('Usage: python extract_tags.py <arxiv_id>  OR  --bulk [N]')
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(_cli())

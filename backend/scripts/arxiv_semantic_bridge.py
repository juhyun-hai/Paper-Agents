"""P3 — Conf seed paper의 임베딩으로 최근 arXiv 의미 검색.

목적: 광범위 cs.* RSS 폐기. Conference oral/best paper와 의미적으로
가까운 최근 arXiv만 골라 daily feed에 추가.

흐름:
  1. 최근 N일 conf seed paper (venue_acceptances + papers JOIN) 픽
  2. 그들의 full_embedding 평균 = "today's conf taste centroid"
  3. 최근 K일 arXiv (papers.published_date >= cutoff, has full_embedding)
     에서 centroid와 cosine top-M
  4. (선택) cross-encoder rerank — 1차에선 생략 (단순/빠름)
  5. 이미 conf로 들어온 paper, 이미 today's feed에 있는 paper 제외
  6. similarity threshold(>=0.55) 미달이면 quota 줄임 (noise X)

호출 위치:
  daily_cron.py에서 Step 1c (OpenReview/S2) 끝난 직후, featured 점수
  계산 전. 결과 arxiv_id들을 trending pool에 'semantic_bridge' source로
  주입한다.
"""
from __future__ import annotations
import asyncio
import sys
import os
from datetime import date, timedelta
from typing import List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncpg
import numpy as np

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'


async def _rows_to_centroid(rows) -> np.ndarray | None:
    """list[Record] 의 full_embedding 들의 평균을 L2-정규화해서 반환."""
    if not rows:
        return None
    vectors = []
    for r in rows:
        emb = r['full_embedding']
        if isinstance(emb, str):
            emb = [float(x) for x in emb.strip('[]').split(',')]
        vectors.append(np.array(emb, dtype=np.float32))
    centroid = np.mean(vectors, axis=0)
    norm = np.linalg.norm(centroid)
    return centroid / norm if norm > 0 else centroid


async def get_conf_seed_centroid(
    conn: asyncpg.Connection, lookback_days: int = 14
) -> Tuple[np.ndarray | None, int, str]:
    """centroid + 몇 편 사용했는지 + 어떤 source 였는지.

    우선순위:
    1) venue_acceptances 의 Oral/Spotlight/Best 트랙 (이상적)
    2) venue_acceptances 전체 (트랙 필터 풀고)
    3) **fallback**: 최근 N일 featured top-rank papers (P1 작동 안 할 때)

    Returns: (centroid|None, count_used, source_label)
    """
    cutoff = date.today() - timedelta(days=lookback_days)

    # 1) Oral/Spotlight/Best
    rows = await conn.fetch("""
        SELECT p.full_embedding
        FROM venue_acceptances va
        JOIN papers p ON p.id = va.paper_id
        WHERE va.fetched_at >= $1
          AND p.full_embedding IS NOT NULL
          AND va.track IN ('Oral', 'Spotlight', 'Best Paper', 'Honorable Mention')
        LIMIT 100
    """, cutoff)
    centroid = await _rows_to_centroid(rows)
    if centroid is not None:
        return centroid, len(rows), 'conf_oral_spotlight'

    # 2) 트랙 무시
    rows = await conn.fetch("""
        SELECT p.full_embedding
        FROM venue_acceptances va
        JOIN papers p ON p.id = va.paper_id
        WHERE va.fetched_at >= $1 AND p.full_embedding IS NOT NULL
        LIMIT 100
    """, cutoff)
    centroid = await _rows_to_centroid(rows)
    if centroid is not None:
        return centroid, len(rows), 'conf_any'

    # 3) Featured fallback (P1 작동 안 할 때) — 최근 N일 featured top-rank
    rows = await conn.fetch("""
        SELECT p.full_embedding
        FROM trending_papers tp
        JOIN papers p ON p.arxiv_id = tp.arxiv_id
        WHERE tp.date >= $1
          AND tp.is_featured = TRUE
          AND tp.rank <= 10
          AND p.full_embedding IS NOT NULL
        LIMIT 100
    """, cutoff)
    centroid = await _rows_to_centroid(rows)
    if centroid is not None:
        return centroid, len(rows), 'featured_fallback'

    return None, 0, 'none'


async def find_related_arxiv(
    conn: asyncpg.Connection,
    centroid: np.ndarray,
    fresh_days: int = 7,
    top_k: int = 15,
    min_similarity: float = 0.55,
    exclude_arxiv_ids: set[str] | None = None,
) -> List[Tuple[str, str, float]]:
    """centroid와 가장 가까운 최근 arxiv paper top-K.

    Returns: [(arxiv_id, title, similarity), ...]
    """
    cutoff = date.today() - timedelta(days=fresh_days)
    exclude = exclude_arxiv_ids or set()
    # pgvector + asyncpg 는 vector 파라미터를 '[v1,v2,...]' 문자열 형태로 받음
    centroid_str = '[' + ','.join(f'{x:.6f}' for x in centroid.tolist()) + ']'

    # alias로 정렬 (pgvector + WHERE planner 이슈 회피)
    rows = await conn.fetch("""
        WITH ranked AS (
          SELECT p.arxiv_id, p.title,
                 1 - (p.full_embedding <=> $1::vector) AS sim
          FROM papers p
          WHERE p.full_embedding IS NOT NULL
            AND p.arxiv_id ~ '^[0-9]{4}\\.[0-9]{4,5}$'
            AND p.published_date >= $2
        )
        SELECT arxiv_id, title, sim
        FROM ranked
        WHERE sim >= $3
        ORDER BY sim DESC
        LIMIT $4
    """, centroid_str, cutoff, min_similarity, top_k * 3)

    out = []
    for r in rows:
        if r['arxiv_id'] in exclude:
            continue
        out.append((r['arxiv_id'], r['title'], float(r['sim'])))
        if len(out) >= top_k:
            break
    return out


async def run_semantic_bridge(
    conn: asyncpg.Connection,
    fresh_days: int = 7,
    top_k: int = 15,
    min_similarity: float = 0.55,
) -> List[Tuple[str, str, float]]:
    """End-to-end: conf centroid → arxiv 의미 검색. 결과 리스트 반환.

    daily_cron.py가 이 결과를 trending pool에 source='semantic_bridge'로 inject.
    """
    centroid, n_seed, src = await get_conf_seed_centroid(conn)
    if centroid is None:
        print(f'  ⚠️ semantic_bridge: seed 없음 (conf 0, featured 0)')
        return []
    print(f'  🔍 semantic_bridge: {n_seed}편 seed [{src}]로 centroid 생성')

    # 이미 venue_acceptances로 들어온 arxiv는 제외
    rows = await conn.fetch("""
        SELECT p.arxiv_id FROM venue_acceptances va
        JOIN papers p ON p.id = va.paper_id
        WHERE p.arxiv_id IS NOT NULL
    """)
    exclude = {r['arxiv_id'] for r in rows}

    related = await find_related_arxiv(
        conn, centroid,
        fresh_days=fresh_days, top_k=top_k,
        min_similarity=min_similarity, exclude_arxiv_ids=exclude,
    )
    print(f'  ✅ semantic_bridge: top {len(related)}편 (≥sim {min_similarity:.2f})')
    return related


# CLI smoke test
async def _cli():
    conn = await asyncpg.connect(DB_URL)
    try:
        result = await run_semantic_bridge(conn)
        for aid, title, sim in result:
            print(f'  [{aid}] sim={sim:.3f} | {title[:70]}')
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(_cli())

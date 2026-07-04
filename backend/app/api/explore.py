"""Interactive explore graph — 최근 featured 논문의 유사도 네트워크.

Connected Papers 스타일 시각화용 데이터:
- nodes: 최근 N일 featured (+semantic_bridge) 논문. cluster = 대표 tag.
- edges: 노드 집합 안에서 embedding cosine top-K (numpy로 일괄 계산).

프론트(/explore)의 d3 force-directed 그래프가 소비한다.
"""
import json
from datetime import date, timedelta
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session

router = APIRouter(prefix="/api/explore", tags=["Explore"])


def _parse_vec(v) -> Optional[np.ndarray]:
    if v is None:
        return None
    if isinstance(v, str):
        try:
            return np.array([float(x) for x in v.strip('[]').split(',')], dtype=np.float32)
        except Exception:
            return None
    try:
        return np.asarray(v, dtype=np.float32)
    except Exception:
        return None


@router.get("/graph")
async def get_explore_graph(
    response: Response,
    days: int = Query(14, ge=3, le=60),
    max_nodes: int = Query(120, ge=20, le=250),
    k: int = Query(3, ge=1, le=6, description="노드당 유사도 edge 수"),
    session: AsyncSession = Depends(get_async_session),
):
    cutoff = date.today() - timedelta(days=days)

    rows = (await session.execute(text("""
        SELECT DISTINCT ON (p.arxiv_id)
               p.id AS pid, p.arxiv_id, p.title, p.full_embedding,
               p.is_hai, tp.upvotes, tp.rank, tp.date AS feat_date,
               s.summary_text IS NOT NULL AS has_summary
        FROM trending_papers tp
        JOIN papers p ON p.arxiv_id = tp.arxiv_id
        LEFT JOIN paper_summaries s ON s.arxiv_id = p.arxiv_id
        WHERE tp.date >= :cutoff
          AND (tp.is_featured = TRUE OR tp.sources::text LIKE '%semantic_bridge%')
          AND p.full_embedding IS NOT NULL
        ORDER BY p.arxiv_id, tp.date DESC
        LIMIT :cap
    """), {'cutoff': cutoff, 'cap': max_nodes})).all()

    if len(rows) < 5:
        return {"nodes": [], "edges": [], "clusters": []}

    # 대표 tag (paper_count 최대) — 클러스터/색상용
    pids = [r.pid for r in rows]
    tag_rows = (await session.execute(text("""
        SELECT DISTINCT ON (pc.paper_id) pc.paper_id, c.name
        FROM paper_concepts pc
        JOIN concepts c ON c.id = pc.concept_id
        WHERE pc.paper_id = ANY(:ids) AND c.type = 'keyword'
        ORDER BY pc.paper_id, c.paper_count DESC
    """), {'ids': pids})).all()
    top_tag = {t.paper_id: t.name for t in tag_rows}

    # 상위 7개 tag = named cluster, 나머지 = other
    from collections import Counter
    tag_counts = Counter(top_tag.get(r.pid) for r in rows if top_tag.get(r.pid))
    named = [t for t, _n in tag_counts.most_common(7)]

    # cosine top-K edges (정규화 후 내적)
    vecs, keep = [], []
    for r in rows:
        v = _parse_vec(r.full_embedding)
        if v is not None:
            n = np.linalg.norm(v)
            if n > 0:
                vecs.append(v / n)
                keep.append(r)
    M = np.stack(vecs)               # (n, d)
    S = M @ M.T                      # (n, n) cosine
    np.fill_diagonal(S, -1)

    edges, seen = [], set()
    for i in range(len(keep)):
        for j in np.argsort(S[i])[::-1][:k]:
            j = int(j)
            if S[i][j] < 0.5:
                continue
            key = (min(i, j), max(i, j))
            if key in seen:
                continue
            seen.add(key)
            edges.append({
                "source": keep[i].arxiv_id,
                "target": keep[j].arxiv_id,
                "weight": round(float(S[i][j]), 3),
            })

    nodes = []
    for r in keep:
        tag = top_tag.get(r.pid)
        nodes.append({
            "id": r.arxiv_id,
            "title": r.title,
            "cluster": tag if tag in named else "other",
            "tag": tag or "",
            "upvotes": r.upvotes or 0,
            "rank": r.rank,
            "date": r.feat_date.isoformat() if r.feat_date else None,
            "is_hai": bool(r.is_hai),
            "has_summary": bool(r.has_summary),
        })

    response.headers["Cache-Control"] = "public, max-age=600"
    return {"nodes": nodes, "edges": edges, "clusters": named + ["other"]}

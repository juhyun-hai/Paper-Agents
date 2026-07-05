"""급상승 키워드 (trending keyword) endpoints.

CLAUDE.md 원 스펙의 trending score:
  score = (recent_freq + 1) / (baseline_freq + 1)
baseline은 30일치이므로 기간 정규화(baseline * days/30)를 적용한다.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session

router = APIRouter(prefix="/api/trends", tags=["Trends"])


@router.get("/keywords")
async def get_trending_keywords(
    response: Response,
    days: int = Query(7, ge=1, le=30, description="recent window (days)"),
    min_recent: int = Query(3, ge=1, le=50),
    limit: int = Query(15, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session),
):
    """최근 N일 tag 빈도 vs 이전 30일 baseline 대비 급상승 키워드."""
    response.headers["Cache-Control"] = "public, max-age=1800"
    today = date.today()
    recent_start = today - timedelta(days=days)          # 최근 N일 시작
    baseline_start = recent_start - timedelta(days=30)   # 이전 30일 baseline 시작
    rows = (await session.execute(text("""
        SELECT c.name,
               COUNT(*) FILTER (
                   WHERE p.published_date >= :recent_start
               ) AS recent,
               COUNT(*) FILTER (
                   WHERE p.published_date < :recent_start
                     AND p.published_date >= :baseline_start
               ) AS baseline
        FROM paper_concepts pc
        JOIN concepts c ON c.id = pc.concept_id
        JOIN papers p ON p.id = pc.paper_id
        WHERE c.type = 'keyword'
          AND p.published_date >= :baseline_start
        GROUP BY c.name
        HAVING COUNT(*) FILTER (
            WHERE p.published_date >= :recent_start
        ) >= :min_recent
    """), {
        'recent_start': recent_start,
        'baseline_start': baseline_start,
        'min_recent': min_recent,
    })).all()

    keywords = []
    for r in rows:
        # baseline(30일)을 recent 기간으로 정규화한 뒤 스펙의 (recent+1)/(baseline+1)
        normalized_baseline = r.baseline * days / 30.0
        score = (r.recent + 1.0) / (normalized_baseline + 1.0)
        keywords.append({
            "name": r.name,
            "recent": r.recent,
            "baseline": r.baseline,
            "score": round(score, 2),
            "new": r.baseline == 0,
        })

    keywords.sort(key=lambda k: (-k["score"], -k["recent"], k["name"]))
    return {
        "days": days,
        "keywords": keywords[:limit],
        "total": len(keywords),
    }

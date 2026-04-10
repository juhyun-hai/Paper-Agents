"""
Trending papers API endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import date, datetime, timedelta

from ..core.database import get_async_session
from ..models import TrendingPaper, Paper
from ..schemas.papers import PaperResponse

router = APIRouter(prefix="/api/trending", tags=["Trending"])


def _parse_sources(sources_str):
    """Parse sources field - could be JSON array string or comma-separated."""
    if not sources_str:
        return []
    import json
    try:
        parsed = json.loads(sources_str)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return [s.strip() for s in sources_str.split(',') if s.strip()]


@router.get("/today")
async def get_today_trending(
    limit: int = Query(20, le=200, description="Number of trending papers"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get today's trending papers."""
    try:
        today = date.today()

        result = await session.execute(
            select(TrendingPaper)
            .where(TrendingPaper.date == today)
            .order_by(TrendingPaper.rank.asc())
            .limit(limit)
        )

        trending_papers = result.scalars().all()

        response_papers = []
        for tp in trending_papers:
            # Get the actual paper data if available
            paper_result = await session.execute(
                select(Paper).where(Paper.arxiv_id == tp.arxiv_id)
            )
            paper = paper_result.scalar_one_or_none()

            if paper:
                response_papers.append({
                    "id": paper.id,
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "authors": paper.authors or [],
                    "abstract": paper.abstract or "",
                    "categories": paper.categories or [],
                    "published_date": paper.published_date.isoformat() if paper.published_date else "",
                    "venue": paper.venue,
                    "citation_count": paper.citation_count or 0,
                    "year": paper.year,
                    "trending_rank": tp.rank,
                    "trending_score": tp.trending_score,
                    "final_score": tp.final_score,
                    "sources": _parse_sources(tp.sources),
                    "multi_source_bonus": tp.multi_source_bonus
                })
            else:
                # Fallback if paper not in main database
                response_papers.append({
                    "id": None,
                    "arxiv_id": tp.arxiv_id,
                    "title": tp.title,
                    "authors": [],
                    "abstract": "",
                    "categories": [],
                    "published_date": "",
                    "venue": None,
                    "citation_count": 0,
                    "year": None,
                    "trending_rank": tp.rank,
                    "trending_score": tp.trending_score,
                    "final_score": tp.final_score,
                    "sources": _parse_sources(tp.sources),
                    "multi_source_bonus": tp.multi_source_bonus
                })

        return {
            "trending_papers": response_papers,
            "total": len(response_papers),
            "date": today.isoformat(),
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve trending papers: {str(e)}"
        )


@router.get("/week")
async def get_weekly_trending(
    limit: int = Query(100, le=200, description="Number of trending papers"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get this week's trending papers aggregated across all days."""
    try:
        week_ago = date.today() - timedelta(days=7)

        # Get ALL trending papers from the last week for proper aggregation
        result = await session.execute(
            select(TrendingPaper)
            .where(TrendingPaper.date >= week_ago)
            .order_by(
                TrendingPaper.final_score.desc(),
                TrendingPaper.trending_score.desc(),
                TrendingPaper.rank.asc()
            )
        )

        trending_papers = result.scalars().all()

        # Group by arxiv_id and aggregate scores
        paper_aggregates = {}
        for tp in trending_papers:
            if tp.arxiv_id not in paper_aggregates:
                paper_aggregates[tp.arxiv_id] = {
                    'paper': tp,
                    'total_score': tp.final_score or tp.trending_score or 0,
                    'best_rank': tp.rank or 999,
                    'days_trending': 1,
                    'all_sources': set(_parse_sources(tp.sources))
                }
            else:
                paper_aggregates[tp.arxiv_id]['total_score'] += tp.final_score or tp.trending_score or 0
                paper_aggregates[tp.arxiv_id]['best_rank'] = min(
                    paper_aggregates[tp.arxiv_id]['best_rank'],
                    tp.rank or 999
                )
                paper_aggregates[tp.arxiv_id]['days_trending'] += 1
                paper_aggregates[tp.arxiv_id]['all_sources'].update(
                    _parse_sources(tp.sources)
                )

        # Sort by aggregated score
        sorted_papers = sorted(
            paper_aggregates.values(),
            key=lambda x: (x['total_score'], -x['best_rank']),
            reverse=True
        )

        response_papers = []
        for item in sorted_papers[:limit]:
            tp = item['paper']

            # Get the actual paper data if available
            paper_result = await session.execute(
                select(Paper).where(Paper.arxiv_id == tp.arxiv_id)
            )
            paper = paper_result.scalar_one_or_none()

            if paper:
                response_papers.append({
                    "id": paper.id,
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "authors": paper.authors or [],
                    "abstract": paper.abstract or "",
                    "categories": paper.categories or [],
                    "published_date": paper.published_date.isoformat() if paper.published_date else "",
                    "venue": paper.venue,
                    "citation_count": paper.citation_count or 0,
                    "year": paper.year,
                    "weekly_score": item['total_score'],
                    "best_rank": item['best_rank'],
                    "days_trending": item['days_trending'],
                    "sources": list(item['all_sources'])
                })

        return {
            "weekly_trending": response_papers,
            "total": len(response_papers),
            "period": "7_days",
            "date_range": f"{week_ago.isoformat()} to {date.today().isoformat()}",
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve weekly trending papers: {str(e)}"
        )


@router.get("/sources")
async def get_trending_sources(session: AsyncSession = Depends(get_async_session)):
    """Get trending sources statistics."""
    try:
        today = date.today()

        # Get source distribution for today
        result = await session.execute(
            select(TrendingPaper.sources)
            .where(TrendingPaper.date == today)
        )

        all_sources = []
        for (sources,) in result.all():
            if sources:
                all_sources.extend(sources.split(','))

        # Count sources
        source_counts = {}
        for source in all_sources:
            source = source.strip()
            source_counts[source] = source_counts.get(source, 0) + 1

        source_stats = [
            {"source": source, "count": count}
            for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            "source_statistics": source_stats,
            "total_sources": len(source_counts),
            "date": today.isoformat(),
            "description": "Sources contributing to today's trending papers"
        }

    except Exception as e:
        return {
            "source_statistics": [],
            "total_sources": 0,
            "error": str(e)
        }


@router.get("/stats")
async def get_trending_stats(session: AsyncSession = Depends(get_async_session)):
    """Get trending papers statistics."""
    try:
        today = date.today()
        week_ago = today - timedelta(days=7)

        # Today's count
        today_result = await session.execute(
            select(func.count(TrendingPaper.id))
            .where(TrendingPaper.date == today)
        )
        today_count = today_result.scalar() or 0

        # This week's unique papers
        week_result = await session.execute(
            select(func.count(func.distinct(TrendingPaper.arxiv_id)))
            .where(TrendingPaper.date >= week_ago)
        )
        week_unique = week_result.scalar() or 0

        # Multi-source papers today
        multi_source_result = await session.execute(
            select(func.count(TrendingPaper.id))
            .where(
                TrendingPaper.date == today,
                TrendingPaper.sources.contains(',')
            )
        )
        multi_source_count = multi_source_result.scalar() or 0

        return {
            "today_count": today_count,
            "week_unique": week_unique,
            "multi_source_today": multi_source_count,
            "collection_active": today_count > 0,
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "today_count": 0,
            "week_unique": 0,
            "multi_source_today": 0,
            "collection_active": False,
            "error": str(e)
        }
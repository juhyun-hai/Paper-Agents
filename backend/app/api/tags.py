"""Dynamic topic tag endpoints (P4)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session

router = APIRouter(prefix="/api/tags", tags=["Tags"])


@router.get("/popular")
async def get_popular_tags(
    limit: int = Query(40, ge=1, le=200),
    min_count: int = Query(2, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """인기 tag 목록 (paper_count desc). chip cloud용."""
    rows = (await session.execute(text("""
        SELECT name, paper_count
        FROM concepts
        WHERE type = 'keyword' AND paper_count >= :min_count
        ORDER BY paper_count DESC, name ASC
        LIMIT :limit
    """), {'min_count': min_count, 'limit': limit})).all()
    return {
        "tags": [{"name": r.name, "count": r.paper_count} for r in rows],
        "total": len(rows),
    }


@router.get("/by-paper/{arxiv_id}")
async def get_paper_tags(
    arxiv_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """특정 paper의 tag 리스트. paper 상세 페이지용."""
    rows = (await session.execute(text("""
        SELECT c.name, c.paper_count, pc.confidence
        FROM paper_concepts pc
        JOIN concepts c ON c.id = pc.concept_id
        JOIN papers p ON p.id = pc.paper_id
        WHERE p.arxiv_id = :aid AND c.type = 'keyword'
        ORDER BY c.paper_count DESC
        LIMIT 15
    """), {'aid': arxiv_id})).all()
    return {
        "arxiv_id": arxiv_id,
        "tags": [{"name": r.name, "count": r.paper_count, "confidence": r.confidence} for r in rows],
    }


@router.get("/papers")
async def papers_by_tag(
    tag: str = Query(..., description="tag name (canonical, lowercase)"),
    limit: int = Query(30, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """특정 tag 가진 paper 리스트 (최신순). tag filter용."""
    rows = (await session.execute(text("""
        SELECT p.arxiv_id, p.title, p.authors, p.abstract,
               p.published_date, p.pdf_url, p.html_url
        FROM paper_concepts pc
        JOIN concepts c ON c.id = pc.concept_id
        JOIN papers p ON p.id = pc.paper_id
        WHERE c.type = 'keyword' AND lower(c.name) = lower(:tag)
        ORDER BY p.published_date DESC NULLS LAST
        LIMIT :limit
    """), {'tag': tag.strip().lower(), 'limit': limit})).all()
    return {
        "tag": tag,
        "papers": [
            {
                "arxiv_id": r.arxiv_id,
                "title": r.title,
                "authors": r.authors or [],
                "abstract": (r.abstract or "")[:400],
                "published_date": r.published_date.isoformat() if r.published_date else "",
                "pdf_url": r.pdf_url,
                "html_url": r.html_url,
            }
            for r in rows
        ],
        "total": len(rows),
    }

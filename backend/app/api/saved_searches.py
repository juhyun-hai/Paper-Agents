"""Saved search endpoints — 사용자가 keyword/tag/category 등록."""
from datetime import timedelta, date as _date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session

router = APIRouter(prefix="/api/saved-searches", tags=["SavedSearch"])


class SavedSearchIn(BaseModel):
    client_id: str = Field(min_length=8, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    keyword: Optional[str] = None
    tag: Optional[str] = None
    category: Optional[str] = None
    email: Optional[str] = Field(default=None, max_length=255)  # email-validator 의존 회피
    frequency: str = Field(default="daily", pattern="^(daily|weekly|off)$")


@router.post("")
async def create_saved_search(payload: SavedSearchIn,
                               session: AsyncSession = Depends(get_async_session)):
    if not (payload.keyword or payload.tag or payload.category):
        raise HTTPException(400, "keyword/tag/category 중 하나 필요")
    r = await session.execute(text("""
        INSERT INTO saved_searches
          (client_id, name, keyword, tag, category, email, frequency)
        VALUES (:c, :n, :kw, :tg, :cat, :em, :f)
        RETURNING id
    """), {'c': payload.client_id, 'n': payload.name, 'kw': payload.keyword,
           'tg': payload.tag, 'cat': payload.category,
           'em': payload.email, 'f': payload.frequency})
    sid = r.scalar()
    await session.commit()
    return {"id": sid, "ok": True}


@router.get("")
async def list_saved_searches(
    client_id: str = Query(..., min_length=8),
    session: AsyncSession = Depends(get_async_session),
):
    rows = (await session.execute(text("""
        SELECT id, name, keyword, tag, category, email, frequency,
               last_matched_at, created_at
        FROM saved_searches WHERE client_id = :c
        ORDER BY created_at DESC
    """), {'c': client_id})).all()
    return {"saved_searches": [dict(r._mapping) for r in rows]}


@router.delete("/{sid}")
async def delete_saved_search(sid: int, client_id: str = Query(..., min_length=8),
                               session: AsyncSession = Depends(get_async_session)):
    await session.execute(text(
        "DELETE FROM saved_searches WHERE id = :i AND client_id = :c"
    ), {'i': sid, 'c': client_id})
    await session.commit()
    return {"ok": True}


@router.get("/{sid}/matches")
async def get_matches(sid: int, days: int = Query(7, ge=1, le=30),
                       session: AsyncSession = Depends(get_async_session)):
    saved = (await session.execute(text(
        "SELECT * FROM saved_searches WHERE id = :i"
    ), {'i': sid})).first()
    if not saved:
        raise HTTPException(404, "not found")
    cutoff = _date.today() - timedelta(days=days)
    s = saved._mapping
    conditions = ["p.published_date >= :cutoff"]
    params = {'cutoff': cutoff}
    if s['tag']:
        conditions.append("""EXISTS (
            SELECT 1 FROM paper_concepts pc
            JOIN concepts c ON c.id = pc.concept_id
            WHERE pc.paper_id = p.id AND c.type='keyword' AND lower(c.name) = lower(:tg)
        )""")
        params['tg'] = s['tag']
    if s['keyword']:
        conditions.append("(p.title ILIKE :kw OR p.abstract ILIKE :kw)")
        params['kw'] = f"%{s['keyword']}%"
    if s['category']:
        conditions.append("p.categories::text ILIKE :cat")
        params['cat'] = f"%{s['category']}%"
    sql = f"""
        SELECT p.arxiv_id, p.title, p.authors, p.published_date, p.html_url
        FROM papers p
        WHERE {' AND '.join(conditions)}
        ORDER BY p.published_date DESC NULLS LAST
        LIMIT 30
    """
    rows = (await session.execute(text(sql), params)).all()
    return {
        "saved_search_id": sid,
        "name": s['name'],
        "matches": [
            {
                "arxiv_id": r.arxiv_id,
                "title": r.title,
                "authors": (r.authors or [])[:3],
                "published_date": r.published_date.isoformat() if r.published_date else None,
                "html_url": r.html_url,
            }
            for r in rows
        ],
        "count": len(rows),
    }

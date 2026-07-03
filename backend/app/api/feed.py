"""RSS / Atom feed — 사용자가 Feedly/Inoreader에 등록 가능.

오늘 featured 25편 + 한국어 요약 일부를 RSS 2.0 / Atom 형식으로 노출.
계정 없이도 매일 자동 업데이트 받음.
"""
from datetime import datetime, timezone, timedelta, date as _date
from typing import Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session

router = APIRouter(prefix="/api/feed", tags=["Feed"])

SITE_URL = "https://hotpaper.ai"


async def _fetch_recent(session: AsyncSession, days: int, limit: int):
    cutoff = _date.today() - timedelta(days=days)
    rows = (await session.execute(text("""
        SELECT p.arxiv_id, p.title, p.authors,
               COALESCE(p.abstract, '') AS abstract,
               p.html_url, p.pdf_url,
               COALESCE(s.summary_text, '') AS summary_text,
               s.figure_count,
               tp.date AS feat_date,
               tp.rank AS rank
        FROM trending_papers tp
        JOIN papers p ON p.arxiv_id = tp.arxiv_id
        LEFT JOIN paper_summaries s ON s.arxiv_id = tp.arxiv_id
        WHERE tp.date >= :cutoff
          AND tp.is_featured = TRUE
        ORDER BY tp.date DESC, tp.rank ASC
        LIMIT :limit
    """), {'cutoff': cutoff, 'limit': limit})).all()
    return rows


def _build_rss(items: list, days: int) -> str:
    """RSS 2.0 XML 생성."""
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">',
        '<channel>',
        f'<title>HotPaper.ai — Featured Daily Papers</title>',
        f'<link>{SITE_URL}</link>',
        f'<description>매일 자동 큐레이션된 AI 논문 Top 25 + 한국어 요약. 최근 {days}일치.</description>',
        '<language>ko-KR</language>',
        f'<lastBuildDate>{now}</lastBuildDate>',
        f'<atom:link href="{SITE_URL}/api/feed/rss" rel="self" type="application/rss+xml" xmlns:atom="http://www.w3.org/2005/Atom"/>',
    ]
    for r in items:
        arxiv_id = r.arxiv_id
        title = escape(r.title or '')
        link = f"{SITE_URL}/paper/{arxiv_id}"
        authors_list = r.authors or []
        author_str = ', '.join(authors_list[:5]) if authors_list else ''
        # 요약 첫 600자만 (HTML 안에 텍스트)
        summary_preview = (r.summary_text or '')[:600].replace('\n', '<br/>')
        if not summary_preview:
            summary_preview = (r.abstract or '')[:400]
        description = f"""<![CDATA[
<p><strong>arXiv:</strong> {arxiv_id} | <strong>저자:</strong> {escape(author_str)}</p>
{summary_preview}
<p><a href="{link}">→ 전체 한국어 요약 + 그림 보기</a></p>
]]>"""
        pub = r.feat_date.strftime("%a, %d %b %Y 09:00:00 +0900") if r.feat_date else now
        lines.extend([
            '<item>',
            f'<title>{title}</title>',
            f'<link>{link}</link>',
            f'<guid isPermaLink="true">{link}</guid>',
            f'<pubDate>{pub}</pubDate>',
            f'<dc:creator>{escape(author_str)}</dc:creator>',
            f'<description>{description}</description>',
            '</item>',
        ])
    lines.extend(['</channel>', '</rss>'])
    return '\n'.join(lines)


@router.get("/rss", response_class=Response)
async def get_rss_feed(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    """RSS 2.0 feed — Feedly/Inoreader 등록용."""
    items = await _fetch_recent(session, days, limit)
    xml = _build_rss(items, days)
    return Response(
        content=xml,
        media_type="application/rss+xml; charset=utf-8",
        headers={"Cache-Control": "public, max-age=600"},
    )


def _extract_one_liner(summary_text: str) -> str:
    """'## 한 줄 요약' 헤더 다음의 첫 비어있지 않은 줄."""
    if not summary_text:
        return ""
    lines = summary_text.splitlines()
    for i, line in enumerate(lines):
        if '한 줄 요약' in line:
            for nxt in lines[i + 1:]:
                t = nxt.strip().lstrip('-').strip()
                if t and not t.startswith('#'):
                    return t.replace('**', '')
            break
    return ""


@router.get("/daily")
async def get_daily_feed(
    date: Optional[str] = Query(None, description="YYYY-MM-DD (없으면 최신 featured 날짜)"),
    limit: int = Query(25, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session),
):
    """홈 daily feed — 랭크된 featured + 한국어 one-liner + tags + 딥 요약 badge.

    HF Daily Papers 스타일 렌더링에 필요한 모든 것을 한 번에.
    """
    # 날짜 네비게이션용: featured 있는 최근 14일
    dates = (await session.execute(text("""
        SELECT DISTINCT date FROM trending_papers
        WHERE is_featured = TRUE
        ORDER BY date DESC LIMIT 14
    """))).scalars().all()
    available = [d.isoformat() for d in dates]
    if not available:
        return {"date": None, "available_dates": [], "papers": []}

    target = date if date in available else available[0]
    target_date = _date.fromisoformat(target)

    rows = (await session.execute(text("""
        SELECT tp.arxiv_id, tp.rank, tp.upvotes, tp.sources, tp.is_hai,
               p.id AS paper_id, p.title, p.authors, p.published_date, p.venue,
               s.summary_text, s.figure_count, s.generation_model
        FROM trending_papers tp
        JOIN papers p ON p.arxiv_id = tp.arxiv_id
        LEFT JOIN paper_summaries s ON s.arxiv_id = tp.arxiv_id
        WHERE tp.date = :d AND tp.is_featured = TRUE
        ORDER BY tp.rank ASC, tp.id ASC
        LIMIT :limit
    """), {'d': target_date, 'limit': limit})).all()

    # 논문별 top tags (concepts.paper_count 순 4개)
    paper_ids = [r.paper_id for r in rows]
    tags_by_paper: dict[int, list[str]] = {}
    if paper_ids:
        tag_rows = (await session.execute(text("""
            SELECT pc.paper_id, c.name,
                   ROW_NUMBER() OVER (PARTITION BY pc.paper_id ORDER BY c.paper_count DESC) AS rn
            FROM paper_concepts pc
            JOIN concepts c ON c.id = pc.concept_id
            WHERE pc.paper_id = ANY(:ids) AND c.type = 'keyword'
        """), {'ids': paper_ids})).all()
        for tr in tag_rows:
            if tr.rn <= 4:
                tags_by_paper.setdefault(tr.paper_id, []).append(tr.name)

    import json as _json
    seen = set()
    papers = []
    for r in rows:
        if r.arxiv_id in seen:
            continue
        seen.add(r.arxiv_id)
        gm = r.generation_model or ""
        srcs = r.sources
        if isinstance(srcs, str):
            try:
                srcs = _json.loads(srcs)
            except Exception:
                srcs = []
        papers.append({
            "arxiv_id": r.arxiv_id,
            "rank": r.rank,
            "title": r.title,
            "authors": (r.authors or [])[:3],
            "one_liner": _extract_one_liner(r.summary_text or ""),
            "has_summary": bool(r.summary_text),
            "deep": '+ar5iv' in gm,
            "unverified": '+unverified' in gm,
            "figure_count": r.figure_count or 0,
            "tags": tags_by_paper.get(r.paper_id, []),
            "upvotes": r.upvotes or 0,
            "sources": srcs or [],
            "is_hai": bool(r.is_hai),
            "venue": r.venue,
        })
    return {"date": target, "available_dates": available, "papers": papers}


@router.get("/today.json")
async def get_today_json(
    session: AsyncSession = Depends(get_async_session),
):
    """오늘 featured 25편 JSON — 간단한 daily digest API용."""
    items = await _fetch_recent(session, days=1, limit=25)
    return {
        "date": datetime.now().date().isoformat(),
        "count": len(items),
        "papers": [
            {
                "arxiv_id": r.arxiv_id,
                "title": r.title,
                "authors": (r.authors or [])[:5],
                "rank": r.rank,
                "html_url": r.html_url,
                "has_summary": bool(r.summary_text),
                "figure_count": r.figure_count or 0,
                "summary_preview": (r.summary_text or '')[:300],
            }
            for r in items
        ],
    }

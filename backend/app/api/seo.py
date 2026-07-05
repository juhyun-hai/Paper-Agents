"""봇/크롤러용 서버렌더 HTML — SPA가 JS 없이 본문 0줄로 보이는 문제(P0) 해결.

검색엔진 봇, AI agent, 링크 프리뷰 크롤러가 읽을 수 있는 완전한 HTML 문서를 제공.
- /api/seo/home              최신 featured 날짜의 25편 + 인기 키워드
- /api/seo/daily/{date}      특정 날짜 버전 (canonical 포함)
- /api/seo/paper/{arxiv_id}  논문 상세 (한국어 요약 전문)
- /api/seo/sitemap.xml       daily + paper + tag 페이지 sitemap
"""
from datetime import date as _date, timedelta
from typing import Optional
from urllib.parse import quote
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session
from .feed import _extract_one_liner

router = APIRouter(prefix="/api/seo", tags=["SEO"])

SITE_URL = "https://hotpaper.ai"
SITE_NAME = "HotPaper.ai"
TAGLINE = "매일 자동 큐레이션되는 AI 논문 Top 25 + 한국어 요약"
CACHE_HEADERS = {"Cache-Control": "public, max-age=1800"}

_BASE_CSS = """
body{font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;
max-width:760px;margin:0 auto;padding:24px 16px;line-height:1.65;color:#1a1a2e}
a{color:#2563eb;text-decoration:none}a:hover{text-decoration:underline}
h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.15rem;margin:1.6em 0 .5em;
border-bottom:1px solid #e5e7eb;padding-bottom:4px}
ol.papers{padding-left:0;list-style:none}ol.papers>li{margin:0 0 18px;padding:12px 14px;
border:1px solid #e5e7eb;border-radius:10px}
.rank{color:#9ca3af;font-weight:700;margin-right:6px}
.one-liner{margin:4px 0;color:#374151}
.authors,.meta{font-size:.85rem;color:#6b7280}
.tags a{display:inline-block;background:#eef2ff;border-radius:999px;
padding:2px 10px;margin:2px 4px 2px 0;font-size:.85rem}
article{margin-top:12px}blockquote{border-left:3px solid #d1d5db;
margin:8px 0;padding:2px 12px;color:#4b5563}
footer{margin-top:32px;font-size:.8rem;color:#9ca3af}
""".strip()


def _esc(s: str) -> str:
    """HTML 본문/속성 공용 escape."""
    return escape(s or "", {'"': "&quot;"})


def _html_doc(title: str, description: str, canonical: str, body: str,
              og_type: str = "website") -> str:
    t, d = _esc(title), _esc(description)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{_esc(canonical)}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{_esc(canonical)}">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<style>{_BASE_CSS}</style>
</head>
<body>
{body}
<footer><a href="{SITE_URL}">{SITE_NAME}</a> — {_esc(TAGLINE)}</footer>
</body>
</html>"""


def _summary_to_html(summary_text: str) -> str:
    """한국어 요약 markdown-lite → HTML (## → h2, - 리스트 → ul, ** → strong)."""
    out: list[str] = []
    in_list = False
    para: list[str] = []

    def _inline(s: str) -> str:
        s = _esc(s)
        # **bold** → <strong>
        parts = s.split("**")
        if len(parts) >= 3:
            rebuilt, open_tag = [], True
            for i, p in enumerate(parts):
                rebuilt.append(p)
                if i < len(parts) - 1:
                    rebuilt.append("<strong>" if open_tag else "</strong>")
                    open_tag = not open_tag
            if not open_tag:  # 짝이 맞을 때만
                s = "".join(rebuilt)
        return s

    def _flush_para():
        if para:
            out.append("<p>" + "<br>".join(para) + "</p>")
            para.clear()

    def _close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in (summary_text or "").splitlines():
        line = raw.strip()
        if not line:
            _flush_para()
            _close_list()
            continue
        if line.startswith("#"):
            _flush_para()
            _close_list()
            heading = line.lstrip("#").strip()
            level = 3 if line.startswith("###") else 2
            out.append(f"<h{level}>{_inline(heading)}</h{level}>")
        elif line.startswith(("- ", "* ")):
            _flush_para()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_inline(line[2:].strip())}</li>")
        elif line.startswith(">"):
            _flush_para()
            _close_list()
            out.append(f"<blockquote>{_inline(line.lstrip('>').strip())}</blockquote>")
        else:
            para.append(_inline(line))
    _flush_para()
    _close_list()
    return "\n".join(out)


async def _featured_dates(session: AsyncSession, limit: int = 60) -> list[_date]:
    rows = (await session.execute(text("""
        SELECT DISTINCT date FROM trending_papers
        WHERE is_featured = TRUE
        ORDER BY date DESC LIMIT :lim
    """), {"lim": limit})).scalars().all()
    return list(rows)


async def _daily_rows(session: AsyncSession, d: _date, limit: int = 25):
    return (await session.execute(text("""
        SELECT tp.rank, tp.arxiv_id, p.title, p.authors, s.summary_text
        FROM trending_papers tp
        JOIN papers p ON p.arxiv_id = tp.arxiv_id
        LEFT JOIN paper_summaries s ON s.arxiv_id = tp.arxiv_id
        WHERE tp.date = :d AND tp.is_featured = TRUE
        ORDER BY tp.rank ASC, tp.id ASC
        LIMIT :lim
    """), {"d": d, "lim": limit})).all()


async def _popular_tags(session: AsyncSession, limit: int = 20):
    return (await session.execute(text("""
        SELECT name, paper_count FROM concepts
        WHERE type = 'keyword' AND paper_count >= 2
        ORDER BY paper_count DESC, name ASC
        LIMIT :lim
    """), {"lim": limit})).all()


def _daily_body(d: _date, rows, tags) -> str:
    items = []
    seen: set[str] = set()
    for r in rows:
        if r.arxiv_id in seen:
            continue
        seen.add(r.arxiv_id)
        authors = ", ".join((r.authors or [])[:5])
        one = _extract_one_liner(r.summary_text or "")
        one_html = f'<p class="one-liner">{_esc(one)}</p>' if one else ""
        items.append(
            f'<li><span class="rank">#{r.rank}</span>'
            f'<a href="{SITE_URL}/paper/{_esc(r.arxiv_id)}"><strong>{_esc(r.title)}</strong></a>'
            f'{one_html}'
            f'<p class="authors">{_esc(authors)}</p></li>'
        )
    tag_links = " ".join(
        f'<a href="{SITE_URL}/tag/{quote(t.name)}">{_esc(t.name)} ({t.paper_count})</a>'
        for t in tags
    )
    return f"""<header>
<h1>{SITE_NAME} — {_esc(TAGLINE)}</h1>
<p class="meta">{d.isoformat()} featured 논문 {len(items)}편</p>
</header>
<main>
<ol class="papers">
{''.join(items)}
</ol>
<h2>인기 키워드</h2>
<p class="tags">{tag_links}</p>
</main>"""


@router.get("/home", response_class=HTMLResponse)
async def seo_home(session: AsyncSession = Depends(get_async_session)):
    """최신 featured 날짜의 25편 — 봇용 서버렌더 홈."""
    dates = await _featured_dates(session, limit=1)
    if not dates:
        raise HTTPException(status_code=404, detail="No featured papers yet")
    d = dates[0]
    rows = await _daily_rows(session, d)
    tags = await _popular_tags(session)
    html = _html_doc(
        title=f"{SITE_NAME} — {TAGLINE}",
        description=f"{d.isoformat()} 기준 featured AI 논문 {len(rows)}편의 한국어 요약.",
        canonical=f"{SITE_URL}/",
        body=_daily_body(d, rows, tags),
    )
    return HTMLResponse(content=html, headers=CACHE_HEADERS)


@router.get("/daily/{date_str}", response_class=HTMLResponse)
async def seo_daily(date_str: str, session: AsyncSession = Depends(get_async_session)):
    """특정 날짜의 featured 논문 페이지 (canonical: /?date=...)."""
    try:
        d = _date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date; use YYYY-MM-DD")
    rows = await _daily_rows(session, d)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No featured papers on {date_str}")
    tags = await _popular_tags(session)
    html = _html_doc(
        title=f"{d.isoformat()} AI 논문 Top {len(rows)} — {SITE_NAME}",
        description=f"{d.isoformat()} featured AI 논문 {len(rows)}편의 한국어 한줄 요약.",
        canonical=f"{SITE_URL}/?date={d.isoformat()}",
        body=_daily_body(d, rows, tags),
    )
    return HTMLResponse(content=html, headers=CACHE_HEADERS)


@router.get("/paper/{arxiv_id}", response_class=HTMLResponse)
async def seo_paper(arxiv_id: str, session: AsyncSession = Depends(get_async_session)):
    """논문 1편 상세 — 제목/저자/초록/한국어 요약 전문."""
    row = (await session.execute(text("""
        SELECT p.arxiv_id, p.title, p.authors, p.abstract,
               p.published_date, p.pdf_url, p.html_url, p.id AS paper_id,
               s.summary_text
        FROM papers p
        LEFT JOIN paper_summaries s ON s.arxiv_id = p.arxiv_id
        WHERE p.arxiv_id = :aid
        LIMIT 1
    """), {"aid": arxiv_id})).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found")

    tag_rows = (await session.execute(text("""
        SELECT c.name FROM paper_concepts pc
        JOIN concepts c ON c.id = pc.concept_id
        WHERE pc.paper_id = :pid AND c.type = 'keyword'
        ORDER BY c.paper_count DESC
        LIMIT 8
    """), {"pid": row.paper_id})).scalars().all()

    one = _extract_one_liner(row.summary_text or "")
    authors = ", ".join(row.authors or [])
    pub = row.published_date.date().isoformat() if row.published_date else ""
    arxiv_url = row.html_url or f"https://arxiv.org/abs/{row.arxiv_id}"
    pdf_url = row.pdf_url or f"https://arxiv.org/pdf/{row.arxiv_id}"

    parts = [
        "<header>",
        f"<h1>{_esc(row.title)}</h1>",
        f'<p class="authors">{_esc(authors)}</p>',
        f'<p class="meta">arXiv:{_esc(row.arxiv_id)}'
        + (f" · {pub} 공개" if pub else "")
        + f' · <a href="{_esc(arxiv_url)}">arXiv</a>'
        + f' · <a href="{_esc(pdf_url)}">PDF</a></p>',
        "</header>",
        "<main>",
    ]
    if tag_rows:
        parts.append('<p class="tags">' + " ".join(
            f'<a href="{SITE_URL}/tag/{quote(t)}">{_esc(t)}</a>' for t in tag_rows
        ) + "</p>")
    if row.abstract:
        parts.append(f"<h2>Abstract</h2><p>{_esc(row.abstract)}</p>")
    if row.summary_text:
        parts.append(f"<h2>한국어 요약</h2><article>{_summary_to_html(row.summary_text)}</article>")
    parts.append("</main>")

    html = _html_doc(
        title=row.title or row.arxiv_id,
        description=one or (row.abstract or "")[:200],
        canonical=f"{SITE_URL}/paper/{row.arxiv_id}",
        body="\n".join(parts),
        og_type="article",
    )
    return HTMLResponse(content=html, headers=CACHE_HEADERS)


@router.get("/sitemap.xml")
async def seo_sitemap(session: AsyncSession = Depends(get_async_session)):
    """sitemap.xml — 최근 30일 daily + 최근 60일 featured paper + 인기 tag."""
    today = _date.today()
    urls: list[tuple[str, Optional[str]]] = [(f"{SITE_URL}/", today.isoformat())]

    day_rows = (await session.execute(text("""
        SELECT DISTINCT date FROM trending_papers
        WHERE is_featured = TRUE AND date >= :cutoff
        ORDER BY date DESC
    """), {"cutoff": today - timedelta(days=30)})).scalars().all()
    for d in day_rows:
        urls.append((f"{SITE_URL}/?date={d.isoformat()}", d.isoformat()))

    paper_rows = (await session.execute(text("""
        SELECT arxiv_id, MAX(date) AS last_date FROM trending_papers
        WHERE is_featured = TRUE AND date >= :cutoff
        GROUP BY arxiv_id
        ORDER BY last_date DESC
    """), {"cutoff": today - timedelta(days=60)})).all()
    for r in paper_rows:
        urls.append((f"{SITE_URL}/paper/{r.arxiv_id}",
                     r.last_date.isoformat() if r.last_date else None))

    tags = await _popular_tags(session, limit=50)
    for t in tags:
        urls.append((f"{SITE_URL}/tag/{quote(t.name)}", None))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in urls:
        entry = f"<loc>{escape(loc)}</loc>"
        if lastmod:
            entry += f"<lastmod>{lastmod}</lastmod>"
        lines.append(f"<url>{entry}</url>")
    lines.append("</urlset>")

    return Response(
        content="\n".join(lines),
        media_type="application/xml; charset=utf-8",
        headers=CACHE_HEADERS,
    )

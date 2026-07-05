#!/usr/bin/env python3
"""오늘의 연구 흐름 요약 — featured 25편 기반 3-4문장 한국어 브리핑 생성.

- 오늘(또는 --date YYYY-MM-DD)의 featured 논문 제목 + one_liner + tags 수집
- Ollama qwen3:14b 로 브리핑 생성 ("오늘은 X, Y 주제가 강세. 특히 Z...")
- daily_overviews upsert (멱등: ON CONFLICT date DO UPDATE)
- auto_daily_summaries.py cron 끝에서 자동 호출됨

Usage:
    python generate_daily_overview.py [--date 2026-07-05] [--force]
"""
from __future__ import annotations
import argparse
import asyncio
import json
import re
import sys
from datetime import date as _date

import asyncpg
import httpx

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
OLLAMA_URL = 'http://localhost:11434'
MODEL = 'qwen3:14b'

SYSTEM_PROMPT = """당신은 AI 연구 동향을 브리핑하는 한국어 에디터입니다.
오늘 큐레이션된 논문 목록(제목 + 한 줄 요약 + 태그)을 보고,
독자가 30초 안에 오늘의 연구 흐름을 파악할 수 있는 브리핑을 작성합니다.

[규칙]
- 반드시 3~4문장 한국어. 형식 예시:
  "오늘은 X, Y 주제가 강세입니다. 특히 Z 접근이 여러 편에서 등장했습니다. 주목할 논문은 ...입니다."
- 목록에 실제로 등장한 주제·논문만 언급. 추측 금지.
- 논문 제목을 언급할 때는 짧게 축약 가능.
- top_themes: 오늘 목록에서 가장 두드러진 주제 3~5개 (한국어 또는 영어 키워드).

[출력 — 반드시 이 JSON 형식만]
{"overview": "3~4문장 브리핑", "top_themes": ["theme1", "theme2", "theme3"]}"""


async def fetch_papers(conn, target: _date) -> list[dict]:
    rows = await conn.fetch("""
        SELECT tp.rank, p.id AS paper_id, p.title,
               COALESCE(s.summary_text, '') AS summary_text
        FROM trending_papers tp
        JOIN papers p ON p.arxiv_id = tp.arxiv_id
        LEFT JOIN paper_summaries s ON s.arxiv_id = tp.arxiv_id
        WHERE tp.date = $1 AND tp.is_featured = TRUE
        ORDER BY tp.rank ASC, tp.id ASC
        LIMIT 25
    """, target)
    papers = [dict(r) for r in rows]
    if not papers:
        return []

    # 논문별 top tags (paper_count 순 최대 4개)
    ids = [p['paper_id'] for p in papers]
    tag_rows = await conn.fetch("""
        SELECT pc.paper_id, c.name,
               ROW_NUMBER() OVER (PARTITION BY pc.paper_id ORDER BY c.paper_count DESC) AS rn
        FROM paper_concepts pc
        JOIN concepts c ON c.id = pc.concept_id
        WHERE pc.paper_id = ANY($1::int[]) AND c.type = 'keyword'
    """, ids)
    tags_by_paper: dict[int, list[str]] = {}
    for tr in tag_rows:
        if tr['rn'] <= 4:
            tags_by_paper.setdefault(tr['paper_id'], []).append(tr['name'])
    for p in papers:
        p['tags'] = tags_by_paper.get(p['paper_id'], [])
        p['one_liner'] = _extract_one_liner(p['summary_text'])
    return papers


def _extract_one_liner(summary_text: str) -> str:
    """'## 한 줄 요약' 헤더 다음의 첫 비어있지 않은 줄 (feed.py와 동일 로직)."""
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


def build_user_msg(papers: list[dict], target: _date) -> str:
    lines = [f"날짜: {target.isoformat()} — 큐레이션 {len(papers)}편\n"]
    for p in papers:
        entry = f"{p['rank']}. {p['title']}"
        if p['one_liner']:
            entry += f"\n   요약: {p['one_liner'][:150]}"
        if p['tags']:
            entry += f"\n   태그: {', '.join(p['tags'])}"
        lines.append(entry)
    lines.append("\n위 목록을 근거로 JSON 브리핑을 작성하세요.")
    return '\n'.join(lines)


def generate_overview(papers: list[dict], target: _date) -> tuple[str, list[str]] | None:
    """Ollama 호출 → (overview_text, top_themes). 실패 시 None."""
    user_msg = build_user_msg(papers, target)
    try:
        with httpx.Client(timeout=300) as cli:
            r = cli.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL,
                    "stream": False,
                    "think": False,
                    "format": "json",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "options": {
                        "num_predict": 600,
                        "num_ctx": 8192,
                        "temperature": 0.4,
                        "top_p": 0.9,
                    },
                },
            )
            r.raise_for_status()
            content = r.json().get('message', {}).get('content', '').strip()
    except Exception as e:
        print(f"  ⚠️ Ollama err: {e}")
        return None

    if not content:
        return None
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # JSON 파싱 실패 fallback — {...} 블록만 추출 시도
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if not m:
            print(f"  ⚠️ invalid JSON: {content[:200]}")
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            print(f"  ⚠️ invalid JSON: {content[:200]}")
            return None

    overview = (data.get('overview') or '').strip()
    themes = data.get('top_themes') or []
    if not isinstance(themes, list):
        themes = []
    themes = [str(t).strip() for t in themes if str(t).strip()][:5]
    if len(overview) < 30:
        print(f"  ⚠️ overview too short: {overview!r}")
        return None
    return overview, themes


async def upsert_overview(conn, target: _date, text: str, themes: list[str]):
    await conn.execute("""
        INSERT INTO daily_overviews (date, overview_text, top_themes, created_at)
        VALUES ($1, $2, $3::jsonb, NOW())
        ON CONFLICT (date) DO UPDATE
        SET overview_text = EXCLUDED.overview_text,
            top_themes = EXCLUDED.top_themes,
            created_at = NOW()
    """, target, text, json.dumps(themes, ensure_ascii=False))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='YYYY-MM-DD (기본: featured 있는 최신 날짜)')
    ap.add_argument('--force', action='store_true', help='이미 있어도 재생성')
    args = ap.parse_args()

    conn = await asyncpg.connect(DB_URL)
    try:
        if args.date:
            target = _date.fromisoformat(args.date)
        else:
            # 오늘 featured 없으면 (아직 큐레이션 전) 최신 featured 날짜로
            row = await conn.fetchrow("""
                SELECT MAX(date) AS d FROM trending_papers WHERE is_featured = TRUE
            """)
            if not row or not row['d']:
                print("❌ featured 데이터 없음")
                sys.exit(1)
            target = row['d']

        existing = await conn.fetchrow(
            "SELECT 1 FROM daily_overviews WHERE date = $1", target)
        if existing and not args.force:
            print(f"✅ {target} overview 이미 존재 — skip (--force로 재생성)")
            return

        papers = await fetch_papers(conn, target)
        if not papers:
            print(f"❌ {target} featured 논문 없음")
            sys.exit(1)
        print(f"🎯 {target} — featured {len(papers)}편으로 overview 생성 ({MODEL})")

        result = generate_overview(papers, target)
        if not result:
            print("❌ overview 생성 실패")
            sys.exit(1)
        overview, themes = result

        await upsert_overview(conn, target, overview, themes)
        print(f"✅ saved daily_overviews[{target}]")
        print(f"   themes: {themes}")
        print(f"   overview: {overview}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
r"""HotPaper MCP server — Claude Desktop / Cursor 에서 hotpaper DB 검색.

설치/실행:
  pip install mcp httpx
  python hotpaper_mcp.py

Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` 또는
Windows `%APPDATA%\Claude\claude_desktop_config.json`):
  {
    "mcpServers": {
      "hotpaper": {
        "command": "python",
        "args": ["/path/to/hotpaper_mcp.py"]
      }
    }
  }

제공하는 tool:
  • hotpaper_search(query, k=10)          — 의미 기반 검색
  • hotpaper_today()                      — 오늘 featured 25편
  • hotpaper_paper(arxiv_id)              — 1편 메타 + 한국어 요약
  • hotpaper_tag_papers(tag, limit=20)    — 특정 tag 가진 paper 리스트
  • hotpaper_popular_tags(limit=30)       — 인기 dynamic tag

모두 hotpaper.ai 공개 API를 호출 — DB 직접 접근 X (배포 무관).
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: 'mcp' package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# api.hotpaper.ai 직접 — hotpaper.ai/api는 정적 호스팅이 SPA를 반환할 수 있음
BASE = os.environ.get("HOTPAPER_API", "https://api.hotpaper.ai/api").rstrip("/")
TIMEOUT = 30.0

# 개인화 프로필 — 사용자 로컬에만 저장, 서버로 전송되지 않음.
PROFILE_PATH = Path(os.environ.get(
    "HOTPAPER_PROFILE", str(Path.home() / ".hotpaper" / "profile.json")))
# 아이디어 인큐베이터 로그 (JSON Lines) — 논문에서 온 아이디어 + 내 아이디어가
# 함께 쌓이는 곳. 로컬 전용.
IDEAS_PATH = Path(os.environ.get(
    "HOTPAPER_IDEAS", str(Path.home() / ".hotpaper" / "ideas.jsonl")))


def _load_profile() -> dict | None:
    try:
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_profile(profile: dict) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_idea(entry: dict) -> int:
    IDEAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_ideas()
    entry["id"] = (max((e.get("id", 0) for e in existing), default=0) + 1)
    with IDEAS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry["id"]


def _load_ideas() -> list[dict]:
    if not IDEAS_PATH.exists():
        return []
    out = []
    for line in IDEAS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as cli:
        r = await cli.get(f"{BASE}{path}", params=params)
        r.raise_for_status()
        return r.json()


def _format_papers(papers: list, limit: int = 10) -> str:
    """paper list를 LLM이 잘 읽을 marakdown으로."""
    if not papers:
        return "(결과 없음)"
    lines = []
    for i, p in enumerate(papers[:limit], 1):
        aid = p.get('arxiv_id', '?')
        title = p.get('title', '?')
        authors = p.get('authors') or []
        authors_str = ', '.join(authors[:3]) + (' …' if len(authors) > 3 else '')
        abs_preview = (p.get('abstract') or p.get('summary_preview') or '')[:200]
        lines.append(
            f"{i}. **{title}** ({aid})\n"
            f"   _{authors_str}_\n"
            f"   {abs_preview}…\n"
            f"   → https://hotpaper.ai/paper/{aid}"
        )
    return '\n\n'.join(lines)


# ── Tool implementations ─────────────────────────────────────────

async def tool_search(query: str, k: int = 10) -> str:
    """의미 기반 paper 검색 (BGE-m3 임베딩)."""
    data = await _get("/search", params={"q": query, "limit": k})
    papers = data.get("papers") or data.get("results") or []
    return f"### '{query}' 검색 결과 ({len(papers)}편)\n\n{_format_papers(papers, k)}"


async def tool_today() -> str:
    """오늘 featured 25편."""
    data = await _get("/feed/today.json")
    papers = data.get("papers", [])
    return f"### 오늘 ({data.get('date')}) Featured {len(papers)}편\n\n{_format_papers(papers, 25)}"


async def tool_paper(arxiv_id: str) -> str:
    """1편 메타 + 한국어 deep summary."""
    data = await _get(f"/papers/{arxiv_id}")
    paper = data.get('paper') or data
    aid = paper.get('arxiv_id', arxiv_id)
    title = paper.get('title', '?')
    authors = ', '.join((paper.get('authors') or [])[:8])
    # 요약은 별도 endpoint
    summary_text = ''
    try:
        sd = await _get(f"/papers/{aid}/summary")
        summary_text = (sd.get('summary') or sd.get('summary_text') or '')
    except Exception:
        pass
    out = [
        f"# {title}",
        f"**arXiv:** {aid} | **저자:** {authors}",
        f"**Link:** https://hotpaper.ai/paper/{aid}",
        "",
        "## Abstract",
        paper.get('abstract', '')[:1500],
    ]
    if summary_text:
        out += ["", "## 한국어 요약", summary_text[:3500]]
    return '\n'.join(out)


async def tool_tag_papers(tag: str, limit: int = 20) -> str:
    """특정 tag 가진 paper."""
    data = await _get("/tags/papers", params={"tag": tag, "limit": limit})
    papers = data.get("papers", [])
    return f"### Tag '{tag}' ({len(papers)}편)\n\n{_format_papers(papers, limit)}"


def tool_save_profile(topics: list, keywords: list, name: str = "",
                       description: str = "") -> str:
    """연구 프로필을 로컬(~/.hotpaper/profile.json)에 저장."""
    profile = {
        "name": name,
        "topics": [str(t).strip() for t in topics if str(t).strip()],
        "keywords": sorted({str(k).strip().lower() for k in keywords if str(k).strip()}),
        "description": description,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_profile(profile)
    return (f"✅ 프로필 저장됨 → {PROFILE_PATH}\n"
            f"- topics: {', '.join(profile['topics'])}\n"
            f"- keywords ({len(profile['keywords'])}): {', '.join(profile['keywords'][:15])}"
            f"{' …' if len(profile['keywords']) > 15 else ''}\n"
            f"(이 파일은 로컬에만 저장되며 서버로 전송되지 않습니다)")


def tool_get_profile() -> str:
    p = _load_profile()
    if not p:
        return ("(프로필 없음) hotpaper_save_profile로 만들 수 있어요.\n"
                "예: 사용자의 연구 폴더/노트를 읽고 topics·keywords를 추출한 뒤 저장하세요.")
    return json.dumps(p, ensure_ascii=False, indent=2)


def _match_score(paper: dict, keywords: list[str]) -> tuple[int, list[str]]:
    """프로필 keyword가 paper의 tags/제목/one-liner에 몇 개나 등장하는지."""
    hay = " ".join([
        paper.get("title", ""), paper.get("one_liner", ""),
        " ".join(paper.get("tags", [])),
    ]).lower()
    hits = [kw for kw in keywords if kw and kw in hay]
    return len(hits), hits


async def tool_today_for_me() -> str:
    """오늘 featured를 프로필과 매칭 — 관련 논문 상세 + 나머지는 제목만."""
    profile = _load_profile()
    if not profile:
        return ("프로필이 없습니다. 먼저 사용자의 연구 폴더/논문/노트를 읽고 "
                "hotpaper_save_profile(topics, keywords)로 프로필을 만들어 주세요.")
    kws = profile.get("keywords", [])
    data = await _get("/feed/daily", params={"limit": 25})
    papers = data.get("papers", [])
    ov = data.get("overview") or {}

    scored = []
    for p in papers:
        n, hits = _match_score(p, kws)
        scored.append((n, hits, p))
    scored.sort(key=lambda x: (-x[0], x[2].get("rank", 99)))

    matched = [(n, h, p) for n, h, p in scored if n > 0]
    rest = [p for n, _h, p in scored if n == 0]

    lines = [f"### {data.get('date')} — '{profile.get('name') or '내'}' 프로필 매칭 결과"]
    if ov.get("text"):
        lines.append(f"\n📡 오늘의 흐름: {ov['text']}")
    lines.append(f"\n**프로필 topics:** {', '.join(profile.get('topics', []))}")
    if matched:
        lines.append(f"\n## 🎯 관련 논문 {len(matched)}편")
        for n, hits, p in matched:
            lines.append(
                f"\n- **{p['title']}** ({p['arxiv_id']}) — 매칭: {', '.join(hits)}\n"
                f"  {p.get('one_liner', '')}\n"
                f"  → https://hotpaper.ai/paper/{p['arxiv_id']}")
    else:
        lines.append("\n(오늘은 키워드 직접 매칭이 없음 — 아래 전체 목록에서 "
                     "의미상 관련된 것을 골라 설명해 주세요)")
    lines.append(f"\n## 나머지 {len(rest)}편 (제목만)")
    for p in rest:
        lines.append(f"- {p['title']} ({p['arxiv_id']})")
    lines.append("\n(매칭은 단순 키워드 기준입니다 — 제목/한줄요약을 보고 "
                 "의미상 관련된 논문을 추가로 짚어 주면 좋습니다. "
                 "특정 논문을 사용자 연구와 깊이 연결하려면 "
                 "hotpaper_research_brief(arxiv_id)를 호출하세요)")
    return "\n".join(lines)


async def tool_research_brief(arxiv_id: str) -> str:
    """research agent 재료 패킷: 프로필 + 딥요약 전문 + 관련 논문.

    호스트 에이전트가 이걸 근거로 '내 연구와의 접점 → 확장 아이디어 →
    다음 읽기 경로'를 브리핑하도록 지시문까지 포함해 반환한다.
    """
    profile = _load_profile() or {}

    # 한국어 딥요약 전문 (hotpaper의 핵심 자산 — 이걸 근거로 안내)
    summary_text, title = "", arxiv_id
    try:
        sd = await _get(f"/summary/{arxiv_id}")
        s = sd.get("summary") or {}
        summary_text = s.get("summary_text", "")
        title = s.get("title") or title
    except Exception:
        pass

    # 임베딩 기반 관련 논문
    related = []
    try:
        rd = await _get(f"/recommend/{arxiv_id}", params={"limit": 5})
        related = rd.get("recommendations") or []
    except Exception:
        pass

    parts = [f"# 연구 연결 브리핑 재료 — {title} ({arxiv_id})"]
    if profile:
        parts.append(
            "\n## 사용자 연구 프로필\n"
            f"- topics: {', '.join(profile.get('topics', []))}\n"
            f"- keywords: {', '.join(profile.get('keywords', [])[:20])}\n"
            f"- 소개: {profile.get('description', '')}")
    else:
        parts.append("\n## 사용자 연구 프로필\n(없음 — 일반 독자 기준으로 브리핑)")

    if summary_text:
        parts.append(f"\n## hotpaper 한국어 딥요약 (근거 자료)\n{summary_text[:4000]}")
    else:
        parts.append("\n## hotpaper 요약\n(아직 없음 — 사이트에서 생성 대기 중일 수 있음)")

    if related:
        parts.append("\n## 임베딩 기반 관련 논문 (다음 읽기 후보)")
        for p in related[:5]:
            parts.append(f"- {p.get('title', '?')} ({p.get('arxiv_id', '?')}) "
                         f"→ https://hotpaper.ai/paper/{p.get('arxiv_id', '')}")

    parts.append(
        "\n---\n"
        "[에이전트 지시] 위 자료만 근거로, 사용자에게 한국어로 다음 구조의 "
        "연구 연결 브리핑을 작성하세요:\n"
        "1. **내 연구와의 접점** — 프로필 topics와 이 논문의 방법/문제의식이 만나는 지점 (1-2개, 구체적으로)\n"
        "2. **확장 아이디어** — 이 논문의 기법을 사용자 연구에 적용/변형하는 구체적 방향 2-3개 "
        "(요약에 명시된 모듈·수치를 인용해 근거 제시)\n"
        "3. **다음 읽기 경로** — 관련 논문 중 사용자 프로필에 맞는 순서 추천\n"
        "요약에 없는 실험 수치는 지어내지 말 것. "
        f"전문/그림은 https://hotpaper.ai/paper/{arxiv_id} 안내.")
    return "\n".join(parts)


def tool_idea_log(text: str, source: str = "paper",
                  papers: list | None = None, tags: list | None = None) -> str:
    """아이디어 한 조각을 로컬 인큐베이터 로그에 추가.

    source: 'paper'(논문에서 발견) | 'mine'(내 생각) | 'combined'(조합해 만든 새 아이디어)
    """
    entry = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "text": text.strip(),
        "source": source if source in ("paper", "mine", "combined") else "paper",
        "papers": [str(p) for p in (papers or [])],
        "tags": [str(t).strip().lower() for t in (tags or []) if str(t).strip()],
    }
    idea_id = _append_idea(entry)
    label = {"paper": "논문 발견", "mine": "내 아이디어", "combined": "조합 아이디어"}[entry["source"]]
    return (f"✅ 아이디어 #{idea_id} 저장됨 [{label}] → {IDEAS_PATH}\n"
            f"  {entry['text'][:120]}\n"
            f"(로컬에만 저장됩니다. 'hotpaper_idea_board'로 지금까지 쌓인 걸 종합할 수 있어요)")


def tool_idea_board(days: int = 0) -> str:
    """쌓인 아이디어 전부 + 종합/조합/수렴 지시를 반환 (research agent의 인큐베이터 모드)."""
    ideas = _load_ideas()
    if days > 0:
        cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # 단순 문자열 비교로 최근 N일 (YYYY-MM-DD 정렬 가능)
        from datetime import timedelta
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        ideas = [i for i in ideas if i.get("date", "") >= since]
    if not ideas:
        return ("(아이디어 로그가 비어 있습니다) hotpaper_idea_log로 조각을 쌓기 시작하세요.\n"
                "예: 오늘 논문을 보다가 떠오른 빈틈, 내 머릿속 아이디어, 두 개를 합친 조합 등.")

    profile = _load_profile() or {}
    by_source = {"paper": [], "mine": [], "combined": []}
    for i in ideas:
        by_source.get(i.get("source", "paper"), by_source["paper"]).append(i)

    lines = [f"# 아이디어 인큐베이터 — 누적 {len(ideas)}조각"]
    if profile.get("topics"):
        lines.append(f"\n관심 영역: {', '.join(profile['topics'])}")
    for src, label in [("paper", "📄 논문에서 발견"), ("mine", "💡 내 아이디어"),
                       ("combined", "🔗 조합해서 만든 것")]:
        items = by_source[src]
        if not items:
            continue
        lines.append(f"\n## {label} ({len(items)})")
        for i in items:
            paps = f" [{', '.join(i['papers'])}]" if i.get("papers") else ""
            lines.append(f"- #{i.get('id')} ({i.get('date')}) {i['text']}{paps}")

    lines.append(
        "\n---\n"
        "[에이전트 지시] 위에 쌓인 아이디어들을 근거로 사용자에게 한국어로 종합해 주세요:\n"
        "1. **수렴 방향** — 반복해서 등장하는 주제/키워드는? 사용자의 관심이 어디로 모이고 있나 (목표 후보)\n"
        "2. **새 조합** — 서로 다른 조각 2-3개를 결합해 만들 수 있는 **새로운 연구 방향**을 "
        "구체적으로 제안 (특히 '내 아이디어'와 '논문 발견'을 교차 결합). 만든 새 방향은 "
        "hotpaper_idea_log(source='combined')로 다시 저장하도록 사용자에게 제안.\n"
        "3. **다음 액션** — 가장 유망한 1-2개에 대해, 검증하려면 무엇을 더 읽거나 실험해야 하는지\n"
        "억지로 연결하지 말고, 근거가 약하면 '아직 조각이 부족하다'고 솔직히 말할 것.")
    return "\n".join(lines)


async def tool_incubate() -> str:
    """오늘 논문(프로필 매칭) + 쌓인 아이디어를 함께 보고 '빈틈·연결·새 조합'을 찾는 재료 패킷."""
    profile = _load_profile() or {}
    kws = profile.get("keywords", [])
    ideas = _load_ideas()

    data = await _get("/feed/daily", params={"limit": 25})
    papers = data.get("papers", [])
    ov = data.get("overview") or {}

    # 프로필 매칭 상위 + 나머지 제목
    scored = []
    for p in papers:
        n, hits = _match_score(p, kws)
        scored.append((n, hits, p))
    scored.sort(key=lambda x: (-x[0], x[2].get("rank", 99)))

    lines = [f"# 아이디어 인큐베이션 — {data.get('date')}"]
    if profile.get("topics"):
        lines.append(f"관심 영역: {', '.join(profile['topics'])}")
    if ov.get("text"):
        lines.append(f"\n오늘의 흐름: {ov['text']}")

    lines.append("\n## 오늘 논문 (제목 · 한줄요약)")
    for n, hits, p in scored:
        mark = f" ⭐{','.join(hits)}" if hits else ""
        lines.append(f"- {p['title']} ({p['arxiv_id']}){mark}\n  {p.get('one_liner', '')}")

    recent = ideas[-8:] if ideas else []
    if recent:
        lines.append(f"\n## 지금까지 쌓인 아이디어 (최근 {len(recent)}개)")
        for i in recent:
            lines.append(f"- #{i.get('id')} [{i.get('source')}] {i['text']}")
    else:
        lines.append("\n## 지금까지 쌓인 아이디어\n(아직 없음 — 오늘이 첫 시작)")

    lines.append(
        "\n---\n"
        "[에이전트 지시] 위 오늘 논문 + 기존 아이디어를 근거로, 사용자에게 한국어로:\n"
        "1. **빈틈 발견** — 오늘 논문 중 '이 기술은 사용자 관심 영역에 아직 적용 안 된 것 같다 = "
        "기회/논문거리'인 것을 1-3개 짚기 (구체적으로 왜 빈틈인지)\n"
        "2. **연결** — 오늘 논문과 '지금까지 쌓인 아이디어'가 이어지는 지점이 있으면 명시\n"
        "3. **새 조합 제안** — 오늘 것 + 기존 것으로 만들 수 있는 새 방향 (있으면)\n"
        "그리고 사용자가 마음에 들어하는 발견은 hotpaper_idea_log로 저장하도록 제안하세요 "
        "(source: 논문 발견이면 'paper', 조합이면 'combined'). "
        "논문 전문은 https://hotpaper.ai/paper/{id} 로 안내. 요약에 없는 수치는 지어내지 말 것.")
    return "\n".join(lines)


async def tool_popular_tags(limit: int = 30) -> str:
    """인기 dynamic tag."""
    data = await _get("/tags/popular", params={"limit": limit, "min_count": 2})
    tags = data.get("tags", [])
    lines = [f"### 인기 키워드 (paper_count 순, {len(tags)}개)\n"]
    for t in tags:
        lines.append(f"- **{t['name']}** ({t['count']}편)")
    return '\n'.join(lines)


# ── MCP server registration ───────────────────────────────────────

server = Server("hotpaper")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="hotpaper_search",
             description="HotPaper.ai DB에서 의미 기반 paper 검색 (BGE-m3 임베딩 + 한국어 요약).",
             inputSchema={
                 "type": "object",
                 "properties": {
                     "query": {"type": "string", "description": "검색어 (한/영 모두 OK)"},
                     "k": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                 },
                 "required": ["query"],
             }),
        Tool(name="hotpaper_today",
             description="오늘 자동 큐레이션된 Featured 25편 (HuggingFace + arXiv + Conference).",
             inputSchema={"type": "object", "properties": {}}),
        Tool(name="hotpaper_paper",
             description="특정 arXiv id의 메타 + 한국어 deep summary (ar5iv 본문 기반).",
             inputSchema={
                 "type": "object",
                 "properties": {"arxiv_id": {"type": "string", "description": "예: 2410.05258"}},
                 "required": ["arxiv_id"],
             }),
        Tool(name="hotpaper_tag_papers",
             description="LLM이 자동 추출한 tag 기준으로 paper 리스트 (예: 'reinforcement-learning', 'vision-language-action').",
             inputSchema={
                 "type": "object",
                 "properties": {
                     "tag": {"type": "string"},
                     "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                 },
                 "required": ["tag"],
             }),
        Tool(name="hotpaper_popular_tags",
             description="현재 인기 dynamic tag 리스트 (자동 추출, paper_count 순).",
             inputSchema={
                 "type": "object",
                 "properties": {"limit": {"type": "integer", "default": 30, "minimum": 5, "maximum": 100}},
             }),
        Tool(name="hotpaper_save_profile",
             description=("사용자의 연구 프로필을 로컬(~/.hotpaper/profile.json)에 저장. "
                          "사용자의 연구 폴더/논문/노트를 읽고 topics(사람이 읽는 주제 3-7개)와 "
                          "keywords(매칭용 영문 소문자 키워드 10-25개, hotpaper tag 스타일: "
                          "'diffusion-models', 'fault-diagnosis' 등)를 추출해 호출하세요. "
                          "로컬에만 저장되며 어떤 서버로도 전송되지 않습니다."),
             inputSchema={
                 "type": "object",
                 "properties": {
                     "topics": {"type": "array", "items": {"type": "string"}},
                     "keywords": {"type": "array", "items": {"type": "string"}},
                     "name": {"type": "string", "description": "사용자 이름/별칭 (선택)"},
                     "description": {"type": "string", "description": "연구 한 줄 소개 (선택)"},
                 },
                 "required": ["topics", "keywords"],
             }),
        Tool(name="hotpaper_get_profile",
             description="저장된 로컬 연구 프로필 조회 (없으면 만들기 안내).",
             inputSchema={"type": "object", "properties": {}}),
        Tool(name="hotpaper_today_for_me",
             description=("오늘 featured 논문을 사용자 프로필과 매칭 — 관련 논문(매칭 키워드 포함) + "
                          "나머지 제목 목록 반환. '오늘 내 연구 관련 논문 뭐 나왔어?' 류 질문에 사용. "
                          "매칭된 논문을 더 깊이 연결하고 싶으면 hotpaper_research_brief로 이어가세요."),
             inputSchema={"type": "object", "properties": {}}),
        Tool(name="hotpaper_research_brief",
             description=("research agent 모드: 특정 논문을 사용자 연구와 연결 — "
                          "hotpaper 한국어 딥요약 전문 + 사용자 프로필 + 임베딩 관련 논문을 재료로 반환. "
                          "'이 논문 내 연구에 어떻게 써먹을 수 있어?', '확장 아이디어 줘', "
                          "'이거 읽을 가치 있어?' 류 질문에 사용. 반환된 지시 구조"
                          "(접점→확장 아이디어→다음 읽기)대로 브리핑할 것."),
             inputSchema={
                 "type": "object",
                 "properties": {"arxiv_id": {"type": "string", "description": "예: 2607.13431"}},
                 "required": ["arxiv_id"],
             }),
        Tool(name="hotpaper_incubate",
             description=("아이디어 인큐베이터 (목표가 막연할 때): 오늘 논문 + 지금까지 쌓인 "
                          "아이디어를 함께 보고 '빈틈(아직 내 분야에 안 쓰인 기술=기회) · 연결 · "
                          "새 조합'을 찾는다. '오늘 파볼 만한 빈틈 찾아줘', '오늘 뭐 인큐베이트 "
                          "할까?' 류에 사용. 발견은 hotpaper_idea_log로 저장 유도."),
             inputSchema={"type": "object", "properties": {}}),
        Tool(name="hotpaper_idea_log",
             description=("아이디어 한 조각을 로컬 인큐베이터 노트(~/.hotpaper/ideas.jsonl)에 저장. "
                          "논문에서 발견한 빈틈, 사용자 본인의 아이디어, 둘을 합친 새 조합 모두 저장 가능. "
                          "'이 아이디어 저장해줘', '내 생각 적어둬' 류에 사용."),
             inputSchema={
                 "type": "object",
                 "properties": {
                     "text": {"type": "string", "description": "아이디어 내용 (한 문장~한 문단)"},
                     "source": {"type": "string", "enum": ["paper", "mine", "combined"],
                                "description": "paper=논문발견 / mine=내생각 / combined=조합해만든것"},
                     "papers": {"type": "array", "items": {"type": "string"},
                                "description": "관련 arxiv id (선택)"},
                     "tags": {"type": "array", "items": {"type": "string"}},
                 },
                 "required": ["text"],
             }),
        Tool(name="hotpaper_idea_board",
             description=("쌓인 아이디어 전부를 종합 — 수렴 방향(목표 후보) · 조각을 결합한 새 "
                          "연구 방향 생성 · 다음 액션. '지금까지 아이디어 정리해줘', '이것들로 "
                          "새로운 거 만들어봐', '내 아이디어 어디로 수렴해?' 류에 사용."),
             inputSchema={
                 "type": "object",
                 "properties": {"days": {"type": "integer", "default": 0,
                                         "description": "최근 N일만 (0=전체)"}},
             }),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "hotpaper_search":
            text = await tool_search(arguments["query"], arguments.get("k", 10))
        elif name == "hotpaper_today":
            text = await tool_today()
        elif name == "hotpaper_paper":
            text = await tool_paper(arguments["arxiv_id"])
        elif name == "hotpaper_tag_papers":
            text = await tool_tag_papers(arguments["tag"], arguments.get("limit", 20))
        elif name == "hotpaper_popular_tags":
            text = await tool_popular_tags(arguments.get("limit", 30))
        elif name == "hotpaper_save_profile":
            text = tool_save_profile(
                arguments["topics"], arguments["keywords"],
                arguments.get("name", ""), arguments.get("description", ""))
        elif name == "hotpaper_get_profile":
            text = tool_get_profile()
        elif name == "hotpaper_today_for_me":
            text = await tool_today_for_me()
        elif name == "hotpaper_research_brief":
            text = await tool_research_brief(arguments["arxiv_id"])
        elif name == "hotpaper_incubate":
            text = await tool_incubate()
        elif name == "hotpaper_idea_log":
            text = tool_idea_log(
                arguments["text"], arguments.get("source", "paper"),
                arguments.get("papers"), arguments.get("tags"))
        elif name == "hotpaper_idea_board":
            text = tool_idea_board(arguments.get("days", 0))
        else:
            text = f"Unknown tool: {name}"
    except httpx.HTTPStatusError as e:
        text = f"API error {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        text = f"Error: {type(e).__name__}: {e}"
    return [TextContent(type="text", text=text)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def cli_main():
    """console_scripts entry point (uvx/pipx: `hotpaper-mcp`)."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()

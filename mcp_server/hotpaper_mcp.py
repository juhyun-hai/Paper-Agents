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


def _load_profile() -> dict | None:
    try:
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_profile(profile: dict) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


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
                 "의미상 관련된 논문을 추가로 짚어 주면 좋습니다)")
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
                          "나머지 제목 목록 반환. '오늘 내 연구 관련 논문 뭐 나왔어?' 류 질문에 사용."),
             inputSchema={"type": "object", "properties": {}}),
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

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
import os
import sys

import httpx

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: 'mcp' package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

BASE = os.environ.get("HOTPAPER_API", "https://hotpaper.ai/api").rstrip("/")
TIMEOUT = 30.0


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


if __name__ == "__main__":
    asyncio.run(main())

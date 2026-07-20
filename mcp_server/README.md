# HotPaper MCP server

> **연구실 공유용 5분 설정 가이드: [docs/COMPANION.md](../docs/COMPANION.md)**
> (uvx 한 줄 설치 + 개인 연구 프로필 매칭 — Claude Code/Desktop/Codex/Cursor)


Claude Desktop / Cursor / Claude Code에서 HotPaper.ai DB를 검색하는 MCP server.

## 설치

```bash
pip install mcp httpx
```

## Claude Desktop 등록

설정 파일 위치:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hotpaper": {
      "command": "python",
      "args": ["/absolute/path/to/hotpaper_mcp.py"]
    }
  }
}
```

재시작 후 Claude Desktop에서 자동 발견.

## Cursor 등록

`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "hotpaper": {
      "command": "python",
      "args": ["/absolute/path/to/hotpaper_mcp.py"]
    }
  }
}
```

## 제공하는 tool

| Tool | 설명 |
|---|---|
| `hotpaper_search(query, k=10)` | BGE-m3 임베딩 의미 검색 (한/영 모두) |
| `hotpaper_today()` | 오늘 자동 큐레이션 Featured 25편 |
| `hotpaper_paper(arxiv_id)` | 1편 메타 + 한국어 deep summary (ar5iv 본문) |
| `hotpaper_tag_papers(tag, limit=20)` | 특정 자동 추출 tag의 paper |
| `hotpaper_popular_tags(limit=30)` | 현재 인기 dynamic tag |

## 사용 예시 (Claude Desktop)

> "최근 vision-language-action 모델 논문 5개 요약해줘"
→ Claude가 `hotpaper_tag_papers("vision-language-action", limit=5)` 호출

> "오늘 hot paper 25편 중에서 robotics 관련만 골라줘"
→ `hotpaper_today()` 호출 후 자체 필터링

> "2410.05258 paper 한국어로 깊이 있게 설명해줘"
→ `hotpaper_paper("2410.05258")` 호출 → ar5iv 기반 deep summary 반환

## 모두 공개 API 호출

DB 직접 접근 X, 공식 endpoint (`https://hotpaper.ai/api/*`) 호출.
배포 환경 무관, 사용자 컴퓨터에서 stdio로 작동.

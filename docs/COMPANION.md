# HotPaper Companion — 내 연구 맞춤 논문 브리핑 (5분 설정)

hotpaper.ai를 **내 연구 분야 기준으로** 쓰게 해주는 플러그인입니다.
Claude Code / Claude Desktop / Codex / Cursor 어디든 MCP로 붙습니다.

- 여러분의 연구 폴더·노트는 **본인 컴퓨터를 떠나지 않습니다** — 프로필은 `~/.hotpaper/profile.json`에만 저장
- 사이트/서버에 계정·개인정보 없음. LLM은 여러분이 쓰는 에이전트(Claude/Codex)가 담당
- 필요한 것: Python 3.10+ 와 [uv](https://docs.astral.sh/uv/) (`pip install uv` 또는 `brew install uv`)

---

## 1. 설치 (도구별 한 줄)

### Claude Code
```bash
claude mcp add hotpaper --scope user -- \
  uvx --from "git+https://github.com/juhyun-hai/Paper-Agents.git#subdirectory=mcp_server" hotpaper-mcp
```

### Codex CLI
```bash
codex mcp add hotpaper -- \
  uvx --from "git+https://github.com/juhyun-hai/Paper-Agents.git#subdirectory=mcp_server" hotpaper-mcp
```

### Claude Desktop
`claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`):
```json
{
  "mcpServers": {
    "hotpaper": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/juhyun-hai/Paper-Agents.git#subdirectory=mcp_server", "hotpaper-mcp"]
    }
  }
}
```

### Cursor
`.cursor/mcp.json` — Claude Desktop과 동일한 JSON.

설치 후 도구를 재시작하면 `hotpaper_*` 도구 8개가 자동으로 붙습니다.

---

## 2. 프로필 만들기 (한 마디)

에이전트에게 이렇게 말하세요 (Claude Code처럼 파일 접근이 되는 도구에서):

> **"내 연구 폴더 `~/research` 읽고 hotpaper 프로필 만들어줘"**

에이전트가 폴더의 README/논문 초안/노트를 읽고 → 연구 주제(topics)와
매칭 키워드(keywords)를 추출해 → `hotpaper_save_profile`로 저장합니다.

파일 접근이 없는 도구(Claude Desktop)라면 직접 말해도 됩니다:

> "내 연구는 산업 설비 고장 진단이랑 physics-informed ML이야. hotpaper 프로필로 저장해줘"

프로필은 `~/.hotpaper/profile.json` — 열어서 직접 고쳐도 되고,
"프로필에 diffusion 키워드 추가해줘"라고 해도 됩니다.

---

## 3. 매일 쓰기

| 하고 싶은 것 | 이렇게 말하세요 |
|---|---|
| 오늘 내 관련 논문 | **"오늘 hotpaper에서 내 연구 관련 논문 뭐 나왔어?"** |
| 🔬 **연구 연결 브리핑** | **"이 논문 내 연구에 어떻게 써먹을 수 있어?"** / "확장 아이디어 줘" |
| 읽을 가치 판단 | "2607.13431 나한테 읽을 가치 있어?" |
| 전체 25편 | "오늘 hotpaper 논문 다 보여줘" |
| 주제 검색 | "hotpaper에서 uncertainty-aware fault diagnosis 검색해줘" |
| 논문 깊이 읽기 | "2607.13431 한국어 요약 보여줘" |
| 트렌드 파악 | "요즘 hotpaper에서 뜨는 키워드 뭐야?" |

**🔬 연구 연결 브리핑**이 핵심입니다 — hotpaper의 딥요약을 근거로
① 내 연구와의 접점 ② 적용/확장 아이디어 2-3개 ③ 다음 읽기 경로를 안내합니다.
(요약에 없는 수치는 지어내지 않도록 설계됨)

`hotpaper_today_for_me`가 프로필 키워드로 1차 매칭을 하고,
에이전트가 의미상 관련된 논문까지 짚어서 설명해줍니다.

---

## 4. FAQ

**Q. 내 연구 데이터가 hotpaper 서버로 가나요?**
아니요. 프로필은 로컬 파일이고, 서버로 가는 것은 공개 API 조회(검색어 등)뿐입니다.

**Q. 사이트에 내 분야가 추가되나요?**
아니요. 사이트는 그대로이고, 개인화는 전부 여러분 컴퓨터 안에서 일어납니다.

**Q. GPU/로컬 LLM 필요한가요?**
아니요. 지능은 여러분이 쓰는 에이전트(Claude/Codex)가 담당합니다.

**Q. 제공 도구 전체 목록?**
`hotpaper_today` · `hotpaper_today_for_me` · `hotpaper_research_brief` · `hotpaper_search` ·
`hotpaper_paper` · `hotpaper_tag_papers` · `hotpaper_popular_tags` ·
`hotpaper_save_profile` · `hotpaper_get_profile`

**Q. 업데이트는?**
`uvx`는 실행 시 git에서 받아오므로, 재시작하면 최신입니다 (캐시 갱신: `uv cache clean hotpaper-companion`).

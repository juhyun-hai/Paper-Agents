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

---

## 4-2. 아이디어 인큐베이터 (목표가 아직 막연할 때)

"이루려는 게 아직 안 정해졌는데, 매일 논문 보며 아이디어를 쌓다 보면 방향이
선명해졌으면" 할 때 쓰는 모드입니다. 논문에서 발견한 것 + 내 머릿속 생각이
`~/.hotpaper/ideas.jsonl`에 함께 쌓이고, 조합해서 새 방향을 만들어냅니다.

| 하고 싶은 것 | 이렇게 말하세요 |
|---|---|
| 오늘 파볼 빈틈 찾기 | **"오늘 논문에서 내가 파볼 만한 빈틈 찾아줘"** (오늘 논문 × 쌓인 아이디어) |
| 아이디어 저장 | "이 아이디어 저장해줘" / "내 생각 적어둬: ..." |
| 종합·새 방향 만들기 | **"지금까지 쌓인 아이디어 정리하고 새로운 방향 만들어봐"** |

**흐름 예시:**
- (월) "오늘 빈틈 찾아줘" → 에이전트가 오늘 논문 중 미개척 지점 짚음 → 마음에 들면 저장
- (목) "오늘도" → 오늘 논문이 월요일 아이디어와 연결되는 지점 발견
- (2주 뒤) "아이디어 정리해줘" → "네 관심이 이 방향으로 수렴 = 목표 후보" + 조각들을 조합한 새 연구 방향 제안

내 아이디어(`source: mine`)와 논문 발견(`source: paper`)을 **교차 결합**해
새 방향(`source: combined`)을 만드는 게 이 모드의 핵심입니다.
매일 한 마디씩 쌓아야 효과가 납니다 — 안 쌓으면 빈 노트예요.

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

**Q. 제공 도구 전체 목록? (14개)**
`hotpaper_today` · `hotpaper_today_for_me` · `hotpaper_research_brief` ·
`hotpaper_incubate` · `hotpaper_idea_log` · `hotpaper_idea_board` ·
`hotpaper_init_workspace` · `hotpaper_workspace_status` ·
`hotpaper_search` · `hotpaper_paper` · `hotpaper_tag_papers` ·
`hotpaper_popular_tags` · `hotpaper_save_profile` · `hotpaper_get_profile`

**Q. 프로젝트(폴더)마다 따로 관리할 수 있나요?**
네. **폴더별로 자동 분리**됩니다 (git이 폴더마다 `.git` 두는 것과 같은 방식).
- 논문 폴더 A에서 프로필을 만들면 → `A/.hotpaper/` 에 저장
- 다른 폴더 B에서 열면 → `B/.hotpaper/` 로 완전히 별개
- 하위 폴더에서 열어도 상위의 프로젝트를 자동으로 찾습니다
- 아무 폴더도 프로젝트가 아니면 → 전역 `~/.hotpaper/` (잡다한 용도)

모든 응답 맨 위에 `📁 프로젝트: <경로>` 로 **지금 어디에 저장 중인지 항상 표시**됩니다.
- **"여기서 hotpaper 시작해줘"** → 현재 폴더를 프로젝트로 만듦 (`hotpaper_init_workspace`)
- **"지금 어느 프로젝트야?"** / "내 프로젝트 목록" → `hotpaper_workspace_status`

**Q. 아이디어/프로필 파일 위치?**
프로젝트면 `<폴더>/.hotpaper/{profile.json, ideas.jsonl}`, 전역이면 `~/.hotpaper/`.
전부 로컬 파일 — 직접 열어봐도 되고, 폴더째 복사하면 다른 컴퓨터로 그대로 옮겨집니다.
서버로 전송되지 않습니다.

**Q. 업데이트는?**
`uvx`는 실행 시 git에서 받아오므로, 재시작하면 최신입니다 (캐시 갱신: `uv cache clean hotpaper-companion`).

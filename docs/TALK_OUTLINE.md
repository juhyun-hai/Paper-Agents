# HotPaper.ai 강연 outline skeleton

> 채워서 강연 prep에 사용. 아래는 30-60분 강연용 골격.

## 1. Hook (2분)

- "매일 arXiv에 1000+ 논문, 어떤 게 중요한지 어떻게 알까?"
- HotPaper 데모 1 클릭: 오늘의 25편 보여주기
- "이 발표 끝나면 여러분도 자기 분야 hotpaper 직접 만들 수 있음"

## 2. 문제 (3분)

- 신선한 정보 ≠ 신뢰할 정보
- 광범위 RSS → 노이즈
- 영어 요약 → 한국어 의역 → 깊이 손실
- 사람이 못 따라감

## 3. 시스템 design (10분)

### 4-layer modular
```
Collector  → 다중 소스 (HF + arXiv + Crossref + Conference)
Scorer     → featured_score v4 (popularity × cross × venue × HAI)
Summarizer → ar5iv 본문 → Ollama qwen3:32b 한국어 deep summary
Agent      → BGE-m3 RAG + qwen3:14b 한국어 답변
```

### 핵심 결정 5개
- **로컬 LLM** (외부 API 의존 0, 비용 0)
- **ar5iv HTML** (PDF 다운로드 0)
- **per-paper transaction** (1편 실패 ≠ 전체 fail)
- **0편이면 fail ping** (구조적 무음 실패 차단)
- **Dynamic tag extraction** (hardcoded 카테고리 폐기)

## 4. Live demo (10분)

| 시연 | 화면 |
|---|---|
| Featured 25 | hotpaper.ai 홈 |
| Deep summary | 1편 클릭, 한국어 요약 + 그림 |
| Tag chip | tag 클릭 → 같은 주제 paper |
| Paper Agent | 자연어 질문 → 인용 답변 |
| MCP from Claude Desktop | "오늘 hot paper 5개 알려줘" |

## 5. 청중 hands-on (15분)

자기 분야 fork → 5분 안에 자기 사이트:

1. `git clone` + `docker compose up`
2. `templates/CUSTOMIZE.md` 보고 keyword 변경
3. 첫 ingest run
4. localhost:8000 확인

## 6. 핵심 lesson (5분)

- **광범위 X, 의미 검색 ○** — conf seed → 관련 arXiv
- **하드코드 X, 자동 추출 ○** — LLM tag extract
- **모니터링 = monitoring** — 0편 fail ping
- **PDF 0** — ar5iv HTML
- **광고 0** — 학술 도구는 학술적으로

## 7. Q&A (5-10분)

자주 묻는 질문 미리 준비:
- "왜 GPT-4 안 쓰고 Ollama?" — 비용, 신뢰, 데이터 privacy
- "강연 시간 안에 진짜 다 만들 수 있어?" — fork만 5분, customize 30분
- "내 분야에 어떻게 적용?" — `templates/CUSTOMIZE.md`
- "Conference 우선이라며 RSS는?" — 둘 다 (Conf seed → arxiv semantic bridge)

---

## Demo mode 준비

```bash
# 청중 화면용 가벼운 demo (실제 DB 안 건드림)
docker compose -f demo.compose.yml up
# → localhost:8001
```

→ TODO: `demo.compose.yml` 작성 (read-only snapshot)

## Slide 패키지

→ TODO: `slides/` 디렉토리 + Keynote/PowerPoint 또는 marp .md

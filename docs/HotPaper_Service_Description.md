# HotPaper.ai 서비스 설명서

> 교수님 발표용 정리 문서. 실제 구현된 기능 중심, 과장 없이 작성.

---

## 1. HotPaper.ai의 전체 목적

### 해결하려는 문제
- 매일 arXiv에 수백 편의 AI 논문이 올라오지만, 연구자가 모두 훑어보는 것은 비현실적
- 영문 초록만 읽고 핵심을 빠르게 판단하는 데 시간이 많이 소요됨
- HAI Lab의 산업 AI 연구 분야(Industrial Foundation Models, PHM, Manufacturing 등)와 관련된 최신 동향을 별도로 추적하기 어려움

### 사이트에서 할 수 있는 일
- 매일 자동 큐레이션된 **Top 25 논문**을 한 페이지에서 확인
- 각 논문의 **한국어 요약**(7개 섹션 구조, 핵심 그림 포함) 열람
- **연구실 관심 분야**(HAI Lab Picks) 별도 페이지에서 산업 AI 관련 논문 탐색
- 키워드 검색 + 의미 기반(semantic) 검색
- 논문 상세 페이지에서 **유사 논문 추천**과 **미니 그래프** 확인

### 기존 방식과 비교한 자동화 포인트
| 단계 | 기존 방식 | HotPaper.ai |
|---|---|---|
| 후보 수집 | 사용자가 arXiv RSS, X(Twitter), HuggingFace 일일 확인 | 3개 소스에서 매일 자동 수집 |
| 중요도 판단 | 사용자가 초록을 직접 훑고 판단 | 다중 소스 consensus + upvote + HAI 키워드 점수화 |
| 한글 이해 | 영문 초록만 → 사용자가 머릿속에서 번역 | 7섹션 한국어 요약 자동 생성 |
| 시각자료 | PDF 내부에서 직접 탐색 | 핵심 Figure/Table 자동 추출 |
| 관련 연구 탐색 | 인용 traversal 수동 | 임베딩 기반 자동 추천 |

---

## 2. 주요 기능 정리

### (1) 매일 후보 논문 수집

**수집 소스 (3개)**
- **HuggingFace Daily Papers** (~50편/일): 사람이 큐레이션한 일일 추천, upvote 신호 포함
- **arXiv RSS** (cs.AI / cs.LG / cs.CL / cs.CV 카테고리 × 약 20편 = ~80편/일): 신규성 신호
- **Crossref** (~30편/일): 최근 30일 인용 급증 저널 논문

**자동 실행 방식**
- `crontab`에 등록: `0 3 * * *` (매일 새벽 3시 KST)
- 실제 실행 파일: `backend/scripts/run_daily.sh`
  → 내부에서 `daily_cron.py` 호출 후 `backfill_figures.py` 호출
- systemd user service로 백엔드 + Cloudflared 터널 24시간 가동 (재부팅 자동 복구)

**저장 기준 (변경됨, 2026-05-26)**
- 이전: 모든 수집 논문(~200편/일)을 `papers` 테이블에 저장
- 현재: **랭킹 후 Top 25만 저장** (비-featured는 폐기)
- 그 결과 매일 누락 요약이 쌓이는 문제 제거

**코드 근거**
- `backend/scripts/daily_cron.py` — `fetch_hf_trending()`, `fetch_arxiv_rss()`, `fetch_crossref_trending()`, `save_papers()`
- `backend/scripts/run_daily.sh` — 일일 파이프라인 wrapper
- `crontab -l` — 새벽 3시 스케줄 등록

---

### (2) 중요도 기반 선정 (Featured Top 25)

**점수 공식 (v3)**
```
popularity  = log10(1 + upvotes) × 2.0
cross_mul   = {1소스: 1.0, 2소스: 1.8, 3소스: 2.6, 4소스: 3.2}
hf_bonus    = 1.0 if HF Daily에 등장 else 0
hai_bonus   = (5 if HAI 회원 저자 else 0) + min(HAI키워드, 5) × 1.5

featured_score = (popularity + 1.0) × cross_mul + hf_bonus + hai_bonus
```

**각 요소의 의미 (발표용)**

| 요소 | 발표용 설명 |
|---|---|
| **log 정규화 popularity** | upvote가 159인 논문이 10인 논문보다 16배 중요한 게 아니라 ~2배 정도라는 직관 반영. outlier에 흔들리지 않음 |
| **cross_mul (consensus)** | 여러 플랫폼이 동시에 동일 논문을 다루는 것이 가장 강한 품질 신호. 곱셈으로 가산 |
| **hf_bonus** | HF Daily Papers는 사람이 큐레이션한 trustable signal — 등장 자체에 가산점 |
| **HAI 회원 floor** | 연구실 구성원 저자 논문은 popularity가 낮아도 일정 점수 보장 |
| **HAI 키워드 cap** | 산업 AI 키워드 매칭은 가산하되 상한 둠 — Top 25를 HAI로 도배하지 않기 위함 (HAI 전용 페이지가 따로 있으므로) |

**선정 절차**
1. 후보 풀의 모든 논문에 점수 계산
2. 점수 내림차순 정렬 후 상위 25편을 `trending_papers` 테이블에 `is_featured=TRUE`로 표시
3. 동일 25편을 `papers` 테이블에도 저장 (이후 단계에서 사용)

**코드 근거**
- `backend/scripts/daily_cron.py` — `save_trending()` 함수 (featured_score 계산 + top-25 선정)
- `backend/app/api/trending.py` — `/api/featured/today`, `/api/featured/this-week` 응답
- `backend/app/models/paper.py` — `trending_papers` 테이블 스키마 (`featured_score`, `is_featured` 컬럼)

---

### (3) 한국어 요약 생성

**LLM**
- Anthropic Claude Opus 4 (`claude-opus-4-20250514`)
- 자동 트리거: 매일 13:07 KST (Remote Trigger / Claude Code Routine)에 당일 Featured 25편 요약 일괄 생성

**요약 템플릿 (7개 섹션)**
```
## 한 줄 요약
## 핵심 기여도
## 핵심 아이디어
## 기술적 접근법
## 주요 결과
## 의의 및 한계
## 실용적 활용
```
- 평균 280–340 단어

**Hallucination 방지 (Prompt Guard)**
- 입력은 **제목 + 초록** 만 사용 (PDF 본문은 사용 안 함)
- 프롬프트 명시 제약:
  - 수치는 초록에 명시된 값만 인용
  - 초록에 없으면 "unknown" 또는 hedging 표현 사용
  - 다른 논문의 결과나 가정을 끌어오지 않음
- 검증 단계: 단어 수 체크 + 7개 섹션 헤더 누락 시 재생성

**입력 정보**
- 제목, 초록 (DB에 저장된 텍스트)
- PDF 본문은 요약 입력에서 제외 (저작권 + hallucination 방지)
- PDF는 **그림 추출용**으로만 다운로드 (PyMuPDF, arXiv 도메인만)

**그림 추출**
- `PyMuPDF`로 PDF 페이지 렌더링
- 정규식으로 캡션(`Figure N:`, `Table N:`) 감지 → 해당 영역만 PNG로 자름
- 최대 5개, DPI 150
- arXiv ID만 허용 (출판사 PDF는 저작권 차단)

**코드 근거**
- `backend/scripts/generate_claude_summaries_bl_062.py` — 표준 배치 요약 스크립트 (템플릿)
- `backend/scripts/generate_claude_summaries_bl_062~099.py` — 배치별 변형 (총 86 + 13 배치 사용)
- `backend/app/services/figure_extractor.py` — `extract_figures()` (캡션 anchor 기반 PNG 렌더링)
- `backend/app/api/summary.py` — `/api/summary/extract-figures/{arxiv_id}`, `/api/summary/save`
- `backend/app/models/paper.py` — `PaperSummary` 모델 (summary_text, figures JSONB, generation_model)

---

### (4) 논문 간 유사도 그래프

**한 줄 요약**
> 모든 논문을 1024차원 임베딩으로 변환해 pgvector에 저장하고, 코사인 거리로 유사 논문을 추천하며, 논문 상세 페이지에서 D3.js 미니 그래프로 시각화한다.

**임베딩 모델**
- `BAAI/bge-m3` (1024차원, multilingual)
- 논문 1개당 3종 임베딩 저장: `title_embedding`, `abstract_embedding`, `full_embedding`

**벡터 DB**
- PostgreSQL 16 + `pgvector` extension
- `Vector(1024)` 컬럼, 코사인 거리 연산자 `<=>` 사용

**유사도 계산 및 활용**
- 코사인 유사도 (`1 - cosine_distance`)
- Hybrid search: 텍스트 가중치 0.3 + 의미 가중치 0.7
- 임계값: `settings.similarity_threshold` (기본 0.7)

**프론트엔드 시각화**
- 논문 상세 페이지(`/paper/:arxiv_id`)에 **MiniGraph 컴포넌트** 표시
- D3.js force-directed layout
- 노드 크기 = 인용 수 (로그 스케일), 색상 = 카테고리, 엣지 두께 = 유사도

**API**
- `GET /api/recommend/{arxiv_id}` — 유사 논문 N개 추천
- `GET /api/graph/mini/{arxiv_id}` — 특정 논문 중심의 미니 그래프 데이터
- `GET /api/search?q=...` — 하이브리드 검색

**참고: 전체 지식 그래프 페이지** (`KnowledgeGraph.jsx`, `Graph.jsx`)는 코드로 구현돼 있으나 현재 라우팅(`App.jsx`)에 등록되지 않은 실험 단계. 사용자가 접근하는 것은 논문별 미니 그래프뿐.

**코드 근거**
- `backend/app/services/embedding_service.py` — `EmbeddingService.encode_texts()`, `find_similar_papers()`
- `backend/scripts/generate_embeddings.py`, `generate_missing_embeddings.py` — 배치 임베딩 생성
- `backend/app/services/graph_service.py` — `build_similarity_edges()` (cosine threshold 기반)
- `backend/app/api/papers.py` — `/api/recommend`, hybrid search 로직
- `backend/app/api/graph.py` — `/api/graph/mini`, `/api/graph/subgraph`
- `frontend/src/components/MiniGraph.jsx` — D3.js force simulation
- `backend/app/core/config.py` — `embedding_model = "BAAI/bge-m3"`, `embedding_dimension = 1024`

---

### (5) 웹 기반 탐색

**활성 라우팅** (`frontend/src/App.jsx`)

| 경로 | 페이지 | 주요 기능 |
|---|---|---|
| `/` | Home | Hero + Hot Topics + Today's Top 25 미리보기 + HAI Lab Picks 미리보기 + 통계 |
| `/search` | Search | 시맨틱 검색 + Sidebar 필터 (카테고리, 정렬, 날짜) + 페이지네이션 |
| `/paper/:arxiv_id` | Paper 상세 | 3개 탭 (Abstract / AI요약 / 관련 논문) + 사이드바 (MiniGraph, Quick Actions) |
| `/trending` | Trending | Today / This Week 탭, 소스 배지, 트렌딩 점수 |
| `/hai` | HaiPapers | HAI Lab 토픽 필터 + 출처 필터(Lab/arXiv) + 제목/저자 텍스트 검색 |

**대표 사용자 흐름**

```
홈 진입
  → "Today's Top 25" 섹션에서 흥미로운 제목 클릭
  → 논문 상세: AI요약 탭에서 한글 7섹션 + 핵심 그림 5개 확인
  → 사이드바 MiniGraph에서 관련 논문 발견
  → 관련 논문 클릭 → 새 상세 페이지
```

```
HAI Picks 진입
  → 토픽 칩에서 "Manufacturing AI" 선택
  → 필터된 논문 카드 목록
  → 카드 클릭 → 상세 페이지 (arXiv 논문이면 한글 요약 / 출판사 논문이면 abstract + 외부 링크)
```

**코드 근거**
- `frontend/src/App.jsx` — Router 정의 (5개 활성 경로)
- `frontend/src/pages/Home.jsx`, `Search.jsx`, `Paper.jsx`, `HaiPapers.jsx`, `TrendingPapers.jsx`
- `frontend/src/components/Navigation.jsx` — 스티키 네비게이션, 4개 메인 메뉴

---

## 3. 시스템 아키텍처

### 계층 구조

```
┌──────────────────────────────────────────────────────────────────┐
│  Frontend: React 18 + Vite + Tailwind                            │
│  - Cloudflare Pages 배포 (hotpaper.ai)                            │
│  - D3.js (MiniGraph), React Router, Axios                         │
└─────────────────────────────┬────────────────────────────────────┘
                              │ HTTPS
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Edge: Cloudflared Tunnel (api.hotpaper.ai → localhost:8000)     │
│  - systemd user service, 자동 재시작                                │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Backend: FastAPI + uvicorn (Python 3.12)                        │
│  - 라우터: papers / trending / summary / research / graph         │
│  - 서비스: embedding_service / figure_extractor / summary_service │
│  - systemd user service                                            │
└─────────────────────────────┬────────────────────────────────────┘
                              │ asyncpg
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Storage: PostgreSQL 16 + pgvector (Docker)                      │
│  - papers / paper_summaries / trending_papers                     │
│  - Vector(1024) 컬럼 (제목/초록/전체 임베딩)                         │
│  - restart: unless-stopped                                         │
└──────────────────────────────────────────────────────────────────┘

      ┌────────────────────────────────────────────────────────────┐
      │  외부: Anthropic Claude Opus 4 (요약 생성)                  │
      │       arXiv / HuggingFace / Crossref API (수집)             │
      └────────────────────────────────────────────────────────────┘
```

### 매일 자동 업데이트 파이프라인

```
03:00 KST   crontab → run_daily.sh
            ├─ daily_cron.py
            │  ├─ HF Daily / arXiv RSS / Crossref fetch
            │  ├─ 저자 batch lookup (arXiv API)
            │  ├─ featured_score 계산 (popularity + consensus + HF + HAI)
            │  ├─ Top 25 선정
            │  └─ papers + trending_papers 테이블에 저장
            └─ backfill_figures.py
               └─ 그림 누락분 추출 (PyMuPDF)

13:07 KST   Remote Trigger → 단일 Claude 에이전트
            ├─ 오늘 featured 25편 조회
            ├─ 각각 한국어 7섹션 요약 생성
            └─ paper_summaries 테이블에 저장

상시        FastAPI 서비스
            └─ 프론트엔드에 API 응답
```

### 사용된 기술 스택

| 영역 | 기술 | 역할 |
|---|---|---|
| Frontend | React 18, Vite, Tailwind, React Router, D3.js | UI, 라우팅, 그래프 시각화 |
| Hosting (FE) | Cloudflare Pages | 정적 배포 |
| Edge | Cloudflared Tunnel | 외부 → 로컬 백엔드 노출 |
| Backend | FastAPI, uvicorn, asyncpg, SQLAlchemy 2.0 | API 서버, 비동기 DB 접근 |
| Storage | PostgreSQL 16, pgvector, Docker | 메타데이터 + 벡터 |
| Embedding | sentence-transformers, BAAI/bge-m3 | 1024차원 임베딩 |
| PDF 처리 | PyMuPDF, Pillow | 그림 추출 |
| LLM | Anthropic Claude Opus 4 | 한국어 요약 |
| 스케줄 | crontab + systemd user services | 자동 실행, 자동 재시작 |

---

## 4. 발표 슬라이드용 요약

### A. 1-slide 요약

- **제목**: HotPaper.ai — 매일 자동 큐레이션되는 한국어 AI 논문 다이제스트
- **한 줄 메시지**: 매일 쏟아지는 AI 논문 중 25편을 자동 선별해, 한국어 요약과 시각자료로 빠르게 훑어볼 수 있는 연구실 맞춤 큐레이션 서비스
- **5개 주요 기능**
  - 다중 소스 일일 자동 수집 (HuggingFace / arXiv / Crossref)
  - consensus + 인기 + 연구실 관심도 기반 Top 25 선정
  - Claude 기반 7섹션 한국어 요약 자동 생성
  - 1024차원 임베딩 기반 유사 논문 추천 + 미니 그래프 시각화
  - HAI Lab 연구 분야 맞춤 큐레이션 페이지 별도 제공

---

### B. 기능별 슬라이드 문구

#### 슬라이드 ①: 매일 후보 논문 자동 수집
- **한 줄 설명**: 매일 새벽 3시에 3개 외부 소스에서 후보 논문을 자동 수집합니다
- **발표용 설명**: HuggingFace Daily Papers, arXiv RSS, Crossref 3개 채널에서 매일 약 130편의 후보 논문을 수집합니다. 사람이 큐레이션한 채널과 카테고리 RSS, 인용 기반 채널을 함께 사용해 단일 소스의 편향을 줄입니다. 모든 수집과 후속 처리는 crontab과 systemd 기반으로 무인 자동화되어 있습니다.
- **그림 아이디어**: 3개 소스 아이콘 → 깔때기(funnel) → 점수화 후보 풀

#### 슬라이드 ②: 중요도 기반 Top 25 선정
- **한 줄 설명**: 인기 신호와 다중 소스 합의, 연구실 관심도를 결합한 점수로 매일 25편을 선정합니다
- **발표용 설명**: HuggingFace upvote(로그 정규화), 출처 중복도(consensus multiplier), HAI Lab 키워드 가중치를 단일 점수로 결합합니다. 단일 outlier에 흔들리지 않도록 로그 변환을 사용하고, 여러 소스에서 동시에 다뤄지는 논문일수록 곱셈으로 점수가 높아져 자연스럽게 상위에 노출됩니다. HAI 키워드는 상한(cap)을 두어 일반 핫이슈가 가려지지 않게 균형을 잡았습니다.
- **그림 아이디어**: 후보 풀 → 점수 공식 박스 → 정렬 후 상위 25개 강조

#### 슬라이드 ③: 한국어 요약 자동 생성
- **한 줄 설명**: Claude Opus 4가 제목과 초록만으로 한국어 7섹션 요약을 생성합니다
- **발표용 설명**: Anthropic Claude Opus 4를 사용해 매일 13시에 당일 선정된 25편의 한국어 요약을 일괄 생성합니다. 한 줄 요약 / 핵심 기여 / 핵심 아이디어 / 기술적 접근 / 주요 결과 / 의의·한계 / 실용적 활용으로 구성된 표준 템플릿을 따르며, 입력은 제목과 초록으로 한정해 본문 외 수치를 끌어오지 않도록 제약합니다. 추가로 PDF에서 핵심 Figure를 최대 5개까지 캡션 기반으로 자동 추출해 요약과 함께 표시합니다.
- **그림 아이디어**: 영문 abstract → Claude 아이콘 → 한글 7섹션 카드

#### 슬라이드 ④: 유사 논문 추천 및 미니 그래프
- **한 줄 설명**: 모든 논문을 1024차원 임베딩으로 변환해 유사 논문을 자동 추천합니다
- **발표용 설명**: BAAI/bge-m3 모델로 제목·초록·전체 텍스트의 임베딩을 만들어 pgvector에 저장합니다. 코사인 유사도로 관련 논문을 빠르게 조회할 수 있고, 논문 상세 페이지에서는 D3.js 기반 미니 그래프로 주변 논문 관계를 시각적으로 확인할 수 있습니다. 검색은 키워드(텍스트)와 의미(임베딩)를 7:3 비율로 결합한 hybrid 방식을 사용합니다.
- **그림 아이디어**: 논문 노드를 중심으로 force-directed 그래프, 엣지 두께 = 유사도

#### 슬라이드 ⑤: 웹 기반 탐색
- **한 줄 설명**: 홈 / 검색 / 트렌딩 / HAI 4개 진입점에서 논문을 빠르게 탐색합니다
- **발표용 설명**: 홈에는 Today's Top 25와 HAI Lab Picks 미리보기가 노출됩니다. 검색은 시맨틱 자동완성과 카테고리·날짜·정렬 필터를 지원하고, 논문 상세 페이지에서는 한국어 요약과 미니 그래프, 관련 논문 추천을 한 화면에서 확인합니다. 모바일을 포함한 반응형 UI로 구현돼 있습니다.
- **그림 아이디어**: 4개 페이지 썸네일을 사용자 흐름 화살표로 연결

---

### C. 교수님 대상 설명 톤 가이드

**권장 표현**
- "매일 자동 수집·선별", "한국어 요약 자동 생성", "연구실 관심 분야 반영"
- "기존 분산된 정보 채널을 한 화면에서 효율화", "최신 동향 탐색을 지원"
- "외부 신호(upvote, 인용, 다중 출처)를 결합해 우선순위 부여"

**피해야 할 표현**
- "최초", "완벽", "환각 없음", "정확도 100%", "유일한"
- "사람보다 잘함", "전문가 수준" 같은 과장 비교

---

## 5. 추가: HAI Lab 연구 분야 맞춤 큐레이션

### (1) HAI Lab 관심 분야 반영

**코드에 정의된 키워드와 토픽** (`backend/app/core/hai_config.py`)

- **HAI Lab 멤버 명단** (`HAI_LAB_MEMBERS`): 지도교수 Byeng D. Youn (이름 변형 포함)
- **HAI 키워드** (40개 이상의 다단어 키워드)
  - 예: `industrial foundation model`, `physics-informed machine learning`, `digital twin`, `fault diagnosis`, `remaining useful life`, `prognostics and health management`, `manufacturing AI`, `condition monitoring`, `vibration signal`, `signal processing` 등
  - 모두 다단어 표현을 사용해 단일 단어("LLM", "AI" 등)로 인한 과도한 매칭을 방지

- **토픽 카테고리** (11개): `industrial-foundation-models`, `physical-ai`, `manufacturing-ai`, `physics-informed-ml`, `signal-processing`, `fault-diagnosis`, `digital-twin`, `rul-phm`, `battery`, `semiconductor`, `reliability`, `robotics`, `other`

**점수 반영 방식**
- `is_hai_author(authors)`: 멤버 매칭 시 featured_score에 `+5` (floor 보장)
- `hai_keyword_score(title, abstract)`: 키워드 매칭 개수 × 1.5 (최대 +7.5, cap)
- `hai_topic(title, abstract)`: 가장 가까운 11개 토픽 중 하나로 자동 분류 → HAI 페이지 필터에 사용

**코드 근거**
- `backend/app/core/hai_config.py` — `HAI_LAB_MEMBERS`, `HAI_KEYWORDS`, `HAI_TOPICS`, `is_hai_author()`, `hai_keyword_score()`, `hai_topic()`
- `backend/scripts/daily_cron.py` — featured_score 계산 시 위 함수 호출

---

### (2) 연구실 논문 통합

**HAI Lab 자체 출판 논문 수집**
- `hai.snu.ac.kr` 연구실 홈페이지에서 233편의 lab 출판 논문 metadata 수집·저장
- arxiv_id가 없는 lab 논문은 `hai:<slug>` 또는 `openalex:<id>` prefix로 식별

**Abstract 보강 4단계 cascade**
1. OpenAlex API
2. Crossref API
3. Semantic Scholar API
4. (마지막 수단) 출판사 페이지 (저작권 안전성 확인 후)

**별도 표시 위치**
- 홈페이지 "HAI Lab Picks" 섹션
- `/hai` 전용 페이지 (Lab 출판 논문 + HAI 키워드 매칭 arXiv 논문 통합)

**코드 근거**
- `backend/scripts/enrich_lab_v3.py`, `enrich_lab_v4.py`, `enrich_lab_v5_s2.py` — 다단계 abstract 보강
- `backend/scripts/fetch_lab_abstracts_v2.py`, `fetch_lab_abstracts_from_publisher.py` — 외부 abstract 수집
- `backend/app/api/trending.py` — `/api/hai/papers`, `/api/hai/topics`, `/api/hai/info`
- `frontend/src/pages/HaiPapers.jsx` — HAI 전용 페이지 UI

---

### (3) HAI 관련 추천/탐색 기능

**일반 Top 25와의 차이**

| 항목 | Top 25 (Featured) | HAI Lab Picks |
|---|---|---|
| 위치 | 홈 + `/trending` 탭 | 홈 미리보기 + `/hai` 전용 페이지 |
| 선정 기준 | popularity × consensus + HF + HAI 가산점 | HAI 키워드 매칭 + Lab 멤버 저자 |
| 한국어 요약 | 자동 생성 (당일 25편) | arXiv 논문은 자동 생성 / Lab 자체 논문은 abstract 표시 |
| 필터 | 카테고리, 날짜 | 11개 HAI 토픽, Lab/arXiv 출처, 텍스트 검색 |
| 풀 크기 | 매일 25편 | 누적 (시간이 갈수록 누적) |

**탐색 흐름**
1. 홈 → "HAI Lab Picks" 미리보기 6편 → "View All" 클릭
2. `/hai` 진입 → 상단 토픽 칩(Industrial Foundation Models, Physical AI, Signal Processing 등) 선택
3. 출처 필터로 Lab 자체 논문만 / arXiv 관련만 선택 가능
4. 카드 클릭 → arXiv 논문이면 한국어 요약 페이지 / Lab 논문이면 외부 링크

---

### (4) 발표자료용 정리

- **기능명**: HAI Lab 연구 분야 맞춤 큐레이션
- **한 줄 설명**: HAI Lab의 주요 연구 키워드와 기존 연구 논문을 기반으로, 연구실 관심 분야와 관련성이 높은 최신 논문을 우선적으로 확인할 수 있도록 지원합니다
- **발표용 설명 (2–3문장)**:
  HotPaper.ai는 일반적인 인기 논문뿐 아니라 HAI Lab의 연구 분야와 관련된 논문을 함께 선별합니다. 연구실 관심 키워드와 토픽 정보를 활용해 Manufacturing AI, PHM, Signal Processing, Robotics 등 관련 논문을 빠르게 확인할 수 있도록 구성합니다. 이를 통해 연구실 구성원이 최신 AI 기술을 자신의 연구 주제와 연결해 검토하는 데 도움을 줍니다.
- **그림 아이디어**:
  ```
  [HAI Lab 키워드 셋]   [매일 새 논문 풀]
            \              /
             ▼ 매칭 + 토픽 분류
      [HAI 관련 논문 큐레이션]
            │
            ▼
   [/hai 페이지 + Home 미리보기]
  ```

# 경쟁분석 기반 기능 개발 계획

## 1. 우리 현재 기능 정확한 파악

### 완벽하게 구현된 기능 ✅
- **React 프론트엔드**: 모든 페이지 완성 (Home, Search, Paper, Graph, Dashboard, Feedback)
- **FastAPI 백엔드**: 8080 포트에서 정상 실행, 모든 API 엔드포인트 동작
- **PostgreSQL 데이터베이스**: 1,201개 논문 저장, 정규화된 스키마 설계
- **논문 검색**: `/api/search?q=transformer` 완전 동작 (16개 결과)
- **지식 그래프 UI**: D3.js 기반 10,264라인 고품질 컴포넌트
- **반응형 디자인**: 모바일/데스크톱 호환, 다크모드 완전 구현
- **arXiv 데이터 수집**: arxiv_collector.py 동작
- **임베딩 생성**: BAAI/bge-m3 모델 캐시됨

### 부분 구현/개선 필요 기능 🔄
- **추천 시스템**: 목업 데이터만 반환, FAISS 인덱스 구축 필요
- **통계 대시보드**: DB 데이터 + 일부 목업, 모든 집계 쿼리 실제 구현 필요
- **그래프 시각화**: D3.js UI 완성, 논문 간 관계 데이터 생성 필요
- **API 경로**: 하드코딩됨, 환경변수 기반 설정 필요

### 완전히 없는 기능 ❌
- **피드백 시스템**: 백엔드 API 미구현, UI만 완성
- **관리자 기능**: 인증 시스템 없음
- **실시간 업데이트**: WebSocket 또는 SSE 미구현
- **AI 자동 요약**: TL;DR 생성 기능 없음
- **커뮤니티 기능**: 투표, 코멘트, 큐레이션 없음
- **이메일 구독**: 일일 추천 이메일 없음

## 2. 경쟁사별 핵심 기능 분석

### HuggingFace Papers
- **핵심 차별화 포인트**:
  - 커뮤니티 기반 큐레이션 (투표, 코멘트)
  - 일일 이메일 구독 시스템
  - 조직/기관 배지 시스템
- **UI/UX 강점**:
  - 썸네일 기반 시각 표현
  - engagement 메트릭 (좋아요, 댓글 수)
  - 다중 기간별 필터 (Daily/Weekly/Monthly)
- **기술 구현 방식**:
  - Plausible Analytics로 사용자 활동 추적
  - Cloudinary CDN으로 이미지 최적화
  - Stripe 결제 연동 (프리미엄 기능)

### Semantic Scholar
- **핵심 차별화 포인트**:
  - AI 자동 TL;DR 생성 (GPT-3 기반)
  - Semantic Reader (증강 독서 도구)
  - 225M+ 논문 커버리지
- **UI/UX 강점**:
  - 인라인 인용 카드
  - 스키밍 하이라이트
  - 시각적 인용 그래프
- **기술 구현 방식**:
  - AI 기반 숨겨진 연결 발견
  - 자동 요약 생성
  - Research Feeds (관심 분야 알림)

### Connected Papers
- **핵심 차별화 포인트**:
  - 시각적 네트워크 탐색
  - 유사도 기반 클러스터링
  - ~50,000 논문 분석으로 그래프 생성
- **UI/UX 강점**:
  - 인터랙티브 그래프 탐색
  - 최단 유사성 경로 표시
  - 연도별/키워드별 필터링
- **기술 구현 방식**:
  - 공동 인용 및 서지 결합 분석
  - 유사성 기반 노드 배치
  - 가격 모델: Free/$6/$10/month

### Papers With Code (현재 오프라인)
- **핵심 차별화 포인트**:
  - 코드+논문+리더보드 연동
  - <Task, Dataset, Metric> 벤치마킹
  - 18,000+ 논문, 1,500+ 리더보드
- **현재 상태**: 2025년 Meta에 의해 종료, HuggingFace로 리다이렉트
- **대안**: CodeSOTA가 유사 서비스 제공 중

### arxiv-sanity-lite (Andrej Karpathy)
- **핵심 차별화 포인트**:
  - 개인화 SVM 추천 (tfidf 기반)
  - 논문 태깅 시스템
  - 일일 이메일 추천
- **기술 구현 방식**:
  - SVM over tfidf 특성 벡터
  - 사용자별 개인화 모델
  - 경량 아키텍처 설계

### Research Rabbit
- **핵심 차별화 포인트**:
  - 시각적 연구 탐색 (맵 기반)
  - 270만+ 논문 접근
  - Zotero 동기화
- **UI/UX 강점**:
  - 비선형 탐색 인터페이스
  - 내장 시각화 도구
  - 연도별 정렬

## 3. 기능 갭 매트릭스

| 기능 | 우리 | HF | SS | CP | PWC | AS | RR | 우선순위 |
|------|-----|----|----|----|----|----|----|---------|
| 논문 검색 | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | - |
| 지식 그래프 | 🔄 | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | **차별화** |
| AI 자동 요약 | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | **9** |
| 커뮤니티 투표 | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | **7** |
| 이메일 구독 | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | **6** |
| 개인화 추천 | 🔄 | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | **8** |
| 시각적 탐색 | 🔄 | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | **차별화** |
| 벤치마킹 | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | **5** |
| 피드백 시스템 | 🔄 | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | **4** |
| 실시간 업데이트 | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | **3** |

## 4. 도입 추천 기능 TOP 10

### 1. FAISS 벡터 검색 기반 추천 시스템 완성
- **우선순위**: 10/10 (최고)
- **구현 난이도**: 3/5
- **예상 개발기간**: 3일
- **변경할 파일들**:
  - `src/recommender/vector_search.py` (FAISS 인덱스 구축)
  - `src/api/main.py` (추천 API 엔드포인트 실제 구현)
  - `frontend/src/pages/Paper.jsx` (추천 논문 표시 개선)
- **기존 코드 수정/삭제**:
  - 현재 목업 데이터 반환 로직을 실제 벡터 검색으로 교체

### 2. 논문 간 관계 그래프 데이터 생성
- **우선순위**: 9/10
- **구현 난이도**: 4/5
- **예상 개발기간**: 5일
- **변경할 파일들**:
  - `src/utils/graph_builder.py` (새로 생성 - 인용 관계 분석)
  - `src/api/main.py` (그래프 데이터 API 추가)
  - `frontend/src/components/KnowledgeGraph.jsx` (실제 데이터 연결)
- **기존 코드 수정/삭제**:
  - 현재 목업 그래프 데이터를 실제 논문 관계 데이터로 교체

### 3. 실시간 트렌딩 업데이트 시스템
- **우선순위**: 8/10
- **구현 난이도**: 3/5
- **예상 개발기간**: 2일
- **변경할 파일들**:
  - `src/api/main.py` (WebSocket 엔드포인트 추가)
  - `frontend/src/components/HotTopics.jsx` (WebSocket 연결)
  - `src/utils/trending_calculator.py` (새로 생성)
- **기존 코드 수정/삭제**:
  - 정적 트렌딩 데이터를 실시간 업데이트로 교체

### 4. 피드백 시스템 백엔드 구현
- **우선순위**: 7/10
- **구현 난이도**: 2/5
- **예상 개발기간**: 2일
- **변경할 파일들**:
  - `schema.sql` (feedback 테이블 추가)
  - `src/api/main.py` (피드백 API 엔드포인트)
  - `src/database.py` (피드백 관련 쿼리)
- **기존 코드 수정/삭제**:
  - `frontend/src/pages/Feedback.jsx` (API 연결 완성)

### 5. AI 자동 요약 (TL;DR) 생성
- **우선순위**: 9/10
- **구현 난이도**: 4/5
- **예상 개발기간**: 4일
- **변경할 파일들**:
  - `src/summarizer/ai_summarizer.py` (GPT 기반 요약 생성)
  - `src/api/main.py` (요약 API 엔드포인트)
  - `frontend/src/components/PaperCard.jsx` (TL;DR 표시 추가)
  - `schema.sql` (summaries 테이블에 tldr 컬럼 추가)
- **기존 코드 수정/삭제**:
  - 기존 수동 요약을 AI 자동 요약으로 보강

### 6. 이메일 구독 시스템
- **우선순위**: 6/10
- **구현 난이도**: 3/5
- **예상 개발기간**: 3일
- **변경할 파일들**:
  - `src/utils/email_service.py` (새로 생성)
  - `schema.sql` (subscription 테이블 추가)
  - `src/api/main.py` (구독 관리 API)
  - `frontend/src/components/EmailSubscription.jsx` (새로 생성)
- **기존 코드 수정/삭제**:
  - 새 기능 추가, 기존 코드 수정 불필요

### 7. 커뮤니티 투표 시스템
- **우선순위**: 7/10
- **구현 난이도**: 3/5
- **예상 개발기간**: 3일
- **변경할 파일들**:
  - `schema.sql` (votes, comments 테이블 추가)
  - `src/api/main.py` (투표 API 엔드포인트)
  - `frontend/src/components/PaperCard.jsx` (투표 UI 추가)
  - `frontend/src/components/VotingSystem.jsx` (새로 생성)
- **기존 코드 수정/삭제**:
  - PaperCard에 투표 버튼과 카운터 추가

### 8. 개인화 추천 알고리즘 개선
- **우선순위**: 8/10
- **구현 난이도**: 4/5
- **예상 개발기간**: 5일
- **변경할 파일들**:
  - `src/recommender/personalized.py` (새로 생성 - 사용자별 모델)
  - `src/api/main.py` (개인화 추천 API)
  - `schema.sql` (user_preferences 테이블 추가)
- **기존 코드 수정/삭제**:
  - 기본 벡터 검색을 사용자 행동 기반으로 개인화

### 9. 논문 메타데이터 자동 추출 개선
- **우선순위**: 6/10
- **구현 난이도**: 3/5
- **예상 개발기간**: 2일
- **변경할 파일들**:
  - `src/collector/semantic_scholar.py` (API 키 환경변수화, 레이트 리미팅)
  - `src/utils/metadata_extractor.py` (새로 생성)
- **기존 코드 수정/삭제**:
  - 하드코딩된 API 키를 환경변수로 이동
  - 백오프 로직 추가

### 10. 고급 필터링 및 정렬 옵션
- **우선순위**: 5/10
- **구현 난이도**: 2/5
- **예상 개발기간**: 2일
- **변경할 파일들**:
  - `frontend/src/components/SearchBar.jsx` (고급 필터 UI)
  - `src/api/search.py` (추가 필터링 로직)
  - `frontend/src/pages/Search.jsx` (정렬 옵션 추가)
- **기존 코드 수정/삭제**:
  - 기존 검색 인터페이스 확장

## 5. 기존 코드 개선/삭제 계획

### 완전 재구현 필요
- **`packages/` 디렉토리**: `src/`와 중복 기능으로 혼란 야기, 사용하지 않는 모듈 정리 또는 통합 필요

### 대폭 수정 필요
- **`frontend/src/api/client.js:4`**: 하드코딩된 API 경로를 환경변수 기반으로 변경
- **`src/collector/semantic_scholar.py:45-67`**: API 키 하드코딩 및 레이트 리미팅 부족 문제 해결

### 삭제 대상
- **`ui_prototype.html` (17.5K)**: React 앱으로 대체됨
- **`logs/json_failures/` 디렉토리**: 개발 중 생성된 임시 로그들
- **미사용 `__pycache__` 디렉토리들**: .gitignore에 추가하고 삭제

### 보안 수정 (즉시)
- **`frontend/package.json`**: npm audit fix 실행으로 moderate 보안 취약점 2개 수정

## 6. 우리만의 차별화 전략 3가지

### 1. 지식 그래프 + AI 추천의 융합
- **기존 강점**: 고품질 D3.js 그래프 컴포넌트 + FAISS 벡터 검색
- **새 기능**: 그래프 노드를 클릭하면 실시간 유사 논문 추천
- **차별화**: Connected Papers의 시각적 탐색 + Semantic Scholar의 AI 추천

### 2. arXiv-first 실시간 트렌딩 엔진
- **기존 강점**: PostgreSQL 기반 안정적 데이터 저장 + 실제 arXiv 수집
- **새 기능**: 일일/주간/월간 트렌딩 키워드 자동 감지 + 이메일 알림
- **차별화**: HuggingFace의 커뮤니티 기반이 아닌 데이터 기반 트렌딩

### 3. 경량 개인화 + 커뮤니티 피드백 결합
- **기존 강점**: 빠른 FastAPI 백엔드 + 반응형 React UI
- **새 기능**: 개인 태깅 + 커뮤니티 투표를 결합한 하이브리드 추천
- **차별화**: arxiv-sanity의 개인화 + HuggingFace의 커뮤니티 요소

## 7. 개발 로드맵

### 1주차: 핵심 인프라 완성 (TOP 3 기능)
- **Day 1-3**: FAISS 벡터 검색 기반 추천 시스템 완성
- **Day 4-6**: 논문 간 관계 그래프 데이터 생성
- **Day 7**: 실시간 트렌딩 업데이트 시스템

### 2주차: 사용자 경험 개선 (TOP 4-6 기능)
- **Day 8-9**: 피드백 시스템 백엔드 구현
- **Day 10-13**: AI 자동 요약 (TL;DR) 생성
- **Day 14**: 이메일 구독 시스템

### 3주차: 커뮤니티 및 고급 기능 (TOP 7-10 + 차별화)
- **Day 15-17**: 커뮤니티 투표 시스템
- **Day 18-22**: 개인화 추천 알고리즘 개선
- **Day 23-24**: 논문 메타데이터 자동 추출 개선
- **Day 25-26**: 고급 필터링 및 정렬 옵션
- **Day 27-30**: 차별화 기능 통합 및 테스팅

### 즉시 수정 (Day 0)
```bash
# 보안 취약점 수정
cd frontend && npm audit fix --force

# 불필요한 코드 정리
rm ui_prototype.html
rm -rf logs/json_failures/
echo "__pycache__/" >> .gitignore

# API 경로 환경변수화
echo "VITE_API_URL=http://localhost:8080/api" >> frontend/.env
```

*분석 완료일: 2026-03-23*
*분석자: Claude Sonnet 4 (Competitive Intelligence Agent)*

---

## 🎯 경쟁사 분석 요약

### 핵심 경쟁사 현황
1. **Hugging Face Papers** (구 Papers with Code) - 커뮤니티 큐레이션 + GitHub 연동
2. **Semantic Scholar** - 233M+ 논문, AI 검색, TL;DR 자동 생성
3. **Connected Papers** - 시각적 네트워크 탐색, JavaScript SPA
4. **arxiv-sanity-lite** - 개인화 ML 추천, 경량 아키텍처
5. **Research Rabbit** - 시각적 연구 탐색 도구

### 시장 트렌드
- **플랫폼 통합**: Papers with Code → Hugging Face 완전 흡수
- **커뮤니티 중심**: 소셜 검증, 업보트, 큐레이션 중요성 증대
- **JavaScript SPA**: 모든 경쟁사가 React/Vue 기반 프론트엔드 사용
- **AI 기반 검색**: 자연어 이해, 의미론적 매칭 표준화
- **다크 모드**: 필수 기능으로 자리잡음

---

## 🏆 우리의 차별화 포인트

### 기존 강점 (유지해야 할 것)
- ✅ **구조화된 추출**: 엄격한 JSON 스키마 검증으로 데이터 품질 보장
- ✅ **할루시네이션 방지**: 팩트 기반 요약만 제공
- ✅ **vLLM 통합**: 고성능 로컬 LLM 추론
- ✅ **견고한 데이터 모델**: 버전 추적, 중복 제거, PostgreSQL
- ✅ **API 우선 설계**: 프로그래머블 액세스

### 신규 차별화 기회
- 🎯 **실시간 트렌딩 분석**: 자동화된 키워드 트렌드 감지
- 🎯 **실험 결과 정확성**: 모델/데이터셋/메트릭 구조화 추출
- 🎯 **개발자 친화적**: 완전한 API 접근 + CLI 도구

---

## 📊 기능 갭 분석

### 🚫 우리에게 없는 것 (경쟁사 보유)

| 기능 | Hugging Face | Semantic Scholar | Connected Papers | arxiv-sanity |
|------|-------------|-----------------|-----------------|-------------|
| **웹 UI** | ✅ Modern SPA | ✅ Responsive | ✅ Interactive | ✅ Minimal |
| **소셜 기능** | ✅ 투표/큐레이션 | ❌ | ❌ | ❌ |
| **시각화** | ✅ 썸네일 | ✅ TL;DR | ✅ 네트워크 그래프 | ❌ |
| **개인화** | ✅ 북마크 | ✅ 라이브러리 | ❌ | ✅ ML 추천 |
| **다크 모드** | ✅ | ✅ | ✅ | ❌ |
| **모바일 지원** | ✅ | ✅ | ✅ | ❌ |
| **검색 고도화** | ✅ 필터 | ✅ AI 검색 | ❌ | ✅ TF-IDF |

### ✅ 우리만의 강점

| 우리 기능 | 경쟁사 대비 우위 |
|----------|----------------|
| **구조화된 요약** | 정확한 실험 결과 추출 (모델, 데이터셋, 메트릭) |
| **API 우선** | 완전한 프로그래머블 액세스 |
| **vLLM 통합** | 로컬 고성능 LLM, 비용 효율성 |
| **버전 추적** | arXiv 논문 버전별 변화 추적 |
| **트렌딩 엔진** | 자동화된 키워드 트렌드 분석 |

---

## 🚀 단계별 개발 로드맵

### Phase 1: 기본 웹 인터페이스 (우선순위 1)
*목표: 경쟁사 수준의 기본 기능 확보*

#### 1.1 FastAPI 서버 구현 (1주)
```python
# 필요한 엔드포인트
GET /api/v1/papers              # 논문 목록 + 검색/필터
GET /api/v1/papers/{arxiv_id}   # 개별 논문 상세
GET /api/v1/papers/{arxiv_id}/summary  # 구조화된 요약
GET /api/v1/trending/keywords   # 트렌딩 키워드
GET /api/v1/stats/daily        # 일일 통계
```

**구현할 파일:**
- `apps/api/main.py` - FastAPI 앱
- `apps/api/routes/papers.py` - 논문 엔드포인트
- `apps/api/routes/trending.py` - 트렌딩 엔드포인트
- `apps/api/models/response.py` - API 응답 모델

#### 1.2 최소 웹 UI (1주)
```javascript
// React 기반 SPA
components/
  ├── PaperList.jsx          // 논문 목록 (Hugging Face 스타일)
  ├── PaperCard.jsx          // 개별 논문 카드
  ├── SearchFilter.jsx       // 검색/필터 바
  ├── TrendingKeywords.jsx   // 트렌딩 키워드 위젯
  └── StructuredSummary.jsx  // 우리만의 구조화된 요약 표시
```

**주요 기능:**
- 다크 모드 지원 (시스템 선호도 감지)
- 반응형 디자인 (모바일 지원)
- 실시간 검색 (debounced)
- 무한 스크롤

#### 1.3 기본 검색/필터 (3일)
- 키워드 검색 (제목, 초록)
- 날짜 필터 (from/to)
- 카테고리 필터
- 정렬 옵션 (최신순, 관련도순)

**기대 결과:** Semantic Scholar 수준의 기본 웹 UI 확보

---

### Phase 2: 차별화 기능 개발 (우선순위 2)
*목표: 우리만의 고유 가치 제공*

#### 2.1 고도화된 구조화 요약 표시 (1주)
```javascript
// 우리만의 차별화된 요약 UI
<StructuredSummary>
  <ModelInfo backbone="GPT-4" parameters="175B" />
  <DatasetList datasets={[{name: "MMLU", task: "reasoning"}]} />
  <MetricsTable metrics={[{name: "Accuracy", value: "67.3%", setting: "0-shot"}]} />
  <ComputeInfo gpus="8x A100" training_time="72h" />
</StructuredSummary>
```

**특징:**
- 경쟁사에 없는 구조화된 정보 표시
- 실험 재현성 정보 강조
- 데이터셋/모델 상호 참조 링크

#### 2.2 실시간 트렌딩 키워드 엔진 (1주)
```python
# 트렌딩 스코어 계산
def compute_trending_score(keyword: str) -> float:
    recent_freq = get_keyword_frequency(keyword, days=7)
    baseline_freq = get_keyword_frequency(keyword, days=30, offset=7)
    return (recent_freq + 1) / (baseline_freq + 1)

# 자동화된 일일 실행
schedule.every().day.at("06:00").do(compute_trending_keywords)
```

**기능:**
- 일일 자동 트렌딩 키워드 업데이트
- 새로운 키워드 감지 ("NEW" 배지)
- 트렌딩 히스토리 추적

#### 2.3 임베딩 기반 추천 고도화 (1주)
- 논문 간 유사도 계산
- "당신이 좋아할 만한 논문" 추천
- 아이디어 텍스트 → 관련 논문 검색

**기대 결과:** 경쟁사 대비 구조화된 정보에서 압도적 우위 확보

---

### Phase 3: 고급 시각화 & UX (우선순위 3)
*목표: Connected Papers 수준의 시각적 탐색*

#### 3.1 논문 네트워크 시각화 (2주)
```javascript
// D3.js 기반 인터랙티브 그래프
<PaperNetworkGraph>
  <Node paper={paper} size={citation_count} />
  <Edge similarity={cosine_similarity} />
  <Zoom enabled={true} />
  <Filter by="category,year,similarity" />
</PaperNetworkGraph>
```

**기능:**
- 인용 관계 네트워크
- 유사도 기반 클러스터링
- 드래그앤드롭 탐색
- 줌/팬 지원

#### 3.2 대시보드 & 분석 (1주)
- 일일/주간/월간 논문 트렌드
- 연구 영역별 통계
- 키워드 트렌드 시각화
- 개인화된 추천 대시보드

**기대 결과:** Connected Papers 수준의 시각적 탐색 + 우리만의 구조화된 분석

---

### Phase 4: 커뮤니티 & 협업 (우선순위 4)
*목표: Hugging Face Papers 수준의 소셜 기능*

#### 4.1 사용자 시스템 (2주)
- 사용자 회원가입/로그인
- 개인 라이브러리 (북마크)
- 읽기 기록 추적
- 개인화된 추천

#### 4.2 소셜 기능 (1주)
- 논문 평점/리뷰 시스템
- 컬렉션 생성/공유
- 댓글/토론 기능

**기대 결과:** 소셜 검증 + 구조화된 정보의 조합

---

## 🔧 기술적 구현 세부사항

### 프론트엔드 아키텍처
```javascript
// Next.js 기반 모던 스택
tech_stack = {
  framework: "Next.js 14",
  ui: "TailwindCSS + shadcn/ui",
  state: "Zustand",
  api: "TanStack Query",
  visualization: "D3.js + Recharts",
  theme: "next-themes (다크 모드)"
}
```

### 백엔드 확장
```python
# FastAPI 확장 구조
apps/api/
├── main.py              # FastAPI 앱 진입점
├── dependencies/        # 의존성 주입
├── middleware/          # 인증, CORS, 로깅
├── routes/
│   ├── papers.py       # 논문 CRUD
│   ├── search.py       # 검색/필터
│   ├── trending.py     # 트렌딩 분석
│   ├── recommend.py    # 추천 시스템
│   └── users.py        # 사용자 관리
└── models/
    ├── request.py      # 요청 모델
    └── response.py     # 응답 모델
```

### 성능 최적화
```python
# 캐싱 전략
- Redis: 검색 결과, 트렌딩 키워드 (TTL: 1시간)
- CDN: 정적 자산, 논문 썸네일
- DB 인덱스: 검색 성능 최적화
- 비동기 처리: 임베딩 생성, 요약 작업

# 스케일링 준비
- 컨테이너화: Docker + docker-compose
- 로드 밸런싱: 다중 vLLM 인스턴스
- 모니터링: Prometheus + Grafana
```

---

## 🗑️ 기존 코드 리팩토링 계획

### 유지할 코드 (✅ 품질 우수)
- `packages/core/storage/` - DB 레이어 잘 설계됨
- `packages/core/summarizers/` - vLLM 통합 완성도 높음
- `packages/core/connectors/arxiv.py` - 속도 제한, 재시도 로직 견고
- `scripts/run_daily_pipeline.py` - 오케스트레이션 잘 구현됨

### 개선 필요한 코드 (🔄)
```python
# 1. API 레이어 추가 필요
packages/core/api/          # 새로 생성
├── endpoints.py
├── models.py
└── dependencies.py

# 2. 프론트엔드 디렉토리 구조
apps/web/                  # 새로 생성
├── components/
├── pages/
├── hooks/
└── utils/

# 3. 설정 중앙화
config/
├── database.py
├── llm.py
└── api.py
```

### 삭제할 코드 (❌ 중복/불필요)
- `packages/core/trending/extract.py` - 사용되지 않는 더미 함수들
- 일부 테스트용 스크립트들

---

## 📈 성공 지표 (KPI)

### Phase 1 목표
- [ ] FastAPI 서버 구동 (기본 엔드포인트 4개)
- [ ] 웹 UI 접속 가능 (다크 모드 지원)
- [ ] 논문 검색/필터 기능 동작
- [ ] 응답 시간 < 200ms (논문 목록 API)

### Phase 2 목표
- [ ] 구조화된 요약 표시 (모델, 데이터셋, 메트릭)
- [ ] 트렌딩 키워드 자동 업데이트
- [ ] 임베딩 기반 추천 정확도 > 0.7 (코사인 유사도)

### Phase 3 목표
- [ ] 네트워크 시각화 인터랙티브 동작
- [ ] 대시보드 로딩 시간 < 1초
- [ ] 모바일 반응형 100% 지원

### 최종 목표 (3개월 후)
- [ ] 일일 활성 사용자 100명+
- [ ] 논문 추천 클릭률 > 15%
- [ ] API 호출량 1,000회/일+
- [ ] 사용자 만족도 4.5/5.0+

---

## ⚠️ 리스크 & 대응책

### 기술적 리스크
1. **vLLM 서버 안정성** → 헬스체크 + 자동 재시작
2. **대용량 임베딩 메모리 부족** → 배치 처리 + 디스크 캐싱
3. **arXiv API 속도 제한** → 지수적 백오프 + 큐잉

### 제품 리스크
1. **경쟁사 대비 차별화 부족** → 구조화된 요약에 집중
2. **사용자 획득 어려움** → 개발자 커뮤니티 타겟팅
3. **유지비용 증가** → 오픈소스화로 커뮤니티 기여 유도

---

## 🎬 마무리

### 핵심 전략
1. **빠른 MVP**: 3개월 내 Semantic Scholar 수준 기본 기능 확보
2. **차별화 집중**: 구조화된 정보 추출에서 압도적 우위
3. **커뮤니티 우선**: 오픈소스로 개발자 생태계 구축
4. **확장성 고려**: API 우선 설계로 다양한 통합 가능

### 예상 완료 일정
- **Phase 1**: 4주 (2026-04-20)
- **Phase 2**: 6주 (2026-06-01)
- **Phase 3**: 8주 (2026-07-27)
- **Phase 4**: 10주 (2026-10-05)

**우리의 목표는 단순한 논문 검색 도구가 아닌, 연구자들의 실험 재현성을 높이는 구조화된 지식 플랫폼이 되는 것입니다.**

---
*분석 완료. touch /tmp/phase2_done 실행 준비*
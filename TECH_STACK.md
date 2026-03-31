# Paper Agent - 기술 스택 및 기능 정리

*최종 업데이트: 2026-03-23*

---

## 🏗️ 기술 스택

### 프론트엔드
- **React 18** + **Vite** - 모던 프론트엔드 개발 환경
- **React Router** - SPA 라우팅
- **Tailwind CSS** - 유틸리티 기반 CSS 프레임워크
- **D3.js** - 지식 그래프 시각화
- **LocalStorage** - 클라이언트 사이드 데이터 저장

### 백엔드
- **FastAPI** (Python) - REST API 서버
- **SQLite** - 경량 데이터베이스 (1,219개 논문 저장)
- **Pydantic** - 데이터 검증 및 직렬화

### 외부 API 연동
- **HuggingFace Papers API** - 트렌딩 논문 데이터
- **GitHub API** - 저장소 메트릭 (별점 수)
- **arXiv API** - 논문 메타데이터

---

## 🚀 핵심 기능

### 1. 논문 검색 및 추천
- 실시간 논문 검색 (debounced)
- 유사도 기반 추천
- 카테고리별 필터링
- Hot Topics 자동 감지

### 2. 지식 그래프 시각화 🕸️
- **D3.js 기반 인터랙티브 그래프**
- 50개 노드 표시 (홈페이지)
- 실시간 검색 및 하이라이팅
- 논문 간 연결 관계 시각화
- 클릭으로 논문 상세 페이지 이동

### 3. 트렌딩 시스템
- **HuggingFace 인기 논문 연동**
- GitHub Stars + HuggingFace Upvotes 결합 점수
- 시간 가중치 적용한 트렌딩 알고리즘
- 실시간 트렌딩 메트릭 표시

### 4. 개인 컬렉션 관리
- **LocalStorage 기반** 완전 익명 시스템
- 3가지 컬렉션: 저장된 논문, 읽을 예정, 즐겨찾기
- 논문 이동/삭제 기능
- 검색 및 필터링
- 백업/복원 기능 (JSON Export)

### 5. 피드백 시스템
- **11개 구체적 카테고리**로 세분화된 피드백
- 완전 익명 피드백 (이름/이메일 제거)
- 관리자 페이지 (`/admin/feedback`)
- 카테고리별 필터링 및 통계

---

## 📊 데이터 현황

- **총 논문 수**: 1,219개
- **카테고리 수**: 76개
- **그래프 엣지**: 다수의 논문 간 연결
- **외부 데이터**: HuggingFace 트렌딩 30개 논문

---

## 🎨 사용자 경험 (UX)

### 성능 최적화
- **HTTP 캐싱 헤더** 적용
- **Debounced 검색** (300ms 지연)
- **Progressive Loading** (중요 데이터 우선)
- **Skeleton Loading** UI
- **Hot Module Replacement** (HMR) 개발 환경

### 반응형 디자인
- 모바일 친화적 네비게이션 (햄버거 메뉴)
- 그리드 레이아웃 (1열 → 2열 → 3열)
- 다크모드 지원
- 터치 최적화

### 접근성
- 키보드 네비게이션 지원
- ARIA 라벨 적용
- 고대비 색상 (다크모드)
- 스크린 리더 호환

---

## 🌐 배포 및 인프라

### 개발 환경
- **Vite Dev Server** (포트 5173)
- **FastAPI Uvicorn** (포트 8000)
- **Hot Reload** 개발 환경

### 외부 접근
- **Cloudflare Tunnel** 활용
- HTTPS 보안 연결
- 실시간 외부 테스트 가능

---

## 🔧 주요 컴포넌트

### 프론트엔드 컴포넌트
```
src/
├── components/
│   ├── Navbar.jsx          # 네비게이션 (모바일 반응형)
│   ├── PaperCard.jsx       # 논문 카드 (북마크 기능)
│   ├── KnowledgeGraph.jsx  # 메인 그래프 (실시간 검색)
│   ├── MiniGraph.jsx       # 홈페이지 미리보기 그래프
│   ├── SearchBar.jsx       # 검색 바
│   └── HotTopics.jsx       # 인기 주제
├── pages/
│   ├── Home.jsx            # 홈페이지
│   ├── Search.jsx          # 검색 페이지
│   ├── Collections.jsx     # 컬렉션 관리
│   ├── Feedback.jsx        # 피드백 폼
│   ├── AdminFeedback.jsx   # 관리자 피드백 조회
│   └── Trending.jsx        # 트렌딩 페이지
└── utils/
    ├── collections.js      # LocalStorage 관리
    └── categories.js       # 카테고리 설정
```

### API 엔드포인트
```
/api/
├── papers/                 # 논문 CRUD
├── search/                 # 검색
├── recommendations/        # 추천
├── trending-papers/        # HF 트렌딩 데이터
├── github-repos/          # GitHub 메트릭
├── feedback/              # 피드백 시스템
└── stats/                 # 통계 정보
```

---

## 🎯 핵심 차별화 요소

### vs. HuggingFace Papers
- **지식 그래프 시각화** - 논문 간 연결 관계 직관적 파악
- **개인 컬렉션** - 사용자 맞춤 논문 관리

### vs. Semantic Scholar
- **실시간 트렌딩** - GitHub + HuggingFace 메트릭 결합
- **인터랙티브 그래프** - 클릭 가능한 논문 네트워크

### vs. Connected Papers
- **통합 플랫폼** - 검색/추천/관리 올인원
- **실시간 데이터** - 최신 트렌딩 반영

### vs. Papers With Code
- **시각적 탐색** - 그래프 기반 논문 발견
- **익명 컬렉션** - 개인정보 없는 논문 관리

---

## 🔜 향후 개선 계획

### Phase 2
- [ ] PDF 텍스트 추출 및 딥 서머리
- [ ] 임베딩 기반 유사도 검색
- [ ] 아이디어 → 관련 논문 추천

### Phase 3
- [ ] 사용자 계정 시스템
- [ ] 소셜 기능 (공유, 댓글)
- [ ] ML 기반 개인화 추천
- [ ] 모바일 앱

---

## 📈 성능 메트릭

- **초기 로딩**: ~2초 (캐싱 적용 후)
- **검색 응답**: ~300ms (debounced)
- **그래프 렌더링**: ~500ms (50 노드)
- **API 응답**: ~100-300ms (캐시 히트)

---

**구축 완료일**: 2026년 3월 23일
**개발자**: Claude Code + User Collaboration
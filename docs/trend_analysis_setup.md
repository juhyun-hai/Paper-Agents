# 실시간 트렌드 분석 시스템 - 설정 가이드

## 📊 Overview

Ralph Phase 3에서 구현된 실시간 트렌드 분석 시스템:

- **Hot Topics, Emerging Tech, Must-Know 분류**
- **키워드 빈도 분석 및 인용 급상승 탐지** 
- **연구 흐름 변화 분석**
- **일일/주간 다이제스트 자동 생성**

## 🚀 Quick Start

### 1. API 엔드포인트 사용

```bash
# 실시간 Hot Topics
curl http://localhost:8080/api/hot-topics-real

# 종합 트렌드 분석
curl http://localhost:8080/api/trend-analysis?analysis_type=full

# 일일 다이제스트
curl http://localhost:8080/api/daily-digest

# 주간 다이제스트  
curl http://localhost:8080/api/weekly-digest

# 연구 인사이트
curl http://localhost:8080/api/research-insights
```

### 2. 다이제스트 생성 스크립트

```bash
# 일일 다이제스트 (JSON + Markdown)
python scripts/generate_daily_digest.py --type daily --markdown

# 주간 다이제스트
python scripts/generate_daily_digest.py --type weekly --markdown

# 둘 다 생성
python scripts/generate_daily_digest.py --type both --markdown
```

## 🔧 Components

### 1. TrendAnalyzer (`src/trend_analyzer.py`)
- 키워드 추출 및 빈도 분석
- Hot/Emerging/Must-Know 분류 로직
- 인용 급상승 탐지
- 연구 흐름 변화 분석

### 2. Trend API (`src/api/trend_api.py`)
- FastAPI 라우터
- 실시간 분석 엔드포인트
- 다이제스트 API

### 3. Digest Generator (`scripts/generate_daily_digest.py`)
- 자동화된 다이제스트 생성
- JSON + Markdown 출력
- 크론 스케줄링 지원

## ⚙️ Configuration

### 분류 기준 조정

`src/trend_analyzer.py`에서 임계값 조정:

```python
class TrendAnalyzer:
    def __init__(self, db_manager):
        # 분류 기준 임계값 설정
        self.hot_threshold = 3.0      # Hot Topics: 급상승 + 높은 활동량
        self.emerging_threshold = 2.0  # Emerging: 새로운 등장
        self.must_know_threshold = 1.5 # Must-Know: 꾸준한 중요도
```

### 키워드 필터링

불용어 리스트 수정:

```python
self.stopwords = {
    'learning', 'neural', 'network', 'model', 'method', 
    # 추가 불용어 설정
}
```

## 🔄 Automation

### 1. 일일 다이제스트 자동화 (cron)

```bash
# 매일 오전 9시에 실행
0 9 * * * cd /path/to/paper-agent && python scripts/generate_daily_digest.py --type daily --markdown --quiet

# 매주 월요일 오전 10시에 주간 다이제스트
0 10 * * 1 cd /path/to/paper-agent && python scripts/generate_daily_digest.py --type weekly --markdown --quiet
```

### 2. 실시간 Hot Topics 수집

기존 `daily_collect.py`와 함께 실행되어 HuggingFace, GitHub Trending 등에서 외부 Hot Topics 수집.

### 3. 임계값 모니터링

데이터가 증가하면 분류 임계값을 조정하여 적절한 수의 Hot/Emerging/Must-Know 토픽이 생성되도록 함.

## 📈 Analysis Methodology

### 트렌드 스코어 계산

```
trend_score = (recent_freq + 1) / (baseline_freq + 1)
```

- **recent_freq**: 최근 7일간 논문 수
- **baseline_freq**: 이전 30일간 논문 수
- **+1 스무딩**: 제로 분모 방지

### 분류 로직

1. **Hot Topics**: 
   - 트렌드 스코어 ≥ 3.0
   - 최근 논문 ≥ 5편
   - 인용 속도 > 0.5

2. **Emerging Tech**:
   - 트렌드 스코어 ≥ 2.0  
   - 최근 논문 ≥ 3편

3. **Must-Know**:
   - 트렌드 스코어 ≥ 1.5
   - 평균 인용 ≥ 10회

## 🎯 Usage Examples

### Frontend Integration

기존 `app.py`의 `/api/hot-topics` 엔드포인트가 실시간 분석으로 업그레이드됨:

```javascript
// React frontend에서 사용
const response = await fetch('/api/hot-topics');
const { topics } = await response.json();

topics.forEach(topic => {
  console.log(`${topic.topic}: score ${topic.score}, trend ${topic.trend}`);
});
```

### 다이제스트 파일 확인

```bash
ls -la data/digests/
# daily_digest_2026-03-31.json
# daily_digest_2026-03-31.md
# weekly_digest_2026-03-31.json
# weekly_digest_2026-03-31.md
```

## 📊 Performance

현재 데이터셋 (1,204 papers) 기준:
- 키워드 분석: ~1초
- 일일 다이제스트 생성: ~2초 
- 메모리 사용량: 최소 (~50MB)

## 🔍 Monitoring

### 로그 확인

```bash
tail -f logs/app.log | grep -i trend
```

### 성능 모니터링

```python
from src.trend_analyzer import TrendAnalyzer
from src.database.db_manager import PaperDBManager

db = PaperDBManager()
analyzer = TrendAnalyzer(db)

# 키워드 통계
trends = analyzer.get_keyword_frequencies()
print(f"분석된 키워드: {len(trends)}")
print(f"분류별: Hot={len([t for t in trends.values() if t.classification=='hot'])}")
```

## 🎉 Next Steps

1. **데이터 증가 대응**: 더 많은 최신 논문이 수집되면 트렌드 분류가 더 정확해짐
2. **임계값 자동 조정**: 데이터 분포에 따른 동적 임계값 설정
3. **외부 소스 확장**: Arxiv Sanity, OpenReview 등 추가 소스 연동
4. **시각화 강화**: 트렌드 그래프, 키워드 클라우드 등

---

✅ **Ralph Phase 3: 실시간 트렌드 분석 시스템 강화 완료**
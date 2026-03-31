"""실시간 트렌드 분석 API 엔드포인트 - FastAPI"""

from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query

from src.database.db_manager import PaperDBManager
from src.trend_analyzer import TrendAnalyzer
from src.utils.logger import get_logger

logger = get_logger(__name__)

# FastAPI Router 생성
trend_router = APIRouter()

# 전역 인스턴스 (앱 시작시 한번 초기화)
db_manager = None
trend_analyzer = None


def init_trend_api(db_path: str = "data/paper_db.sqlite"):
    """트렌드 API 초기화"""
    global db_manager, trend_analyzer
    db_manager = PaperDBManager(db_path)
    trend_analyzer = TrendAnalyzer(db_manager)
    logger.info("Trend API initialized")


@trend_router.get("/api/hot-topics-real")
async def get_hot_topics_real():
    """실시간 Hot Topics 분석"""
    try:
        if trend_analyzer is None:
            init_trend_api()

        # 트렌드 메트릭 분석
        trend_metrics = trend_analyzer.get_keyword_frequencies()

        # Hot Topics 분류
        hot_topics = [
            tm for tm in trend_metrics.values()
            if tm.classification == 'hot'
        ]

        # 트렌드 스코어 기준 정렬
        hot_topics.sort(key=lambda x: x.trend_score, reverse=True)

        # API 응답 형식으로 변환
        topics = []
        for i, tm in enumerate(hot_topics[:6]):  # 상위 6개
            # 트렌드 방향 결정
            if tm.trend_score >= 3.0:
                trend_direction = "up"
            elif tm.trend_score >= 1.5:
                trend_direction = "stable"
            else:
                trend_direction = "down"

            topics.append({
                "topic": tm.keyword.title(),
                "score": round(tm.trend_score, 1),
                "papers": tm.paper_count_7d,
                "trend": trend_direction,
                "citations": round(tm.avg_citations, 1),
                "classification": "hot",
                "velocity": round(tm.citation_velocity, 2)
            })

        # 외부 Hot Topics도 포함 (HuggingFace 등)
        today = datetime.now().strftime("%Y-%m-%d")
        external_topics = db_manager.get_hot_topics(today)

        for ext_topic in external_topics[:3]:  # 상위 3개만
            topics.append({
                "topic": ext_topic.get("tech_name", "").title(),
                "score": 8.0 + (ext_topic.get("upvotes", 0) * 0.1),  # 가중치 적용
                "papers": 1,
                "trend": "up",
                "citations": 0,
                "classification": "external",
                "source": ext_topic.get("source", ""),
                "url": ext_topic.get("paper_url", "") or ext_topic.get("github_url", "")
            })

        # 중복 제거 및 최종 정렬
        seen_topics = set()
        unique_topics = []
        for topic in topics:
            topic_key = topic["topic"].lower()
            if topic_key not in seen_topics:
                seen_topics.add(topic_key)
                unique_topics.append(topic)

        unique_topics.sort(key=lambda x: x["score"], reverse=True)

        return {
            "topics": unique_topics[:6],
            "generated_at": datetime.now().isoformat(),
            "source": "real-time analysis"
        }

    except Exception as e:
        logger.error(f"Hot topics analysis failed: {e}")
        # 에러시 폴백 응답
        raise HTTPException(status_code=500, detail={
            "topics": [
                {"topic": "Analysis Error", "score": 0.0, "papers": 0, "trend": "stable"}
            ],
            "error": str(e)
        })


@trend_router.get("/api/trend-analysis")
async def get_trend_analysis(analysis_type: str = Query('full', description="Analysis type: full, keywords, citations, flow")):
    """종합 트렌드 분석"""
    try:
        if trend_analyzer is None:
            init_trend_api()

        result = {}

        if analysis_type in ['full', 'keywords']:
            # 키워드 트렌드 분석
            trend_metrics = trend_analyzer.get_keyword_frequencies()

            # 분류별 정리
            classifications = {
                'hot': [],
                'emerging': [],
                'must_know': [],
                'normal': []
            }

            for tm in trend_metrics.values():
                classifications[tm.classification].append({
                    'keyword': tm.keyword,
                    'trend_score': round(tm.trend_score, 2),
                    'recent_papers': tm.paper_count_7d,
                    'total_papers': tm.paper_count_30d,
                    'avg_citations': round(tm.avg_citations, 1),
                    'citation_velocity': round(tm.citation_velocity, 2)
                })

            # 각 분류별 정렬
            for category in classifications:
                if category == 'must_know':
                    classifications[category].sort(key=lambda x: x['avg_citations'], reverse=True)
                else:
                    classifications[category].sort(key=lambda x: x['trend_score'], reverse=True)

            result['keyword_trends'] = {
                'hot_topics': classifications['hot'][:10],
                'emerging_tech': classifications['emerging'][:10],
                'must_know': classifications['must_know'][:10],
                'summary': {
                    'total_keywords': len(trend_metrics),
                    'hot_count': len(classifications['hot']),
                    'emerging_count': len(classifications['emerging']),
                    'must_know_count': len(classifications['must_know'])
                }
            }

        if analysis_type in ['full', 'citations']:
            # 인용 급상승 분석
            citation_surges = trend_analyzer.detect_citation_surges()
            result['citation_analysis'] = {
                'surge_papers': citation_surges[:10],
                'surge_count': len(citation_surges)
            }

        if analysis_type in ['full', 'flow']:
            # 연구 흐름 변화 분석
            flow_changes = trend_analyzer.analyze_research_flow_changes()
            result['research_flow'] = flow_changes

        result.update({
            'analysis_type': analysis_type,
            'generated_at': datetime.now().isoformat(),
            'data_freshness': 'real-time'
        })

        return result

    except Exception as e:
        logger.error(f"Trend analysis failed: {e}")
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "트렌드 분석 중 오류가 발생했습니다"
        })


@trend_router.get("/api/daily-digest")
async def get_daily_digest(date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format")):
    """일일 다이제스트 조회"""
    try:
        if trend_analyzer is None:
            init_trend_api()

        # 일일 다이제스트 생성
        digest = trend_analyzer.generate_daily_digest(date)

        return digest

    except Exception as e:
        logger.error(f"Daily digest generation failed: {e}")
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "일일 다이제스트 생성 중 오류가 발생했습니다"
        })


@trend_router.get("/api/weekly-digest")
async def get_weekly_digest():
    """주간 다이제스트 조회"""
    try:
        if trend_analyzer is None:
            init_trend_api()

        # 주간 다이제스트 생성
        digest = trend_analyzer.generate_weekly_digest()

        return digest

    except Exception as e:
        logger.error(f"Weekly digest generation failed: {e}")
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "주간 다이제스트 생성 중 오류가 발생했습니다"
        })


@trend_router.get("/api/research-insights")
async def get_research_insights():
    """연구 인사이트 및 추천"""
    try:
        if trend_analyzer is None:
            init_trend_api()

        # 종합 분석 실행
        trend_metrics = trend_analyzer.get_keyword_frequencies()
        flow_changes = trend_analyzer.analyze_research_flow_changes()

        # 인사이트 생성
        insights = {
            'trending_directions': [],
            'emerging_opportunities': [],
            'research_gaps': [],
            'collaboration_hints': []
        }

        # 트렌딩 방향 분석
        hot_keywords = [tm for tm in trend_metrics.values() if tm.classification == 'hot']
        if hot_keywords:
            top_hot = sorted(hot_keywords, key=lambda x: x.trend_score, reverse=True)[:3]
            insights['trending_directions'] = [
                f"'{kw.keyword}' 분야가 급성장 중 (트렌드 점수: {kw.trend_score:.1f})"
                for kw in top_hot
            ]

        # 새로운 기회 분석
        emerging_keywords = [tm for tm in trend_metrics.values() if tm.classification == 'emerging']
        if emerging_keywords:
            top_emerging = sorted(emerging_keywords, key=lambda x: x.trend_score, reverse=True)[:3]
            insights['emerging_opportunities'] = [
                f"'{kw.keyword}' 분야에서 새로운 연구 기회 (최근 {kw.paper_count_7d}편의 논문)"
                for kw in top_emerging
            ]

        # 연구 공백 분석 (상대적으로 논문수는 많지만 인용이 적은 분야)
        potential_gaps = [
            tm for tm in trend_metrics.values()
            if tm.paper_count_7d >= 3 and tm.avg_citations < 5
        ]
        if potential_gaps:
            sorted_gaps = sorted(potential_gaps, key=lambda x: x.paper_count_7d, reverse=True)[:2]
            insights['research_gaps'] = [
                f"'{kw.keyword}' 분야는 활발하지만 영향력 개선 필요 (논문 {kw.paper_count_7d}편, 평균 인용 {kw.avg_citations:.1f}회)"
                for kw in sorted_gaps
            ]

        # 카테고리 변화에서 협업 힌트 추출
        cat_changes = flow_changes.get('category_changes', {})
        increasing_cats = [cat for cat, data in cat_changes.items()
                          if data['trend'] == 'increasing']
        if len(increasing_cats) >= 2:
            insights['collaboration_hints'] = [
                f"{increasing_cats[0]}와 {increasing_cats[1]} 분야 간 융합 연구 기회"
            ]

        return {
            'insights': insights,
            'generated_at': datetime.now().isoformat(),
            'confidence': 'medium',  # 데이터 양에 따라 조정 가능
            'recommendation': '실시간 데이터 기반 연구 방향 제안'
        }

    except Exception as e:
        logger.error(f"Research insights generation failed: {e}")
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "연구 인사이트 생성 중 오류가 발생했습니다"
        })
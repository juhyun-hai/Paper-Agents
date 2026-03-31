"""실시간 트렌드 분석 시스템 - Real-time Trend Analysis System

Hot Topics, Emerging Tech, Must-Know 분류 시스템
키워드 빈도 분석, 인용 급상승 탐지, 연구 흐름 변화 분석
"""

import re
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass

from src.database.db_manager import PaperDBManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TrendMetrics:
    """트렌드 메트릭 클래스"""
    keyword: str
    recent_freq: int
    baseline_freq: int
    trend_score: float
    classification: str  # 'hot', 'emerging', 'must_know'
    paper_count_7d: int
    paper_count_30d: int
    avg_citations: float
    citation_velocity: float


class TrendAnalyzer:
    """실시간 트렌드 분석 엔진"""

    def __init__(self, db_manager: PaperDBManager):
        self.db = db_manager

        # 분류 기준 임계값 설정
        self.hot_threshold = 3.0      # 최근 활동 급증
        self.emerging_threshold = 2.0  # 새로운 기술 등장
        self.must_know_threshold = 1.5 # 꾸준한 중요도

        # 제외할 일반적인 단어들
        self.stopwords = {
            'learning', 'neural', 'network', 'model', 'method', 'approach',
            'paper', 'study', 'research', 'analysis', 'performance', 'results',
            'using', 'based', 'framework', 'system', 'algorithm', 'technique',
            'deep', 'machine', 'artificial', 'intelligence', 'data', 'training'
        }

    def extract_keywords_from_text(self, text: str) -> List[str]:
        """텍스트에서 의미있는 키워드 추출"""
        if not text:
            return []

        # 텍스트 전처리 및 키워드 추출
        text = text.lower()
        # 특수 문자 제거하되 하이픈은 유지 (multi-modal 등)
        text = re.sub(r'[^\w\s\-]', ' ', text)

        # 1-3 단어 조합 추출
        words = text.split()
        keywords = []

        # 단일 단어 (3글자 이상, stopword 제외)
        for word in words:
            if (len(word) >= 3 and
                word not in self.stopwords and
                not word.isdigit()):
                keywords.append(word)

        # 2단어 조합 (특정 패턴만)
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            if (len(phrase) >= 6 and
                any(w not in self.stopwords for w in [words[i], words[i+1]])):
                keywords.append(phrase)

        # 3단어 조합 (매우 선별적)
        for i in range(len(words) - 2):
            if words[i+1] in ['language', 'vision', 'learning']:  # 중간 단어가 특정 패턴
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                keywords.append(phrase)

        return keywords

    def get_keyword_frequencies(self, days_recent: int = 7, days_baseline: int = 30) -> Dict[str, TrendMetrics]:
        """키워드 빈도 분석 및 트렌드 계산"""

        # 날짜 범위 계산
        now = datetime.now()
        recent_start = (now - timedelta(days=days_recent)).strftime("%Y-%m-%d")
        baseline_start = (now - timedelta(days=days_baseline)).strftime("%Y-%m-%d")

        # 최근 논문들 가져오기
        recent_papers = self.db.get_papers_by_date_range(recent_start, now.strftime("%Y-%m-%d"))
        baseline_papers = self.db.get_papers_by_date_range(baseline_start, recent_start)

        logger.info(f"Analyzing {len(recent_papers)} recent papers, {len(baseline_papers)} baseline papers")

        # 키워드 추출 및 카운팅
        recent_keywords = Counter()
        baseline_keywords = Counter()

        # 논문별 인용수와 키워드 매핑
        keyword_citations = defaultdict(list)

        for paper in recent_papers:
            keywords = self.extract_keywords_from_text(
                f"{paper['title']} {paper['abstract']}"
            )
            citations = paper.get('citation_count', 0)

            for kw in keywords:
                recent_keywords[kw] += 1
                keyword_citations[kw].append(citations)

        for paper in baseline_papers:
            keywords = self.extract_keywords_from_text(
                f"{paper['title']} {paper['abstract']}"
            )
            for kw in keywords:
                baseline_keywords[kw] += 1

        # 트렌드 메트릭 계산
        trend_metrics = {}

        for keyword in recent_keywords.keys():
            if recent_keywords[keyword] < 2:  # 최소 2번 이상 언급된 키워드만
                continue

            recent_freq = recent_keywords[keyword]
            baseline_freq = baseline_keywords.get(keyword, 0)

            # 트렌드 스코어 계산 (스무딩 적용)
            trend_score = (recent_freq + 1) / (baseline_freq + 1)

            # 평균 인용수와 인용 속도 계산
            citations = keyword_citations[keyword]
            avg_citations = sum(citations) / len(citations) if citations else 0
            citation_velocity = avg_citations / days_recent  # 일일 평균 인용 속도

            # 분류 결정
            classification = self._classify_trend(
                trend_score, recent_freq, avg_citations, citation_velocity
            )

            trend_metrics[keyword] = TrendMetrics(
                keyword=keyword,
                recent_freq=recent_freq,
                baseline_freq=baseline_freq,
                trend_score=trend_score,
                classification=classification,
                paper_count_7d=recent_freq,
                paper_count_30d=recent_freq + baseline_freq,
                avg_citations=avg_citations,
                citation_velocity=citation_velocity
            )

        return trend_metrics

    def _classify_trend(self, trend_score: float, frequency: int,
                       avg_citations: float, citation_velocity: float) -> str:
        """트렌드 분류 로직"""

        # Hot Topics: 급격한 상승 + 높은 활동량
        if (trend_score >= self.hot_threshold and
            frequency >= 5 and
            citation_velocity > 0.5):
            return 'hot'

        # Emerging Tech: 새로운 등장 + 잠재력
        if (trend_score >= self.emerging_threshold and
            frequency >= 3):
            return 'emerging'

        # Must-Know: 꾸준한 중요도 + 높은 인용
        if (trend_score >= self.must_know_threshold and
            avg_citations >= 10):
            return 'must_know'

        return 'normal'

    def detect_citation_surges(self, threshold_multiplier: float = 2.0) -> List[Dict[str, Any]]:
        """인용 급상승 논문 탐지"""

        # 최근 30일간 인용수가 급증한 논문 찾기
        with self.db._get_conn() as conn:
            rows = conn.execute("""
                SELECT arxiv_id, title, citation_count, date
                FROM papers
                WHERE date >= date('now', '-30 days')
                AND citation_count > 0
                ORDER BY citation_count DESC
                LIMIT 20
            """).fetchall()

        surge_papers = []
        for row in rows:
            paper = dict(row)
            # 단순화된 급상승 기준: 최근 논문 중 인용수 상위 20개
            surge_papers.append({
                'arxiv_id': paper['arxiv_id'],
                'title': paper['title'],
                'citation_count': paper['citation_count'],
                'date': paper['date'],
                'surge_ratio': paper['citation_count'] / 1.0,  # 향후 더 정교한 계산 가능
            })

        return surge_papers

    def analyze_research_flow_changes(self) -> Dict[str, Any]:
        """연구 흐름 변화 분석"""

        # 카테고리별 논문 증감 분석
        with self.db._get_conn() as conn:
            # 최근 7일 vs 이전 7일 카테고리 분포 비교
            recent_cats = conn.execute("""
                SELECT categories, COUNT(*) as count
                FROM papers
                WHERE date >= date('now', '-7 days')
                GROUP BY categories
            """).fetchall()

            prev_cats = conn.execute("""
                SELECT categories, COUNT(*) as count
                FROM papers
                WHERE date >= date('now', '-14 days') AND date < date('now', '-7 days')
                GROUP BY categories
            """).fetchall()

        # 카테고리 변화율 계산
        recent_dist = {row[0]: row[1] for row in recent_cats}
        prev_dist = {row[0]: row[1] for row in prev_cats}

        category_changes = {}
        for cat in set(recent_dist.keys()) | set(prev_dist.keys()):
            recent_count = recent_dist.get(cat, 0)
            prev_count = prev_dist.get(cat, 0)

            if prev_count > 0:
                change_ratio = (recent_count - prev_count) / prev_count
            else:
                change_ratio = 1.0 if recent_count > 0 else 0.0

            category_changes[cat] = {
                'recent_count': recent_count,
                'prev_count': prev_count,
                'change_ratio': change_ratio,
                'trend': 'increasing' if change_ratio > 0.2 else 'decreasing' if change_ratio < -0.2 else 'stable'
            }

        return {
            'category_changes': category_changes,
            'analysis_date': datetime.now().isoformat(),
            'summary': self._summarize_flow_changes(category_changes)
        }

    def _summarize_flow_changes(self, category_changes: Dict) -> str:
        """연구 흐름 변화 요약"""
        increasing = [cat for cat, data in category_changes.items()
                     if data['trend'] == 'increasing']
        decreasing = [cat for cat, data in category_changes.items()
                     if data['trend'] == 'decreasing']

        summary_parts = []
        if increasing:
            summary_parts.append(f"증가 추세: {', '.join(increasing[:3])}")
        if decreasing:
            summary_parts.append(f"감소 추세: {', '.join(decreasing[:3])}")

        return '; '.join(summary_parts) if summary_parts else "안정적인 연구 분포 유지"

    def generate_daily_digest(self, date: str = None) -> Dict[str, Any]:
        """일일 다이제스트 생성"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # 트렌드 분석 실행
        trend_metrics = self.get_keyword_frequencies()
        citation_surges = self.detect_citation_surges()
        flow_changes = self.analyze_research_flow_changes()

        # Hot Topics 수집
        hot_topics = self.db.get_hot_topics(date)

        # 분류별 상위 키워드 추출
        hot_keywords = [tm for tm in trend_metrics.values() if tm.classification == 'hot']
        emerging_keywords = [tm for tm in trend_metrics.values() if tm.classification == 'emerging']
        must_know_keywords = [tm for tm in trend_metrics.values() if tm.classification == 'must_know']

        # 정렬 (트렌드 스코어 기준)
        hot_keywords.sort(key=lambda x: x.trend_score, reverse=True)
        emerging_keywords.sort(key=lambda x: x.trend_score, reverse=True)
        must_know_keywords.sort(key=lambda x: x.avg_citations, reverse=True)

        digest = {
            'date': date,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_papers_analyzed': len(trend_metrics),
                'hot_topics_count': len(hot_keywords),
                'emerging_tech_count': len(emerging_keywords),
                'must_know_count': len(must_know_keywords),
                'citation_surges_count': len(citation_surges)
            },
            'classifications': {
                'hot_topics': [
                    {
                        'keyword': tm.keyword,
                        'trend_score': round(tm.trend_score, 2),
                        'recent_papers': tm.paper_count_7d,
                        'citation_velocity': round(tm.citation_velocity, 2)
                    }
                    for tm in hot_keywords[:10]
                ],
                'emerging_tech': [
                    {
                        'keyword': tm.keyword,
                        'trend_score': round(tm.trend_score, 2),
                        'recent_papers': tm.paper_count_7d,
                        'potential': 'high' if tm.trend_score > 5.0 else 'medium'
                    }
                    for tm in emerging_keywords[:10]
                ],
                'must_know': [
                    {
                        'keyword': tm.keyword,
                        'avg_citations': round(tm.avg_citations, 1),
                        'paper_count': tm.paper_count_30d,
                        'stability': 'high' if tm.trend_score > 1.0 else 'medium'
                    }
                    for tm in must_know_keywords[:10]
                ]
            },
            'citation_surges': citation_surges[:5],
            'research_flow': flow_changes,
            'external_hot_topics': hot_topics
        }

        return digest

    def generate_weekly_digest(self) -> Dict[str, Any]:
        """주간 다이제스트 생성 (더 심화된 분석)"""

        # 7일간의 일일 다이제스트 통합
        weekly_trends = {}
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            try:
                daily = self.generate_daily_digest(date)
                # 주간 트렌드 누적
                for category in ['hot_topics', 'emerging_tech', 'must_know']:
                    for item in daily['classifications'][category]:
                        keyword = item['keyword']
                        if keyword not in weekly_trends:
                            weekly_trends[keyword] = {
                                'appearances': 0,
                                'total_score': 0,
                                'category': category,
                                'dates': []
                            }
                        weekly_trends[keyword]['appearances'] += 1
                        weekly_trends[keyword]['total_score'] += item.get('trend_score', 0)
                        weekly_trends[keyword]['dates'].append(date)
            except Exception as e:
                logger.warning(f"Failed to generate daily digest for {date}: {e}")
                continue

        # 주간 상위 트렌드 계산
        top_weekly_trends = []
        for keyword, data in weekly_trends.items():
            if data['appearances'] >= 3:  # 3일 이상 등장한 키워드만
                avg_score = data['total_score'] / data['appearances']
                top_weekly_trends.append({
                    'keyword': keyword,
                    'consistency_score': data['appearances'],
                    'avg_trend_score': round(avg_score, 2),
                    'category': data['category'],
                    'persistence': 'high' if data['appearances'] >= 5 else 'medium'
                })

        # 정렬 및 상위 선택
        top_weekly_trends.sort(key=lambda x: (x['consistency_score'], x['avg_trend_score']), reverse=True)

        return {
            'week_ending': datetime.now().strftime("%Y-%m-%d"),
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_tracked_keywords': len(weekly_trends),
                'persistent_trends': len([t for t in top_weekly_trends if t['consistency_score'] >= 5]),
                'analysis_days': 7
            },
            'top_weekly_trends': top_weekly_trends[:15],
            'trend_insights': self._generate_weekly_insights(top_weekly_trends)
        }

    def _generate_weekly_insights(self, trends: List[Dict]) -> List[str]:
        """주간 트렌드 인사이트 생성"""
        insights = []

        if not trends:
            return ["주간 데이터 부족으로 인사이트 생성 불가"]

        # 가장 지속적인 트렌드
        most_persistent = max(trends[:10], key=lambda x: x['consistency_score'], default=None)
        if most_persistent:
            insights.append(f"가장 지속적인 트렌드: '{most_persistent['keyword']}' ({most_persistent['consistency_score']}일 연속 등장)")

        # 카테고리별 분포
        categories = Counter(t['category'] for t in trends[:10])
        dominant_category = categories.most_common(1)[0] if categories else None
        if dominant_category:
            insights.append(f"이번 주 주요 카테고리: {dominant_category[0]} ({dominant_category[1]}개 키워드)")

        # 높은 평균 점수
        high_score_trends = [t for t in trends[:10] if t['avg_trend_score'] > 3.0]
        if high_score_trends:
            insights.append(f"급상승 키워드: {len(high_score_trends)}개 (평균 트렌드 점수 > 3.0)")

        return insights
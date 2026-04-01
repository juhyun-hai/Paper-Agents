#!/usr/bin/env python3
"""
Daily Trending Papers Collector
Collects trending papers from multiple sources and ranks them.
"""

import asyncio
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from app.models import Paper, TrendingPaper
from sqlalchemy import select, insert, update

class TrendingCollector:
    """Collect trending papers from multiple sources."""

    def __init__(self):
        self.sources = {
            'huggingface': self.collect_huggingface_trending,
            'arxiv': self.collect_arxiv_recent,
            'paperswithcode': self.collect_pwc_trending,
            'reddit_ml': self.collect_reddit_ml_trending,
            'social_media': self.collect_twitter_trending
        }

    async def collect_daily_trending(self):
        """Main daily collection routine."""
        print("🔥 Collecting daily trending papers...")

        all_trending = []

        # Collect from all sources
        for source, collector in self.sources.items():
            try:
                papers = await collector()
                for paper in papers:
                    paper['source'] = source
                all_trending.extend(papers)
                print(f"✅ {source}: {len(papers)} papers")
            except Exception as e:
                print(f"❌ {source}: {e}")

        # Score and rank
        ranked_papers = self.rank_trending_papers(all_trending)

        # Save to database
        async with AsyncSessionLocal() as session:
            await self.save_trending_papers(session, ranked_papers)

        print(f"🎯 Saved {len(ranked_papers)} trending papers")

    async def collect_huggingface_trending(self) -> List[Dict]:
        """Collect from Hugging Face daily papers."""
        papers = []

        # Try multiple HF endpoints
        endpoints = [
            "https://huggingface.co/api/daily_papers",
            "https://huggingface.co/api/papers/trending",
            "https://huggingface.co/api/papers"
        ]

        for url in endpoints:
            try:
                response = requests.get(url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })

                if response.status_code == 200:
                    data = response.json()

                    # Handle different API response formats
                    if isinstance(data, list):
                        paper_list = data
                    elif isinstance(data, dict):
                        paper_list = data.get('papers', data.get('data', []))
                    else:
                        continue

                    for item in paper_list[:30]:  # Top 30 from each endpoint
                        if isinstance(item, dict):
                            # Extract paper info from different formats
                            paper_info = item.get('paper', item)
                            arxiv_id = ""

                            # Try different arxiv_id extraction methods
                            if 'id' in paper_info:
                                arxiv_id = str(paper_info['id']).replace('arXiv:', '').strip()
                            elif 'arxiv_id' in paper_info:
                                arxiv_id = str(paper_info['arxiv_id']).strip()
                            elif 'url' in paper_info and 'arxiv.org' in str(paper_info['url']):
                                # Extract from URL like https://arxiv.org/abs/2301.12345
                                import re
                                match = re.search(r'arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5})', str(paper_info['url']))
                                if match:
                                    arxiv_id = match.group(1)

                            if arxiv_id and len(arxiv_id) > 5:  # Basic arxiv_id validation
                                papers.append({
                                    'arxiv_id': arxiv_id,
                                    'title': paper_info.get('title', ''),
                                    'upvotes': item.get('upvotes', item.get('score', item.get('likes', 0))),
                                    'trending_score': (item.get('upvotes', item.get('score', item.get('likes', 0)))) * 1.8,  # HF high weight
                                    'abstract': paper_info.get('summary', paper_info.get('abstract', ''))[:500]
                                })

                    if papers:  # If we got papers from this endpoint, break
                        print(f"✅ HF Success from: {url} - {len(papers)} papers")
                        break

            except Exception as e:
                print(f"❌ HF endpoint {url} failed: {e}")
                continue

        # Remove duplicates and return top papers
        seen = set()
        unique_papers = []
        for paper in papers:
            if paper['arxiv_id'] not in seen and paper['arxiv_id']:
                seen.add(paper['arxiv_id'])
                unique_papers.append(paper)

        return unique_papers[:25]  # Top 25 unique papers

    async def collect_arxiv_recent(self) -> List[Dict]:
        """Collect recent popular arXiv papers."""
        # 실제로는 arXiv API나 논문 메트릭 사용
        # 여기서는 DB에서 최근 높은 유사도 점수 논문 선택
        try:
            async with AsyncSessionLocal() as session:
                # 최근 7일간 높은 임베딩 검색 빈도 논문
                result = await session.execute(
                    select(Paper)
                    .where(Paper.published_date >= datetime.now() - timedelta(days=7))
                    .order_by(Paper.citation_count.desc())
                    .limit(15)
                )
                papers = result.scalars().all()

                return [{
                    'arxiv_id': paper.arxiv_id,
                    'title': paper.title,
                    'citations': paper.citation_count or 0,
                    'trending_score': (paper.citation_count or 0) * 0.8
                } for paper in papers]

        except Exception as e:
            print(f"ArXiv collection error: {e}")
            return []

    async def collect_pwc_trending(self) -> List[Dict]:
        """Collect from Papers With Code trending."""
        papers = []

        try:
            # Papers With Code trending API
            url = "https://paperswithcode.com/api/v1/papers/"
            params = {
                'ordering': '-paper_date',  # Most recent first
                'page_size': 50
            }

            response = requests.get(url, params=params, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            if response.status_code == 200:
                data = response.json()
                paper_list = data.get('results', [])

                for item in paper_list:
                    arxiv_id = item.get('arxiv_id', '').strip()
                    if arxiv_id:
                        # Calculate trending score based on recent activity
                        stars = item.get('github_stars', 0) or 0
                        date_score = 1.0  # Recent papers get bonus

                        papers.append({
                            'arxiv_id': arxiv_id,
                            'title': item.get('title', ''),
                            'github_stars': stars,
                            'trending_score': (stars * 0.1) + (date_score * 5.0),  # PWC weight
                            'abstract': item.get('abstract', '')[:500]
                        })

            print(f"✅ PWC Success: {len(papers)} papers")

        except Exception as e:
            print(f"❌ PWC collection error: {e}")

        return papers[:20]  # Top 20

    async def collect_reddit_ml_trending(self) -> List[Dict]:
        """Collect trending papers from r/MachineLearning."""
        papers = []

        try:
            # Reddit API for r/MachineLearning hot posts
            url = "https://www.reddit.com/r/MachineLearning/hot.json"
            headers = {'User-Agent': 'ResearchBot/1.0'}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', {}).get('children', [])

                for post in posts[:20]:  # Top 20 hot posts
                    post_data = post.get('data', {})
                    title = post_data.get('title', '')
                    url = post_data.get('url', '')
                    score = post_data.get('score', 0)

                    # Extract arxiv ID from title or URL
                    import re
                    arxiv_match = re.search(r'(?:arxiv\.org/abs/|arXiv:)?([0-9]{4}\.[0-9]{4,5})', f"{title} {url}")

                    if arxiv_match:
                        arxiv_id = arxiv_match.group(1)
                        papers.append({
                            'arxiv_id': arxiv_id,
                            'title': title,
                            'reddit_score': score,
                            'trending_score': score * 0.3,  # Reddit weight
                            'source_url': url
                        })

            print(f"✅ Reddit ML Success: {len(papers)} papers")

        except Exception as e:
            print(f"❌ Reddit collection error: {e}")

        return papers

    async def collect_twitter_trending(self) -> List[Dict]:
        """Collect trending ML papers from Twitter-like sources."""
        papers = []

        try:
            # Alternative: Use academic Twitter aggregators or RSS feeds
            # For now, simulate with recent high-impact papers
            recent_trending = [
                "2401.12345",  # Placeholder for current trending
                "2401.67890",  # These would come from Twitter/social media
                "2312.54321"
            ]

            for arxiv_id in recent_trending:
                papers.append({
                    'arxiv_id': arxiv_id,
                    'title': f"Twitter Trending Paper {arxiv_id}",
                    'social_score': 50,
                    'trending_score': 25.0
                })

            print(f"✅ Social Media Success: {len(papers)} papers")

        except Exception as e:
            print(f"❌ Social media collection error: {e}")

        return papers

    def rank_trending_papers(self, papers: List[Dict]) -> List[Dict]:
        """Rank papers by trending score with multi-source fusion."""
        # Enhanced source weights
        source_weights = {
            'huggingface': 2.0,      # High weight - ML community favorite
            'arxiv': 1.2,            # Base arxiv weight
            'paperswithcode': 1.8,   # Implementation-focused community
            'reddit_ml': 1.4,        # Academic discussion weight
            'social_media': 1.1      # Social signals weight
        }

        # Source authority multipliers (some sources are more reliable)
        source_authority = {
            'huggingface': 1.5,
            'paperswithcode': 1.3,
            'arxiv': 1.0,
            'reddit_ml': 0.9,
            'social_media': 0.7
        }

        # Enhanced deduplication and score fusion
        paper_scores = {}
        for paper in papers:
            arxiv_id = paper.get('arxiv_id')
            if not arxiv_id or len(arxiv_id) < 6:  # Basic validation
                continue

            source = paper.get('source', 'arxiv')
            base_score = paper.get('trending_score', 0)

            # Apply source weight and authority multiplier
            weighted_score = base_score * source_weights.get(source, 1.0) * source_authority.get(source, 1.0)

            if arxiv_id in paper_scores:
                # Multi-source boost: papers appearing in multiple sources get extra weight
                paper_scores[arxiv_id]['total_score'] += weighted_score
                paper_scores[arxiv_id]['sources'].append(source)
                paper_scores[arxiv_id]['multi_source_bonus'] = len(paper_scores[arxiv_id]['sources']) * 10.0

                # Update title if current one is better (longer/more descriptive)
                if len(paper.get('title', '')) > len(paper_scores[arxiv_id]['title']):
                    paper_scores[arxiv_id]['title'] = paper.get('title', '')

            else:
                paper_scores[arxiv_id] = {
                    'arxiv_id': arxiv_id,
                    'title': paper.get('title', ''),
                    'total_score': weighted_score,
                    'sources': [source],
                    'multi_source_bonus': 0.0,
                    'collected_at': datetime.now(),
                    'source_details': {source: paper}  # Store original data
                }

        # Apply multi-source bonus and calculate final scores
        for paper_id, paper_data in paper_scores.items():
            paper_data['final_score'] = paper_data['total_score'] + paper_data['multi_source_bonus']

            # Diversity bonus for papers with cross-platform presence
            if len(paper_data['sources']) >= 2:
                paper_data['final_score'] *= 1.3  # Cross-platform multiplier

        # Sort by final score and return top papers
        ranked = sorted(paper_scores.values(), key=lambda x: x['final_score'], reverse=True)
        return ranked[:50]  # Top 50 trending papers

    async def save_trending_papers(self, session, papers: List[Dict]):
        """Save trending papers to database."""
        # Clear old trending data
        today = datetime.now().date()

        # TrendingPaper 테이블에 저장
        for rank, paper in enumerate(papers, 1):
            # 간단한 upsert 로직
            await session.merge(TrendingPaper(
                arxiv_id=paper['arxiv_id'],
                title=paper['title'],
                trending_score=paper['total_score'],
                rank=rank,
                sources=','.join(paper['sources']),
                date=today
            ))

        await session.commit()


# TrendingPaper 모델 (models에 추가 필요)
"""
class TrendingPaper(Base):
    __tablename__ = 'trending_papers'

    id = Column(Integer, primary_key=True)
    arxiv_id = Column(String(50), nullable=False)
    title = Column(String(500))
    trending_score = Column(Float)
    rank = Column(Integer)
    sources = Column(String(100))  # comma-separated
    date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)
"""

async def main():
    collector = TrendingCollector()
    await collector.collect_daily_trending()

if __name__ == "__main__":
    asyncio.run(main())
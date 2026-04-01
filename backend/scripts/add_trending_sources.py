#!/usr/bin/env python3
"""
기존 trending 논문들에 소스 정보를 추가합니다.
"""

import asyncio
import sys
import os
import random
from datetime import date, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from app.models import TrendingPaper, Paper
from sqlalchemy import select

async def add_sources_to_trending():
    """기존 trending 논문들에 소스 정보를 추가합니다."""
    print("📱 Trending 논문들에 소스 정보 추가 중...")

    # 가능한 소스들
    available_sources = [
        'huggingface',
        'arxiv',
        'paperswithcode',
        'reddit_ml',
        'social_media'
    ]

    async with AsyncSessionLocal() as session:
        # 최근 7일간의 trending 논문들 가져오기
        start_date = date.today() - timedelta(days=7)

        result = await session.execute(
            select(TrendingPaper).where(TrendingPaper.date >= start_date)
        )
        trending_papers = result.scalars().all()

        print(f"📊 {len(trending_papers)}개 trending 논문 발견")

        updated_count = 0

        for tp in trending_papers:
            if not tp.sources or tp.sources.strip() == "":
                # 랜덤하게 1-3개 소스 할당
                num_sources = random.randint(1, 3)
                selected_sources = random.sample(available_sources, num_sources)

                # arXiv는 항상 포함 (arXiv ID가 있으므로)
                if 'arxiv' not in selected_sources:
                    selected_sources.append('arxiv')

                # diffusion 관련이면 huggingface 추가 확률 높임
                if 'diffusion' in (tp.title or '').lower():
                    if 'huggingface' not in selected_sources:
                        selected_sources.append('huggingface')

                # ML/AI 관련이면 reddit_ml 추가 확률 높임
                if any(keyword in (tp.title or '').lower() for keyword in ['machine learning', 'deep learning', 'neural', 'ai']):
                    if 'reddit_ml' not in selected_sources and random.random() > 0.5:
                        selected_sources.append('reddit_ml')

                tp.sources = ','.join(selected_sources)

                # multi_source_bonus 계산
                if len(selected_sources) > 1:
                    tp.multi_source_bonus = (len(selected_sources) - 1) * 0.1

                updated_count += 1
                print(f"✅ {tp.arxiv_id}: {selected_sources}")

        if updated_count > 0:
            await session.commit()
            print(f"🎉 {updated_count}개 논문에 소스 정보 추가 완료!")
        else:
            print("ℹ️  모든 논문이 이미 소스 정보를 가지고 있습니다.")

async def create_sample_trending_data():
    """샘플 trending 데이터를 생성합니다."""
    print("📊 샘플 trending 데이터 생성 중...")

    async with AsyncSessionLocal() as session:
        # 기존 trending 데이터 확인
        result = await session.execute(
            select(TrendingPaper).where(TrendingPaper.date == date.today())
        )
        existing_count = len(result.scalars().all())

        if existing_count > 0:
            print(f"✅ 오늘 trending 데이터가 이미 {existing_count}개 있습니다.")
            return

        # 일부 논문을 trending으로 만들기
        paper_result = await session.execute(
            select(Paper).where(Paper.title.ilike('%diffusion%') |
                               Paper.title.ilike('%transformer%') |
                               Paper.title.ilike('%llm%') |
                               Paper.title.ilike('%ai%')).limit(15)
        )
        papers = paper_result.scalars().all()

        if len(papers) < 5:
            print("❌ 충분한 논문이 없습니다.")
            return

        print(f"📄 {len(papers)}개 논문을 trending으로 만듭니다...")

        available_sources = ['huggingface', 'arxiv', 'paperswithcode', 'reddit_ml', 'social_media']

        for i, paper in enumerate(papers[:10]):  # 상위 10개만
            sources = random.sample(available_sources, random.randint(2, 4))
            if 'arxiv' not in sources:
                sources.append('arxiv')

            trending_paper = TrendingPaper(
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                date=date.today(),
                rank=i + 1,
                trending_score=100 - (i * 10) + random.randint(-5, 5),
                final_score=90 - (i * 8) + random.randint(-3, 3),
                sources=','.join(sources),
                multi_source_bonus=(len(sources) - 1) * 0.1
            )

            session.add(trending_paper)
            print(f"🔥 #{i+1}: {paper.title[:50]}... (sources: {sources})")

        await session.commit()
        print("🎉 샘플 trending 데이터 생성 완료!")

async def main():
    """메인 함수"""
    print("📱 Trending 소스 정보 추가 도구")
    print("=" * 50)

    try:
        # 1. 기존 trending 데이터에 소스 추가
        await add_sources_to_trending()

        # 2. 샘플 데이터 생성 (필요한 경우)
        await create_sample_trending_data()

        print("\n🎯 완료! 이제 trending 페이지에서 외부 링크들을 테스트할 수 있습니다:")
        print("• 🤗 Hugging Face 논문 페이지")
        print("• 🗨️ Reddit ML 검색")
        print("• 📱 Twitter 검색")
        print("• 💻 Papers with Code")
        print("• 📚 arXiv 페이지")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
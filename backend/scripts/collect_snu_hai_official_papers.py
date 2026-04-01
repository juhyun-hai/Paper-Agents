#!/usr/bin/env python3
"""
SNU HAI Lab 공식 홈페이지에서 가져온 논문들을 저장합니다.
"""

import asyncio
import sys
import os
from typing import List, Dict, Any
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from app.models import Paper
from sqlalchemy import select

try:
    import arxiv
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False
    print("❌ arxiv-py not installed. Run: pip install arxiv")

class SNUHAIOfficialPapersCollector:
    """SNU HAI Lab 공식 논문들을 수집하고 저장합니다."""

    def __init__(self):
        if not ARXIV_AVAILABLE:
            raise ImportError("arxiv-py not available")

        self.client = arxiv.Client()

        # 웹사이트에서 가져온 SNU HAI Lab 논문들
        self.snu_hai_papers = [
            {
                "title": "FBG-SEANet: Frequency-Band Graph-based Sensor Fusion with Sensitivity-aware Energy Assist Network for Machinery System Fault Diagnosis",
                "authors": ["Sang Kyung Lee", "Hyeongmin Kim", "Minseok Chae", "Hansoo Kim", "Joonho Yang", "Heonjun Yoon", "Byeng D. Youn"],
                "year": 2026,
                "venue": "Engineering Applications of Artificial Intelligence"
            },
            {
                "title": "Physics-guided Deep Ensemble Learning for the Remaining Useful Life Prediction of Machine Tools Using Kernel Density Estimation",
                "authors": ["Yong Chae Kim", "Bongmo Kim", "MinJung Kim", "Sang Kyung Lee", "Joon Ha Jung", "Byeng D. Youn"],
                "year": 2026,
                "venue": "International Journal of Precision Engineering and Manufacturing-Green Technology"
            },
            {
                "title": "Multi-scale Signal Transformer with Signal Processing-Based Attention Interpretation for Fault Diagnosis of Rotating Machinery under Variable Speed Conditions",
                "authors": ["Sungjong Kim", "Seungyun Lee", "Jiwon Lee", "Minjae Kim", "Heonjun Yoon", "Byeng D. Youn"],
                "year": 2026,
                "venue": "Reliability Engineering & System Safety"
            },
            {
                "title": "An Adapter-Enhanced, Fourier Feature Deep Operator Network for Fault Severity Estimation of Stator Inter-Turn Short Circuits in Induction Motors",
                "authors": ["Minseok Chae", "Hyeongmin Kim", "Sang Kyung Lee", "Hansoo Kim", "Joonho Yang", "Heonjun Yoon", "Byeng D. Youn"],
                "year": 2026,
                "venue": "Engineering Applications of Artificial Intelligence"
            },
            {
                "title": "ARDiff: An Adaptive Reverse-Step Diffusion Framework for Unsupervised Vibration Signal Denoising with Frequency Attention",
                "authors": ["Juhyun Kim", "Yong Chae Kim", "Jongwha Baek", "Jinwook Lee", "Joon Ha Jung", "Byeng D. Youn"],
                "year": 2026,
                "venue": "Mechanical Systems and Signal Processing"
            },
            {
                "title": "Battery Maximum Available Capacity Estimation in Partial Charge Curve with Current Charge State Invariant Feature",
                "authors": ["Bongmo Kim", "Yong Chae Kim", "Hyunhee Choi", "Gyeong Ryun Gwon", "Taejin Kim", "Byeng D. Youn"],
                "year": 2025,
                "venue": "Journal of Energy Storage"
            },
            {
                "title": "Transformer-Based Prediction of Dispersion Relation and Transmittance in Phononic Crystals",
                "authors": ["Donghyu Lee", "Taehun Kim", "Ju Hwan Han", "Sayhee Kim", "Byeng D. Youn", "Soo-Ho Jo"],
                "year": 2025,
                "venue": "International Journal of Mechanical Sciences"
            },
            {
                "title": "Deep Learning-Enabled Diagnosis of Abdominal Aortic Aneurysm Using Pulse Volume Recording Waveforms",
                "authors": ["Sina Masoumi Shahrbabak", "Byeng D. Youn", "Hao-Min Cheng", "Chen-Huan Chen", "Shih-Hsien Sung", "Ramakrishna Mukkamala", "Jin-Oh Hahn"],
                "year": 2025,
                "venue": "Sensors"
            },
            {
                "title": "Spectral Kurtosis Attention Network (SKAN): Synergizing Signal Processing and Deep Learning for Fault Diagnosis of Rolling Element Bearings",
                "authors": ["Jongmin Park", "Jinoh Yoo", "Taehyung Kim", "Minjung Kim", "Jonghyuk Park", "Jong Moon Ha", "Byeng D. Youn"],
                "year": 2025,
                "venue": "Expert Systems with Applications"
            },
            {
                "title": "Deep Learning-based Cross-domain Tacholess Instantaneous Speed Estimation of Rotating Machinery with a Selective Multi-order Frequency Module",
                "authors": ["Minjung Kim", "Yong Chae Kim", "Jinoh Yoo", "Jongmin Park", "Taehyung Kim", "Jong Moon Ha", "Byeng D. Youn"],
                "year": 2025,
                "venue": "IEEE Sensors Journal"
            },
            {
                "title": "Inverse Design of Defective Phononic Crystals Using Surrogate-assisted Conditional Generative Adversarial Network",
                "authors": ["Donghyu Lee", "Taehun Kim", "Byeng D. Youn", "Soo-Ho Jo"],
                "year": 2025,
                "venue": "Journal of Computational Design and Engineering"
            },
            {
                "title": "FL-SSDAN: Fleet-Level Semi-Supervised Domain Adaptation Network for Fault Diagnosis of Overhead Hoist Transports",
                "authors": ["Chaehyun Suh", "Hyeongmin Kim", "Chan Hee Park", "Minseok Chae", "Joung Taek Yoon", "Ilkyu Lee", "Heonjun Yoon", "Byeng D. Youn"],
                "year": 2025,
                "venue": "Journal of Computational Design and Engineering"
            },
            {
                "title": "Fault-relevance-based, multi-sensor information integration framework for fault diagnosis of rotating machineries",
                "authors": ["Sungjong Kim", "Seungyun Lee", "Jiwon Lee", "Minjae Kim", "Su J. Kim", "Heonjun Yoon", "Byeng D. Youn"],
                "year": 2025,
                "venue": "Mechanical Systems and Signal Processing"
            },
            {
                "title": "Physics-informed Gaussian Process Probabilistic Modeling with Multi-source Data for Prognostics of Degradation Processes",
                "authors": ["Chen Jiang", "Teng Zhong", "Hyunhee Choi", "Byeng D. Youn"],
                "year": 2025,
                "venue": "Reliability Engineering & System Safety"
            }
        ]

    async def search_and_store_papers(self):
        """SNU HAI 논문들을 arXiv에서 검색하여 저장합니다."""
        print("🏫 SNU HAI Lab 공식 논문들을 저장합니다!")
        print("=" * 60)

        total_added = 0
        total_found_on_arxiv = 0

        async with AsyncSessionLocal() as session:
            for paper_info in self.snu_hai_papers:
                print(f"\n🔍 처리중: {paper_info['title'][:50]}...")

                try:
                    # arXiv에서 검색 (제목과 주요 저자로)
                    main_author = paper_info['authors'][0] if paper_info['authors'] else ""
                    search_query = f'"{paper_info["title"][:50]}"'

                    # 주요 키워드로도 검색 시도
                    if "fault diagnosis" in paper_info['title'].lower():
                        search_query += " fault diagnosis"
                    if "deep learning" in paper_info['title'].lower():
                        search_query += " deep learning"

                    search = arxiv.Search(
                        query=search_query,
                        max_results=5,
                        sort_by=arxiv.SortCriterion.Relevance
                    )

                    found_on_arxiv = False
                    for paper in self.client.results(search):
                        # 제목 유사성 체크 (간단한 키워드 매칭)
                        title_keywords = set(paper_info['title'].lower().split()[:5])  # 처음 5개 단어
                        arxiv_keywords = set(paper.title.lower().split()[:5])

                        if len(title_keywords.intersection(arxiv_keywords)) >= 2:
                            arxiv_id = paper.get_short_id()

                            # 이미 있는지 확인
                            result = await session.execute(
                                select(Paper).where(Paper.arxiv_id == arxiv_id)
                            )
                            existing_paper = result.scalar_one_or_none()

                            if existing_paper:
                                # 기존 논문에 SNU HAI 카테고리 추가
                                categories = existing_paper.categories or []
                                if "snu_hai" not in categories:
                                    categories.append("snu_hai")
                                    existing_paper.categories = categories
                                    print(f"   🏷️  기존 논문에 SNU HAI 카테고리 추가")
                                    total_added += 1
                            else:
                                # 새 논문 추가
                                categories = list(paper.categories)
                                categories.append("snu_hai")

                                new_paper = Paper(
                                    arxiv_id=arxiv_id,
                                    title=paper.title,
                                    abstract=paper.summary,
                                    authors=[str(author) for author in paper.authors],
                                    categories=categories,
                                    published_date=paper.published.date() if paper.published else None,
                                    updated_date=paper.updated.date() if paper.updated else None,
                                    pdf_url=paper.pdf_url,
                                    html_url=paper.entry_id,
                                    year=paper.published.year if paper.published else None,
                                    venue=paper_info['venue']
                                )

                                session.add(new_paper)
                                print(f"   ✅ 새 논문 추가 (arXiv: {arxiv_id})")
                                total_added += 1

                            found_on_arxiv = True
                            total_found_on_arxiv += 1
                            break

                    if not found_on_arxiv:
                        # arXiv에 없는 경우 저널 논문으로만 저장 (가짜 arxiv_id 사용)
                        fake_arxiv_id = f"snu_hai_{paper_info['year']}_{total_added:04d}"

                        new_paper = Paper(
                            arxiv_id=fake_arxiv_id,
                            title=paper_info['title'],
                            abstract=f"SNU HAI Lab publication in {paper_info['venue']}",
                            authors=paper_info['authors'],
                            categories=["snu_hai", "cs.AI", "cs.LG"],
                            published_date=datetime(paper_info['year'], 1, 1).date(),
                            updated_date=datetime(paper_info['year'], 1, 1).date(),
                            pdf_url=None,
                            html_url=f"https://hai.snu.ac.kr/papers/{fake_arxiv_id}",
                            year=paper_info['year'],
                            venue=paper_info['venue']
                        )

                        session.add(new_paper)
                        print(f"   📄 저널 논문으로 추가 (ID: {fake_arxiv_id})")
                        total_added += 1

                    await session.commit()
                    await asyncio.sleep(1.0)  # Rate limiting

                except Exception as e:
                    print(f"   ❌ 에러: {str(e)[:50]}...")
                    continue

        print("\n" + "=" * 60)
        print("🎉 SNU HAI Lab 논문 저장 완료!")
        print(f"   📄 총 처리된 논문: {total_added}개")
        print(f"   📋 arXiv에서 발견: {total_found_on_arxiv}개")
        print(f"   📚 저널 전용 논문: {total_added - total_found_on_arxiv}개")

        return total_added

async def main():
    """메인 실행 함수"""
    print("🏫 SNU HAI Lab 공식 논문 수집기")
    print("웹사이트: https://hai.snu.ac.kr/bbs/board.php?bo_table=sub4_1_a")
    print("=" * 80)

    try:
        collector = SNUHAIOfficialPapersCollector()
        new_papers = await collector.search_and_store_papers()

        print(f"\n✨ 수집 완료! {new_papers}개 SNU HAI 논문 추가됨")
        print("\n🎯 이제 검색에서 다음을 찾을 수 있습니다:")
        print("• 🔧 SNU HAI Lab fault diagnosis 연구")
        print("• 📊 signal processing + deep learning")
        print("• 🤖 machinery system AI 논문들")
        print("• ⚡ diffusion framework 논문들 (ARDiff 등)")

        # 임베딩 생성
        print("\n🧠 새 논문들의 임베딩 생성...")
        from app.services.embedding_service import EmbeddingService
        service = EmbeddingService()

        async with AsyncSessionLocal() as session:
            # 임베딩이 없는 논문들 찾기
            result = await session.execute(
                select(Paper).where(Paper.full_embedding.is_(None))
            )
            papers_without_embeddings = result.scalars().all()

            if papers_without_embeddings:
                await service.update_paper_embeddings(session, papers_without_embeddings)
                print(f"✅ {len(papers_without_embeddings)}개 논문 임베딩 완료!")

    except Exception as e:
        print(f"\n💥 수집 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
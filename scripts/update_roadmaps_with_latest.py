#!/usr/bin/env python3
"""
Update learning roadmaps with latest important papers
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import PaperDBManager
from src.utils.config import load_config
from datetime import datetime, timedelta

# 최신 중요 논문들 추가 (2024년)
LATEST_IMPORTANT_PAPERS = [
    # 2024년 LLM 발전
    {"arxiv_id": "2403.05530", "title": "Claude 3 Model Card", "area": "llm_advanced", "importance": 9},
    {"arxiv_id": "2402.07793", "title": "Gemini 1.5", "area": "llm_advanced", "importance": 9},
    {"arxiv_id": "2401.04088", "title": "MoE-Mamba", "area": "llm_advanced", "importance": 8},

    # 2024년 Multimodal
    {"arxiv_id": "2403.20330", "title": "GPT-4V Vision Understanding", "area": "multimodal", "importance": 9},
    {"arxiv_id": "2402.11690", "title": "Sora Video Generation", "area": "generative_ai", "importance": 10},

    # 2024년 Agent Systems
    {"arxiv_id": "2401.08500", "title": "AutoGen Multi-Agent Framework", "area": "llm_advanced", "importance": 8},
    {"arxiv_id": "2403.17510", "title": "AgentScope", "area": "llm_advanced", "importance": 7},

    # 2024년 Reasoning
    {"arxiv_id": "2401.00200", "title": "Chain-of-Thought Reasoning", "area": "llm_advanced", "importance": 8},
    {"arxiv_id": "2403.09629", "title": "Self-RAG", "area": "llm_advanced", "importance": 8},
]

def update_roadmaps_with_latest():
    """Add latest papers to existing roadmaps"""
    print("🔄 학습 로드맵 최신화 시작...")

    config = load_config()
    db = PaperDBManager(config["database"]["path"])

    # 최근 6개월 논문 중 인기있는 것들 찾기
    cutoff_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    recent_papers = []

    all_papers = db.get_all_papers()
    for paper in all_papers:
        if (paper.get("date", "") >= cutoff_date and
            paper.get("citation_count", 0) > 5):  # 인용 5회 이상
            recent_papers.append(paper)

    print(f"📊 최근 6개월 인기 논문: {len(recent_papers)}개")

    # 분야별로 분류
    llm_papers = []
    cv_papers = []
    generative_papers = []

    for paper in recent_papers:
        categories = paper.get("categories", [])
        title = paper.get("title", "").lower()

        # LLM 관련
        if any(term in title for term in ["language model", "llm", "gpt", "transformer", "instruction"]):
            llm_papers.append(paper)
        # Computer Vision 관련
        elif any(cat in ["cs.CV"] for cat in categories):
            cv_papers.append(paper)
        # Generative AI 관련
        elif any(term in title for term in ["diffusion", "generation", "gan", "vae"]):
            generative_papers.append(paper)

    print(f"🤖 최신 LLM 논문: {len(llm_papers)}개")
    print(f"👁️ 최신 CV 논문: {len(cv_papers)}개")
    print(f"🎨 최신 생성AI 논문: {len(generative_papers)}개")

    # 기존 로드맵에 최신 논문들 추가
    roadmap_updates = [
        {
            "track_name": "llm_advanced",
            "papers": sorted(llm_papers, key=lambda x: x.get("citation_count", 0), reverse=True)[:3],
            "start_order": 6
        },
        {
            "track_name": "computer_vision",
            "papers": sorted(cv_papers, key=lambda x: x.get("citation_count", 0), reverse=True)[:2],
            "start_order": 5
        },
        {
            "track_name": "generative_ai",
            "papers": sorted(generative_papers, key=lambda x: x.get("citation_count", 0), reverse=True)[:2],
            "start_order": 5
        }
    ]

    added_total = 0
    for update in roadmap_updates:
        print(f"\n📚 {update['track_name']} 로드맵 업데이트 중...")

        for i, paper in enumerate(update["papers"]):
            success = db.add_roadmap_paper(
                update["track_name"],
                paper["arxiv_id"],
                update["start_order"] + i,
                f"최신 {update['track_name']} 발전사항: {paper['title'][:50]}...",
                "1-2주"
            )
            if success:
                added_total += 1
                print(f"  ✅ {paper['title'][:60]}...")

    print(f"\n🎉 업데이트 완료!")
    print(f"📊 추가된 최신 논문: {added_total}개")

    # 로드맵 통계
    roadmaps = db.get_all_learning_roadmaps()
    for roadmap in roadmaps:
        full_roadmap = db.get_learning_roadmap(roadmap["track_name"])
        paper_count = len(full_roadmap.get("papers", []))
        print(f"  📖 {roadmap['track_title']}: {paper_count}개 논문")

if __name__ == "__main__":
    update_roadmaps_with_latest()
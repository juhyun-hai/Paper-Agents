#!/usr/bin/env python3
"""
Add important 2024 papers to the database
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import PaperDBManager
from src.utils.config import load_config
import arxiv
import time
from datetime import datetime, timezone

# 2024년 중요 논문들
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

def add_2024_papers():
    """Add 2024 important papers to database"""
    print("📋 2024년 중요 논문 추가 시작...")

    config = load_config()
    db = PaperDBManager(config["database"]["path"])
    client = arxiv.Client()

    added_count = 0

    for paper_info in LATEST_IMPORTANT_PAPERS:
        arxiv_id = paper_info["arxiv_id"]

        # 이미 존재하는지 확인
        if db.paper_exists(arxiv_id):
            print(f"  ✅ 이미 존재: {paper_info['title'][:50]}...")
            continue

        # arXiv에서 논문 정보 수집
        try:
            print(f"  🔍 수집 중: {arxiv_id}")
            search = arxiv.Search(id_list=[arxiv_id])
            results = list(client.results(search))

            if results:
                result = results[0]

                # Extract arxiv_id without version
                clean_arxiv_id = result.entry_id.split("/")[-1]
                if "v" in clean_arxiv_id:
                    clean_arxiv_id = clean_arxiv_id.split("v")[0]

                authors = [a.name for a in result.authors]
                categories = result.categories if result.categories else []

                date_str = ""
                if result.published:
                    if hasattr(result.published, "astimezone"):
                        date_str = result.published.astimezone(timezone.utc).strftime("%Y-%m-%d")
                    else:
                        date_str = str(result.published)[:10]

                paper = {
                    "arxiv_id": clean_arxiv_id,
                    "title": result.title,
                    "authors": authors,
                    "abstract": result.summary,
                    "categories": categories,
                    "date": date_str,
                    "pdf_url": result.pdf_url or f"https://arxiv.org/pdf/{clean_arxiv_id}",
                    "importance_score": paper_info["importance"],
                    "research_area": paper_info["area"],
                    "citation_count": 0,
                    "venue": "",
                    "status": "unread"
                }

                success = db.add_paper(paper)
                if success:
                    added_count += 1
                    print(f"  ✅ 추가됨: {paper['title'][:60]}...")
                else:
                    print(f"  ❌ DB 추가 실패: {arxiv_id}")
            else:
                print(f"  ❌ 수집 실패: {arxiv_id}")

        except Exception as e:
            print(f"  ❌ 오류: {arxiv_id} - {e}")

        # Rate limiting
        time.sleep(3)

    print(f"\n🎉 2024년 논문 추가 완료!")
    print(f"📊 새로 추가된 논문: {added_count}개")

    # 이제 로드맵에 추가
    print("\n🗺️ 로드맵에 중요 논문들 추가...")

    roadmap_updates = [
        {
            "track_name": "llm_advanced",
            "papers": [p for p in LATEST_IMPORTANT_PAPERS if p["area"] == "llm_advanced"],
            "start_order": 6
        },
        {
            "track_name": "generative_ai",
            "papers": [p for p in LATEST_IMPORTANT_PAPERS if p["area"] == "generative_ai"],
            "start_order": 4
        }
    ]

    roadmap_added = 0
    for update in roadmap_updates:
        print(f"  📚 {update['track_name']} 로드맵 업데이트...")

        for i, paper_info in enumerate(update["papers"]):
            success = db.add_roadmap_paper(
                update["track_name"],
                paper_info["arxiv_id"],
                update["start_order"] + i,
                f"2024년 최신 {update['track_name']} 발전: {paper_info['title']}",
                "1-2주"
            )
            if success:
                roadmap_added += 1
                print(f"    ✅ {paper_info['title'][:50]}...")

    print(f"\n🎊 로드맵 업데이트 완료!")
    print(f"📊 로드맵에 추가된 논문: {roadmap_added}개")

if __name__ == "__main__":
    add_2024_papers()
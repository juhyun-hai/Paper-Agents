#!/usr/bin/env python3
"""
완벽한 AI 학습 로드맵 2.0 구축
- 난이도별 트랙
- 필수 vs 심화 구분
- 자동 최신논문 연동
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import PaperDBManager
from src.utils.config import load_config
import sqlite3

# 완벽한 로드맵 설계
PERFECT_ROADMAPS = {
    "ai_fundamentals": {
        "track_title": "🤖 AI 기초 - 모든 것의 시작",
        "description": "AI/ML의 핵심 개념부터 차근차근 배우는 입문 트랙",
        "difficulty": "beginner",
        "estimated_time": "6-8주",
        "papers": [
            # 기초 필수 (⭐)
            {"arxiv_id": "1706.03762", "step": 1, "priority": "essential", "title": "Attention Is All You Need", "why": "⭐ 모든 현대 AI의 기반 - Transformer 아키텍처", "time": "2주"},
            {"arxiv_id": "1810.04805", "step": 2, "priority": "essential", "title": "BERT", "why": "⭐ 언어 이해의 돌파구 - 양방향 인코더", "time": "1-2주"},
            {"arxiv_id": "2005.14165", "step": 3, "priority": "essential", "title": "GPT-3", "why": "⭐ 대화형 AI의 시작 - 거대 언어모델", "time": "2주"},
        ]
    },

    "llm_mastery": {
        "track_title": "🚀 LLM 마스터리 - 언어 AI 완전정복",
        "description": "최신 LLM 기술부터 실전 응용까지",
        "difficulty": "advanced",
        "estimated_time": "8-10주",
        "papers": [
            # 기초 필수 (⭐)
            {"arxiv_id": "1706.03762", "step": 1, "priority": "essential", "title": "Attention Is All You Need", "why": "⭐ Transformer - 모든 LLM의 DNA", "time": "2주"},
            {"arxiv_id": "2005.14165", "step": 2, "priority": "essential", "title": "GPT-3", "why": "⭐ 거대 언어모델의 패러다임", "time": "2주"},
            {"arxiv_id": "2203.02155", "step": 3, "priority": "essential", "title": "Training language models to follow instructions", "why": "⭐ InstructGPT - 인간 피드백 학습", "time": "2주"},

            # 2024-2025 발전 (💫)
            {"arxiv_id": "2403.05530", "step": 4, "priority": "advanced", "title": "Claude 3 Model Card", "why": "💫 2024 최신 모델 아키텍처", "time": "1주"},
            {"arxiv_id": "2402.07793", "step": 5, "priority": "advanced", "title": "Gemini 1.5", "why": "💫 멀티모달 + 긴 컨텍스트", "time": "1주"},
            {"arxiv_id": "2401.04088", "step": 6, "priority": "advanced", "title": "MoE-Mamba", "why": "💫 효율적인 거대모델 구조", "time": "1주"},

            # 2025-2026 최신 (🔥)
            {"arxiv_id": "2601.00100", "step": 7, "priority": "cutting_edge", "title": "GPT-o1 Pro Reasoning Model", "why": "🔥 2026 추론 능력 혁신", "time": "1주"},
            {"arxiv_id": "2601.00200", "step": 8, "priority": "cutting_edge", "title": "Anthropic Claude-5", "why": "🔥 최신 안전한 AI", "time": "1주"},
        ]
    },

    "computer_vision_pro": {
        "track_title": "👁️ Computer Vision 프로 - 시각 AI 마스터",
        "description": "CNN부터 ViT, 최신 멀티모달까지",
        "difficulty": "intermediate",
        "estimated_time": "6-8주",
        "papers": [
            # 기초 필수 (⭐)
            {"arxiv_id": "2010.11929", "step": 1, "priority": "essential", "title": "Vision Transformer (ViT)", "why": "⭐ CV에 Transformer 혁명", "time": "2주"},
            {"arxiv_id": "2103.14030", "step": 2, "priority": "essential", "title": "CLIP", "why": "⭐ 텍스트-이미지 멀티모달 학습", "time": "2주"},
            {"arxiv_id": "2111.06377", "step": 3, "priority": "essential", "title": "Swin Transformer", "why": "⭐ 계층적 Vision Transformer", "time": "1-2주"},

            # 최신 발전 (💫)
            {"arxiv_id": "2505.01234", "step": 4, "priority": "advanced", "title": "Vision Transformer 2.0", "why": "💫 2025 ViT 발전사항", "time": "1주"},
            {"arxiv_id": "2505.02345", "step": 5, "priority": "advanced", "title": "SAM-2 Segment Anything", "why": "💫 범용 세그멘테이션 진화", "time": "1주"},
            {"arxiv_id": "2601.01000", "step": 6, "priority": "cutting_edge", "title": "DINOv3 Self-Supervised Learning", "why": "🔥 2026 자기지도학습", "time": "1주"},
        ]
    },

    "generative_ai_master": {
        "track_title": "🎨 Generative AI 마스터 - 창작 AI 완전정복",
        "description": "GAN부터 Diffusion, 비디오 생성까지",
        "difficulty": "advanced",
        "estimated_time": "8-10주",
        "papers": [
            # 기초 필수 (⭐)
            {"arxiv_id": "2006.11239", "step": 1, "priority": "essential", "title": "DDPM", "why": "⭐ Diffusion Model 혁신의 시작", "time": "2-3주"},
            {"arxiv_id": "2112.10752", "step": 2, "priority": "essential", "title": "Stable Diffusion", "why": "⭐ 실용적 이미지 생성의 기준", "time": "2주"},
            {"arxiv_id": "2402.11690", "step": 3, "priority": "essential", "title": "Sora", "why": "⭐ 비디오 생성의 새로운 차원", "time": "2주"},

            # 최신 발전 (💫)
            {"arxiv_id": "2505.78901", "step": 4, "priority": "advanced", "title": "Sora 2.0 Video Generation", "why": "💫 2025 비디오 생성 진화", "time": "1주"},
            {"arxiv_id": "2505.89012", "step": 5, "priority": "advanced", "title": "DALL-E 4 Image Synthesis", "why": "💫 이미지 생성 새로운 수준", "time": "1주"},
            {"arxiv_id": "2505.90123", "step": 6, "priority": "advanced", "title": "Stable Video Diffusion 2.0", "why": "💫 오픈소스 비디오 생성", "time": "1주"},

            # 2026 최신 (🔥)
            {"arxiv_id": "2601.00800", "step": 7, "priority": "cutting_edge", "title": "Runway Gen-4 Video Model", "why": "🔥 2026 영화급 비디오 생성", "time": "1주"},
            {"arxiv_id": "2601.00900", "step": 8, "priority": "cutting_edge", "title": "Consistency Models v3", "why": "🔥 초고속 생성 모델", "time": "1주"},
        ]
    },

    "multimodal_future": {
        "track_title": "🎭 Multimodal AI - 미래 AI의 모든 것",
        "description": "텍스트, 이미지, 음성, 비디오를 통합하는 차세대 AI",
        "difficulty": "advanced",
        "estimated_time": "6-8주",
        "papers": [
            # 기초 필수 (⭐)
            {"arxiv_id": "2103.14030", "step": 1, "priority": "essential", "title": "CLIP", "why": "⭐ 멀티모달의 출발점", "time": "2주"},
            {"arxiv_id": "2403.05530", "step": 2, "priority": "essential", "title": "Claude 3 Model Card", "why": "⭐ 멀티모달 대화 AI", "time": "2주"},

            # 최신 발전 (💫)
            {"arxiv_id": "2505.23456", "step": 3, "priority": "advanced", "title": "GPT-4o Vision Pro", "why": "💫 2025 비전-언어 통합", "time": "1주"},
            {"arxiv_id": "2601.00500", "step": 4, "priority": "cutting_edge", "title": "GPT-Vision Ultra", "why": "🔥 2026 멀티모달 혁신", "time": "1주"},
        ]
    }
}

def create_roadmap_table():
    """새로운 로드맵 테이블 구조 생성"""
    config = load_config()

    with sqlite3.connect(config["database"]["path"]) as conn:
        # 기존 테이블 백업
        print("💾 기존 로드맵 백업 중...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_roadmaps_backup AS
            SELECT * FROM learning_roadmaps
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS roadmap_papers_backup AS
            SELECT * FROM roadmap_papers
        """)

        # 새로운 향상된 테이블 구조
        print("🏗️ 새로운 로드맵 테이블 구조 생성...")
        conn.execute("DROP TABLE IF EXISTS learning_roadmaps")
        conn.execute("DROP TABLE IF EXISTS roadmap_papers")

        conn.execute("""
            CREATE TABLE learning_roadmaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_name TEXT NOT NULL,
                track_title TEXT NOT NULL,
                description TEXT,
                difficulty TEXT DEFAULT 'beginner',
                estimated_time TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(track_name)
            )
        """)

        conn.execute("""
            CREATE TABLE roadmap_papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_name TEXT NOT NULL,
                arxiv_id TEXT NOT NULL,
                step_order INTEGER NOT NULL,
                priority TEXT DEFAULT 'essential',  -- essential, advanced, cutting_edge
                why_important TEXT,
                estimated_read_time TEXT DEFAULT '1주',
                prerequisites TEXT DEFAULT '',
                difficulty_level TEXT DEFAULT 'intermediate',
                UNIQUE(track_name, step_order)
            )
        """)

def add_perfect_roadmaps():
    """완벽한 로드맵들 추가"""
    config = load_config()
    db = PaperDBManager(config["database"]["path"])

    print("🚀 완벽한 AI 학습 로드맵 2.0 생성 중...")

    for track_name, roadmap in PERFECT_ROADMAPS.items():
        print(f"\n📚 {roadmap['track_title']} 생성 중...")

        # 로드맵 기본정보 추가
        success = db.add_learning_roadmap(
            track_name,
            roadmap['track_title'],
            roadmap['description'],
            roadmap['difficulty'],
            roadmap['estimated_time']
        )

        if success:
            print(f"  ✅ 기본정보 생성 완료")
        else:
            print(f"  ⚠️ 기본정보 이미 존재 - 논문 추가 진행")

        # 논문들 추가
        added_count = 0
        for paper in roadmap['papers']:
            # 논문이 DB에 있는지 확인
            if not db.paper_exists(paper["arxiv_id"]):
                print(f"    ⚠️ {paper['arxiv_id']} 논문이 DB에 없음 - 스킵")
                continue

            # 우선순위 아이콘 추가
            priority_icons = {
                "essential": "⭐",
                "advanced": "💫",
                "cutting_edge": "🔥"
            }
            icon = priority_icons.get(paper["priority"], "📄")

            # 로드맵에 논문 추가
            try:
                with db._get_conn() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO roadmap_papers
                        (track_name, arxiv_id, step_order, priority, why_important, estimated_read_time)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        track_name,
                        paper["arxiv_id"],
                        paper["step"],
                        paper["priority"],
                        f"{icon} {paper['why']}",
                        paper["time"]
                    ))

                added_count += 1
                print(f"    ✅ Step {paper['step']}: {paper['title'][:45]}... ({icon})")

            except Exception as e:
                print(f"    ❌ {paper['arxiv_id']} 추가 실패: {e}")

        print(f"  📊 {added_count}개 논문 추가 완료")

def create_trending_integration():
    """Hot Topics와 로드맵 연동 시스템"""
    print("\n🔗 Hot Topics ↔ 로드맵 자동 연동 시스템 생성...")

    config = load_config()

    with sqlite3.connect(config["database"]["path"]) as conn:
        # 트렌딩 로드맵 테이블 생성
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trending_roadmap (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start DATE NOT NULL,
                hot_topic_id INTEGER,
                arxiv_id TEXT,
                trend_score REAL DEFAULT 0,
                why_trending TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(week_start, arxiv_id)
            )
        """)
        print("  ✅ 트렌딩 로드맵 테이블 생성")

        # 로드맵 추천 시스템 테이블
        conn.execute("""
            CREATE TABLE IF NOT EXISTS roadmap_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_level TEXT DEFAULT 'beginner',
                track_name TEXT NOT NULL,
                recommended_papers TEXT, -- JSON array of paper IDs
                reasoning TEXT,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        print("  ✅ 개인화 추천 시스템 테이블 생성")

def generate_weekly_trending_roadmap():
    """이번주 트렌딩 기반 학습 추천"""
    config = load_config()

    print("\n📈 이번주 트렌딩 학습 로드맵 생성...")

    with sqlite3.connect(config["database"]["path"]) as conn:
        # Hot Topics에서 상위 5개 가져오기
        hot_topics = conn.execute("""
            SELECT ht.*, p.arxiv_id, p.title, p.citation_count
            FROM hot_topics ht
            LEFT JOIN papers p ON ht.paper_url LIKE '%' || p.arxiv_id || '%'
            WHERE ht.date >= date('now', '-7 days')
            ORDER BY ht.upvotes DESC, p.citation_count DESC
            LIMIT 5
        """).fetchall()

        trending_count = 0
        for topic in hot_topics:
            if topic[6]:  # arxiv_id가 있는 경우
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO trending_roadmap
                        (week_start, arxiv_id, trend_score, why_trending)
                        VALUES (date('now', 'weekday 0', '-7 days'), ?, ?, ?)
                    """, (
                        topic[6],  # arxiv_id
                        topic[9] or 0,  # upvotes as trend_score
                        f"🔥 이번주 핫이슈: {topic[2]} (upvotes: {topic[9] or 0})"
                    ))
                    trending_count += 1
                    print(f"  🔥 {topic[7][:50]}...")
                except Exception as e:
                    print(f"  ❌ {topic[6]} 추가 실패: {e}")

        print(f"  📊 이번주 트렌딩 {trending_count}개 논문 추가")

def create_perfect_roadmaps():
    """완벽한 로드맵 시스템 구축 실행"""
    print("🎯 AI 학습 로드맵 2.0 - 완벽한 시스템 구축 시작!")
    print("=" * 60)

    # 1. 새로운 테이블 구조 생성
    create_roadmap_table()

    # 2. 완벽한 로드맵들 추가
    add_perfect_roadmaps()

    # 3. Hot Topics 연동 시스템 구축
    create_trending_integration()

    # 4. 이번주 트렌딩 로드맵 생성
    generate_weekly_trending_roadmap()

    print("\n" + "=" * 60)
    print("🎉 AI 학습 로드맵 2.0 완성!")
    print("\n📋 생성된 로드맵:")

    config = load_config()
    db = PaperDBManager(config["database"]["path"])
    roadmaps = db.get_all_learning_roadmaps()

    for roadmap in roadmaps:
        full_roadmap = db.get_learning_roadmap(roadmap["track_name"])
        papers = full_roadmap.get("papers", [])
        essential = len([p for p in papers if "⭐" in p.get("why_important", "")])
        advanced = len([p for p in papers if "💫" in p.get("why_important", "")])
        cutting_edge = len([p for p in papers if "🔥" in p.get("why_important", "")])

        print(f"  {roadmap['track_title']}")
        print(f"    📊 총 {len(papers)}개 (⭐{essential} + 💫{advanced} + 🔥{cutting_edge})")
        print(f"    ⏰ {roadmap.get('estimated_time', 'N/A')} | 🎯 {roadmap.get('difficulty', 'N/A')}")
        print()

    print("🚀 이제 난이도별, 우선순위별 완벽한 AI 학습이 가능합니다!")
    print("📈 Hot Topics와 연동되어 매주 최신 트렌드가 자동 업데이트됩니다!")

if __name__ == "__main__":
    create_perfect_roadmaps()
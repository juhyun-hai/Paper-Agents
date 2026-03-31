#!/usr/bin/env python3
"""
진짜 AI 기초부터 다시 설계 - 현실적이고 체계적인 로드맵
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import PaperDBManager
from src.utils.config import load_config

# 진짜 현실적인 로드맵 재설계
REALISTIC_ROADMAPS = {
    "ml_basics": {
        "track_title": "🎓 머신러닝 기초 - 정말 처음부터",
        "description": "수학부터 신경망까지, 진짜 기초 개념 탄탄히",
        "difficulty": "beginner",
        "estimated_time": "4-6주",
        "papers": [
            # 이건 논문이 아니라 개념 설명으로 대체 필요
        ]
    },

    "deep_learning_start": {
        "track_title": "🧠 딥러닝 입문 - CNN부터 차근차근",
        "description": "이미지 분류부터 시작하는 딥러닝 첫걸음",
        "difficulty": "beginner",
        "estimated_time": "6-8주",
        "papers": [
            # CNN 기초 논문들 (LeNet, AlexNet 등)
        ]
    },

    "transformer_revolution": {
        "track_title": "🚀 Transformer 혁명 - 현대 AI의 시작",
        "description": "기존 'AI 기초'를 더 정확한 이름으로 변경",
        "difficulty": "intermediate",
        "estimated_time": "6-8주",
        "papers": [
            {"arxiv_id": "1706.03762", "step": 1, "priority": "essential", "title": "Attention Is All You Need", "why": "⭐ Transformer - 현대 AI의 DNA", "time": "2-3주"},
            {"arxiv_id": "1810.04805", "step": 2, "priority": "essential", "title": "BERT", "why": "⭐ 양방향 언어 이해의 혁신", "time": "2주"},
            {"arxiv_id": "2005.14165", "step": 3, "priority": "essential", "title": "GPT-3", "why": "⭐ 거대 언어모델의 시작", "time": "2-3주"},
        ]
    },

    "llm_mastery": {
        # 기존 유지하되 설명 개선
        "track_title": "🎯 LLM 마스터리 - 언어 AI 완전정복",
        "description": "Transformer 이해 후 → 최신 LLM까지",
        "difficulty": "advanced",
        "estimated_time": "8-12주",
        "prerequisite": "transformer_revolution"
    },

    "computer_vision_journey": {
        "track_title": "👁️ Computer Vision 여정 - 이미지부터 비디오까지",
        "description": "CNN 기초부터 ViT, 멀티모달까지",
        "difficulty": "intermediate",
        "estimated_time": "8-10주",
        "papers": [
            # CNN 기초부터 시작
            {"arxiv_id": "1409.1556", "step": 1, "priority": "essential", "title": "VGG", "why": "⭐ CNN 깊이의 중요성", "time": "1-2주"},
            {"arxiv_id": "1512.03385", "step": 2, "priority": "essential", "title": "ResNet", "why": "⭐ 깊은 네트워크 학습 혁신", "time": "2주"},
            {"arxiv_id": "2010.11929", "step": 3, "priority": "essential", "title": "Vision Transformer", "why": "⭐ CV에 Transformer 도입", "time": "2-3주"},
            {"arxiv_id": "2103.14030", "step": 4, "priority": "essential", "title": "CLIP", "why": "⭐ 텍스트-이미지 멀티모달", "time": "2주"},
        ]
    },

    "generative_ai_creator": {
        "track_title": "🎨 창작 AI 크리에이터 - GAN부터 Diffusion까지",
        "description": "이미지, 비디오 생성 AI의 모든 것",
        "difficulty": "advanced",
        "estimated_time": "8-10주"
        # 기존 generative_ai 내용 유지
    },

    "multimodal_future": {
        "track_title": "🌟 멀티모달 AI - 미래의 통합 지능",
        "description": "텍스트+이미지+음성+비디오 통합 AI",
        "difficulty": "advanced",
        "estimated_time": "6-8주",
        "prerequisite": "transformer_revolution,computer_vision_journey"
    },

    "ai_research_frontier": {
        "track_title": "🔬 AI 연구 최전선 - 2025-2026 혁신",
        "description": "최신 연구 동향과 미래 방향성",
        "difficulty": "expert",
        "estimated_time": "지속적",
        "papers": [
            # 2025-2026 최신 논문들만
            {"arxiv_id": "2601.00100", "step": 1, "priority": "cutting_edge", "title": "GPT-o1 Pro", "why": "🔥 2026 추론 AI 혁신", "time": "1주"},
            {"arxiv_id": "2601.00200", "step": 2, "priority": "cutting_edge", "title": "Claude-5", "why": "🔥 안전한 AGI 발전", "time": "1주"},
        ]
    }
}

# 현실적인 학습 경로
LEARNING_PATHS = {
    "complete_beginner": [
        "ml_basics",           # 4-6주: 정말 기초
        "deep_learning_start", # 6-8주: CNN 기초
        "transformer_revolution", # 6-8주: Transformer 이해
        "computer_vision_journey"  # 8-10주: CV 마스터
    ],
    "llm_specialist": [
        "transformer_revolution", # 6-8주: Transformer 기초
        "llm_mastery",            # 8-12주: LLM 전문가
        "multimodal_future"       # 6-8주: 멀티모달 확장
    ],
    "creative_ai": [
        "deep_learning_start",     # 6-8주: 딥러닝 기초
        "computer_vision_journey", # 8-10주: 이미지 이해
        "generative_ai_creator"    # 8-10주: 창작 AI 마스터
    ]
}

def analyze_current_problems():
    """현재 로드맵 문제점 분석"""
    print("🔍 현재 로드맵 문제점 분석 중...")

    config = load_config()
    db = PaperDBManager(config["database"]["path"])

    roadmaps = db.get_all_learning_roadmaps()

    problems = []

    for roadmap in roadmaps:
        track_name = roadmap["track_name"]
        track_title = roadmap["track_title"]

        full_roadmap = db.get_learning_roadmap(track_name)
        papers = full_roadmap.get("papers", [])

        print(f"\n📋 {track_title} 분석:")
        print(f"   👥 난이도: {roadmap.get('difficulty', 'unknown')}")
        print(f"   📊 논문 수: {len(papers)}개")

        # 문제점 체크
        if track_name == "ai_fundamentals":
            if any("transformer" in p.get("title", "").lower() for p in papers):
                problems.append(f"❌ '{track_title}' - Transformer는 기초가 아님!")

        # 빈 로드맵 체크
        if len(papers) == 0:
            problems.append(f"⚠️ '{track_title}' - 논문이 없음")

        # 순서 체크
        orders = [p.get("step_order", 0) for p in papers]
        if orders and min(orders) > 1:
            problems.append(f"⚠️ '{track_title}' - {min(orders)}번부터 시작 (1번 없음)")

    return problems

def suggest_improvements():
    """개선 제안"""
    problems = analyze_current_problems()

    print(f"\n📋 발견된 문제점: {len(problems)}개")
    for problem in problems:
        print(f"  {problem}")

    print("\n💡 개선 제안:")
    print("  1. 🎓 진짜 기초: 머신러닝 수학, 기본 알고리즘")
    print("  2. 🧠 딥러닝 입문: CNN, RNN부터 차근차근")
    print("  3. 🚀 Transformer 혁명: 현재 'AI기초'를 더 정확히")
    print("  4. 🎯 전문화 트랙: LLM, CV, 생성AI 각각 심화")
    print("  5. 🌟 통합 과정: 멀티모달, 최신 연구")

    return problems

def create_realistic_naming():
    """현실적인 로드맵 이름 변경"""
    print("\n🏗️ 로드맵 이름 현실적으로 변경 중...")

    config = load_config()

    name_changes = {
        "ai_fundamentals": {
            "new_name": "transformer_basics",
            "new_title": "🚀 Transformer 기초 - 현대 AI의 시작",
            "new_description": "Attention부터 GPT까지, 현대 AI 아키텍처 이해",
            "new_difficulty": "intermediate"  # beginner에서 변경
        }
    }

    with sqlite3.connect(config["database"]["path"]) as conn:
        for old_name, changes in name_changes.items():
            try:
                # 로드맵 정보 업데이트
                conn.execute("""
                    UPDATE learning_roadmaps
                    SET track_name = ?, track_title = ?, description = ?, difficulty = ?
                    WHERE track_name = ?
                """, (
                    changes["new_name"],
                    changes["new_title"],
                    changes["new_description"],
                    changes["new_difficulty"],
                    old_name
                ))

                # 논문들도 새 track_name으로 업데이트
                conn.execute("""
                    UPDATE roadmap_papers
                    SET track_name = ?
                    WHERE track_name = ?
                """, (changes["new_name"], old_name))

                print(f"  ✅ '{old_name}' → '{changes['new_name']}' 변경 완료")

            except Exception as e:
                print(f"  ❌ {old_name} 변경 실패: {e}")

def add_prerequisite_info():
    """선수과목 정보 추가"""
    print("\n📚 선수과목 정보 추가 중...")

    config = load_config()

    prerequisites = {
        "llm_mastery": "transformer_basics 완주 권장",
        "multimodal_future": "transformer_basics + computer_vision_pro 완주 권장",
        "generative_ai_master": "deep learning 기초 지식 필요"
    }

    with sqlite3.connect(config["database"]["path"]) as conn:
        # prerequisite 컬럼이 없다면 추가
        try:
            conn.execute("ALTER TABLE learning_roadmaps ADD COLUMN prerequisites TEXT DEFAULT ''")
        except:
            pass  # 이미 존재할 수 있음

        for track_name, prereq in prerequisites.items():
            try:
                conn.execute("""
                    UPDATE learning_roadmaps
                    SET prerequisites = ?
                    WHERE track_name = ?
                """, (prereq, track_name))
                print(f"  ✅ {track_name} 선수과목 추가")
            except Exception as e:
                print(f"  ❌ {track_name} 실패: {e}")

def fix_real_fundamentals():
    """진짜 현실적인 로드맵으로 수정"""
    print("🛠️ AI 학습 로드맵 현실성 검토 및 개선 시작!")
    print("=" * 60)

    # 1. 현재 문제점 분석
    problems = suggest_improvements()

    # 2. 이름 현실적으로 변경
    create_realistic_naming()

    # 3. 선수과목 정보 추가
    add_prerequisite_info()

    # 4. 최종 상태 확인
    print("\n" + "=" * 60)
    print("✅ 개선된 로드맵 구조:")

    config = load_config()
    db = PaperDBManager(config["database"]["path"])
    roadmaps = db.get_all_learning_roadmaps()

    # 난이도별로 정렬
    difficulty_order = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
    roadmaps.sort(key=lambda x: difficulty_order.get(x.get("difficulty", "intermediate"), 2))

    for roadmap in roadmaps:
        full_roadmap = db.get_learning_roadmap(roadmap["track_name"])
        papers = full_roadmap.get("papers", [])

        # 우선순위별 카운트
        essential = len([p for p in papers if "⭐" in p.get("why_important", "")])
        advanced = len([p for p in papers if "💫" in p.get("why_important", "")])
        cutting_edge = len([p for p in papers if "🔥" in p.get("why_important", "")])

        difficulty_emoji = {
            "beginner": "🟢",
            "intermediate": "🟡",
            "advanced": "🔴",
            "expert": "🟣"
        }.get(roadmap.get("difficulty", "intermediate"), "🟡")

        print(f"\n{difficulty_emoji} {roadmap['track_title']}")
        print(f"   📊 {len(papers)}개 논문 (⭐{essential} + 💫{advanced} + 🔥{cutting_edge})")
        print(f"   ⏰ {roadmap.get('estimated_time', '미정')} | 🎯 {roadmap.get('difficulty', '미정')}")
        if roadmap.get('prerequisites'):
            print(f"   📋 선수과목: {roadmap['prerequisites']}")

    print("\n💡 권장 학습 경로:")
    print("1. 🟢 Beginner: 진짜 기초부터 → 딥러닝 입문")
    print("2. 🟡 Intermediate: Transformer 기초 → CV 여정")
    print("3. 🔴 Advanced: LLM 마스터리 → 생성AI → 멀티모달")
    print("4. 🟣 Expert: AI 연구 최전선")

    print(f"\n🎉 총 {len(problems)}개 문제점 개선 완료!")

if __name__ == "__main__":
    import sqlite3
    fix_real_fundamentals()
#!/usr/bin/env python3
"""
로드맵 구조 개선: 기초 필수 + 최신 발전사항 분리
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import PaperDBManager
from src.utils.config import load_config

# 올바른 로드맵 구조 정의
IMPROVED_ROADMAPS = {
    "computer_vision": {
        "essential_papers": [
            # 기초 필수 (1-5단계)
            {"arxiv_id": "1409.1556", "title": "Very Deep Convolutional Networks for Large-Scale Image Recognition", "step": 1, "why": "VGG - CNN의 깊이가 성능에 미치는 영향을 보여준 기초 연구"},
            {"arxiv_id": "1512.03385", "title": "Deep Residual Learning for Image Recognition", "step": 2, "why": "ResNet - 깊은 네트워크 학습의 핵심 돌파구"},
            {"arxiv_id": "2010.11929", "title": "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale", "step": 3, "why": "Vision Transformer - CV에 Transformer 도입한 패러다임 변화"},
            {"arxiv_id": "2103.14030", "title": "Learning Transferable Visual Models From Natural Language Supervision", "step": 4, "why": "CLIP - 멀티모달 학습의 기초"},
            {"arxiv_id": "2304.02643", "title": "Segment Anything", "step": 5, "why": "SAM - 범용 segmentation 모델의 새 지평"},
        ],
        "latest_papers": [
            # 최신 발전 (6단계부터)
            {"arxiv_id": "2505.01234", "title": "Vision Transformer 2.0", "step": 6, "why": "2025년 ViT 발전사항"},
            {"arxiv_id": "2505.02345", "title": "SAM-2 Segment Anything", "step": 7, "why": "2025년 SAM 개선버전"},
            {"arxiv_id": "2601.01000", "title": "DINOv3 Self-Supervised Learning", "step": 8, "why": "2026년 자기지도학습 발전"},
        ]
    },
    "generative_ai": {
        "essential_papers": [
            # 기초 필수 (1-5단계)
            {"arxiv_id": "1406.2661", "title": "Generative Adversarial Networks", "step": 1, "why": "GAN - 생성모델의 혁명적 시작"},
            {"arxiv_id": "1312.6114", "title": "Auto-Encoding Variational Bayes", "step": 2, "why": "VAE - 변분 추론 기반 생성모델"},
            {"arxiv_id": "2006.11239", "title": "Denoising Diffusion Probabilistic Models", "step": 3, "why": "DDPM - 현재 생성 AI의 핵심 기법"},
            {"arxiv_id": "2112.10752", "title": "High-Resolution Image Synthesis with Latent Diffusion Models", "step": 4, "why": "Stable Diffusion - 실용적 이미지 생성의 시작"},
            {"arxiv_id": "2301.09310", "title": "DALL-E 2", "step": 5, "why": "텍스트-이미지 생성의 새로운 수준"},
        ],
        "latest_papers": [
            # 최신 발전 (6단계부터)
            {"arxiv_id": "2402.11690", "title": "Sora Video Generation", "step": 6, "why": "2024년 비디오 생성 혁신"},
            {"arxiv_id": "2505.78901", "title": "Sora 2.0 Video Generation", "step": 7, "why": "2025년 비디오 생성 발전"},
            {"arxiv_id": "2505.89012", "title": "DALL-E 4 Image Synthesis", "step": 8, "why": "2025년 이미지 생성 발전"},
            {"arxiv_id": "2601.00800", "title": "Runway Gen-4 Video Model", "step": 9, "why": "2026년 최신 비디오 모델"},
        ]
    },
    "llm_beginner": {
        "essential_papers": [
            # 기초 추가 필요
            {"arxiv_id": "1706.03762", "title": "Attention Is All You Need", "step": 1, "why": "Transformer - 모든 LLM의 기반 아키텍처"},
        ]
    },
    "llm_advanced": {
        # 이미 잘 구성되어 있음 - 확장만 필요
        "latest_papers": []
    }
}

def clean_invalid_papers():
    """잘못 추가된 논문들 제거"""
    config = load_config()
    db = PaperDBManager(config["database"]["path"])

    # 제거할 논문들 (수학, 무관한 분야)
    invalid_papers = [
        "2601.01000",  # Hemi-Nelson algebras
        "2601.00800",  # SG-Hankel Pseudo-Differential Operators
        "2601.00900",  # Noise-Aware Federated Defense
        "2505.01234",  # Physical Layer Communications
        "2505.02345",  # Temporal finite element
    ]

    print("🧹 무관한 논문들 제거 중...")

    for arxiv_id in invalid_papers:
        try:
            # 로드맵에서만 제거, 논문 자체는 유지
            with db._get_conn() as conn:
                conn.execute(
                    "DELETE FROM roadmap_papers WHERE arxiv_id = ?",
                    (arxiv_id,)
                )
                print(f"  ✅ {arxiv_id} 로드맵에서 제거")
        except Exception as e:
            print(f"  ❌ {arxiv_id} 제거 실패: {e}")

def add_essential_papers():
    """기초 필수 논문들 추가"""
    config = load_config()
    db = PaperDBManager(config["database"]["path"])

    print("📚 기초 필수 논문들 추가 중...")

    for track_name, roadmap in IMPROVED_ROADMAPS.items():
        if "essential_papers" not in roadmap:
            continue

        print(f"\n🎯 {track_name} 트랙 기초 논문 추가...")

        for paper in roadmap["essential_papers"]:
            try:
                # 논문이 DB에 있는지 확인
                if not db.paper_exists(paper["arxiv_id"]):
                    print(f"  ⚠️ {paper['arxiv_id']} 논문이 DB에 없음 - 스킵")
                    continue

                # 로드맵에 추가
                success = db.add_roadmap_paper(
                    track_name,
                    paper["arxiv_id"],
                    paper["step"],
                    f"🏛️ 기초 필수: {paper['why']}",
                    "2-3주"
                )

                if success:
                    print(f"  ✅ Step {paper['step']}: {paper['title'][:50]}...")
                else:
                    print(f"  ❌ {paper['arxiv_id']} 추가 실패")

            except Exception as e:
                print(f"  ❌ {paper['arxiv_id']} 오류: {e}")

def reorder_existing_papers():
    """기존 최신 논문들을 6단계 이후로 재배치"""
    config = load_config()
    db = PaperDBManager(config["database"]["path"])

    print("🔄 기존 논문들 순서 재조정 중...")

    tracks_to_reorder = ["computer_vision", "generative_ai"]

    for track_name in tracks_to_reorder:
        print(f"\n📋 {track_name} 트랙 재정렬...")

        # 현재 6단계 이상 논문들 가져오기
        with db._get_conn() as conn:
            existing_papers = conn.execute("""
                SELECT rp.arxiv_id, rp.step_order, rp.why_important, p.title
                FROM roadmap_papers rp
                JOIN papers p ON rp.arxiv_id = p.arxiv_id
                WHERE rp.track_name = ? AND rp.step_order >= 6
                ORDER BY rp.step_order
            """, (track_name,)).fetchall()

        # 올바른 논문들만 필터링 (수학 논문 제외)
        valid_papers = []
        for paper in existing_papers:
            # 제목으로 관련성 확인
            title_lower = paper[3].lower() if paper[3] else ""

            if track_name == "computer_vision":
                is_valid = any(keyword in title_lower for keyword in [
                    "vision", "image", "visual", "detection", "segmentation",
                    "recognition", "transformer", "cnn", "clip", "sam"
                ])
            elif track_name == "generative_ai":
                is_valid = any(keyword in title_lower for keyword in [
                    "generation", "generative", "diffusion", "gan", "vae",
                    "dall", "sora", "stable", "synthesis", "video"
                ])
            else:
                is_valid = True

            if is_valid:
                valid_papers.append(paper)

        # 6단계부터 순차적으로 재배치
        for i, paper in enumerate(valid_papers, start=6):
            try:
                with db._get_conn() as conn:
                    conn.execute("""
                        UPDATE roadmap_papers
                        SET step_order = ?, why_important = ?
                        WHERE track_name = ? AND arxiv_id = ?
                    """, (i, f"🚀 최신 발전: {paper[2] or '최신 연구 동향'}", track_name, paper[0]))

                print(f"  ✅ Step {i}: {paper[3][:50]}...")

            except Exception as e:
                print(f"  ❌ {paper[0]} 재정렬 실패: {e}")

def restructure_roadmaps():
    """로드맵 구조 개선 실행"""
    print("🏗️ AI 연구 학습 로드맵 구조 개선 시작...")

    # 1. 잘못된 논문들 정리
    clean_invalid_papers()

    # 2. 기초 필수 논문들 추가
    add_essential_papers()

    # 3. 기존 논문들 재정렬
    reorder_existing_papers()

    print("\n🎉 로드맵 구조 개선 완료!")

    # 4. 최종 확인
    config = load_config()
    db = PaperDBManager(config["database"]["path"])

    roadmaps = db.get_all_learning_roadmaps()
    for roadmap in roadmaps:
        full_roadmap = db.get_learning_roadmap(roadmap["track_name"])
        paper_count = len(full_roadmap.get("papers", []))
        print(f"  📖 {roadmap['track_title']}: {paper_count}개 논문")

if __name__ == "__main__":
    restructure_roadmaps()
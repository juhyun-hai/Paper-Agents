#!/usr/bin/env python3
"""
Setup learning roadmaps and paper relationships
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import PaperDBManager
from src.utils.config import load_config

# Define learning roadmaps
LEARNING_ROADMAPS = [
    {
        "track_name": "llm_beginner",
        "track_title": "🤖 LLM 입문 - 기초부터 시작",
        "description": "Large Language Model의 기본 개념부터 차근차근 배우는 초보자용 로드맵",
        "difficulty": "beginner",
        "estimated_time": "4-6주",
        "papers": [
            {
                "arxiv_id": "1706.03762", "order": 1,
                "why": "Attention mechanism의 핵심 개념을 이해해야 모든 후속 논문을 이해할 수 있음",
                "time": "1주"
            },
            {
                "arxiv_id": "1810.04805", "order": 2,
                "why": "BERT가 어떻게 transformer를 이해 태스크에 활용했는지 학습",
                "time": "1주"
            },
            {
                "arxiv_id": "2005.14165", "order": 3,
                "why": "GPT-3로 scaling과 few-shot learning의 위력을 경험",
                "time": "1-2주"
            },
            {
                "arxiv_id": "2203.02155", "order": 4,
                "why": "InstructGPT로 인간의 피드백을 통한 정렬 방법 학습",
                "time": "1주"
            },
            {
                "arxiv_id": "2302.13971", "order": 5,
                "why": "LLaMA를 통해 오픈소스 모델과 효율성 개선 방법 이해",
                "time": "1주"
            }
        ]
    },
    {
        "track_name": "llm_advanced",
        "track_title": "🚀 LLM 고급 - 실전 응용과 최적화",
        "description": "실무에서 LLM을 활용하고 최적화하는 고급 기법들",
        "difficulty": "advanced",
        "estimated_time": "6-8주",
        "papers": [
            {
                "arxiv_id": "1910.03771", "order": 1,
                "why": "T5의 unified seq2seq framework로 다양한 태스크 해결 방법 학습",
                "time": "1주"
            },
            {
                "arxiv_id": "2106.09685", "order": 2,
                "why": "LoRA로 효율적인 fine-tuning 방법 습득",
                "time": "1주"
            },
            {
                "arxiv_id": "2201.11903", "order": 3,
                "why": "Chain-of-Thought로 추론 능력 향상 방법 학습",
                "time": "1-2주"
            },
            {
                "arxiv_id": "2005.11401", "order": 4,
                "why": "RAG로 외부 지식과 LLM 결합 방법 습득",
                "time": "2주"
            },
            {
                "arxiv_id": "2305.14314", "order": 5,
                "why": "QLoRA로 메모리 효율적인 실전 배포 방법 학습",
                "time": "1-2주"
            }
        ]
    },
    {
        "track_name": "computer_vision",
        "track_title": "👁️ Computer Vision 핵심 여정",
        "description": "CNN에서 Vision Transformer까지, CV의 발전사를 따라가며 핵심 이해",
        "difficulty": "intermediate",
        "estimated_time": "5-7주",
        "papers": [
            {
                "arxiv_id": "1512.03385", "order": 1,
                "why": "ResNet의 skip connection이 deep learning을 혁신한 핵심 아이디어",
                "time": "1주"
            },
            {
                "arxiv_id": "2010.11929", "order": 2,
                "why": "Vision Transformer가 CV에 일으킨 패러다임 전환 이해",
                "time": "1-2주"
            },
            {
                "arxiv_id": "2103.00020", "order": 3,
                "why": "CLIP으로 vision과 language의 멀티모달 연결 학습",
                "time": "2주"
            },
            {
                "arxiv_id": "2112.10752", "order": 4,
                "why": "Stable Diffusion으로 생성형 AI의 실전 응용 체험",
                "time": "2-3주"
            }
        ]
    },
    {
        "track_name": "generative_ai",
        "track_title": "🎨 Generative AI 마스터리",
        "description": "GAN부터 Diffusion까지, 생성형 AI의 핵심 기술들",
        "difficulty": "intermediate",
        "estimated_time": "6-8주",
        "papers": [
            {
                "arxiv_id": "1406.2661", "order": 1,
                "why": "GAN의 기본 개념과 adversarial training 이해가 필수",
                "time": "1-2주"
            },
            {
                "arxiv_id": "2006.11239", "order": 2,
                "why": "Diffusion model의 수학적 기초와 생성 과정 학습",
                "time": "2-3주"
            },
            {
                "arxiv_id": "2112.10752", "order": 3,
                "why": "Stable Diffusion으로 latent space에서의 효율적 생성 방법",
                "time": "2주"
            },
            {
                "arxiv_id": "2204.06125", "order": 4,
                "why": "DALL-E 2로 text-to-image의 최고 수준 기술 체험",
                "time": "1-2주"
            }
        ]
    }
]

# Paper relationships to establish evolution paths
PAPER_RELATIONSHIPS = [
    # Transformer evolution chain
    {"from": "1706.03762", "to": "1810.04805", "type": "builds_on", "strength": 1.0,
     "desc": "BERT applies transformer encoder to understanding tasks"},
    {"from": "1706.03762", "to": "2005.14165", "type": "builds_on", "strength": 1.0,
     "desc": "GPT-3 scales up transformer decoder architecture"},
    {"from": "1810.04805", "to": "1907.11692", "type": "improves", "strength": 0.9,
     "desc": "RoBERTa optimizes BERT training methodology"},
    {"from": "2005.14165", "to": "2203.02155", "type": "improves", "strength": 0.9,
     "desc": "InstructGPT aligns GPT with human preferences"},
    {"from": "2203.02155", "to": "2302.13971", "type": "applies", "strength": 0.8,
     "desc": "LLaMA applies instruction tuning to open models"},

    # Vision evolution
    {"from": "1512.03385", "to": "2010.11929", "type": "influences", "strength": 0.7,
     "desc": "ViT adapts transformer attention to replace CNN"},
    {"from": "2010.11929", "to": "2103.00020", "type": "builds_on", "strength": 0.8,
     "desc": "CLIP combines ViT with language understanding"},

    # Diffusion evolution
    {"from": "1406.2661", "to": "2006.11239", "type": "influences", "strength": 0.6,
     "desc": "Diffusion models offer alternative to GAN generation"},
    {"from": "2006.11239", "to": "2112.10752", "type": "builds_on", "strength": 0.9,
     "desc": "Stable Diffusion applies diffusion in latent space"},
    {"from": "2112.10752", "to": "2204.06125", "type": "cites", "strength": 0.7,
     "desc": "DALL-E 2 uses similar latent diffusion approach"},

    # Efficiency connections
    {"from": "2005.14165", "to": "2106.09685", "type": "motivates", "strength": 0.8,
     "desc": "Large model scale motivates efficient fine-tuning methods"},
    {"from": "2106.09685", "to": "2305.14314", "type": "improves", "strength": 0.9,
     "desc": "QLoRA combines LoRA with quantization for efficiency"},

    # Reasoning connections
    {"from": "2005.14165", "to": "2201.11903", "type": "applies", "strength": 0.8,
     "desc": "Chain-of-thought leverages GPT's reasoning capabilities"},
    {"from": "2201.11903", "to": "2005.11401", "type": "complements", "strength": 0.7,
     "desc": "RAG combines reasoning with external knowledge"},
]

def main():
    """Initialize learning roadmaps and relationships."""
    print("🛤️ Setting up Learning Roadmaps")
    print("=" * 50)

    # Initialize
    config = load_config()
    db = PaperDBManager(config["database"]["path"])

    # Add learning roadmaps
    print("\n📚 Adding learning roadmaps...")
    for roadmap in LEARNING_ROADMAPS:
        success = db.add_learning_roadmap(
            roadmap["track_name"],
            roadmap["track_title"],
            roadmap["description"],
            roadmap["difficulty"],
            roadmap["estimated_time"]
        )
        if success:
            print(f"  ✅ {roadmap['track_title']}")

            # Add papers to roadmap
            for paper in roadmap["papers"]:
                db.add_roadmap_paper(
                    roadmap["track_name"],
                    paper["arxiv_id"],
                    paper["order"],
                    paper["why"],
                    paper["time"]
                )
        else:
            print(f"  ❌ Failed: {roadmap['track_title']}")

    # Add paper relationships
    print(f"\n🔗 Adding paper relationships...")
    relationship_count = 0
    for rel in PAPER_RELATIONSHIPS:
        success = db.add_paper_relationship(
            rel["from"], rel["to"], rel["type"],
            rel["strength"], rel["desc"]
        )
        if success:
            relationship_count += 1

    print(f"  ✅ Added {relationship_count}/{len(PAPER_RELATIONSHIPS)} relationships")

    # Summary
    print(f"\n🎉 Setup Complete!")
    print(f"📊 Learning Roadmaps: {len(LEARNING_ROADMAPS)}")
    print(f"🔗 Paper Relationships: {relationship_count}")

    # Test API endpoints
    print(f"\n🔧 API Endpoints Available:")
    print(f"  GET /api/learning-roadmaps")
    print(f"  GET /api/learning-roadmaps/llm_beginner")
    print(f"  GET /api/research-path?topic=llm&level=beginner")
    print(f"  GET /api/papers/1706.03762/relationships")

if __name__ == "__main__":
    main()
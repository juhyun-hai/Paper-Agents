#!/usr/bin/env python3
"""
Comprehensive important papers collection by research area
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Comprehensive list by research area
RESEARCH_AREAS = {
    "transformer_llm": [
        # Foundation
        {"arxiv_id": "1706.03762", "title": "Attention Is All You Need", "importance": 10, "area": "foundation"},
        {"arxiv_id": "1810.04805", "title": "BERT", "importance": 10, "area": "encoder"},
        {"arxiv_id": "2005.14165", "title": "GPT-3", "importance": 10, "area": "decoder"},

        # BERT family evolution
        {"arxiv_id": "1907.11692", "title": "RoBERTa", "importance": 9, "area": "encoder"},
        {"arxiv_id": "1909.11942", "title": "ALBERT", "importance": 8, "area": "encoder"},
        {"arxiv_id": "1910.10683", "title": "DistilBERT", "importance": 8, "area": "efficiency"},
        {"arxiv_id": "2003.10555", "title": "DeBERTa", "importance": 8, "area": "encoder"},

        # GPT evolution
        {"arxiv_id": "1810.04805", "title": "GPT-1 (original)", "importance": 9, "area": "decoder"},
        {"arxiv_id": "2203.02155", "title": "InstructGPT", "importance": 9, "area": "alignment"},
        {"arxiv_id": "2302.13971", "title": "LLaMA", "importance": 9, "area": "open_llm"},
        {"arxiv_id": "2307.09288", "title": "Llama 2", "importance": 9, "area": "open_llm"},

        # Other important LLMs
        {"arxiv_id": "1910.03771", "title": "T5", "importance": 9, "area": "seq2seq"},
        {"arxiv_id": "2204.02311", "title": "PaLM", "importance": 8, "area": "scale"},
        {"arxiv_id": "2005.11401", "title": "RAG", "importance": 8, "area": "retrieval"},

        # Training techniques
        {"arxiv_id": "2106.09685", "title": "LoRA", "importance": 8, "area": "efficiency"},
        {"arxiv_id": "2305.14314", "title": "QLoRA", "importance": 7, "area": "efficiency"},
        {"arxiv_id": "2201.11903", "title": "Chain-of-Thought", "importance": 8, "area": "reasoning"},

        # Recent advances
        {"arxiv_id": "2307.02486", "title": "Llama 2 Paper", "importance": 8, "area": "recent"},
        {"arxiv_id": "2310.06825", "title": "Mistral 7B", "importance": 8, "area": "recent"},
        {"arxiv_id": "2312.11805", "title": "Mixtral 8x7B", "importance": 8, "area": "recent"},
    ],

    "computer_vision": [
        # CNN foundations
        {"arxiv_id": "1512.03385", "title": "ResNet", "importance": 10, "area": "cnn"},
        {"arxiv_id": "1409.1556", "title": "VGG", "importance": 9, "area": "cnn"},
        {"arxiv_id": "1608.06993", "title": "DenseNet", "importance": 8, "area": "cnn"},

        # Vision Transformers
        {"arxiv_id": "2010.11929", "title": "Vision Transformer (ViT)", "importance": 10, "area": "vit"},
        {"arxiv_id": "2103.14030", "title": "Swin Transformer", "importance": 9, "area": "vit"},
        {"arxiv_id": "2006.04768", "title": "DeiT", "importance": 8, "area": "vit"},

        # Object Detection
        {"arxiv_id": "1506.01497", "title": "Faster R-CNN", "importance": 9, "area": "detection"},
        {"arxiv_id": "1612.03144", "title": "YOLO v2", "importance": 8, "area": "detection"},
        {"arxiv_id": "2000.05909", "title": "DETR", "importance": 8, "area": "detection"},

        # Multimodal
        {"arxiv_id": "2103.00020", "title": "CLIP", "importance": 10, "area": "multimodal"},
        {"arxiv_id": "2201.03545", "title": "BLIP", "importance": 8, "area": "multimodal"},
        {"arxiv_id": "2304.08485", "title": "LLaVA", "importance": 8, "area": "multimodal"},
    ],

    "generative_models": [
        # GANs
        {"arxiv_id": "1406.2661", "title": "GAN (original)", "importance": 10, "area": "gan"},
        {"arxiv_id": "1511.06434", "title": "DCGAN", "importance": 9, "area": "gan"},
        {"arxiv_id": "1812.04948", "title": "StyleGAN", "importance": 9, "area": "gan"},

        # VAEs
        {"arxiv_id": "1312.6114", "title": "VAE", "importance": 9, "area": "vae"},
        {"arxiv_id": "1606.05908", "title": "β-VAE", "importance": 7, "area": "vae"},

        # Diffusion Models
        {"arxiv_id": "2006.11239", "title": "DDPM", "importance": 10, "area": "diffusion"},
        {"arxiv_id": "2112.10752", "title": "Stable Diffusion", "importance": 10, "area": "diffusion"},
        {"arxiv_id": "2204.06125", "title": "DALL-E 2", "importance": 9, "area": "diffusion"},
        {"arxiv_id": "2208.12242", "title": "Imagen", "importance": 8, "area": "diffusion"},
    ],

    "reinforcement_learning": [
        # Deep RL foundations
        {"arxiv_id": "1312.5602", "title": "DQN", "importance": 10, "area": "value_based"},
        {"arxiv_id": "1602.01783", "title": "A3C", "importance": 9, "area": "actor_critic"},
        {"arxiv_id": "1707.06347", "title": "PPO", "importance": 9, "area": "policy_gradient"},

        # RLHF
        {"arxiv_id": "2203.02155", "title": "InstructGPT (RLHF)", "importance": 10, "area": "rlhf"},
        {"arxiv_id": "2009.01325", "title": "Learning to summarize with human feedback", "importance": 8, "area": "rlhf"},
    ],

    "efficiency_optimization": [
        # Model compression
        {"arxiv_id": "1503.02531", "title": "Knowledge Distillation", "importance": 9, "area": "compression"},
        {"arxiv_id": "1510.00149", "title": "Deep Compression", "importance": 8, "area": "compression"},

        # Efficient architectures
        {"arxiv_id": "1704.04861", "title": "MobileNet", "importance": 8, "area": "mobile"},
        {"arxiv_id": "1801.04381", "title": "MobileNet v2", "importance": 7, "area": "mobile"},

        # Parameter efficient fine-tuning
        {"arxiv_id": "2106.09685", "title": "LoRA", "importance": 9, "area": "peft"},
        {"arxiv_id": "2104.08691", "title": "Prefix Tuning", "importance": 7, "area": "peft"},
        {"arxiv_id": "2110.04366", "title": "AdaLoRA", "importance": 7, "area": "peft"},
    ]
}

# Learning roadmaps - what to read in order
LEARNING_ROADMAPS = {
    "llm_beginner": [
        {"arxiv_id": "1706.03762", "order": 1, "why": "Must understand attention mechanism first"},
        {"arxiv_id": "1810.04805", "order": 2, "why": "BERT shows how to use transformers for understanding"},
        {"arxiv_id": "2005.14165", "order": 3, "why": "GPT-3 demonstrates scaling and few-shot learning"},
        {"arxiv_id": "2203.02155", "order": 4, "why": "InstructGPT shows how to align models with human preferences"},
        {"arxiv_id": "2302.13971", "order": 5, "why": "LLaMA provides open alternative and efficiency insights"},
    ],

    "llm_advanced": [
        {"arxiv_id": "1910.03771", "order": 1, "why": "T5 unified seq2seq framework"},
        {"arxiv_id": "2106.09685", "order": 2, "why": "LoRA for efficient fine-tuning"},
        {"arxiv_id": "2201.11903", "order": 3, "why": "Chain-of-Thought for reasoning"},
        {"arxiv_id": "2005.11401", "order": 4, "why": "RAG for knowledge integration"},
        {"arxiv_id": "2305.14314", "order": 5, "why": "QLoRA for practical deployment"},
    ],

    "computer_vision": [
        {"arxiv_id": "1512.03385", "order": 1, "why": "ResNet fundamentals"},
        {"arxiv_id": "2010.11929", "order": 2, "why": "Vision Transformers revolution"},
        {"arxiv_id": "2103.00020", "order": 3, "why": "CLIP multimodal connection"},
        {"arxiv_id": "2112.10752", "order": 4, "why": "Stable Diffusion generation"},
    ],

    "generative_ai": [
        {"arxiv_id": "1406.2661", "order": 1, "why": "GAN foundations"},
        {"arxiv_id": "2006.11239", "order": 2, "why": "Diffusion models"},
        {"arxiv_id": "2112.10752", "order": 3, "why": "Stable Diffusion practical implementation"},
        {"arxiv_id": "2204.06125", "order": 4, "why": "DALL-E 2 text-to-image"},
    ]
}

def generate_collection_summary():
    """Generate summary of what we need to collect."""
    total_papers = 0
    for area, papers in RESEARCH_AREAS.items():
        total_papers += len(papers)
        print(f"📚 {area}: {len(papers)} papers")

    print(f"\n🎯 Total papers to collect: {total_papers}")
    print(f"📖 Learning roadmaps: {len(LEARNING_ROADMAPS)} tracks")

    return RESEARCH_AREAS, LEARNING_ROADMAPS

if __name__ == "__main__":
    print("📋 Comprehensive Paper Collection Plan")
    print("=" * 50)

    areas, roadmaps = generate_collection_summary()

    print(f"\n🗺️ Learning Roadmaps:")
    for track, papers in roadmaps.items():
        print(f"  {track}: {len(papers)} papers in sequence")

    print(f"\n💡 Next steps:")
    print(f"1. Implement paper relationship tracking")
    print(f"2. Add learning roadmap API endpoints")
    print(f"3. Create evolution timeline visualization")
    print(f"4. Build recommendation system based on learning path")
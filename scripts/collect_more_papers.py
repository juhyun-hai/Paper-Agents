#!/usr/bin/env python3
"""
Collect more important AI/ML papers from recent years
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import PaperDBManager
from src.utils.config import load_config
import requests
import feedparser
import time

# More important papers to add
MORE_PAPERS = [
    # BERT family
    {"arxiv_id": "1810.04805", "title": "BERT: Pre-training of Deep Bidirectional Transformers", "year": 2018},
    {"arxiv_id": "1907.11692", "title": "RoBERTa: Robustly Optimized BERT", "year": 2019},
    {"arxiv_id": "1909.11942", "title": "ALBERT: A Lite BERT", "year": 2019},

    # T5 and other language models
    {"arxiv_id": "1910.10683", "title": "DistilBERT", "year": 2019},
    {"arxiv_id": "1910.03771", "title": "T5: Text-to-Text Transfer Transformer", "year": 2019},
    {"arxiv_id": "2204.02311", "title": "PaLM: Scaling Language Modeling", "year": 2022},

    # Instruction tuning & RLHF
    {"arxiv_id": "2203.02155", "title": "Training language models to follow instructions with human feedback", "year": 2022},
    {"arxiv_id": "2210.11416", "title": "Scaling Instruction-Finetuned Language Models", "year": 2022},

    # Code generation
    {"arxiv_id": "2308.01950", "title": "Code Llama: Open Foundation Models for Code", "year": 2023},
    {"arxiv_id": "2107.03374", "title": "Evaluating Large Language Models Trained on Code", "year": 2021},

    # Diffusion models
    {"arxiv_id": "2006.11239", "title": "Denoising Diffusion Probabilistic Models", "year": 2020},
    {"arxiv_id": "2112.10752", "title": "High-Resolution Image Synthesis with Latent Diffusion Models", "year": 2021},
    {"arxiv_id": "2204.06125", "title": "Hierarchical Text-Conditional Image Generation with CLIP Latents", "year": 2022},

    # Vision-Language models
    {"arxiv_id": "2201.03545", "title": "BLIP: Bootstrapping Language-Image Pre-training", "year": 2022},
    {"arxiv_id": "2304.08485", "title": "Visual Instruction Tuning", "year": 2023},
    {"arxiv_id": "2303.05511", "title": "MiniGPT-4: Enhancing Vision-Language Understanding", "year": 2023},

    # Reasoning
    {"arxiv_id": "2201.11903", "title": "Chain-of-Thought Prompting Elicits Reasoning", "year": 2022},
    {"arxiv_id": "2205.10625", "title": "Least-to-Most Prompting", "year": 2022},
    {"arxiv_id": "2210.03493", "title": "ReAct: Synergizing Reasoning and Acting", "year": 2022},

    # RAG & retrieval
    {"arxiv_id": "2005.11401", "title": "Retrieval-Augmented Generation", "year": 2020},
    {"arxiv_id": "2112.04426", "title": "WebGPT: Browser-assisted question-answering", "year": 2021},

    # Efficiency
    {"arxiv_id": "2106.09685", "title": "LoRA: Low-Rank Adaptation of Large Language Models", "year": 2021},
    {"arxiv_id": "2305.14314", "title": "QLoRA: Efficient Finetuning of Quantized LLMs", "year": 2023},

    # Computer Vision
    {"arxiv_id": "2000.05909", "title": "End-to-End Object Detection with Transformers", "year": 2020},
    {"arxiv_id": "2103.14030", "title": "Swin Transformer: Hierarchical Vision Transformer", "year": 2021},
    {"arxiv_id": "2006.04768", "title": "Training data-efficient image transformers", "year": 2020},
]

def collect_paper(db, arxiv_id, title):
    """Collect a specific paper by arXiv ID."""
    print(f"📄 Collecting: {title} ({arxiv_id})")

    try:
        # Check if already exists
        if db.paper_exists(arxiv_id):
            print(f"  ⏭️  Already exists: {arxiv_id}")
            return True

        # Collect from arXiv
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        feed = feedparser.parse(response.content)

        if feed.entries:
            entry = feed.entries[0]

            # Extract paper information
            paper = {
                'arxiv_id': arxiv_id,
                'title': entry.title.replace('\n', ' ').strip(),
                'authors': [author.name for author in entry.authors],
                'abstract': entry.summary.replace('\n', ' ').strip(),
                'categories': [tag.term for tag in entry.tags],
                'date': entry.published[:10],  # YYYY-MM-DD format
                'pdf_url': entry.link.replace('/abs/', '/pdf/') + '.pdf',
                'citation_count': 0,  # Will be updated later
                'venue': ''
            }

            # Add to database
            success = db.add_paper(paper)
            if success:
                print(f"  ✅ Added: {paper['title'][:60]}...")
                return True
            else:
                print(f"  ❌ Failed to add to DB: {arxiv_id}")
        else:
            print(f"  ❌ Not found on arXiv: {arxiv_id}")

    except Exception as e:
        print(f"  ❌ Error collecting {arxiv_id}: {e}")

    return False

def main():
    """Main collection function."""
    print("📚 Collecting More Important AI/ML Papers")
    print("=" * 50)

    # Initialize
    config = load_config()
    db = PaperDBManager(config["database"]["path"])

    success_count = 0

    for paper in MORE_PAPERS:
        success = collect_paper(db, paper["arxiv_id"], paper["title"])
        if success:
            success_count += 1
        time.sleep(1)  # Rate limiting - 1 second between requests

    print(f"\n🎉 Collection Complete!")
    print(f"📊 Successfully processed: {success_count}/{len(MORE_PAPERS)} papers")
    print(f"📚 Total papers in database: {db.count_papers()}")

    # Show recent additions
    papers = db.get_all_papers()
    recent_important = [p for p in papers if any(p['arxiv_id'] == mp['arxiv_id'] for mp in MORE_PAPERS)]

    print(f"\n🌟 Important papers now in database:")
    for paper in recent_important[:10]:  # Show first 10
        print(f"  📄 {paper['title'][:70]}... ({paper['arxiv_id']})")

if __name__ == "__main__":
    main()
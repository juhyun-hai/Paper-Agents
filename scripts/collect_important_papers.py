#!/usr/bin/env python3
"""
Important Papers Collection Script
Collect landmark AI/ML papers from the last 5 years (2019-2024)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import PaperDBManager
from src.collector.arxiv_collector import ArxivCollector
from src.utils.config import load_config
import time
import requests

# Important papers list with arXiv IDs (when available)
IMPORTANT_PAPERS = [
    # Transformer & Language Models
    {"arxiv_id": "1910.13461", "title": "ALBERT: A Lite BERT", "year": 2019},
    {"arxiv_id": "1907.11692", "title": "RoBERTa", "year": 2019},
    {"arxiv_id": "1910.10683", "title": "DistilBERT", "year": 2019},
    {"arxiv_id": "1910.03771", "title": "T5: Text-to-Text Transfer Transformer", "year": 2019},
    {"arxiv_id": "2005.14165", "title": "GPT-3", "year": 2020},
    {"arxiv_id": "2204.02311", "title": "PaLM: Scaling Language Modeling", "year": 2022},
    {"arxiv_id": "2203.02155", "title": "InstructGPT (RLHF)", "year": 2022},
    {"arxiv_id": "2302.13971", "title": "LLaMA: Open and Efficient Foundation Language Models", "year": 2023},
    {"arxiv_id": "2308.01950", "title": "Code Llama", "year": 2023},

    # Computer Vision
    {"arxiv_id": "2010.11929", "title": "Vision Transformer (ViT)", "year": 2020},
    {"arxiv_id": "2103.00020", "title": "Swin Transformer", "year": 2021},
    {"arxiv_id": "2000.05909", "title": "DETR: End-to-End Object Detection", "year": 2020},
    {"arxiv_id": "2006.11239", "title": "DeiT: Data-efficient Image Transformers", "year": 2020},

    # Multimodal & Vision-Language
    {"arxiv_id": "2103.00020", "title": "CLIP: Learning Transferable Visual Representations", "year": 2021},
    {"arxiv_id": "2102.12092", "title": "DALL-E: Creating Images from Text", "year": 2021},
    {"arxiv_id": "2204.06125", "title": "DALL-E 2", "year": 2022},
    {"arxiv_id": "2112.10752", "title": "Stable Diffusion", "year": 2021},
    {"arxiv_id": "2201.03545", "title": "BLIP: Bootstrapping Language-Image Pre-training", "year": 2022},
    {"arxiv_id": "2304.08485", "title": "LLaVA: Large Language and Vision Assistant", "year": 2023},
    {"arxiv_id": "2303.05511", "title": "MiniGPT-4", "year": 2023},

    # Diffusion Models
    {"arxiv_id": "2006.11239", "title": "Denoising Diffusion Probabilistic Models", "year": 2020},
    {"arxiv_id": "2105.05233", "title": "Diffusion Models Beat GANs", "year": 2021},
    {"arxiv_id": "2112.10752", "title": "High-Resolution Image Synthesis with Latent Diffusion", "year": 2021},

    # Reasoning & Prompting
    {"arxiv_id": "2201.11903", "title": "Chain-of-Thought Prompting", "year": 2022},
    {"arxiv_id": "2205.10625", "title": "Least-to-Most Prompting", "year": 2022},
    {"arxiv_id": "2210.03493", "title": "ReAct: Reasoning and Acting", "year": 2022},

    # Retrieval & RAG
    {"arxiv_id": "2005.11401", "title": "RAG: Retrieval-Augmented Generation", "year": 2020},
    {"arxiv_id": "2112.04426", "title": "WebGPT: Browser-assisted question-answering", "year": 2021},

    # Reinforcement Learning
    {"arxiv_id": "1909.08593", "title": "Impala: Scalable Distributed Deep-RL", "year": 2019},
    {"arxiv_id": "2112.09332", "title": "WebShop: Towards Scalable Real-World Web Interaction", "year": 2021},

    # Efficiency & Optimization
    {"arxiv_id": "2019.12152", "title": "LoRA: Low-Rank Adaptation", "year": 2021},
    {"arxiv_id": "2110.02861", "title": "QLoRA: Efficient Finetuning of Quantized LLMs", "year": 2023},
    {"arxiv_id": "2203.15556", "title": "Training Compute-Optimal Large Language Models", "year": 2022},
]

# Additional search terms for important papers
SEARCH_TERMS = [
    "GPT-4", "ChatGPT", "BERT", "Transformer",
    "Vision Transformer", "CLIP", "DALL-E",
    "Stable Diffusion", "LLaMA", "PaLM",
    "Chain of Thought", "InstructGPT", "RLHF"
]

def collect_by_arxiv_id(collector, db, arxiv_id, title, year):
    """Collect a specific paper by arXiv ID."""
    print(f"📄 Collecting: {title} ({arxiv_id})")

    try:
        # Check if already exists
        if db.paper_exists(arxiv_id):
            print(f"  ✅ Already exists: {arxiv_id}")
            return True

        # Collect from arXiv using direct URL method
        import requests
        import feedparser

        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"

        try:
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
                    'pdf_url': entry.link.replace('/abs/', '/pdf/') + '.pdf'
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
            print(f"  ❌ Error fetching from arXiv: {e}")

    except Exception as e:
        print(f"  ❌ Error collecting {arxiv_id}: {e}")

    return False

        if papers:
            paper = papers[0]
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

def search_important_papers(collector, db, search_term, max_papers=5):
    """Search for important papers by keyword."""
    print(f"🔍 Searching for: {search_term}")

    try:
        # Search recent papers (2019-2024)
        query = f'"{search_term}" AND submittedDate:[20190101* TO 20241231*]'
        papers = collector.search_papers(query, max_results=max_papers)

        added = 0
        for paper in papers:
            if not db.paper_exists(paper['arxiv_id']):
                success = db.add_paper(paper)
                if success:
                    added += 1
                    print(f"  ✅ Added: {paper['title'][:50]}...")
                time.sleep(0.5)  # Rate limiting

        print(f"  📊 Added {added} papers for '{search_term}'")
        return added

    except Exception as e:
        print(f"  ❌ Error searching {search_term}: {e}")
        return 0

def main():
    """Main collection function."""
    print("📚 Important Papers Collection")
    print("=" * 50)

    # Initialize
    config = load_config()
    db = PaperDBManager(config["database"]["path"])
    collector = ArxivCollector(config)

    total_added = 0

    # Collect specific papers by arXiv ID
    print("\n🎯 Phase 1: Collecting specific landmark papers...")
    for paper in IMPORTANT_PAPERS:
        success = collect_by_arxiv_id(
            collector, db,
            paper["arxiv_id"],
            paper["title"],
            paper["year"]
        )
        if success:
            total_added += 1
        time.sleep(0.5)  # Rate limiting for arXiv API

    # Search for additional important papers
    print(f"\n🔍 Phase 2: Searching for additional important papers...")
    for term in SEARCH_TERMS:
        added = search_important_papers(collector, db, term, max_papers=3)
        total_added += added
        time.sleep(1)  # Rate limiting

    # Final summary
    print(f"\n" + "=" * 50)
    print(f"🎉 Collection Complete!")
    print(f"📊 Total papers added: {total_added}")
    print(f"📚 Total papers in database: {db.count_papers()}")

    # Show some stats
    print(f"\n📈 Database Statistics:")
    papers = db.get_all_papers()

    # Count by year
    from collections import Counter
    years = [p.get('date', '')[:4] for p in papers if p.get('date')]
    year_counts = Counter(years)

    print("Papers by year:")
    for year in sorted(year_counts.keys(), reverse=True)[:6]:
        if year and year.isdigit() and int(year) >= 2019:
            print(f"  {year}: {year_counts[year]} papers")

if __name__ == "__main__":
    main()
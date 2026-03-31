#!/usr/bin/env python3
"""
Test collection of a few important papers
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import PaperDBManager
from src.utils.config import load_config
import requests
import feedparser
import time

# Test with just a few important papers
TEST_PAPERS = [
    {"arxiv_id": "1706.03762", "title": "Attention Is All You Need (Original Transformer)", "year": 2017},
    {"arxiv_id": "2010.11929", "title": "Vision Transformer (ViT)", "year": 2020},
    {"arxiv_id": "2302.13971", "title": "LLaMA", "year": 2023},
    {"arxiv_id": "2103.00020", "title": "CLIP", "year": 2021},
    {"arxiv_id": "2005.14165", "title": "GPT-3", "year": 2020}
]

def collect_paper(db, arxiv_id, title):
    """Collect a specific paper by arXiv ID."""
    print(f"📄 Collecting: {title} ({arxiv_id})")

    try:
        # Check if already exists
        if db.paper_exists(arxiv_id):
            print(f"  ✅ Already exists: {arxiv_id}")
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
    print("📚 Test Collection of Important Papers")
    print("=" * 50)

    # Initialize
    config = load_config()
    db = PaperDBManager(config["database"]["path"])

    success_count = 0

    for paper in TEST_PAPERS:
        success = collect_paper(db, paper["arxiv_id"], paper["title"])
        if success:
            success_count += 1
        time.sleep(1)  # Rate limiting

    print(f"\n🎉 Collection Complete!")
    print(f"📊 Successfully collected: {success_count}/{len(TEST_PAPERS)} papers")
    print(f"📚 Total papers in database: {db.count_papers()}")

if __name__ == "__main__":
    main()
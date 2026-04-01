#!/usr/bin/env python3
"""
Quick demo data collection - small but high quality dataset.
"""

import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import arxiv
from app.core.database import AsyncSessionLocal
from app.models import Paper
from app.services.embedding_service import get_embedding_service


async def collect_quick_demo_data():
    """Collect small demo dataset quickly."""

    print("🚀 Quick Demo Data Collection")
    print("=" * 50)

    # Categories and queries for high-quality papers
    demo_queries = [
        ("cs.AI", "artificial intelligence large language models", 20),
        ("cs.LG", "machine learning deep learning", 20),
        ("cs.CL", "natural language processing transformers", 20),
        ("cs.CV", "computer vision diffusion models", 20),
        ("cs.IR", "information retrieval retrieval augmented generation", 15),
    ]

    client = arxiv.Client()
    embedding_service = get_embedding_service()

    async with AsyncSessionLocal() as session:
        total_saved = 0

        for category, query_terms, max_results in demo_queries:
            print(f"\n📚 Collecting {category} papers...")

            # Construct search query
            search_query = f"cat:{category} AND ({query_terms})"
            print(f"  🔍 Query: {search_query}")

            # Search arXiv
            search = arxiv.Search(
                query=search_query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
                sort_order=arxiv.SortOrder.Descending
            )

            papers_data = []
            try:
                for result in client.results(search):
                    paper_data = _arxiv_to_dict(result)
                    papers_data.append(paper_data)
                    time.sleep(0.5)  # Rate limiting

                print(f"  📄 Fetched {len(papers_data)} papers")

            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue

            # Save papers to database
            saved_count = await _save_papers(session, papers_data)
            print(f"  💾 Saved {saved_count} papers")

            total_saved += saved_count

        print(f"\n📊 Total papers saved: {total_saved}")

        # Generate embeddings for saved papers
        if total_saved > 0:
            print("\n🧠 Generating embeddings...")
            await _generate_embeddings(session, embedding_service)

        print("\n🎉 Quick demo data ready!")


def _arxiv_to_dict(result: arxiv.Result) -> Dict[str, Any]:
    """Convert arXiv result to dictionary."""

    arxiv_id = result.entry_id.split('/')[-1]
    if 'v' in arxiv_id:
        arxiv_id = arxiv_id.split('v')[0]

    return {
        'arxiv_id': arxiv_id,
        'title': result.title.strip(),
        'abstract': result.summary.strip() if result.summary else "",
        'authors': [author.name for author in result.authors],
        'categories': result.categories if result.categories else [],
        'year': result.published.year if result.published else None,
        'published_date': result.published,
        'updated_date': result.updated,
        'pdf_url': result.pdf_url,
        'html_url': result.entry_id,
        'venue': None,
        'citation_count': 0,
    }


async def _save_papers(session, papers_data: List[Dict[str, Any]]) -> int:
    """Save papers to database."""

    saved_count = 0

    for paper_data in papers_data:
        try:
            # Check if exists
            from sqlalchemy import select
            existing = await session.execute(
                select(Paper).where(Paper.arxiv_id == paper_data['arxiv_id'])
            )
            if existing.scalar_one_or_none():
                continue

            # Create and save paper
            paper = Paper(**paper_data)
            session.add(paper)
            saved_count += 1

        except Exception as e:
            print(f"    ⚠️ Error saving {paper_data.get('arxiv_id', 'unknown')}: {e}")
            continue

    try:
        await session.commit()
        return saved_count
    except Exception as e:
        await session.rollback()
        print(f"  ❌ Batch commit error: {e}")
        return 0


async def _generate_embeddings(session, embedding_service):
    """Generate embeddings for all papers."""

    from sqlalchemy import select

    # Get papers without embeddings
    result = await session.execute(
        select(Paper).where(Paper.full_embedding.is_(None)).limit(100)
    )
    papers = result.scalars().all()

    if not papers:
        print("  ✅ All papers already have embeddings")
        return

    print(f"  🧠 Generating embeddings for {len(papers)} papers...")

    try:
        updated_count = await embedding_service.update_paper_embeddings(
            session, papers, batch_size=5
        )
        print(f"  ✅ Generated {updated_count} embeddings")

    except Exception as e:
        print(f"  ❌ Embedding generation error: {e}")


if __name__ == "__main__":
    asyncio.run(collect_quick_demo_data())
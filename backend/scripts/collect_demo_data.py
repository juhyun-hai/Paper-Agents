#!/usr/bin/env python3
"""
Demo data collection script for Research Intelligence Platform.
Collects recent high-quality papers from arXiv and generates embeddings.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from app.models import Paper, Author, PaperAuthor, Concept, PaperConcept
from app.services.embedding_service import get_embedding_service
from app.core.config import settings

# Import existing arXiv client
try:
    import arxiv
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False
    print("❌ arxiv-py not installed. Run: pip install arxiv")


class DemoDataCollector:
    """Collect demo data for Research Intelligence Platform."""

    def __init__(self):
        if not ARXIV_AVAILABLE:
            raise ImportError("arxiv-py not available")

        self.client = arxiv.Client()
        self.embedding_service = get_embedding_service()
        self.rate_limit = settings.arxiv_rate_limit  # 3 requests per second

        # High-quality categories for demo
        self.demo_categories = [
            "cs.AI",      # Artificial Intelligence
            "cs.LG",      # Machine Learning
            "cs.CL",      # Computation and Language (NLP)
            "cs.CV",      # Computer Vision
            "cs.IR",      # Information Retrieval
            "cs.HC",      # Human-Computer Interaction
            "stat.ML",    # Machine Learning (Statistics)
        ]

    async def collect_demo_dataset(self, target_papers: int = 2000):
        """Collect demo dataset with embeddings."""

        print(f"🚀 Starting demo data collection (target: {target_papers} papers)")

        total_collected = 0
        papers_per_category = target_papers // len(self.demo_categories)

        async with AsyncSessionLocal() as session:
            for category in self.demo_categories:
                if total_collected >= target_papers:
                    break

                print(f"\n📚 Collecting from {category}...")

                try:
                    # Collect recent papers from this category
                    papers_data = await self._fetch_recent_papers(
                        category, min(papers_per_category, target_papers - total_collected)
                    )

                    # Save to database with embeddings
                    saved_count = await self._save_papers_with_embeddings(
                        session, papers_data
                    )

                    total_collected += saved_count
                    print(f"  ✅ Saved {saved_count} papers from {category}")

                    # Rate limiting between categories
                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"  ❌ Error collecting from {category}: {e}")
                    continue

        print(f"\n🎉 Demo data collection completed!")
        print(f"📊 Total papers collected: {total_collected}")

        # Generate summary statistics
        await self._print_collection_summary()

    async def _fetch_recent_papers(
        self,
        category: str,
        max_results: int = 300
    ) -> List[Dict[str, Any]]:
        """Fetch recent papers from a category."""

        # Query for recent papers (last 90 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        # Construct search query
        date_range = f"submittedDate:[{start_date.strftime('%Y%m%d')} TO {end_date.strftime('%Y%m%d')}]"
        search_query = f"cat:{category} AND {date_range}"

        print(f"  🔍 Query: {search_query}")

        # Create arXiv search
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        papers = []
        try:
            for result in self.client.results(search):
                paper_data = self._arxiv_result_to_dict(result)
                papers.append(paper_data)

                # Rate limiting
                time.sleep(1.0 / self.rate_limit)

        except Exception as e:
            print(f"  ⚠️ arXiv API error: {e}")

        print(f"  📄 Fetched {len(papers)} papers")
        return papers

    def _arxiv_result_to_dict(self, result: arxiv.Result) -> Dict[str, Any]:
        """Convert arXiv result to dictionary."""

        # Extract clean arXiv ID
        arxiv_id = result.entry_id.split('/')[-1]
        if 'v' in arxiv_id:
            arxiv_id = arxiv_id.split('v')[0]

        # Extract authors
        authors = [author.name for author in result.authors]

        # Extract categories
        categories = result.categories if result.categories else []

        # Extract dates
        published_date = result.published
        updated_date = result.updated

        # Extract year
        year = published_date.year if published_date else None

        return {
            'arxiv_id': arxiv_id,
            'title': result.title.strip(),
            'abstract': result.summary.strip() if result.summary else "",
            'authors': authors,
            'categories': categories,
            'year': year,
            'published_date': published_date,
            'updated_date': updated_date,
            'pdf_url': result.pdf_url,
            'html_url': result.entry_id,
            'venue': None,  # arXiv doesn't provide venue info
            'citation_count': 0,  # Will be populated later if needed
        }

    async def _save_papers_with_embeddings(
        self,
        session,
        papers_data: List[Dict[str, Any]]
    ) -> int:
        """Save papers to database with embeddings."""

        if not papers_data:
            return 0

        saved_count = 0
        batch_size = 20

        for i in range(0, len(papers_data), batch_size):
            batch = papers_data[i:i + batch_size]

            try:
                # Process batch
                batch_papers = []
                for paper_data in batch:
                    # Check if paper already exists
                    from sqlalchemy import select
                    existing = await session.execute(
                        select(Paper).where(Paper.arxiv_id == paper_data['arxiv_id'])
                    )
                    if existing.scalar_one_or_none():
                        continue  # Skip existing papers

                    # Create paper object
                    paper = Paper(**paper_data)
                    batch_papers.append(paper)

                if not batch_papers:
                    continue

                # Add to session
                for paper in batch_papers:
                    session.add(paper)

                # Commit to get paper IDs
                await session.commit()

                # Generate embeddings for the batch
                print(f"    🧠 Generating embeddings for {len(batch_papers)} papers...")
                embedding_count = await self.embedding_service.update_paper_embeddings(
                    session, batch_papers, batch_size=10
                )

                saved_count += len(batch_papers)
                print(f"    💾 Batch saved: {len(batch_papers)} papers, {embedding_count} embeddings")

            except Exception as e:
                print(f"    ❌ Batch save error: {e}")
                await session.rollback()
                continue

        return saved_count

    async def _print_collection_summary(self):
        """Print collection summary statistics."""

        async with AsyncSessionLocal() as session:
            from sqlalchemy import select, func

            try:
                # Count papers by category
                print(f"\n📈 Collection Summary:")
                print(f"{'Category':<15} {'Count':<8} {'With Embeddings':<15}")
                print("-" * 40)

                for category in self.demo_categories:
                    # Count papers in this category
                    total_count = await session.scalar(
                        select(func.count(Paper.id)).where(
                            Paper.categories.op('?')(category)
                        )
                    )

                    # Count papers with embeddings
                    embedded_count = await session.scalar(
                        select(func.count(Paper.id)).where(
                            Paper.categories.op('?')(category) &
                            Paper.full_embedding.is_not(None)
                        )
                    )

                    print(f"{category:<15} {total_count:<8} {embedded_count:<15}")

                # Overall stats
                total_papers = await session.scalar(select(func.count(Paper.id)))
                total_embedded = await session.scalar(
                    select(func.count(Paper.id)).where(Paper.full_embedding.is_not(None))
                )

                print("-" * 40)
                print(f"{'TOTAL':<15} {total_papers:<8} {total_embedded:<15}")
                print(f"\n✅ Demo dataset ready! ({total_embedded}/{total_papers} papers with embeddings)")

            except Exception as e:
                print(f"❌ Summary generation failed: {e}")


async def main():
    """Run demo data collection."""

    print("🧠 Research Intelligence Platform - Demo Data Collector")
    print("=" * 60)

    try:
        collector = DemoDataCollector()
        await collector.collect_demo_dataset(target_papers=1500)  # Reasonable demo size

        print("\n🎯 Demo data collection completed successfully!")
        print("\nNext steps:")
        print("1. Test research analysis: POST /api/research/analyze")
        print("2. Try paper comparison: POST /api/research/compare")
        print("3. Generate research questions: POST /api/research/questions")
        print("4. View API docs: http://localhost:8080/docs")

    except Exception as e:
        print(f"\n💥 Collection failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
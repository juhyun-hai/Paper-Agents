"""
Database migration and population script.
Migrates from SQLite to PostgreSQL and populates with arXiv data.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_db, AsyncSessionLocal
from app.models import Paper, Author, PaperAuthor, Concept, PaperConcept
from app.core.config import settings

# Import existing arXiv collector
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from src.collector.arxiv_collector import ArxivCollector


class DatabaseMigrator:
    """Handle database migration and population."""

    def __init__(self):
        self.collector = ArxivCollector()

    async def migrate_and_populate(self, max_papers: int = 5000):
        """Main migration function."""
        print("🚀 Starting Research Intelligence Platform Migration")

        # Step 1: Initialize database
        print("\n📊 Initializing PostgreSQL database...")
        await init_db()
        print("✅ Database schema created")

        # Step 2: Populate with recent arXiv papers
        print(f"\n📚 Collecting recent arXiv papers (max {max_papers})...")
        await self._collect_arxiv_papers(max_papers)

        print("\n🎉 Migration completed successfully!")

    async def _collect_arxiv_papers(self, max_papers: int):
        """Collect recent papers from arXiv."""
        categories = [
            "cs.AI",      # Artificial Intelligence
            "cs.LG",      # Machine Learning
            "cs.CL",      # Computation and Language
            "cs.CV",      # Computer Vision
            "cs.IR",      # Information Retrieval
            "cs.NE",      # Neural and Evolutionary Computing
            "stat.ML",    # Machine Learning (Statistics)
        ]

        # Calculate date range (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        papers_collected = 0

        for category in categories:
            if papers_collected >= max_papers:
                break

            print(f"  📖 Collecting from {category}...")

            try:
                # Get papers from this category
                papers_data = await self._fetch_papers_from_category(
                    category, start_date, end_date, min(500, max_papers - papers_collected)
                )

                # Save to database
                saved_count = await self._save_papers_to_db(papers_data)
                papers_collected += saved_count

                print(f"    ✅ Saved {saved_count} papers from {category}")

                # Rate limiting
                time.sleep(1)

            except Exception as e:
                print(f"    ❌ Error collecting from {category}: {e}")
                continue

        print(f"\n📈 Total papers collected: {papers_collected}")

    async def _fetch_papers_from_category(
        self,
        category: str,
        start_date: datetime,
        end_date: datetime,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Fetch papers from a specific category."""

        # Construct arXiv search query
        date_filter = f"submittedDate:[{start_date.strftime('%Y%m%d')} TO {end_date.strftime('%Y%m%d')}]"
        query = f"cat:{category} AND {date_filter}"

        try:
            papers = self.collector.search_papers(
                query=query,
                max_results=max_results,
                sort_by="submittedDate",
                sort_order="descending"
            )
            return papers
        except Exception as e:
            print(f"Error fetching papers: {e}")
            return []

    async def _save_papers_to_db(self, papers_data: List[Dict[str, Any]]) -> int:
        """Save papers to PostgreSQL database."""
        if not papers_data:
            return 0

        async with AsyncSessionLocal() as session:
            saved_count = 0

            for paper_data in papers_data:
                try:
                    # Check if paper already exists
                    arxiv_id = paper_data.get('arxiv_id')
                    if not arxiv_id:
                        continue

                    existing = await session.get(Paper, {'arxiv_id': arxiv_id})
                    if existing:
                        continue

                    # Create paper object
                    paper = Paper(
                        arxiv_id=arxiv_id,
                        title=paper_data.get('title', ''),
                        abstract=paper_data.get('abstract', ''),
                        authors=paper_data.get('authors', []),
                        categories=paper_data.get('categories', []),
                        venue=paper_data.get('venue', ''),
                        year=paper_data.get('year'),
                        citation_count=paper_data.get('citation_count', 0),
                        pdf_url=paper_data.get('pdf_url', ''),
                        published_date=paper_data.get('published_date'),
                        updated_date=paper_data.get('updated_date'),
                    )

                    session.add(paper)
                    saved_count += 1

                except Exception as e:
                    print(f"Error saving paper {paper_data.get('arxiv_id', 'unknown')}: {e}")
                    continue

            # Commit all papers
            try:
                await session.commit()
                print(f"    💾 Committed {saved_count} papers to database")
            except Exception as e:
                print(f"    ❌ Error committing papers: {e}")
                await session.rollback()
                return 0

            return saved_count

    async def _extract_and_save_concepts(self, papers: List[Paper]):
        """Extract concepts from papers and save them."""
        # This will be implemented in Phase 1 with AI services
        pass


async def main():
    """Run the migration."""
    migrator = DatabaseMigrator()

    # Collect 5000 recent papers for demo
    await migrator.migrate_and_populate(max_papers=5000)


if __name__ == "__main__":
    asyncio.run(main())
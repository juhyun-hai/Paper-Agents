#!/usr/bin/env python3
"""
Collect engineering and systems papers including fault diagnosis, SNU HAI Lab.
"""

import asyncio
import sys
import os
from typing import List, Dict, Any
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from app.models import Paper
from sqlalchemy import select

try:
    import arxiv
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False
    print("❌ arxiv-py not installed. Run: pip install arxiv")

class EngineeringPapersCollector:
    """Collect engineering and systems papers."""

    def __init__(self):
        if not ARXIV_AVAILABLE:
            raise ImportError("arxiv-py not available")

        self.client = arxiv.Client()

        # Engineering and systems topics
        self.engineering_searches = {
            "fault_diagnosis": [
                "fault diagnosis deep learning",
                "fault detection neural networks",
                "anomaly detection systems",
                "failure prediction machine learning",
                "diagnostic systems AI",
                "condition monitoring deep learning",
                "predictive maintenance neural networks"
            ],

            "diffusion_applications": [
                "diffusion models applications",
                "diffusion process engineering",
                "diffusion based image processing",
                "diffusion probabilistic models",
                "denoising diffusion applications"
            ],

            "snu_hai_lab": [
                "Seoul National University HAI",
                "SNU Human-AI Interaction",
                "Seoul National University computer science",
                "SNU deep learning",
                "Korea University AI",
                "KAIST machine learning"
            ],

            "systems_engineering": [
                "systems engineering AI",
                "industrial AI applications",
                "manufacturing machine learning",
                "process control neural networks",
                "automation deep learning",
                "cyber physical systems AI"
            ],

            "computer_vision_applications": [
                "medical image diagnosis",
                "industrial vision inspection",
                "autonomous driving perception",
                "robotics vision systems",
                "quality control computer vision"
            ]
        }

    async def search_and_collect_papers(self):
        """Search and collect engineering papers."""
        print("🔧 Collecting Engineering and Systems Papers")
        print("Including: Fault Diagnosis, SNU HAI Lab, Diffusion Applications")
        print("=" * 70)

        total_collected = 0
        total_existing = 0

        async with AsyncSessionLocal() as session:
            for category, search_terms in self.engineering_searches.items():
                print(f"\n🎯 Category: {category.replace('_', ' ').title()}")
                print("-" * 50)

                category_collected = 0
                category_existing = 0

                for search_term in search_terms:
                    try:
                        print(f"  🔍 Searching: '{search_term}'")

                        # Search arXiv
                        search = arxiv.Search(
                            query=search_term,
                            max_results=20,
                            sort_by=arxiv.SortCriterion.Relevance
                        )

                        papers_found = 0
                        for paper in self.client.results(search):
                            try:
                                arxiv_id = paper.get_short_id()

                                # Check if paper already exists
                                result = await session.execute(
                                    select(Paper).where(Paper.arxiv_id == arxiv_id)
                                )
                                existing_paper = result.scalar_one_or_none()

                                if existing_paper:
                                    category_existing += 1
                                    continue

                                # Create Paper object
                                new_paper = Paper(
                                    arxiv_id=arxiv_id,
                                    title=paper.title,
                                    abstract=paper.summary,
                                    authors=[str(author) for author in paper.authors],
                                    categories=[cat for cat in paper.categories],
                                    published_date=paper.published.date() if paper.published else None,
                                    updated_date=paper.updated.date() if paper.updated else None,
                                    pdf_url=paper.pdf_url,
                                    html_url=paper.entry_id,
                                    year=paper.published.year if paper.published else None
                                )

                                session.add(new_paper)
                                papers_found += 1
                                category_collected += 1

                                if papers_found >= 5:  # Limit per search to avoid overwhelming
                                    break

                            except Exception as e:
                                print(f"    ❌ Error processing paper: {str(e)[:50]}...")

                        if papers_found > 0:
                            await session.commit()
                            print(f"    ✅ Added {papers_found} papers from '{search_term[:30]}...'")

                        # Rate limiting
                        await asyncio.sleep(1.0)

                    except Exception as e:
                        print(f"    💥 Search error for '{search_term}': {e}")

                print(f"  📊 {category}: {category_collected} new, {category_existing} existing")
                total_collected += category_collected
                total_existing += category_existing

        print("\n" + "=" * 70)
        print(f"🎯 Engineering Collection Summary:")
        print(f"   📄 New papers collected: {total_collected}")
        print(f"   ✓ Papers already present: {total_existing}")
        print(f"   📚 Total engineering papers processed: {total_collected + total_existing}")

        return total_collected

async def main():
    """Run engineering paper collection."""
    print("🏭 Research Intelligence Platform - Engineering Papers Collection")
    print("Collecting specialized engineering and systems papers:")
    print("• 🔧 Fault Diagnosis & Anomaly Detection")
    print("• 🎨 Diffusion Model Applications")
    print("• 🏫 SNU HAI Lab & Korean Universities")
    print("• ⚙️ Systems Engineering & Industrial AI")
    print("• 👁️ Computer Vision Applications")
    print("=" * 80)

    try:
        collector = EngineeringPapersCollector()
        new_papers = await collector.search_and_collect_papers()

        print(f"\n🎉 Engineering collection completed! Added {new_papers} papers")
        print("\nYour research platform now includes specialized papers in:")
        print("• 🔧 Fault diagnosis and predictive maintenance")
        print("• 🏭 Industrial AI and manufacturing applications")
        print("• 🏫 Korean university research (SNU, KAIST)")
        print("• 🎨 Diffusion model applications beyond generative AI")
        print("• 👁️ Applied computer vision in industry")

    except Exception as e:
        print(f"\n💥 Collection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
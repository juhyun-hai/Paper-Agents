#!/usr/bin/env python3
"""
Collect Korean university papers specifically focusing on SNU HAI Lab.
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

class KoreanUniversityPapersCollector:
    """Collect papers from Korean universities and research institutes."""

    def __init__(self):
        if not ARXIV_AVAILABLE:
            raise ImportError("arxiv-py not available")

        self.client = arxiv.Client()

        # Korean university and research institute searches
        self.korean_searches = {
            "snu_hai_lab": [
                "Seoul National University Human-AI Interaction",
                "Seoul National University HAI",
                "SNU HAI Lab",
                "Seoul National University computer science AI",
                "Seoul National University machine learning",
                "Seoul National University artificial intelligence",
                "Seoul National University HCI",
                "Seoul National University interaction design"
            ],

            "snu_general": [
                "Seoul National University deep learning",
                "Seoul National University neural networks",
                "Seoul National University computer vision",
                "Seoul National University natural language processing",
                "Seoul National University robotics",
                "Seoul National University data mining"
            ],

            "kaist": [
                "KAIST machine learning",
                "KAIST artificial intelligence",
                "KAIST deep learning",
                "KAIST computer vision",
                "KAIST robotics",
                "Korea Advanced Institute Science Technology AI"
            ],

            "other_korean": [
                "Yonsei University machine learning",
                "Korea University artificial intelligence",
                "POSTECH deep learning",
                "Hanyang University computer science",
                "Sungkyunkwan University AI"
            ],

            "korean_authors": [
                "Kyomin Jung Seoul National",
                "Bohyung Han Seoul National",
                "Gunhee Kim Seoul National",
                "Jinwoo Shin KAIST",
                "Sung Ju Hwang KAIST",
                "Jaegul Choo KAIST"
            ]
        }

    async def search_and_collect_papers(self):
        """Search and collect Korean university papers."""
        print("🇰🇷 Collecting Korean University & Research Papers")
        print("Focus: SNU HAI Lab, KAIST, and other top Korean institutions")
        print("=" * 70)

        total_collected = 0
        total_existing = 0

        async with AsyncSessionLocal() as session:
            for category, search_terms in self.korean_searches.items():
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
                            max_results=25,  # More results for focused searches
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

                                # Additional filtering for Korean relevance
                                is_korean_relevant = self._is_korean_relevant(paper)
                                if not is_korean_relevant and category != "korean_authors":
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

                                print(f"    ✅ Found: {paper.title[:60]}...")

                                if papers_found >= 10:  # Reasonable limit per search
                                    break

                            except Exception as e:
                                print(f"    ❌ Error processing paper: {str(e)[:50]}...")

                        if papers_found > 0:
                            await session.commit()
                            print(f"    📄 Added {papers_found} papers from '{search_term[:30]}...'")

                        # Rate limiting
                        await asyncio.sleep(1.5)  # Slightly longer delay

                    except Exception as e:
                        print(f"    💥 Search error for '{search_term}': {e}")

                print(f"  📊 {category}: {category_collected} new, {category_existing} existing")
                total_collected += category_collected
                total_existing += category_existing

        print("\n" + "=" * 70)
        print(f"🇰🇷 Korean Universities Collection Summary:")
        print(f"   📄 New papers collected: {total_collected}")
        print(f"   ✓ Papers already present: {total_existing}")
        print(f"   📚 Total Korean papers processed: {total_collected + total_existing}")

        return total_collected

    def _is_korean_relevant(self, paper) -> bool:
        """Check if paper is relevant to Korean research."""
        text_to_check = (paper.title + " " + paper.summary + " " +
                        " ".join([str(author) for author in paper.authors])).lower()

        korean_keywords = [
            "seoul national", "snu", "kaist", "korea advanced institute",
            "yonsei", "korea university", "postech", "hanyang",
            "sungkyunkwan", "kyomin jung", "bohyung han", "gunhee kim",
            "jinwoo shin", "sung ju hwang", "jaegul choo",
            "hai lab", "human-ai", "korea", "seoul"
        ]

        return any(keyword in text_to_check for keyword in korean_keywords)

async def main():
    """Run Korean university paper collection."""
    print("🏫 Research Intelligence Platform - Korean Universities Collection")
    print("Collecting papers from top Korean research institutions:")
    print("• 🇰🇷 Seoul National University (SNU) - especially HAI Lab")
    print("• 🔬 Korea Advanced Institute of Science & Technology (KAIST)")
    print("• 🏛️ Yonsei University, Korea University, POSTECH")
    print("• 👨‍🏫 Papers by prominent Korean AI researchers")
    print("=" * 80)

    try:
        collector = KoreanUniversityPapersCollector()
        new_papers = await collector.search_and_collect_papers()

        print(f"\n🎉 Korean universities collection completed! Added {new_papers} papers")
        print("\nYour research platform now includes papers from:")
        print("• 🏫 SNU HAI Lab and computer science department")
        print("• 🔬 KAIST AI and machine learning research")
        print("• 🇰🇷 Other top Korean universities and institutes")
        print("• 👨‍🏫 Leading Korean AI researchers")

    except Exception as e:
        print(f"\n💥 Collection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
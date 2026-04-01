#!/usr/bin/env python3
"""
Create simple graph edges based on category and author overlap.
"""

import asyncio
import sys
import os
from typing import List, Dict, Set
from collections import defaultdict

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from app.models import Paper
from app.models.graph import GraphEdge
from sqlalchemy import select

class SimpleGraphEdgeBuilder:
    """Build graph edges using simple heuristics."""

    def __init__(self):
        self.max_edges_per_paper = 8
        self.min_common_categories = 1
        self.min_common_authors = 1

    async def create_category_based_edges(self):
        """Create edges between papers with common categories."""
        print("📚 Creating category-based edges")
        print("-" * 40)

        async with AsyncSessionLocal() as session:
            # Get all papers with categories
            result = await session.execute(
                select(Paper).where(Paper.categories.is_not(None))
            )
            papers = result.scalars().all()

            # Group papers by categories
            category_to_papers = defaultdict(list)
            for paper in papers:
                if paper.categories:
                    for category in paper.categories:
                        category_to_papers[category].append(paper)

            edges_created = 0
            for category, category_papers in category_to_papers.items():
                if len(category_papers) < 2:
                    continue

                print(f"🏷️ Processing {category}: {len(category_papers)} papers")

                # Create edges between papers in same category (limit connections)
                for i, paper1 in enumerate(category_papers[:30]):  # Limit papers per category
                    connections = 0
                    for paper2 in category_papers[i+1:]:
                        if connections >= self.max_edges_per_paper:
                            break

                        # Check if edge already exists
                        existing_edge = await session.execute(
                            select(GraphEdge).where(
                                ((GraphEdge.source_paper_id == paper1.id) &
                                 (GraphEdge.target_paper_id == paper2.id)) |
                                ((GraphEdge.source_paper_id == paper2.id) &
                                 (GraphEdge.target_paper_id == paper1.id))
                            )
                        )

                        if existing_edge.scalar_one_or_none():
                            continue

                        # Create edge
                        edge = GraphEdge(
                            source_paper_id=paper1.id,
                            target_paper_id=paper2.id,
                            edge_type="category",
                            weight=0.6,
                            metadata={
                                "shared_category": category,
                                "source_title": paper1.title[:80],
                                "target_title": paper2.title[:80]
                            }
                        )

                        session.add(edge)
                        edges_created += 1
                        connections += 1

                # Commit category batch
                if edges_created % 100 == 0:
                    await session.commit()

            # Final commit
            await session.commit()
            print(f"✅ Created {edges_created} category-based edges")
            return edges_created

    async def create_author_based_edges(self):
        """Create edges between papers with common authors."""
        print("👥 Creating author-based edges")
        print("-" * 40)

        async with AsyncSessionLocal() as session:
            # Get all papers with authors
            result = await session.execute(
                select(Paper).where(Paper.authors.is_not(None))
            )
            papers = result.scalars().all()

            # Group papers by authors
            author_to_papers = defaultdict(list)
            for paper in papers:
                if paper.authors:
                    for author in paper.authors:
                        # Normalize author name (remove extra spaces, standardize)
                        normalized_author = " ".join(author.strip().split())
                        if len(normalized_author) > 3:  # Skip very short names
                            author_to_papers[normalized_author].append(paper)

            edges_created = 0
            for author, author_papers in author_to_papers.items():
                if len(author_papers) < 2:
                    continue

                print(f"👤 Processing {author}: {len(author_papers)} papers")

                # Create edges between papers by same author
                for i, paper1 in enumerate(author_papers[:15]):  # Limit papers per author
                    connections = 0
                    for paper2 in author_papers[i+1:]:
                        if connections >= 5:  # Max 5 connections per paper for author-based
                            break

                        # Check if edge already exists
                        existing_edge = await session.execute(
                            select(GraphEdge).where(
                                ((GraphEdge.source_paper_id == paper1.id) &
                                 (GraphEdge.target_paper_id == paper2.id)) |
                                ((GraphEdge.source_paper_id == paper2.id) &
                                 (GraphEdge.target_paper_id == paper1.id))
                            )
                        )

                        if existing_edge.scalar_one_or_none():
                            continue

                        # Create edge
                        edge = GraphEdge(
                            source_paper_id=paper1.id,
                            target_paper_id=paper2.id,
                            edge_type="author",
                            weight=0.8,  # Higher weight for author connections
                            metadata={
                                "shared_author": author,
                                "source_title": paper1.title[:80],
                                "target_title": paper2.title[:80]
                            }
                        )

                        session.add(edge)
                        edges_created += 1
                        connections += 1

                # Commit author batch
                if edges_created % 100 == 0:
                    await session.commit()

            # Final commit
            await session.commit()
            print(f"✅ Created {edges_created} author-based edges")
            return edges_created

    async def create_cross_category_edges(self):
        """Create edges between related categories."""
        print("🔗 Creating cross-category edges")
        print("-" * 40)

        # Define related categories that should be connected
        related_categories = [
            (["cs.AI", "cs.LG", "cs.ML"], "AI/ML"),
            (["cs.CV", "cs.AI", "cs.LG"], "Computer Vision"),
            (["cs.CL", "cs.AI", "cs.LG"], "NLP"),
            (["cs.RO", "cs.AI", "cs.CV"], "Robotics"),
            (["cs.HC", "cs.AI"], "HCI"),
            (["cs.IR", "cs.CL", "cs.LG"], "Information Retrieval"),
            (["physics.app-ph", "cs.AI"], "Applied Physics + AI"),
            (["stat.ML", "cs.LG", "cs.AI"], "Statistics + ML")
        ]

        async with AsyncSessionLocal() as session:
            edges_created = 0

            for categories, description in related_categories:
                print(f"🔗 Connecting {description}: {categories}")

                # Get papers from each category
                category_papers = {}
                for category in categories:
                    result = await session.execute(
                        select(Paper).where(Paper.categories.contains([category])).limit(20)
                    )
                    category_papers[category] = result.scalars().all()

                # Connect papers across related categories
                for i, cat1 in enumerate(categories):
                    for cat2 in categories[i+1:]:
                        papers1 = category_papers.get(cat1, [])
                        papers2 = category_papers.get(cat2, [])

                        # Create limited cross-category connections
                        for paper1 in papers1[:10]:
                            connections = 0
                            for paper2 in papers2[:10]:
                                if connections >= 3:  # Max 3 cross-category connections
                                    break

                                # Check if edge already exists
                                existing_edge = await session.execute(
                                    select(GraphEdge).where(
                                        ((GraphEdge.source_paper_id == paper1.id) &
                                         (GraphEdge.target_paper_id == paper2.id)) |
                                        ((GraphEdge.source_paper_id == paper2.id) &
                                         (GraphEdge.target_paper_id == paper1.id))
                                    )
                                )

                                if existing_edge.scalar_one_or_none():
                                    continue

                                # Create cross-category edge
                                edge = GraphEdge(
                                    source_paper_id=paper1.id,
                                    target_paper_id=paper2.id,
                                    edge_type="cross_category",
                                    weight=0.4,  # Lower weight for cross-category
                                    metadata={
                                        "category1": cat1,
                                        "category2": cat2,
                                        "relationship": description,
                                        "source_title": paper1.title[:80],
                                        "target_title": paper2.title[:80]
                                    }
                                )

                                session.add(edge)
                                edges_created += 1
                                connections += 1

            # Commit all cross-category edges
            await session.commit()
            print(f"✅ Created {edges_created} cross-category edges")
            return edges_created

async def main():
    """Main function to create simple graph edges."""
    print("🚀 Research Intelligence - Simple Graph Edge Builder")
    print("Building basic connections between papers for better discovery")
    print("=" * 70)

    builder = SimpleGraphEdgeBuilder()

    try:
        # Create different types of edges
        category_edges = await builder.create_category_based_edges()
        author_edges = await builder.create_author_based_edges()
        cross_category_edges = await builder.create_cross_category_edges()

        total_edges = category_edges + author_edges + cross_category_edges

        print("\n" + "=" * 70)
        print("🎯 Simple Graph Edge Creation Summary:")
        print(f"   📚 Category edges: {category_edges}")
        print(f"   👥 Author edges: {author_edges}")
        print(f"   🔗 Cross-category edges: {cross_category_edges}")
        print(f"   📊 Total new edges: {total_edges}")

        if total_edges > 0:
            print("\n✨ Knowledge graph connectivity improved!")
            print("Papers are now connected by:")
            print("• 📚 Shared research categories")
            print("• 👥 Common authors")
            print("• 🔗 Related research domains")

    except Exception as e:
        print(f"\n💥 Edge creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Create graph edges based on paper similarity using embeddings.
"""

import asyncio
import sys
import os
from typing import List, Tuple
import numpy as np
from sqlalchemy import select, text

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from app.models import Paper
from app.models.graph import GraphEdge

class GraphEdgeBuilder:
    """Build graph edges based on paper similarity."""

    def __init__(self):
        self.similarity_threshold = 0.75  # High threshold for strong connections
        self.max_edges_per_paper = 10    # Limit connections per paper

    async def create_similarity_edges(self):
        """Create edges based on paper similarity."""
        print("🕸️ Creating graph edges based on paper similarity")
        print("=" * 60)

        async with AsyncSessionLocal() as session:
            # Get papers with embeddings
            result = await session.execute(
                select(Paper).where(Paper.full_embedding.is_not(None))
            )
            papers_with_embeddings = result.scalars().all()

            total_papers = len(papers_with_embeddings)
            print(f"📄 Found {total_papers} papers with embeddings")

            if total_papers < 2:
                print("❌ Need at least 2 papers with embeddings to create edges")
                return 0

            edges_created = 0
            batch_size = 50  # Process in batches to avoid memory issues

            for i in range(0, total_papers, batch_size):
                batch = papers_with_embeddings[i:i + batch_size]
                print(f"🔄 Processing batch {i//batch_size + 1}/{(total_papers + batch_size - 1)//batch_size}")

                batch_edges = await self._create_edges_for_batch(session, batch, papers_with_embeddings)
                edges_created += batch_edges

                # Commit batch
                await session.commit()
                print(f"✅ Created {batch_edges} edges in this batch")

            print(f"\n🎯 Total edges created: {edges_created}")
            return edges_created

    async def _create_edges_for_batch(self, session, batch: List[Paper], all_papers: List[Paper]) -> int:
        """Create edges for a batch of papers."""
        edges_created = 0

        for paper in batch:
            if paper.full_embedding is None:
                continue

            # Find similar papers using vector similarity
            try:
                # Use PostgreSQL's vector similarity search
                query = text("""
                    SELECT id, arxiv_id, title,
                           (full_embedding <=> :target_embedding) AS distance
                    FROM papers
                    WHERE id != :paper_id
                      AND full_embedding IS NOT NULL
                      AND (full_embedding <=> :target_embedding) < :distance_threshold
                    ORDER BY distance ASC
                    LIMIT :max_edges
                """)

                result = await session.execute(query, {
                    'target_embedding': paper.full_embedding,
                    'paper_id': paper.id,
                    'distance_threshold': 1.0 - self.similarity_threshold,  # Convert similarity to distance
                    'max_edges': self.max_edges_per_paper
                })

                similar_papers = result.fetchall()

                for similar_paper in similar_papers:
                    similarity_score = 1.0 - similar_paper.distance  # Convert back to similarity

                    # Check if edge already exists
                    existing_edge = await session.execute(
                        select(GraphEdge).where(
                            ((GraphEdge.source_paper_id == paper.id) &
                             (GraphEdge.target_paper_id == similar_paper.id)) |
                            ((GraphEdge.source_paper_id == similar_paper.id) &
                             (GraphEdge.target_paper_id == paper.id))
                        )
                    )

                    if existing_edge.scalar_one_or_none():
                        continue  # Edge already exists

                    # Create new edge
                    edge = GraphEdge(
                        source_paper_id=paper.id,
                        target_paper_id=similar_paper.id,
                        edge_type="similarity",
                        weight=similarity_score,
                        metadata={
                            "source_title": paper.title[:100],
                            "target_title": similar_paper.title[:100],
                            "similarity_score": similarity_score
                        }
                    )

                    session.add(edge)
                    edges_created += 1

            except Exception as e:
                print(f"    ❌ Error processing {paper.arxiv_id}: {str(e)[:50]}...")
                continue

        return edges_created

    async def create_category_edges(self):
        """Create edges between papers in same categories."""
        print("📚 Creating category-based edges")
        print("-" * 40)

        async with AsyncSessionLocal() as session:
            # Get papers grouped by categories
            result = await session.execute(
                select(Paper).where(Paper.categories.is_not(None))
            )
            papers = result.scalars().all()

            category_groups = {}
            for paper in papers:
                for category in paper.categories:
                    if category not in category_groups:
                        category_groups[category] = []
                    category_groups[category].append(paper)

            edges_created = 0

            for category, category_papers in category_groups.items():
                if len(category_papers) < 2:
                    continue

                print(f"🏷️ Processing category: {category} ({len(category_papers)} papers)")

                # Create edges between papers in same category (limit to avoid explosion)
                for i, paper1 in enumerate(category_papers[:20]):  # Limit to 20 papers per category
                    for paper2 in category_papers[i+1:min(i+6, len(category_papers))]:  # Max 5 connections per paper
                        # Check if edge exists
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

                        edge = GraphEdge(
                            source_paper_id=paper1.id,
                            target_paper_id=paper2.id,
                            edge_type="category",
                            weight=0.5,  # Medium weight for category connections
                            metadata={
                                "category": category,
                                "source_title": paper1.title[:100],
                                "target_title": paper2.title[:100]
                            }
                        )

                        session.add(edge)
                        edges_created += 1

            await session.commit()
            print(f"✅ Created {edges_created} category edges")
            return edges_created

async def main():
    """Main function to create graph edges."""
    print("🚀 Research Intelligence - Graph Edge Builder")
    print("Building connections between papers for better discovery")
    print("=" * 70)

    builder = GraphEdgeBuilder()

    try:
        # Create similarity-based edges
        similarity_edges = await builder.create_similarity_edges()

        # Create category-based edges
        category_edges = await builder.create_category_edges()

        total_edges = similarity_edges + category_edges

        print("\n" + "=" * 70)
        print("🎯 Graph Edge Creation Summary:")
        print(f"   🔗 Similarity edges: {similarity_edges}")
        print(f"   🏷️ Category edges: {category_edges}")
        print(f"   📊 Total new edges: {total_edges}")

        if total_edges > 0:
            print("\n✨ Knowledge graph connectivity improved!")
            print("Papers are now better connected for:")
            print("• 🔍 Enhanced search and discovery")
            print("• 📈 Better recommendation accuracy")
            print("• 🕸️ Richer graph visualizations")

    except Exception as e:
        print(f"\n💥 Edge creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
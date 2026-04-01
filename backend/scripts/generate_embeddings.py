#!/usr/bin/env python3
"""
Generate embeddings for existing papers.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from app.models import Paper
from app.services.embedding_service import get_embedding_service
from sqlalchemy import select


async def generate_all_embeddings():
    """Generate embeddings for all papers without embeddings."""

    print("🧠 Embedding Generation")
    print("=" * 30)

    embedding_service = get_embedding_service()

    async with AsyncSessionLocal() as session:
        # Get papers without embeddings
        result = await session.execute(
            select(Paper).where(Paper.full_embedding.is_(None))
        )
        papers = result.scalars().all()

        if not papers:
            print("✅ All papers already have embeddings!")
            return

        print(f"📄 Found {len(papers)} papers without embeddings")
        print("🚀 Starting embedding generation...")

        try:
            # Generate embeddings in batches
            batch_size = 10
            total_updated = 0

            for i in range(0, len(papers), batch_size):
                batch = papers[i:i + batch_size]
                print(f"  🧠 Processing batch {i//batch_size + 1}/{(len(papers) + batch_size - 1)//batch_size} ({len(batch)} papers)...")

                updated_count = await embedding_service.update_paper_embeddings(
                    session, batch, batch_size=len(batch)
                )

                total_updated += updated_count
                print(f"    ✅ Generated {updated_count} embeddings")

            print(f"\n🎉 Embedding generation completed!")
            print(f"📊 Total embeddings generated: {total_updated}")

            # Verify final state
            embedded_count = await session.scalar(
                select(Paper).where(Paper.full_embedding.is_not(None)).count()
            )
            total_count = await session.scalar(select(Paper).count())

            print(f"📈 Final state: {embedded_count}/{total_count} papers with embeddings")

        except Exception as e:
            print(f"❌ Error during embedding generation: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(generate_all_embeddings())
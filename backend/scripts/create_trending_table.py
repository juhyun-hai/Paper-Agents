#!/usr/bin/env python3
"""
Create trending_papers table.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal, async_engine
from app.models import Base, TrendingPaper

async def create_trending_table():
    """Create the trending_papers table."""
    print("🗄️ Creating trending_papers table...")

    try:
        # Create the table
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ trending_papers table created successfully!")

        # Test the table
        async with AsyncSessionLocal() as session:
            # Try to query the table to make sure it exists
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT COUNT(*) FROM trending_papers")
            )
            count = result.scalar()
            print(f"📊 trending_papers table is ready (current count: {count})")

    except Exception as e:
        print(f"❌ Failed to create trending_papers table: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_trending_table())
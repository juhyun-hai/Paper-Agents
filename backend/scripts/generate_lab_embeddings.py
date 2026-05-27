#!/usr/bin/env python3
"""Generate embeddings for HAI Lab papers (hai:* / openalex:* prefix).

Run before regular arXiv backfill so /api/hai/related is usable ASAP.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('HF_HOME', '/home/juhyun/agent/paper-agent-github/backend/hf_cache')

from app.core.database import AsyncSessionLocal
from app.models import Paper
from app.services.embedding_service import get_embedding_service
from sqlalchemy import select, or_


async def main():
    svc = get_embedding_service()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Paper).where(
                or_(Paper.arxiv_id.like('hai:%'), Paper.arxiv_id.like('openalex:%')),
                Paper.full_embedding.is_(None),
                Paper.abstract.is_not(None),
            )
        )
        papers = result.scalars().all()
        print(f'Lab papers without embedding: {len(papers)}')

        BATCH = 16
        done = 0
        for i in range(0, len(papers), BATCH):
            batch = papers[i:i + BATCH]
            n = await svc.update_paper_embeddings(session, batch, batch_size=len(batch))
            done += n
            print(f'  [{i + len(batch)}/{len(papers)}] +{n}')
        print(f'Done — {done} lab embeddings generated.')


if __name__ == '__main__':
    asyncio.run(main())

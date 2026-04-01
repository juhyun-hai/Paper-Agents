"""
Embedding service for semantic search using BAAI/bge-m3.
"""

import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from ..models import Paper
from ..core.config import settings


class EmbeddingService:
    """Service for generating and managing embeddings."""

    def __init__(self):
        self.model_name = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.batch_size = settings.batch_size
        self.max_tokens = settings.max_tokens

        # Initialize model lazily
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._model is None:
            self._model = SentenceTransformer(
                self.model_name,
                device='cpu',  # Use CPU for ARM64 compatibility
                trust_remote_code=True
            )
            # Set max sequence length
            self._model.max_seq_length = self.max_tokens
        return self._model

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """Encode texts to embeddings synchronously."""
        if not texts:
            return np.array([])

        # Normalize and truncate texts
        normalized_texts = []
        for text in texts:
            if not text or not text.strip():
                normalized_texts.append("empty")
            else:
                # Truncate long texts (rough token estimation)
                words = text.split()
                if len(words) > self.max_tokens // 2:  # Rough estimation
                    text = " ".join(words[:self.max_tokens // 2])
                normalized_texts.append(text.strip())

        # Generate embeddings
        embeddings = self.model.encode(
            normalized_texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalize for cosine similarity
        )

        return embeddings

    async def encode_texts_async(self, texts: List[str]) -> np.ndarray:
        """Encode texts asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.encode_texts, texts)

    def build_paper_index_text(self, paper: Paper, summary_data: Dict[str, Any] = None) -> str:
        """Build rich index text for a paper."""
        parts = []

        # Core content
        if paper.title:
            parts.append(paper.title)

        if paper.abstract:
            parts.append(paper.abstract)

        # Author information
        if paper.authors:
            authors_text = ", ".join(paper.authors)
            parts.append(f"Authors: {authors_text}")

        # Categories
        if paper.categories:
            categories_text = ", ".join(paper.categories)
            parts.append(f"Categories: {categories_text}")

        # Venue
        if paper.venue:
            parts.append(f"Published in: {paper.venue}")

        # Summary enrichment (if available)
        if summary_data:
            if summary_data.get("one_liner"):
                parts.append(f"Summary: {summary_data['one_liner']}")

            if summary_data.get("method"):
                parts.append(f"Method: {summary_data['method']}")

            if summary_data.get("keywords"):
                if isinstance(summary_data["keywords"], list):
                    keywords_text = ", ".join(summary_data["keywords"])
                    parts.append(f"Keywords: {keywords_text}")

            if summary_data.get("datasets"):
                datasets = summary_data["datasets"]
                if isinstance(datasets, list):
                    dataset_names = [d.get("name", str(d)) if isinstance(d, dict) else str(d) for d in datasets]
                    parts.append(f"Datasets: {', '.join(dataset_names)}")

        return " ".join(parts)

    async def search_papers_by_embedding(
        self,
        session: AsyncSession,
        query_embedding: np.ndarray,
        limit: int = 20,
        similarity_threshold: float = None
    ) -> List[Tuple[Paper, float]]:
        """Search papers by embedding similarity using pgvector."""
        similarity_threshold = similarity_threshold or settings.similarity_threshold

        # Convert numpy array to list for PostgreSQL
        query_vector = query_embedding.tolist()

        # Use pgvector cosine similarity search
        query = select(
            Paper,
            (1 - Paper.full_embedding.cosine_distance(query_vector)).label('similarity')
        ).where(
            Paper.full_embedding.is_not(None)
        ).where(
            (1 - Paper.full_embedding.cosine_distance(query_vector)) >= similarity_threshold
        ).order_by(
            Paper.full_embedding.cosine_distance(query_vector)
        ).limit(limit)

        result = await session.execute(query)
        papers_with_scores = result.all()

        return [(paper, float(score)) for paper, score in papers_with_scores]

    async def search_papers_hybrid(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 20,
        text_weight: float = 0.3,
        semantic_weight: float = 0.7
    ) -> List[Tuple[Paper, float]]:
        """Hybrid search combining text and semantic similarity."""

        # Generate query embedding
        query_embedding = await self.encode_texts_async([query])
        query_vector = query_embedding[0].tolist()

        # Hybrid search query
        sql_query = text("""
        WITH semantic_scores AS (
            SELECT
                id,
                (1 - (full_embedding <=> CAST(:query_vector AS vector))) as semantic_score
            FROM papers
            WHERE full_embedding IS NOT NULL
        ),
        text_scores AS (
            SELECT
                id,
                GREATEST(
                    ts_rank_cd(to_tsvector('english', title), plainto_tsquery('english', :query)),
                    ts_rank_cd(to_tsvector('english', abstract), plainto_tsquery('english', :query))
                ) as text_score
            FROM papers
            WHERE
                to_tsvector('english', title) @@ plainto_tsquery('english', :query) OR
                to_tsvector('english', abstract) @@ plainto_tsquery('english', :query)
        )
        SELECT
            p.*,
            COALESCE(:semantic_weight * s.semantic_score, 0) +
            COALESCE(:text_weight * t.text_score, 0) as combined_score
        FROM papers p
        LEFT JOIN semantic_scores s ON p.id = s.id
        LEFT JOIN text_scores t ON p.id = t.id
        WHERE s.semantic_score IS NOT NULL OR t.text_score IS NOT NULL
        ORDER BY combined_score DESC
        LIMIT :limit
        """)

        # Convert vector to string format for PostgreSQL
        query_vector_str = "[" + ",".join(map(str, query_vector)) + "]"

        result = await session.execute(
            sql_query,
            {
                "query": query,
                "query_vector": query_vector_str,
                "semantic_weight": semantic_weight,
                "text_weight": text_weight,
                "limit": limit
            }
        )

        # Convert results to Paper objects with scores
        papers_with_scores = []
        for row in result:
            paper_data = dict(row._mapping)
            score = paper_data.pop('combined_score')

            paper = Paper(**{k: v for k, v in paper_data.items() if hasattr(Paper, k)})
            papers_with_scores.append((paper, float(score)))

        return papers_with_scores

    async def update_paper_embeddings(
        self,
        session: AsyncSession,
        papers: List[Paper],
        batch_size: int = None
    ) -> int:
        """Update embeddings for multiple papers."""
        batch_size = batch_size or self.batch_size
        updated_count = 0

        for i in range(0, len(papers), batch_size):
            batch_papers = papers[i:i + batch_size]

            # Build index texts
            index_texts = []
            for paper in batch_papers:
                index_text = self.build_paper_index_text(paper)
                index_texts.append(index_text)

            # Generate embeddings
            embeddings = await self.encode_texts_async(index_texts)

            # Update papers
            for paper, embedding in zip(batch_papers, embeddings):
                paper.full_embedding = embedding.tolist()

                # Also generate title and abstract embeddings separately
                if paper.title:
                    title_embedding = await self.encode_texts_async([paper.title])
                    paper.title_embedding = title_embedding[0].tolist()

                if paper.abstract:
                    abstract_embedding = await self.encode_texts_async([paper.abstract])
                    paper.abstract_embedding = abstract_embedding[0].tolist()

                updated_count += 1

            # Commit batch
            await session.commit()

        return updated_count

    async def find_similar_papers(
        self,
        session: AsyncSession,
        paper_id: int,
        limit: int = 10
    ) -> List[Tuple[Paper, float]]:
        """Find papers similar to a given paper."""

        # Get the source paper
        result = await session.execute(
            select(Paper).where(Paper.id == paper_id)
        )
        source_paper = result.scalar_one_or_none()

        if not source_paper or not source_paper.full_embedding:
            return []

        # Find similar papers
        query_embedding = np.array(source_paper.full_embedding)
        similar_papers = await self.search_papers_by_embedding(
            session, query_embedding, limit + 1  # +1 to exclude self
        )

        # Filter out the source paper
        return [(paper, score) for paper, score in similar_papers if paper.id != paper_id]


# Global embedding service instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
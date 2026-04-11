"""
Paper-related SQLAlchemy models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger, String, Text, Integer, DateTime,
    UniqueConstraint, CheckConstraint, ForeignKey, Boolean, Float
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from .base import Base, TimestampMixin


class Paper(Base, TimestampMixin):
    """Core paper entity."""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    arxiv_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authors: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    categories: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    venue: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    citation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    html_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Vector embeddings
    title_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1024), nullable=True)
    abstract_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1024), nullable=True)
    full_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1024), nullable=True)

    # Relationships
    paper_concepts = relationship("PaperConcept", back_populates="paper", cascade="all, delete-orphan")
    paper_authors = relationship("PaperAuthor", back_populates="paper", cascade="all, delete-orphan")
    explanations = relationship("Explanation", back_populates="paper", cascade="all, delete-orphan")
    summaries = relationship("PaperSummary", back_populates="paper", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "arxiv_id ~ '^[0-9]{4}\\.[0-9]{4,5}$|^[a-z\\\\-]+/[0-9]{7}$'",
            name="papers_arxiv_id_check"
        ),
    )

    def __repr__(self) -> str:
        return f"<Paper(id={self.id}, arxiv_id='{self.arxiv_id}', title='{self.title[:50]}...')>"


class Author(Base, TimestampMixin):
    """Author entity for better author tracking."""

    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    affiliations: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    h_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_citations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    paper_authors = relationship("PaperAuthor", back_populates="author", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Author(id={self.id}, name='{self.name}')>"


class PaperAuthor(Base):
    """Many-to-many relationship between papers and authors."""

    __tablename__ = "paper_authors"

    paper_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True)
    author_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_corresponding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    paper = relationship("Paper", back_populates="paper_authors")
    author = relationship("Author", back_populates="paper_authors")

    def __repr__(self) -> str:
        return f"<PaperAuthor(paper_id={self.paper_id}, author_id={self.author_id}, order={self.author_order})>"


class Concept(Base, TimestampMixin):
    """Extracted concepts: methods, tasks, datasets, etc."""

    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="method, task, dataset, metric, domain, keyword"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    aliases: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1024), nullable=True)
    paper_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    paper_concepts = relationship("PaperConcept", back_populates="concept", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint("name", "type", name="concepts_name_type_unique"),
        CheckConstraint(
            "type IN ('method', 'task', 'dataset', 'metric', 'domain', 'keyword')",
            name="concepts_type_check"
        ),
    )

    def __repr__(self) -> str:
        return f"<Concept(id={self.id}, name='{self.name}', type='{self.type}')>"


class PaperConcept(Base, TimestampMixin):
    """Many-to-many relationship between papers and concepts."""

    __tablename__ = "paper_concepts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    concept_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)

    # Relationships
    paper = relationship("Paper", back_populates="paper_concepts")
    concept = relationship("Concept", back_populates="paper_concepts")

    # Constraints
    __table_args__ = (
        UniqueConstraint("paper_id", "concept_id", name="paper_concepts_unique"),
    )

    def __repr__(self) -> str:
        return f"<PaperConcept(paper_id={self.paper_id}, concept_id={self.concept_id}, weight={self.weight})>"
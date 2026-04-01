"""
User workspace SQLAlchemy models.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger, String, Text, Boolean, Float, ForeignKey,
    CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class UserNote(Base, TimestampMixin):
    """User notes and annotations."""

    __tablename__ = "user_notes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[str] = mapped_column(String(20), default="general", nullable=False)
    linked_papers: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    linked_concepts: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<UserNote(id={self.id}, title='{self.title[:30]}...', type='{self.note_type}')>"


class ResearchQuestion(Base, TimestampMixin):
    """Research questions generated from analysis."""

    __tablename__ = "research_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="gap, contradiction, extension, application, methodology"
    )
    related_papers: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    novelty_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_by: Mapped[str] = mapped_column(String(50), default="system", nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "question_type IN ('gap', 'contradiction', 'extension', 'application', 'methodology')",
            name="research_questions_type_check"
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="research_questions_confidence_check"
        ),
        CheckConstraint(
            "novelty_score IS NULL OR (novelty_score >= 0 AND novelty_score <= 1)",
            name="research_questions_novelty_check"
        ),
    )

    def __repr__(self) -> str:
        return f"<ResearchQuestion(id={self.id}, type='{self.question_type}', question='{self.question[:50]}...')>"


class Collection(Base, TimestampMixin):
    """Paper collections (curated sets)."""

    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paper_ids: Mapped[List[int]] = mapped_column(JSONB, default=list, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Collection(id={self.id}, name='{self.name}', papers={len(self.paper_ids)})>"


class Comparison(Base, TimestampMixin):
    """Paper comparisons (side-by-side analysis)."""

    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    paper_ids: Mapped[List[int]] = mapped_column(JSONB, nullable=False)
    comparison_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    focus_aspects: Mapped[List[str]] = mapped_column(
        JSONB,
        default=["method", "task", "dataset", "results"],
        nullable=False
    )
    generated_by: Mapped[str] = mapped_column(String(50), default="system", nullable=False)

    def __repr__(self) -> str:
        return f"<Comparison(id={self.id}, papers={len(self.paper_ids)}, aspects={len(self.focus_aspects)})>"


class Explanation(Base, TimestampMixin):
    """Explanations for recommendations."""

    __tablename__ = "explanations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False
    )
    query_idea: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="relevance, method_similarity, task_similarity, gap_analysis, trend_analysis"
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    generated_by: Mapped[str] = mapped_column(String(50), default="system", nullable=False)

    # Relationships
    paper = relationship("Paper", back_populates="explanations")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "explanation_type IN ('relevance', 'method_similarity', 'task_similarity', 'gap_analysis', 'trend_analysis')",
            name="explanations_type_check"
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="explanations_confidence_check"
        ),
    )

    def __repr__(self) -> str:
        return f"<Explanation(id={self.id}, paper_id={self.paper_id}, type='{self.explanation_type}')>"
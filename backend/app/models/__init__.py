"""
SQLAlchemy models for Research Intelligence Platform.
"""

from .base import Base, TimestampMixin, SoftDeleteMixin
from .paper import Paper, Author, PaperAuthor, Concept, PaperConcept
from .graph import GraphNode, GraphEdge
from .workspace import UserNote, ResearchQuestion, Collection, Comparison, Explanation
from .trending import TrendingPaper

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",

    # Paper models
    "Paper",
    "Author",
    "PaperAuthor",
    "Concept",
    "PaperConcept",

    # Graph models
    "GraphNode",
    "GraphEdge",

    # Workspace models
    "UserNote",
    "ResearchQuestion",
    "Collection",
    "Comparison",
    "Explanation",

    # Trending models
    "TrendingPaper",
]
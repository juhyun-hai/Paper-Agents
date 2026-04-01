"""
Knowledge Graph SQLAlchemy models.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger, String, Text, Float, ForeignKey,
    CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from .base import Base, TimestampMixin


class GraphNode(Base, TimestampMixin):
    """Unified graph node representation."""

    __tablename__ = "graph_nodes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    node_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="paper, concept, author, venue, user_note, collection"
    )
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    properties: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1024), nullable=True)

    # Relationships
    source_edges = relationship("GraphEdge", foreign_keys="GraphEdge.source_node_id", back_populates="source_node", cascade="all, delete-orphan")
    target_edges = relationship("GraphEdge", foreign_keys="GraphEdge.target_node_id", back_populates="target_node", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint("node_type", "entity_id", name="graph_nodes_type_entity_unique"),
        CheckConstraint(
            "node_type IN ('paper', 'concept', 'author', 'venue', 'user_note', 'collection')",
            name="graph_nodes_type_check"
        ),
    )

    def __repr__(self) -> str:
        return f"<GraphNode(id={self.id}, type='{self.node_type}', label='{self.label[:30]}...')>"


class GraphEdge(Base, TimestampMixin):
    """Relationships between graph nodes."""

    __tablename__ = "graph_edges"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_node_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False
    )
    target_node_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False
    )
    edge_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="citation, similarity, uses_method, uses_dataset, same_author, same_venue, user_link, contains"
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    properties: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    source_node = relationship("GraphNode", foreign_keys=[source_node_id], back_populates="source_edges")
    target_node = relationship("GraphNode", foreign_keys=[target_node_id], back_populates="target_edges")

    # Constraints
    __table_args__ = (
        UniqueConstraint("source_node_id", "target_node_id", "edge_type", name="graph_edges_unique"),
        CheckConstraint(
            "edge_type IN ('citation', 'similarity', 'uses_method', 'uses_dataset', 'same_author', 'same_venue', 'user_link', 'contains')",
            name="graph_edges_type_check"
        ),
    )

    def __repr__(self) -> str:
        return f"<GraphEdge(id={self.id}, type='{self.edge_type}', weight={self.weight})>"
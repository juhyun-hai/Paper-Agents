"""
Knowledge Graph service for Research Intelligence Platform.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set
import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from sqlalchemy.orm import selectinload

from ..models import (
    Paper, Author, Concept, GraphNode, GraphEdge,
    PaperAuthor, PaperConcept
)
from ..core.config import settings
from .embedding_service import get_embedding_service


class GraphService:
    """Service for managing knowledge graph operations."""

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.max_nodes = settings.max_graph_nodes
        self.default_depth = settings.default_graph_depth

    async def build_paper_graph_nodes(self, session: AsyncSession) -> int:
        """Build graph nodes for all papers."""

        # Get papers without graph nodes
        papers_query = select(Paper).outerjoin(
            GraphNode,
            (GraphNode.node_type == "paper") & (GraphNode.entity_id == Paper.id)
        ).where(GraphNode.id.is_(None))

        result = await session.execute(papers_query)
        papers = result.scalars().all()

        if not papers:
            return 0

        nodes_created = 0

        for paper in papers:
            # Create paper node
            paper_node = GraphNode(
                node_type="paper",
                entity_id=paper.id,
                label=paper.title,
                properties={
                    "arxiv_id": paper.arxiv_id,
                    "categories": paper.categories,
                    "year": paper.year,
                    "citation_count": paper.citation_count,
                    "authors": paper.authors[:3],  # First 3 authors
                },
                embedding=paper.full_embedding
            )
            session.add(paper_node)
            nodes_created += 1

        await session.commit()
        return nodes_created

    async def build_concept_graph_nodes(self, session: AsyncSession) -> int:
        """Build graph nodes for concepts."""

        # Get concepts without graph nodes
        concepts_query = select(Concept).outerjoin(
            GraphNode,
            (GraphNode.node_type == "concept") & (GraphNode.entity_id == Concept.id)
        ).where(GraphNode.id.is_(None))

        result = await session.execute(concepts_query)
        concepts = result.scalars().all()

        if not concepts:
            return 0

        nodes_created = 0

        for concept in concepts:
            concept_node = GraphNode(
                node_type="concept",
                entity_id=concept.id,
                label=concept.name,
                properties={
                    "type": concept.type,
                    "description": concept.description,
                    "paper_count": concept.paper_count,
                    "aliases": concept.aliases
                },
                embedding=concept.embedding
            )
            session.add(concept_node)
            nodes_created += 1

        await session.commit()
        return nodes_created

    async def build_similarity_edges(self, session: AsyncSession, limit: int = 1000) -> int:
        """Build similarity edges between papers."""

        # Get paper nodes with embeddings
        paper_nodes_query = select(GraphNode).where(
            GraphNode.node_type == "paper",
            GraphNode.embedding.is_not(None)
        ).limit(limit)

        result = await session.execute(paper_nodes_query)
        paper_nodes = result.scalars().all()

        if len(paper_nodes) < 2:
            return 0

        edges_created = 0
        similarity_threshold = settings.similarity_threshold

        # Build similarity edges using vector similarity
        for i, node1 in enumerate(paper_nodes):
            # Find top-k similar papers for this node
            similar_query = select(
                GraphNode,
                (1 - GraphNode.embedding.cosine_distance(node1.embedding)).label('similarity')
            ).where(
                GraphNode.node_type == "paper",
                GraphNode.id != node1.id,
                GraphNode.embedding.is_not(None),
                (1 - GraphNode.embedding.cosine_distance(node1.embedding)) >= similarity_threshold
            ).order_by(
                GraphNode.embedding.cosine_distance(node1.embedding)
            ).limit(5)  # Top 5 similar papers

            similar_result = await session.execute(similar_query)
            similar_nodes = similar_result.all()

            for similar_node, similarity in similar_nodes:
                # Check if edge already exists
                existing_edge = await session.scalar(
                    select(GraphEdge).where(
                        GraphEdge.source_node_id == node1.id,
                        GraphEdge.target_node_id == similar_node.id,
                        GraphEdge.edge_type == "similarity"
                    )
                )

                if not existing_edge:
                    edge = GraphEdge(
                        source_node_id=node1.id,
                        target_node_id=similar_node.id,
                        edge_type="similarity",
                        weight=float(similarity),
                        properties={"similarity_score": float(similarity)}
                    )
                    session.add(edge)
                    edges_created += 1

                    # Add reverse edge
                    reverse_edge = GraphEdge(
                        source_node_id=similar_node.id,
                        target_node_id=node1.id,
                        edge_type="similarity",
                        weight=float(similarity),
                        properties={"similarity_score": float(similarity)}
                    )
                    session.add(reverse_edge)
                    edges_created += 1

            # Commit in batches
            if i % 10 == 0:
                await session.commit()

        await session.commit()
        return edges_created

    async def build_concept_edges(self, session: AsyncSession) -> int:
        """Build edges between papers and concepts."""

        # Get paper-concept relationships
        pc_query = select(PaperConcept).options(
            selectinload(PaperConcept.paper),
            selectinload(PaperConcept.concept)
        )

        result = await session.execute(pc_query)
        paper_concepts = result.scalars().all()

        edges_created = 0

        for pc in paper_concepts:
            # Get corresponding graph nodes
            paper_node = await session.scalar(
                select(GraphNode).where(
                    GraphNode.node_type == "paper",
                    GraphNode.entity_id == pc.paper_id
                )
            )

            concept_node = await session.scalar(
                select(GraphNode).where(
                    GraphNode.node_type == "concept",
                    GraphNode.entity_id == pc.concept_id
                )
            )

            if paper_node and concept_node:
                # Check if edge exists
                existing_edge = await session.scalar(
                    select(GraphEdge).where(
                        GraphEdge.source_node_id == paper_node.id,
                        GraphEdge.target_node_id == concept_node.id,
                        GraphEdge.edge_type == "uses_method"
                    )
                )

                if not existing_edge:
                    edge = GraphEdge(
                        source_node_id=paper_node.id,
                        target_node_id=concept_node.id,
                        edge_type="uses_method",
                        weight=pc.weight,
                        properties={
                            "confidence": pc.confidence,
                            "extraction_method": pc.extraction_method
                        }
                    )
                    session.add(edge)
                    edges_created += 1

        await session.commit()
        return edges_created

    async def get_subgraph(
        self,
        session: AsyncSession,
        center_node_id: int,
        depth: int = None,
        max_nodes: int = None
    ) -> Dict[str, Any]:
        """Get subgraph around a center node."""

        depth = depth or self.default_depth
        max_nodes = max_nodes or self.max_nodes

        visited_nodes = set()
        edges_result = []
        current_level = {center_node_id}

        for level in range(depth):
            if not current_level or len(visited_nodes) >= max_nodes:
                break

            # Get edges from current level nodes
            edges_query = select(GraphEdge, GraphNode).join(
                GraphNode, GraphEdge.target_node_id == GraphNode.id
            ).where(
                GraphEdge.source_node_id.in_(current_level)
            )

            result = await session.execute(edges_query)
            level_edges = result.all()

            next_level = set()

            for edge, target_node in level_edges:
                if edge.target_node_id not in visited_nodes and len(visited_nodes) < max_nodes:
                    edges_result.append({
                        "source": edge.source_node_id,
                        "target": edge.target_node_id,
                        "type": edge.edge_type,
                        "weight": edge.weight,
                        "properties": edge.properties
                    })
                    next_level.add(edge.target_node_id)

            visited_nodes.update(current_level)
            current_level = next_level

        # Get all involved nodes
        all_node_ids = {center_node_id}
        for edge in edges_result:
            all_node_ids.add(edge["source"])
            all_node_ids.add(edge["target"])

        nodes_query = select(GraphNode).where(GraphNode.id.in_(all_node_ids))
        nodes_result = await session.execute(nodes_query)
        nodes = nodes_result.scalars().all()

        nodes_data = []
        for node in nodes:
            nodes_data.append({
                "id": node.id,
                "type": node.node_type,
                "label": node.label,
                "properties": node.properties
            })

        return {
            "nodes": nodes_data,
            "edges": edges_result,
            "center_node": center_node_id,
            "depth": depth
        }

    async def find_shortest_path(
        self,
        session: AsyncSession,
        source_id: int,
        target_id: int,
        max_depth: int = 5
    ) -> Optional[List[int]]:
        """Find shortest path between two nodes."""

        # Use BFS to find shortest path
        visited = set()
        queue = [(source_id, [source_id])]

        while queue:
            current_id, path = queue.pop(0)

            if current_id == target_id:
                return path

            if len(path) > max_depth:
                continue

            if current_id in visited:
                continue

            visited.add(current_id)

            # Get neighbors
            edges_query = select(GraphEdge.target_node_id).where(
                GraphEdge.source_node_id == current_id
            )

            result = await session.execute(edges_query)
            neighbors = [row[0] for row in result.all()]

            for neighbor_id in neighbors:
                if neighbor_id not in visited:
                    queue.append((neighbor_id, path + [neighbor_id]))

        return None

    async def get_graph_statistics(self, session: AsyncSession) -> Dict[str, Any]:
        """Get graph statistics."""

        stats = {}

        # Node counts by type
        node_counts_query = select(
            GraphNode.node_type,
            func.count(GraphNode.id)
        ).group_by(GraphNode.node_type)

        result = await session.execute(node_counts_query)
        node_counts = dict(result.all())
        stats["node_counts"] = node_counts
        stats["total_nodes"] = sum(node_counts.values())

        # Edge counts by type
        edge_counts_query = select(
            GraphEdge.edge_type,
            func.count(GraphEdge.id)
        ).group_by(GraphEdge.edge_type)

        result = await session.execute(edge_counts_query)
        edge_counts = dict(result.all())
        stats["edge_counts"] = edge_counts
        stats["total_edges"] = sum(edge_counts.values())

        # Top connected nodes
        top_nodes_query = select(
            GraphNode.label,
            GraphNode.node_type,
            func.count(GraphEdge.source_node_id).label('degree')
        ).join(
            GraphEdge, GraphNode.id == GraphEdge.source_node_id
        ).group_by(
            GraphNode.id, GraphNode.label, GraphNode.node_type
        ).order_by(
            func.count(GraphEdge.source_node_id).desc()
        ).limit(10)

        result = await session.execute(top_nodes_query)
        top_nodes = [
            {"label": label, "type": node_type, "degree": degree}
            for label, node_type, degree in result.all()
        ]
        stats["top_connected_nodes"] = top_nodes

        return stats

    async def build_complete_graph(self, session: AsyncSession) -> Dict[str, int]:
        """Build complete knowledge graph."""

        print("🔗 Building Knowledge Graph...")

        # Step 1: Build paper nodes
        print("  📄 Creating paper nodes...")
        paper_nodes = await self.build_paper_graph_nodes(session)
        print(f"    ✅ Created {paper_nodes} paper nodes")

        # Step 2: Build concept nodes
        print("  🧠 Creating concept nodes...")
        concept_nodes = await self.build_concept_graph_nodes(session)
        print(f"    ✅ Created {concept_nodes} concept nodes")

        # Step 3: Build similarity edges
        print("  🔗 Creating similarity edges...")
        similarity_edges = await self.build_similarity_edges(session)
        print(f"    ✅ Created {similarity_edges} similarity edges")

        # Step 4: Build concept edges
        print("  🎯 Creating concept edges...")
        concept_edges = await self.build_concept_edges(session)
        print(f"    ✅ Created {concept_edges} concept edges")

        return {
            "paper_nodes": paper_nodes,
            "concept_nodes": concept_nodes,
            "similarity_edges": similarity_edges,
            "concept_edges": concept_edges,
            "total_nodes": paper_nodes + concept_nodes,
            "total_edges": similarity_edges + concept_edges
        }


# Global service instance
_graph_service = None

def get_graph_service() -> GraphService:
    """Get global graph service instance."""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
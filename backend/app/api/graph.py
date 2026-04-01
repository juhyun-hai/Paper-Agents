"""
Graph API endpoints for Research Intelligence Platform.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session
from ..services.graph_service import get_graph_service
from ..models import GraphNode as GraphNodeModel


# Request/Response Models
class GraphBuildRequest(BaseModel):
    """Request to build knowledge graph."""
    build_nodes: bool = True
    build_edges: bool = True
    edge_limit: int = Field(default=1000, description="Max papers to process for similarity edges")


class GraphBuildResponse(BaseModel):
    """Response from graph building."""
    paper_nodes: int
    concept_nodes: int
    similarity_edges: int
    concept_edges: int
    total_nodes: int
    total_edges: int
    processing_time_ms: int


class SubgraphRequest(BaseModel):
    """Request for subgraph around a node."""
    center_node_id: int
    depth: Optional[int] = Field(default=2, description="Graph traversal depth")
    max_nodes: Optional[int] = Field(default=50, description="Maximum nodes to return")


class GraphNode(BaseModel):
    """Graph node representation."""
    id: int
    type: str
    label: str
    properties: Dict[str, Any]


class GraphEdge(BaseModel):
    """Graph edge representation."""
    source: int
    target: int
    type: str
    weight: float
    properties: Dict[str, Any]


class SubgraphResponse(BaseModel):
    """Subgraph response."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    center_node: int
    depth: int
    processing_time_ms: int


class ShortestPathRequest(BaseModel):
    """Request for shortest path between nodes."""
    source_id: int
    target_id: int
    max_depth: int = Field(default=5, description="Maximum path depth")


class ShortestPathResponse(BaseModel):
    """Shortest path response."""
    path: Optional[List[int]]
    length: Optional[int]
    processing_time_ms: int


class GraphStatsResponse(BaseModel):
    """Graph statistics response."""
    node_counts: Dict[str, int]
    edge_counts: Dict[str, int]
    total_nodes: int
    total_edges: int
    top_connected_nodes: List[Dict[str, Any]]
    processing_time_ms: int


# Router
router = APIRouter(prefix="/api/graph", tags=["Graph"])


@router.post("/build", response_model=GraphBuildResponse)
async def build_graph(
    request: GraphBuildRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Build or update the knowledge graph."""
    import time
    start_time = time.time()

    try:
        graph_service = get_graph_service()

        if request.build_nodes and request.build_edges:
            # Build complete graph
            result = await graph_service.build_complete_graph(session)
        else:
            # Build selectively
            result = {
                "paper_nodes": 0,
                "concept_nodes": 0,
                "similarity_edges": 0,
                "concept_edges": 0
            }

            if request.build_nodes:
                paper_nodes = await graph_service.build_paper_graph_nodes(session)
                concept_nodes = await graph_service.build_concept_graph_nodes(session)
                result.update({
                    "paper_nodes": paper_nodes,
                    "concept_nodes": concept_nodes
                })

            if request.build_edges:
                similarity_edges = await graph_service.build_similarity_edges(
                    session, limit=request.edge_limit
                )
                concept_edges = await graph_service.build_concept_edges(session)
                result.update({
                    "similarity_edges": similarity_edges,
                    "concept_edges": concept_edges
                })

            result.update({
                "total_nodes": result.get("paper_nodes", 0) + result.get("concept_nodes", 0),
                "total_edges": result.get("similarity_edges", 0) + result.get("concept_edges", 0)
            })

        processing_time = int((time.time() - start_time) * 1000)

        return GraphBuildResponse(
            **result,
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph building failed: {str(e)}")


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(session: AsyncSession = Depends(get_async_session)):
    """Get knowledge graph statistics."""
    import time
    start_time = time.time()

    try:
        graph_service = get_graph_service()
        stats = await graph_service.get_graph_statistics(session)

        processing_time = int((time.time() - start_time) * 1000)

        return GraphStatsResponse(
            **stats,
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get graph stats: {str(e)}")


@router.post("/subgraph", response_model=SubgraphResponse)
async def get_subgraph(
    request: SubgraphRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Get subgraph around a center node."""
    import time
    start_time = time.time()

    try:
        graph_service = get_graph_service()

        # Get subgraph data
        subgraph_data = await graph_service.get_subgraph(
            session,
            center_node_id=request.center_node_id,
            depth=request.depth,
            max_nodes=request.max_nodes
        )

        processing_time = int((time.time() - start_time) * 1000)

        return SubgraphResponse(
            nodes=[GraphNode(**node) for node in subgraph_data["nodes"]],
            edges=[GraphEdge(**edge) for edge in subgraph_data["edges"]],
            center_node=subgraph_data["center_node"],
            depth=subgraph_data["depth"],
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subgraph query failed: {str(e)}")


@router.post("/shortest-path", response_model=ShortestPathResponse)
async def get_shortest_path(
    request: ShortestPathRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Find shortest path between two nodes."""
    import time
    start_time = time.time()

    try:
        graph_service = get_graph_service()

        path = await graph_service.find_shortest_path(
            session,
            source_id=request.source_id,
            target_id=request.target_id,
            max_depth=request.max_depth
        )

        processing_time = int((time.time() - start_time) * 1000)

        return ShortestPathResponse(
            path=path,
            length=len(path) if path else None,
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shortest path query failed: {str(e)}")


@router.get("/nodes/search")
async def search_nodes(
    q: str = Query(..., description="Search query"),
    node_type: Optional[str] = Query(None, description="Filter by node type"),
    limit: int = Query(20, description="Maximum results"),
    session: AsyncSession = Depends(get_async_session)
):
    """Search graph nodes by label."""
    try:
        from sqlalchemy import select, or_

        # Build search query
        query = select(GraphNodeModel).where(
            or_(
                GraphNodeModel.label.ilike(f"%{q}%"),
                GraphNodeModel.properties.op('->>')('description').ilike(f"%{q}%")
            )
        )

        if node_type:
            query = query.where(GraphNodeModel.node_type == node_type)

        query = query.limit(limit)

        result = await session.execute(query)
        nodes = result.scalars().all()

        return {
            "nodes": [
                {
                    "id": node.id,
                    "type": node.node_type,
                    "label": node.label,
                    "properties": node.properties
                }
                for node in nodes
            ],
            "total": len(nodes),
            "query": q
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Node search failed: {str(e)}")


@router.get("/nodes/{node_id}/neighbors")
async def get_node_neighbors(
    node_id: int,
    edge_type: Optional[str] = Query(None, description="Filter by edge type"),
    limit: int = Query(10, description="Maximum neighbors"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get direct neighbors of a node."""
    try:
        from sqlalchemy import select
        from ..models import GraphEdge

        # Build neighbors query
        query = select(GraphNodeModel, GraphEdge).join(
            GraphEdge, GraphNodeModel.id == GraphEdge.target_node_id
        ).where(GraphEdge.source_node_id == node_id)

        if edge_type:
            query = query.where(GraphEdge.edge_type == edge_type)

        query = query.limit(limit)

        result = await session.execute(query)
        neighbors_data = result.all()

        neighbors = []
        for neighbor_node, edge in neighbors_data:
            neighbors.append({
                "node": {
                    "id": neighbor_node.id,
                    "type": neighbor_node.node_type,
                    "label": neighbor_node.label,
                    "properties": neighbor_node.properties
                },
                "edge": {
                    "type": edge.edge_type,
                    "weight": edge.weight,
                    "properties": edge.properties
                }
            })

        return {
            "node_id": node_id,
            "neighbors": neighbors,
            "total": len(neighbors)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get neighbors: {str(e)}")
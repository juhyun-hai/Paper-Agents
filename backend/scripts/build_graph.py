#!/usr/bin/env python3
"""
Build knowledge graph from existing papers and concepts.
"""

import asyncio
import sys
import os
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from app.services.graph_service import get_graph_service
from sqlalchemy import select, func
from app.models import Paper, GraphNode, GraphEdge


async def build_knowledge_graph():
    """Build complete knowledge graph."""

    print("🔗 Knowledge Graph Builder")
    print("=" * 50)

    graph_service = get_graph_service()

    async with AsyncSessionLocal() as session:
        try:
            # Check current state
            print("📊 Checking current graph state...")

            paper_count = await session.scalar(select(func.count(Paper.id)))
            node_count = await session.scalar(select(func.count(GraphNode.id)))
            edge_count = await session.scalar(select(func.count(GraphEdge.id)))

            print(f"  📄 Papers in database: {paper_count}")
            print(f"  🔶 Nodes in graph: {node_count}")
            print(f"  🔗 Edges in graph: {edge_count}")

            if paper_count == 0:
                print("❌ No papers found. Please run data collection first.")
                return

            # Build complete graph
            print(f"\n🚀 Building complete knowledge graph...")
            start_time = time.time()

            result = await graph_service.build_complete_graph(session)

            build_time = time.time() - start_time

            print(f"\n🎉 Graph building completed in {build_time:.2f} seconds!")
            print("=" * 50)
            print("📊 GRAPH CONSTRUCTION SUMMARY:")
            print(f"  🔶 Paper nodes created: {result['paper_nodes']}")
            print(f"  🧠 Concept nodes created: {result['concept_nodes']}")
            print(f"  🔗 Similarity edges created: {result['similarity_edges']}")
            print(f"  🎯 Concept edges created: {result['concept_edges']}")
            print(f"  📊 Total nodes: {result['total_nodes']}")
            print(f"  📊 Total edges: {result['total_edges']}")

            # Show final statistics
            print(f"\n📈 Getting final graph statistics...")
            stats = await graph_service.get_graph_statistics(session)

            print(f"\n📋 FINAL GRAPH STATISTICS:")
            print(f"  📊 Total nodes: {stats['total_nodes']}")
            print(f"  📊 Total edges: {stats['total_edges']}")

            print(f"\n  🔶 Node types:")
            for node_type, count in stats['node_counts'].items():
                print(f"    • {node_type}: {count}")

            print(f"\n  🔗 Edge types:")
            for edge_type, count in stats['edge_counts'].items():
                print(f"    • {edge_type}: {count}")

            if stats.get('top_connected_nodes'):
                print(f"\n  🌟 Most connected nodes:")
                for i, node in enumerate(stats['top_connected_nodes'][:5], 1):
                    print(f"    {i}. {node['label'][:50]}... ({node['type']}, degree: {node['degree']})")

            print(f"\n✅ Knowledge graph is ready for exploration!")
            print(f"   Use /api/graph/subgraph to explore neighborhoods")
            print(f"   Use /api/graph/stats for detailed statistics")

        except Exception as e:
            print(f"❌ Error during graph construction: {e}")
            import traceback
            traceback.print_exc()


async def quick_graph_test():
    """Test graph functionality with a small subgraph."""

    print(f"\n🧪 Testing graph functionality...")
    graph_service = get_graph_service()

    async with AsyncSessionLocal() as session:
        try:
            # Get a random node for testing
            random_node = await session.scalar(
                select(GraphNode).where(GraphNode.node_type == "paper").limit(1)
            )

            if random_node:
                print(f"  🎯 Testing subgraph around: {random_node.label[:50]}...")

                subgraph = await graph_service.get_subgraph(
                    session,
                    center_node_id=random_node.id,
                    depth=2,
                    max_nodes=10
                )

                print(f"  ✅ Subgraph test successful:")
                print(f"    • Nodes returned: {len(subgraph['nodes'])}")
                print(f"    • Edges returned: {len(subgraph['edges'])}")
                print(f"    • Center node: {subgraph['center_node']}")
                print(f"    • Depth: {subgraph['depth']}")

            else:
                print(f"  ⚠️ No graph nodes found for testing")

        except Exception as e:
            print(f"  ❌ Graph test failed: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build knowledge graph")
    parser.add_argument("--test", action="store_true", help="Run graph functionality test")
    parser.add_argument("--stats-only", action="store_true", help="Show graph statistics only")

    args = parser.parse_args()

    if args.stats_only:
        # Just show stats
        async def show_stats():
            graph_service = get_graph_service()
            async with AsyncSessionLocal() as session:
                stats = await graph_service.get_graph_statistics(session)

                print("📊 Current Graph Statistics:")
                print(f"  Total nodes: {stats['total_nodes']}")
                print(f"  Total edges: {stats['total_edges']}")

                for node_type, count in stats['node_counts'].items():
                    print(f"  {node_type} nodes: {count}")

                for edge_type, count in stats['edge_counts'].items():
                    print(f"  {edge_type} edges: {count}")

        asyncio.run(show_stats())
    else:
        # Build graph
        asyncio.run(build_knowledge_graph())

        if args.test:
            asyncio.run(quick_graph_test())
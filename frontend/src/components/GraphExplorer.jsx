import React, { useState, useEffect } from 'react';
import { getGraphStats, buildKnowledgeGraph, searchGraphNodes, getSubgraph } from '../api/research';
import SimpleGraphViz from './SimpleGraphViz';

const GraphExplorer = () => {
  const [stats, setStats] = useState(null);
  const [isBuilding, setIsBuilding] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [subgraphData, setSubgraphData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    loadGraphStats();
  }, []);

  const loadGraphStats = async () => {
    try {
      const statsData = await getGraphStats();
      setStats(statsData);
    } catch (err) {
      console.error('Failed to load graph stats:', err);
    }
  };

  const handleBuildGraph = async () => {
    setIsBuilding(true);
    setError('');

    try {
      const result = await buildKnowledgeGraph();
      setStats(prev => ({
        ...prev,
        total_nodes: result.total_nodes,
        total_edges: result.total_edges,
        node_counts: {
          paper: result.paper_nodes,
          concept: result.concept_nodes
        },
        edge_counts: {
          similarity: result.similarity_edges,
          uses_method: result.concept_edges
        }
      }));

      // Refresh stats
      await loadGraphStats();
    } catch (err) {
      setError(err.message || 'Failed to build graph');
    } finally {
      setIsBuilding(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    try {
      const results = await searchGraphNodes(searchQuery.trim());
      setSearchResults(results.nodes || []);
    } catch (err) {
      console.error('Search failed:', err);
      setSearchResults([]);
    }
  };

  const handleNodeSelect = async (node) => {
    setSelectedNode(node);

    try {
      const subgraph = await getSubgraph({
        center_node_id: node.id,
        depth: 2,
        max_nodes: 20
      });
      setSubgraphData(subgraph);
    } catch (err) {
      console.error('Failed to get subgraph:', err);
      setSubgraphData(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Knowledge Graph Explorer
        </h1>
        <p className="text-gray-600">
          Explore relationships between papers, concepts, and research areas
        </p>
      </div>

      {/* Graph Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow border p-6">
          <div className="text-3xl font-bold text-blue-600 mb-2">
            {stats?.total_nodes || 0}
          </div>
          <div className="text-sm text-gray-600">Total Nodes</div>
          {stats?.node_counts && (
            <div className="mt-2 space-y-1">
              {Object.entries(stats.node_counts).map(([type, count]) => (
                <div key={type} className="text-xs text-gray-500">
                  {type}: {count}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow border p-6">
          <div className="text-3xl font-bold text-green-600 mb-2">
            {stats?.total_edges || 0}
          </div>
          <div className="text-sm text-gray-600">Total Edges</div>
          {stats?.edge_counts && (
            <div className="mt-2 space-y-1">
              {Object.entries(stats.edge_counts).map(([type, count]) => (
                <div key={type} className="text-xs text-gray-500">
                  {type}: {count}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow border p-6">
          <button
            onClick={handleBuildGraph}
            disabled={isBuilding}
            className="w-full bg-purple-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-purple-700 disabled:bg-gray-400 transition-colors"
          >
            {isBuilding ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                Building...
              </div>
            ) : (
              '🔨 Build/Update Graph'
            )}
          </button>
          <div className="text-xs text-gray-500 mt-2 text-center">
            Creates nodes and edges from papers
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Node Search */}
        <div className="bg-white rounded-lg shadow border">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              🔍 Search Nodes
            </h2>

            <div className="flex space-x-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search papers, concepts, or topics..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={handleSearch}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Search
              </button>
            </div>
          </div>

          <div className="p-6">
            {searchResults.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <div className="text-4xl mb-4">🕸️</div>
                <div>No nodes found</div>
                <div className="text-sm mt-1">Try searching for paper titles or concepts</div>
              </div>
            ) : (
              <div className="space-y-3">
                {searchResults.map((node) => (
                  <div
                    key={node.id}
                    onClick={() => handleNodeSelect(node)}
                    className="border border-gray-200 rounded-lg p-3 cursor-pointer hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="text-sm">
                            {node.type === 'paper' ? '📄' : '🧠'}
                          </span>
                          <span className="text-xs font-medium text-gray-600 uppercase">
                            {node.type}
                          </span>
                        </div>
                        <div className="font-medium text-sm text-gray-900">
                          {node.label}
                        </div>
                        {node.properties?.description && (
                          <div className="text-xs text-gray-600 mt-1">
                            {node.properties.description.slice(0, 100)}...
                          </div>
                        )}
                      </div>
                      <button className="text-blue-600 text-xs">
                        Explore →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Subgraph View */}
        <div className="bg-white rounded-lg shadow border">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              🕸️ Node Neighborhood
            </h2>
            {selectedNode && (
              <div className="text-sm text-gray-600 mt-2">
                Exploring: {selectedNode.label.slice(0, 50)}...
              </div>
            )}
          </div>

          <div className="p-6">
            {!selectedNode ? (
              <div className="text-center text-gray-500 py-8">
                <div className="text-4xl mb-4">🎯</div>
                <div>Select a node to explore</div>
                <div className="text-sm mt-1">
                  Click on a search result to see its connections
                </div>
              </div>
            ) : !subgraphData ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Graph Visualization */}
                <SimpleGraphViz
                  nodes={subgraphData.nodes || []}
                  edges={subgraphData.edges || []}
                  centerNode={subgraphData.center_node || selectedNode.id}
                  onNodeClick={(node) => {
                    // Handle node click - could navigate to paper or show details
                    if (node.type === 'paper' && node.properties?.arxiv_id) {
                      window.open(`/paper/${node.properties.arxiv_id}`, '_blank');
                    }
                  }}
                />

                {/* Subgraph Stats */}
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-sm font-medium text-gray-900 mb-2">
                    Neighborhood Summary
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <div className="font-medium text-gray-700">Nodes:</div>
                      <div className="text-gray-600">{subgraphData.nodes?.length || 0}</div>
                    </div>
                    <div>
                      <div className="font-medium text-gray-700">Connections:</div>
                      <div className="text-gray-600">{subgraphData.edges?.length || 0}</div>
                    </div>
                  </div>
                </div>

                {/* Connected Nodes */}
                <div>
                  <div className="text-sm font-medium text-gray-900 mb-3">
                    Connected Nodes
                  </div>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {subgraphData.nodes
                      ?.filter(node => node.id !== selectedNode.id)
                      .slice(0, 10)
                      .map((node) => (
                        <div key={node.id} className="flex items-center space-x-3 text-xs p-2 bg-gray-50 rounded">
                          <span>
                            {node.type === 'paper' ? '📄' : '🧠'}
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-gray-900 truncate">
                              {node.label}
                            </div>
                            <div className="text-gray-600">
                              {node.type}
                            </div>
                          </div>
                          <button
                            onClick={() => handleNodeSelect(node)}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            →
                          </button>
                        </div>
                      ))}
                  </div>
                </div>

                {/* Edge Types */}
                {subgraphData.edges && subgraphData.edges.length > 0 && (
                  <div>
                    <div className="text-sm font-medium text-gray-900 mb-3">
                      Connection Types
                    </div>
                    <div className="space-y-1">
                      {[...new Set(subgraphData.edges.map(e => e.type))].map(type => (
                        <div key={type} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded inline-block mr-2">
                          {type}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Top Connected Nodes */}
      {stats?.top_connected_nodes && stats.top_connected_nodes.length > 0 && (
        <div className="mt-8 bg-white rounded-lg shadow border p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            🌟 Most Connected Nodes
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stats.top_connected_nodes.slice(0, 6).map((node, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm">
                    {node.type === 'paper' ? '📄' : '🧠'}
                  </span>
                  <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                    {node.degree} connections
                  </span>
                </div>
                <div className="font-medium text-sm text-gray-900">
                  {node.label.slice(0, 60)}
                  {node.label.length > 60 && '...'}
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  {node.type}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GraphExplorer;
import React, { useEffect, useRef, useState } from 'react';

const SimpleGraphViz = ({ nodes = [], edges = [], centerNode = null, onNodeClick = null }) => {
  const svgRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 });

  useEffect(() => {
    if (!nodes.length) return;

    const svg = svgRef.current;
    const { width, height } = dimensions;

    // Clear previous content
    svg.innerHTML = '';

    // Create simple force layout positions
    const nodePositions = {};
    const radius = Math.min(width, height) * 0.3;
    const centerX = width / 2;
    const centerY = height / 2;

    // Position center node
    if (centerNode && nodes.find(n => n.id === centerNode)) {
      nodePositions[centerNode] = { x: centerX, y: centerY };
    }

    // Position other nodes in a circle
    const otherNodes = nodes.filter(n => n.id !== centerNode);
    otherNodes.forEach((node, index) => {
      const angle = (2 * Math.PI * index) / otherNodes.length;
      nodePositions[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      };
    });

    // Create SVG elements
    const svgElement = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svgElement.setAttribute('width', width);
    svgElement.setAttribute('height', height);
    svgElement.setAttribute('viewBox', `0 0 ${width} ${height}`);

    // Add edges
    edges.forEach(edge => {
      const sourcePos = nodePositions[edge.source];
      const targetPos = nodePositions[edge.target];

      if (sourcePos && targetPos) {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', sourcePos.x);
        line.setAttribute('y1', sourcePos.y);
        line.setAttribute('x2', targetPos.x);
        line.setAttribute('y2', targetPos.y);
        line.setAttribute('stroke', '#e5e7eb');
        line.setAttribute('stroke-width', Math.max(1, (edge.weight || 0.1) * 3));
        line.setAttribute('opacity', '0.6');
        svgElement.appendChild(line);
      }
    });

    // Add nodes
    nodes.forEach(node => {
      const pos = nodePositions[node.id];
      if (!pos) return;

      const isCenterNode = node.id === centerNode;
      const nodeSize = isCenterNode ? 12 : 8;
      const nodeColor = isCenterNode ? '#3b82f6' :
                       node.group === 'similar' ? '#10b981' : '#6b7280';

      // Node circle
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', pos.x);
      circle.setAttribute('cy', pos.y);
      circle.setAttribute('r', nodeSize);
      circle.setAttribute('fill', nodeColor);
      circle.setAttribute('stroke', '#ffffff');
      circle.setAttribute('stroke-width', '2');
      circle.style.cursor = 'pointer';

      // Add click handler
      if (onNodeClick) {
        circle.addEventListener('click', () => onNodeClick(node));
      }

      svgElement.appendChild(circle);

      // Node label (for center node only to avoid clutter)
      if (isCenterNode) {
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', pos.x);
        text.setAttribute('y', pos.y - nodeSize - 5);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-size', '12');
        text.setAttribute('font-weight', 'bold');
        text.setAttribute('fill', '#374151');
        text.textContent = node.label?.slice(0, 30) + (node.label?.length > 30 ? '...' : '');
        svgElement.appendChild(text);
      }
    });

    svg.appendChild(svgElement);

  }, [nodes, edges, centerNode, dimensions]);

  const handleNodeClick = (node) => {
    if (onNodeClick) {
      onNodeClick(node);
    }
  };

  return (
    <div className="w-full bg-gray-50 rounded-lg border p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900">
          📊 Graph Visualization
        </h3>
        <div className="text-xs text-gray-500">
          {nodes.length} nodes, {edges.length} edges
        </div>
      </div>

      <div className="relative bg-white rounded border" style={{ height: '400px' }}>
        {nodes.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <div className="text-4xl mb-2">🕸️</div>
              <div className="text-sm">No graph data</div>
              <div className="text-xs">Build the graph or search for nodes</div>
            </div>
          </div>
        ) : (
          <svg
            ref={svgRef}
            width="100%"
            height="100%"
            className="rounded"
          />
        )}
      </div>

      {/* Legend */}
      {nodes.length > 0 && (
        <div className="mt-3 flex items-center justify-center space-x-4 text-xs">
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span className="text-gray-600">Center Node</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-gray-600">Similar Papers</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 rounded-full bg-gray-500"></div>
            <span className="text-gray-600">Other Nodes</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default SimpleGraphViz;
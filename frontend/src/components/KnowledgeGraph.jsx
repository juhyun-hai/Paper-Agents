import React, { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import { useNavigate } from 'react-router-dom'
import { CATEGORY_COLORS, getCategoryLabel } from '../utils/categories.js'

function getNodeColor(node) {
  const cat = (node.categories || [])[0] || node.category || ''
  return CATEGORY_COLORS[cat] || '#9ca3af'
}

function getNodeRadius(node) {
  return Math.max(5, Math.min(20, 5 + Math.log1p(node.citation_count || 0) * 1.5))
}

export default function KnowledgeGraph({ data, highlightId, filterCategory, filterMinCitations }) {
  const svgRef = useRef(null)
  const navigate = useNavigate()
  const [tooltip, setTooltip] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [doubleClickFilter, setDoubleClickFilter] = useState(null)
  const simRef = useRef(null)

  const buildGraph = useCallback(() => {
    if (!data || !svgRef.current) return
    let { nodes, edges } = data

    if (!nodes || !nodes.length) return

    const isDark = document.documentElement.classList.contains('dark')

    // Apply filters
    let filteredNodes = nodes
    if (filterCategory) filteredNodes = filteredNodes.filter(n => (n.categories||[]).includes(filterCategory) || n.category === filterCategory)
    if (filterMinCitations > 0) filteredNodes = filteredNodes.filter(n => (n.citation_count || 0) >= filterMinCitations)
    if (doubleClickFilter) {
      const connected = new Set([doubleClickFilter])
      edges.forEach(e => {
        const src = e.source?.id || e.source
        const tgt = e.target?.id || e.target
        if (src === doubleClickFilter) connected.add(tgt)
        if (tgt === doubleClickFilter) connected.add(src)
      })
      filteredNodes = filteredNodes.filter(n => connected.has(n.id))
    }

    const nodeIds = new Set(filteredNodes.map(n => n.id))
    const filteredEdges = edges.filter(e => {
      const src = e.source?.id || e.source
      const tgt = e.target?.id || e.target
      return nodeIds.has(src) && nodeIds.has(tgt)
    })

    const W = svgRef.current.clientWidth || 900
    const H = svgRef.current.clientHeight || 600

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    // Zoom
    const g = svg.append('g')
    const zoom = d3.zoom()
      .scaleExtent([0.1, 5])
      .on('zoom', (event) => g.attr('transform', event.transform))
    svg.call(zoom)

    // Simulation
    const nodesCopy = filteredNodes.map(n => ({ ...n }))
    const edgesCopy = filteredEdges.map(e => ({ ...e }))

    const sim = d3.forceSimulation(nodesCopy)
      .alphaDecay(0.03)
      .force('link', d3.forceLink(edgesCopy).id(d => d.id).distance(80).strength(0.5))
      .force('charge', d3.forceManyBody().strength(-120))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide().radius(d => getNodeRadius(d) + 3))

    simRef.current = sim

    // Links
    const link = g.append('g')
      .selectAll('line')
      .data(edgesCopy)
      .join('line')
      .attr('stroke', isDark ? '#374151' : '#d1d5db')
      .attr('stroke-width', d => d.weight ? Math.max(0.5, d.weight * 2) : 1)
      .attr('stroke-opacity', 0.5)

    // Nodes
    const node = g.append('g')
      .selectAll('circle')
      .data(nodesCopy)
      .join('circle')
      .attr('r', d => getNodeRadius(d))
      .attr('fill', d => getNodeColor(d))
      .attr('stroke', d => d.id === highlightId ? '#fff' : isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.15)')
      .attr('stroke-width', d => d.id === highlightId ? 3 : 1)
      .attr('filter', d => d.id === highlightId ? 'drop-shadow(0 0 8px rgba(26,115,232,0.8))' : null)
      .style('cursor', 'pointer')
      .call(
        d3.drag()
          .on('start', (event, d) => {
            if (!event.active) sim.alphaTarget(0.3).restart()
            d.fx = d.x; d.fy = d.y
          })
          .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
          .on('end', (event, d) => {
            if (!event.active) sim.alphaTarget(0)
            d.fx = null; d.fy = null
          })
      )
      .on('mouseover', (event, d) => {
        setTooltip({
          x: event.clientX,
          y: event.clientY,
          title: d.title || d.id,
          authors: (d.authors || []).slice(0, 2).join(', '),
          citations: d.citation_count || 0,
          category: (d.categories || [])[0] || d.category || '',
        })
      })
      .on('mousemove', (event) => {
        setTooltip(t => t ? { ...t, x: event.clientX, y: event.clientY } : t)
      })
      .on('mouseout', () => setTooltip(null))
      .on('click', (event, d) => {
        event.stopPropagation()
        setSelectedNode(d)
      })
      .on('dblclick', (event, d) => {
        event.stopPropagation()
        setDoubleClickFilter(prev => prev === d.id ? null : d.id)
      })

    // Labels for larger nodes
    const label = g.append('g')
      .selectAll('text')
      .data(nodesCopy.filter(n => getNodeRadius(n) > 10))
      .join('text')
      .attr('text-anchor', 'middle')
      .attr('dy', d => getNodeRadius(d) + 12)
      .attr('font-size', 9)
      .attr('fill', isDark ? '#9ca3af' : '#6b7280')
      .attr('pointer-events', 'none')
      .text(d => (d.title || d.id).slice(0, 20) + ((d.title || d.id).length > 20 ? '…' : ''))

    sim.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)
      node
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
      label
        .attr('x', d => d.x)
        .attr('y', d => d.y)
    })

    svg.on('click', () => setSelectedNode(null))

    // Minimap
    const mm = svg.append('g').attr('transform', `translate(${W - 150}, ${H - 110})`)
    mm.append('rect').attr('width', 140).attr('height', 100).attr('rx', 6)
      .attr('fill', isDark ? '#1f2937' : 'white').attr('stroke', isDark ? '#374151' : '#e5e7eb').attr('stroke-width', 1)
      .attr('fill-opacity', 0.9)
    const mmScale = 0.12
    const mmG = mm.append('g').attr('transform', `translate(70, 50) scale(${mmScale})`)
    mmG.append('g')
      .selectAll('circle')
      .data(nodesCopy)
      .join('circle')
      .attr('cx', d => d.x - W / 2)
      .attr('cy', d => d.y - H / 2)
      .attr('r', 12)
      .attr('fill', d => getNodeColor(d))
      .attr('fill-opacity', 0.7)

    sim.on('tick.minimap', () => {
      mmG.selectAll('circle')
        .attr('cx', d => d.x - W / 2)
        .attr('cy', d => d.y - H / 2)
    })

    return () => sim.stop()
  }, [data, highlightId, filterCategory, filterMinCitations, doubleClickFilter])

  useEffect(() => {
    const cleanup = buildGraph()
    return cleanup
  }, [buildGraph])

  return (
    <div className="relative w-full h-full">
      <svg ref={svgRef} className="w-full h-full bg-gray-50 dark:bg-gray-900" />

      {tooltip && (
        <div
          className="fixed z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 text-xs max-w-xs pointer-events-none"
          style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}
        >
          <p className="font-semibold text-gray-900 dark:text-gray-100 mb-1 leading-snug">{tooltip.title}</p>
          {tooltip.authors && <p className="text-gray-500 dark:text-gray-400">{tooltip.authors}</p>}
          <div className="flex gap-2 mt-1">
            <span className="text-gray-400">{getCategoryLabel(tooltip.category)}</span>
            {tooltip.citations > 0 && <span className="text-gray-400">{tooltip.citations} citations</span>}
          </div>
        </div>
      )}

      {doubleClickFilter && (
        <div className="absolute top-4 left-4 bg-white dark:bg-gray-800 border border-primary rounded-lg px-3 py-2 text-xs shadow flex items-center gap-2">
          <span className="text-gray-600 dark:text-gray-300">Showing connected nodes only</span>
          <button onClick={() => setDoubleClickFilter(null)} className="text-primary font-medium hover:underline">Reset</button>
        </div>
      )}

      {selectedNode && (
        <div className="absolute top-0 right-0 h-full w-72 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 shadow-xl flex flex-col overflow-auto animate-slide-in">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-start justify-between gap-2">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-sm leading-snug">{selectedNode.title || selectedNode.id}</h3>
            <button onClick={() => setSelectedNode(null)} className="text-gray-400 hover:text-gray-600 flex-shrink-0">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="p-4 space-y-3 flex-1">
            {selectedNode.authors && selectedNode.authors.length > 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400">{selectedNode.authors.join(', ')}</p>
            )}
            {selectedNode.abstract && (
              <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed line-clamp-6">{selectedNode.abstract}</p>
            )}
            {selectedNode.citation_count > 0 && (
              <p className="text-xs text-gray-500">Citations: {selectedNode.citation_count}</p>
            )}
            <div className="flex flex-wrap gap-1">
              {(selectedNode.categories || []).map(c => (
                <span key={c} className="text-xs bg-blue-50 dark:bg-blue-900 text-blue-600 dark:text-blue-300 px-2 py-0.5 rounded">{getCategoryLabel(c)}</span>
              ))}
            </div>
          </div>
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={() => navigate(`/paper/${selectedNode.id}`)}
              className="w-full bg-primary hover:bg-primary-dark text-white rounded-lg py-2 text-sm font-medium transition"
            >
              View Paper
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

import React, { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { useNavigate } from 'react-router-dom'
import { CATEGORY_COLORS } from '../utils/categories.js'

function nodeColor(node) {
  const cat = (node.categories || [])[0] || node.category || ''
  return CATEGORY_COLORS[cat] || '#9ca3af'
}

export default function MiniGraph({ data, focusId }) {
  const svgRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (!data || !svgRef.current) return
    const { nodes = [], edges = [] } = data
    if (!nodes.length) return

    const container = svgRef.current.parentElement
    const W = container.clientWidth || 400
    const H = 280

    const svg = d3.select(svgRef.current)
      .attr('width', W)
      .attr('height', H)

    svg.selectAll('*').remove()

    const g = svg.append('g')

    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(edges).id((d) => d.id).distance(60))
      .force('charge', d3.forceManyBody().strength(-80))
      .force('center', d3.forceCenter(W / 2, H / 2))

    const link = g.append('g')
      .selectAll('line')
      .data(edges)
      .join('line')
      .attr('stroke', '#d1d5db')
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.7)

    const node = g.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d) => (d.id === focusId ? 10 : Math.max(4, Math.min(8, 4 + Math.log1p(d.citation_count || 0)))))
      .attr('fill', (d) => nodeColor(d))
      .attr('stroke', (d) => d.id === focusId ? '#fff' : 'none')
      .attr('stroke-width', (d) => d.id === focusId ? 2 : 0)
      .attr('cursor', 'pointer')
      .on('click', (_, d) => navigate(`/paper/${d.id}`))

    node.append('title').text((d) => d.title || d.id)

    sim.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y)
      node
        .attr('cx', (d) => d.x)
        .attr('cy', (d) => d.y)
    })

    return () => sim.stop()
  }, [data, focusId])

  return (
    <div className="w-full overflow-hidden rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700">
      <svg ref={svgRef} className="w-full" />
    </div>
  )
}

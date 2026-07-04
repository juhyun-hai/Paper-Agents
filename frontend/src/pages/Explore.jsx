import { useEffect, useRef, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import * as d3 from 'd3'
import { API_BASE } from '../api/client'

/**
 * Interactive paper map — Connected Papers 스타일.
 * 최근 featured 논문을 embedding 유사도로 연결한 force-directed 그래프.
 *
 * 색상: dataviz 검증 8-slot categorical palette (CVD-safe 순서).
 * 노드 크기: upvotes 로그 스케일. hover 툴팁 + 클릭 시 우측 상세 패널.
 */

// 검증된 categorical palette — light / dark 페어 (순서가 CVD 안전 장치)
const PALETTE_LIGHT = ['#2a78d6', '#1baf7a', '#eda100', '#008300', '#4a3aa7', '#e34948', '#e87ba4', '#eb6834']
const PALETTE_DARK  = ['#3987e5', '#199e70', '#c98500', '#008300', '#9085e9', '#e66767', '#d55181', '#d95926']
const OTHER_COLOR = { light: '#9ca3af', dark: '#6b7280' }

export default function Explore() {
  const svgRef = useRef(null)
  const simRef = useRef(null)
  const [days, setDays] = useState(14)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)     // 클릭된 node
  const [hidden, setHidden] = useState(new Set())    // legend로 숨긴 클러스터

  useEffect(() => {
    setLoading(true)
    fetch(`${API_BASE}/explore/graph?days=${days}&max_nodes=150&k=3`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [days])

  const isDark = () => document.documentElement.classList.contains('dark')
    || window.matchMedia('(prefers-color-scheme: dark)').matches

  const colorOf = useCallback((cluster, clusters) => {
    const dark = isDark()
    if (cluster === 'other') return dark ? OTHER_COLOR.dark : OTHER_COLOR.light
    const idx = clusters.indexOf(cluster)
    const pal = dark ? PALETTE_DARK : PALETTE_LIGHT
    return pal[idx % pal.length]
  }, [])

  // d3 렌더링
  useEffect(() => {
    if (!data || !data.nodes.length || !svgRef.current) return
    const { nodes: rawNodes, edges, clusters } = data
    const named = clusters.filter(c => c !== 'other')

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    const { width, height } = svgRef.current.getBoundingClientRect()

    const visible = rawNodes.filter(n => !hidden.has(n.cluster))
    const visIds = new Set(visible.map(n => n.id))
    const nodes = visible.map(n => ({ ...n }))
    const links = edges
      .filter(e => visIds.has(e.source) && visIds.has(e.target))
      .map(e => ({ ...e }))

    const g = svg.append('g')

    // zoom + pan
    svg.call(d3.zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', (ev) => g.attr('transform', ev.transform)))

    const dark = isDark()
    const linkColor = dark ? '#374151' : '#e5e7eb'

    const link = g.append('g')
      .selectAll('line').data(links).join('line')
      .attr('stroke', linkColor)
      .attr('stroke-width', d => 0.6 + d.weight * 1.6)
      .attr('stroke-opacity', 0.55)

    const rScale = (n) => 5 + Math.min(13, Math.log1p(n.upvotes) * 3.2)

    const node = g.append('g')
      .selectAll('circle').data(nodes).join('circle')
      .attr('r', rScale)
      .attr('fill', d => colorOf(d.cluster, named))
      .attr('stroke', dark ? '#111827' : '#ffffff')
      .attr('stroke-width', 1.5)
      .attr('cursor', 'pointer')

    // 상위 upvote 노드는 직접 라벨 (selective labeling)
    const topIds = new Set([...nodes].sort((a, b) => b.upvotes - a.upvotes).slice(0, 10).map(n => n.id))
    const label = g.append('g')
      .selectAll('text').data(nodes.filter(n => topIds.has(n.id))).join('text')
      .text(d => d.title.length > 34 ? d.title.slice(0, 32) + '…' : d.title)
      .attr('font-size', 10)
      .attr('fill', dark ? '#d1d5db' : '#374151')
      .attr('pointer-events', 'none')
      .attr('text-anchor', 'middle')

    // hover 툴팁 (HTML div)
    const tip = d3.select('#explore-tip')
    node
      .on('mouseenter', (ev, d) => {
        tip.style('display', 'block')
          .html(`<div class="font-semibold">${d.title}</div>
                 <div class="text-xs opacity-70 mt-0.5">${d.tag || d.cluster} · ▲${d.upvotes}${d.is_hai ? ' · 🎓 HAI' : ''}</div>`)
      })
      .on('mousemove', (ev) => {
        tip.style('left', (ev.pageX + 14) + 'px').style('top', (ev.pageY - 12) + 'px')
      })
      .on('mouseleave', () => tip.style('display', 'none'))
      .on('click', (ev, d) => { setSelected(d); ev.stopPropagation() })

    svg.on('click', () => setSelected(null))

    // drag
    node.call(d3.drag()
      .on('start', (ev, d) => {
        if (!ev.active) sim.alphaTarget(0.3).restart()
        d.fx = d.x; d.fy = d.y
      })
      .on('drag', (ev, d) => { d.fx = ev.x; d.fy = ev.y })
      .on('end', (ev, d) => {
        if (!ev.active) sim.alphaTarget(0)
        d.fx = null; d.fy = null
      }))

    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id)
        .distance(d => 60 - d.weight * 25).strength(d => d.weight))
      .force('charge', d3.forceManyBody().strength(-120))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(d => rScale(d) + 3))
      .on('tick', () => {
        link
          .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
        node.attr('cx', d => d.x).attr('cy', d => d.y)
        label.attr('x', d => d.x).attr('y', d => d.y - rScale(d) - 4)
      })
    simRef.current = sim
    return () => sim.stop()
  }, [data, hidden, colorOf])

  const named = (data?.clusters || []).filter(c => c !== 'other')

  return (
    <main className="max-w-[1400px] mx-auto px-4 py-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">🕸 Paper Map</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            최근 논문을 의미 유사도로 연결한 지도 — 드래그·줌·클릭으로 탐색
          </p>
        </div>
        {/* 기간 필터 */}
        <div className="flex items-center gap-1">
          {[7, 14, 30].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                days === d
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}>
              {d}일
            </button>
          ))}
        </div>
      </div>

      {/* Legend — 클러스터 토글 */}
      {named.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {[...named, 'other'].map((c) => {
            const off = hidden.has(c)
            return (
              <button key={c}
                onClick={() => {
                  const next = new Set(hidden)
                  off ? next.delete(c) : next.add(c)
                  setHidden(next)
                }}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border transition-all ${
                  off ? 'opacity-35' : ''
                } border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800`}>
                <span className="w-2.5 h-2.5 rounded-full"
                  style={{ background: c === 'other'
                    ? OTHER_COLOR.light
                    : PALETTE_LIGHT[named.indexOf(c) % PALETTE_LIGHT.length] }} />
                {c}
              </button>
            )
          })}
        </div>
      )}

      <div className="relative">
        {/* Graph canvas */}
        <div className="bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden"
          style={{ height: '640px' }}>
          {loading && (
            <div className="h-full flex items-center justify-center text-gray-400">
              그래프 로딩 중…
            </div>
          )}
          <svg ref={svgRef} className="w-full h-full" style={{ display: loading ? 'none' : 'block' }} />
        </div>

        {/* 클릭 상세 패널 */}
        {selected && (
          <div className="absolute top-4 right-4 w-80 max-w-[85vw] bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl p-4">
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-semibold text-gray-900 dark:text-white text-sm leading-snug">{selected.title}</h3>
              <button onClick={() => setSelected(null)}
                className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
              <span className="px-1.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300">{selected.tag || selected.cluster}</span>
              {selected.upvotes > 0 && <span className="text-gray-500">▲ {selected.upvotes}</span>}
              {selected.is_hai && <span className="text-blue-600 dark:text-blue-300">🎓 HAI</span>}
              {selected.date && <span className="text-gray-400">{selected.date}</span>}
            </div>
            <Link to={`/paper/${selected.id}`}
              className="mt-3 block text-center text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg py-2 font-medium transition-colors">
              {selected.has_summary ? '한국어 요약 보기 →' : '논문 상세 →'}
            </Link>
          </div>
        )}
      </div>

      {/* tooltip (fixed position, page-level) */}
      <div id="explore-tip"
        className="fixed z-50 hidden max-w-xs bg-gray-900/95 text-white text-sm rounded-lg px-3 py-2 pointer-events-none shadow-lg"
        style={{ display: 'none' }} />

      <p className="mt-3 text-xs text-gray-400 dark:text-gray-500">
        노드 크기 = 커뮤니티 인기 (▲) · 연결 = BGE-m3 임베딩 유사도 (cosine ≥ 0.5, 노드당 상위 3개) · 색 = 대표 키워드 클러스터
      </p>
    </main>
  )
}

import { useEffect, useRef, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import * as d3 from 'd3'
import { API_BASE } from '../api/client'

/**
 * Paper Map — 갤럭시 스타일 interactive graph.
 * 항상 딥-다크 캔버스 (Obsidian/Connected Papers 계열):
 * - 노드 glow (SVG feGaussianBlur) + 상위 노드 pulse
 * - hover 시 이웃만 밝히고 나머지 dim
 * - 시맨틱 줌: 확대할수록 라벨 더 많이 표시
 * - 클릭 → fly-to + glassmorphism 상세 패널
 * - 검색 → 매칭 노드 하이라이트
 */

// 다크 캔버스 전용으로 채도 올린 8색 (CVD-safe 순서 유지)
const PALETTE = ['#5ba3f5', '#2dd4a7', '#fbbf24', '#4ade80', '#a78bfa', '#f87171', '#f472b6', '#fb923c']
const OTHER = '#64748b'

export default function Explore() {
  const svgRef = useRef(null)
  const zoomRef = useRef(null)
  const [days, setDays] = useState(14)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [hidden, setHidden] = useState(new Set())
  const [query, setQuery] = useState('')

  useEffect(() => {
    setLoading(true)
    fetch(`${API_BASE}/explore/graph?days=${days}&max_nodes=150&k=3`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [days])

  const named = useMemo(() => (data?.clusters || []).filter(c => c !== 'other'), [data])
  const colorOf = (cluster) =>
    cluster === 'other' ? OTHER : PALETTE[named.indexOf(cluster) % PALETTE.length]

  useEffect(() => {
    if (!data || !data.nodes.length || !svgRef.current) return
    const { nodes: rawNodes, edges } = data

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    const { width, height } = svgRef.current.getBoundingClientRect()

    const visible = rawNodes.filter(n => !hidden.has(n.cluster))
    const visIds = new Set(visible.map(n => n.id))
    const nodes = visible.map(n => ({ ...n }))
    const links = edges
      .filter(e => visIds.has(e.source) && visIds.has(e.target))
      .map(e => ({ ...e }))

    // 인접 맵 (hover 이웃 하이라이트용)
    const adj = new Map()
    nodes.forEach(n => adj.set(n.id, new Set([n.id])))
    links.forEach(l => {
      adj.get(l.source)?.add(l.target)
      adj.get(l.target)?.add(l.source)
    })

    // ── defs: glow 필터 + 배경 그라데이션 ──────────────────────
    const defs = svg.append('defs')
    const glow = defs.append('filter').attr('id', 'nodeGlow')
      .attr('x', '-80%').attr('y', '-80%').attr('width', '260%').attr('height', '260%')
    glow.append('feGaussianBlur').attr('stdDeviation', 3.2).attr('result', 'blur')
    const m = glow.append('feMerge')
    m.append('feMergeNode').attr('in', 'blur')
    m.append('feMergeNode').attr('in', 'SourceGraphic')

    const strongGlow = defs.append('filter').attr('id', 'nodeGlowStrong')
      .attr('x', '-120%').attr('y', '-120%').attr('width', '340%').attr('height', '340%')
    strongGlow.append('feGaussianBlur').attr('stdDeviation', 7).attr('result', 'blur')
    const m2 = strongGlow.append('feMerge')
    m2.append('feMergeNode').attr('in', 'blur')
    m2.append('feMergeNode').attr('in', 'SourceGraphic')

    const bgGrad = defs.append('radialGradient').attr('id', 'bgGrad')
      .attr('cx', '50%').attr('cy', '38%').attr('r', '80%')
    bgGrad.append('stop').attr('offset', '0%').attr('stop-color', '#141b33')
    bgGrad.append('stop').attr('offset', '55%').attr('stop-color', '#0c1122')
    bgGrad.append('stop').attr('offset', '100%').attr('stop-color', '#070a15')

    svg.append('rect').attr('width', width).attr('height', height).attr('fill', 'url(#bgGrad)')

    // 별 배경 (subtle)
    const starLayer = svg.append('g')
    const rand = d3.randomLcg(42)
    for (let i = 0; i < 90; i++) {
      starLayer.append('circle')
        .attr('cx', rand() * width).attr('cy', rand() * height)
        .attr('r', rand() * 1.1 + 0.2)
        .attr('fill', '#8b9dc9')
        .attr('opacity', rand() * 0.35 + 0.05)
    }

    const g = svg.append('g')

    // zoom + 시맨틱 라벨
    let currentK = 1
    const zoom = d3.zoom()
      .scaleExtent([0.25, 5])
      .on('zoom', (ev) => {
        g.attr('transform', ev.transform)
        if (Math.abs(ev.transform.k - currentK) > 0.25) {
          currentK = ev.transform.k
          label.attr('display', d =>
            (topIds.has(d.id) || currentK > 1.6) ? null : 'none')
        }
      })
    svg.call(zoom)
    zoomRef.current = { svg, zoom }

    const rScale = (n) => 5 + Math.min(15, Math.log1p(n.upvotes) * 3.4)

    // ── edges: 소스 클러스터 색으로 은은하게 ──────────────────
    const link = g.append('g')
      .selectAll('line').data(links).join('line')
      .attr('stroke', d => {
        const src = nodes.find(n => n.id === d.source || n.id === d.source.id)
        return src ? colorOf(src.cluster) : OTHER
      })
      .attr('stroke-width', d => 0.5 + d.weight * 1.8)
      .attr('stroke-opacity', 0.22)
      .attr('stroke-linecap', 'round')

    // ── glow 헤일로 (노드 뒤 큰 blur 원) ───────────────────────
    const halo = g.append('g')
      .selectAll('circle').data(nodes).join('circle')
      .attr('r', d => rScale(d) * 2.1)
      .attr('fill', d => colorOf(d.cluster))
      .attr('opacity', 0.13)
      .attr('filter', 'url(#nodeGlowStrong)')
      .attr('pointer-events', 'none')

    // ── nodes ──────────────────────────────────────────────────
    const node = g.append('g')
      .selectAll('circle').data(nodes).join('circle')
      .attr('class', 'pnode')
      .attr('r', 0)
      .attr('fill', d => colorOf(d.cluster))
      .attr('stroke', '#0c1122')
      .attr('stroke-width', 1.2)
      .attr('filter', 'url(#nodeGlow)')
      .attr('cursor', 'pointer')

    // 입장 애니메이션 (stagger)
    node.transition().duration(700).delay((d, i) => i * 6)
      .ease(d3.easeBackOut.overshoot(1.4))
      .attr('r', rScale)

    // 상위 인기 3개 노드 pulse
    const top3 = new Set([...nodes].sort((a, b) => b.upvotes - a.upvotes).slice(0, 3).map(n => n.id))
    function pulse() {
      node.filter(d => top3.has(d.id))
        .transition().duration(1600).ease(d3.easeSinInOut)
        .attr('stroke', '#ffffff').attr('stroke-width', 2.2).attr('stroke-opacity', 0.85)
        .transition().duration(1600).ease(d3.easeSinInOut)
        .attr('stroke', '#0c1122').attr('stroke-width', 1.2).attr('stroke-opacity', 1)
        .on('end', function (d, i) { if (i === 0) pulse() })
    }
    setTimeout(pulse, 900)

    // ── labels (시맨틱 줌) ─────────────────────────────────────
    const topIds = new Set([...nodes].sort((a, b) => b.upvotes - a.upvotes).slice(0, 12).map(n => n.id))
    const label = g.append('g')
      .selectAll('text').data(nodes).join('text')
      .text(d => d.title.length > 36 ? d.title.slice(0, 34) + '…' : d.title)
      .attr('font-size', 10.5)
      .attr('font-weight', 500)
      .attr('fill', '#c7d2ee')
      .attr('paint-order', 'stroke')
      .attr('stroke', '#0a0f1f')
      .attr('stroke-width', 3)
      .attr('pointer-events', 'none')
      .attr('text-anchor', 'middle')
      .attr('display', d => topIds.has(d.id) ? null : 'none')

    // ── hover: 이웃 하이라이트 ─────────────────────────────────
    const tip = d3.select('#explore-tip')
    node
      .on('mouseenter', (ev, d) => {
        const nb = adj.get(d.id) || new Set()
        node.attr('opacity', o => nb.has(o.id) ? 1 : 0.12)
        halo.attr('opacity', o => nb.has(o.id) ? 0.2 : 0.03)
        label.attr('opacity', o => nb.has(o.id) ? 1 : 0.08)
        link
          .attr('stroke-opacity', l =>
            (l.source.id === d.id || l.target.id === d.id) ? 0.75 : 0.04)
          .attr('stroke-width', l =>
            (l.source.id === d.id || l.target.id === d.id) ? 1.2 + l.weight * 2.4 : 0.5)
        tip.style('display', 'block')
          .html(`<div class="font-semibold leading-snug">${d.title}</div>
                 <div class="text-[11px] opacity-60 mt-1">${d.tag || d.cluster} · HF▲${d.upvotes}${d.is_hai ? ' · 🎓' : ''}</div>`)
      })
      .on('mousemove', (ev) => {
        tip.style('left', (ev.pageX + 16) + 'px').style('top', (ev.pageY - 10) + 'px')
      })
      .on('mouseleave', () => {
        node.attr('opacity', 1)
        halo.attr('opacity', 0.13)
        label.attr('opacity', 1)
        link.attr('stroke-opacity', 0.22).attr('stroke-width', d => 0.5 + d.weight * 1.8)
        tip.style('display', 'none')
      })
      .on('click', (ev, d) => {
        setSelected(d)
        // fly-to
        const t = d3.zoomTransform(svg.node())
        svg.transition().duration(600).ease(d3.easeCubicOut)
          .call(zoom.transform, d3.zoomIdentity
            .translate(width / 2 - d.x * Math.max(t.k, 1.4), height / 2 - d.y * Math.max(t.k, 1.4))
            .scale(Math.max(t.k, 1.4)))
        ev.stopPropagation()
      })

    svg.on('click', () => setSelected(null))

    node.call(d3.drag()
      .on('start', (ev, d) => { if (!ev.active) sim.alphaTarget(0.25).restart(); d.fx = d.x; d.fy = d.y })
      .on('drag', (ev, d) => { d.fx = ev.x; d.fy = ev.y })
      .on('end', (ev, d) => { if (!ev.active) sim.alphaTarget(0); d.fx = null; d.fy = null }))

    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id)
        .distance(d => 65 - d.weight * 28).strength(d => d.weight * 0.9))
      .force('charge', d3.forceManyBody().strength(-140))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(d => rScale(d) + 4))
      .on('tick', () => {
        link
          .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
        node.attr('cx', d => d.x).attr('cy', d => d.y)
        halo.attr('cx', d => d.x).attr('cy', d => d.y)
        label.attr('x', d => d.x).attr('y', d => d.y - rScale(d) - 6)
      })

    return () => sim.stop()
  }, [data, hidden])

  // 검색 하이라이트 (.pnode만 — 별/헤일로는 안 건드림)
  useEffect(() => {
    if (!svgRef.current) return
    const q = query.trim().toLowerCase()
    const svg = d3.select(svgRef.current)
    if (!q) {
      svg.selectAll('.pnode').attr('opacity', 1)
      return
    }
    svg.selectAll('.pnode')
      .attr('opacity', d => (d && d.title && d.title.toLowerCase().includes(q)) ? 1 : 0.08)
  }, [query])

  return (
    <main className="relative min-h-[calc(100vh-64px)] bg-[#070a15]">
      {/* 상단 컨트롤 바 — 캔버스 위 글래스 */}
      <div className="absolute top-4 left-4 right-4 z-10 flex flex-col sm:flex-row sm:items-center gap-2 pointer-events-none">
        <div className="pointer-events-auto flex items-center gap-3 bg-white/[0.07] backdrop-blur-md border border-white/10 rounded-2xl px-4 py-2.5">
          <h1 className="text-base font-bold text-white whitespace-nowrap">🕸 Paper Map</h1>
          <div className="w-px h-5 bg-white/15" />
          <div className="flex items-center gap-1">
            {[7, 14, 30].map(d => (
              <button key={d} onClick={() => setDays(d)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  days === d ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/40'
                             : 'text-gray-300 hover:bg-white/10'}`}>
                {d}일
              </button>
            ))}
          </div>
        </div>
        <input
          type="text" value={query} onChange={e => setQuery(e.target.value)}
          placeholder="논문 제목 검색…"
          className="pointer-events-auto w-full sm:w-64 bg-white/[0.07] backdrop-blur-md border border-white/10 rounded-2xl px-4 py-2.5 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-indigo-400/50"
        />
      </div>

      {/* Legend — 좌하단 글래스 */}
      {named.length > 0 && (
        <div className="absolute bottom-4 left-4 z-10 flex flex-wrap gap-1.5 max-w-md">
          {[...named, 'other'].map((c) => {
            const off = hidden.has(c)
            return (
              <button key={c}
                onClick={() => {
                  const next = new Set(hidden)
                  off ? next.delete(c) : next.add(c)
                  setHidden(next)
                }}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium
                  bg-white/[0.07] backdrop-blur-md border border-white/10 text-gray-200
                  hover:bg-white/15 transition-all ${off ? 'opacity-30' : ''}`}>
                <span className="w-2 h-2 rounded-full" style={{
                  background: c === 'other' ? OTHER : PALETTE[named.indexOf(c) % PALETTE.length],
                  boxShadow: off ? 'none' : `0 0 6px ${c === 'other' ? OTHER : PALETTE[named.indexOf(c) % PALETTE.length]}`,
                }} />
                {c}
              </button>
            )
          })}
        </div>
      )}

      {/* 안내 — 우하단 */}
      <div className="absolute bottom-4 right-4 z-10 text-[11px] text-gray-500 bg-white/[0.04] backdrop-blur-sm rounded-lg px-3 py-1.5 hidden sm:block">
        드래그 이동 · 스크롤 줌 · 노드 클릭 = 상세 · 크기 = HF 인기
      </div>

      {/* Canvas */}
      <div className="w-full" style={{ height: 'calc(100vh - 64px)' }}>
        {loading && (
          <div className="h-full flex flex-col items-center justify-center text-gray-400 gap-3">
            <div className="w-10 h-10 rounded-full border-2 border-indigo-500/30 border-t-indigo-400 animate-spin" />
            <span className="text-sm">논문 지도를 그리는 중…</span>
          </div>
        )}
        <svg ref={svgRef} className="w-full h-full" style={{ display: loading ? 'none' : 'block' }} />
      </div>

      {/* 클릭 상세 — glassmorphism 패널 */}
      {selected && (
        <div className="absolute top-20 right-4 z-20 w-80 max-w-[85vw] bg-[#0e1428]/85 backdrop-blur-xl border border-white/15 rounded-2xl shadow-2xl shadow-black/50 p-5">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-semibold text-white text-sm leading-snug">{selected.title}</h3>
            <button onClick={() => setSelected(null)}
              className="text-gray-500 hover:text-gray-300 text-xl leading-none flex-shrink-0">×</button>
          </div>
          <div className="mt-2.5 flex flex-wrap gap-1.5 text-[11px]">
            <span className="px-2 py-0.5 rounded-full font-medium"
              style={{ background: `${colorOf(selected.cluster)}22`, color: colorOf(selected.cluster) }}>
              {selected.tag || selected.cluster}
            </span>
            {selected.upvotes > 0 && <span className="text-gray-400 px-1 py-0.5">HF▲ {selected.upvotes}</span>}
            {selected.is_hai && <span className="text-blue-300 px-1 py-0.5">🎓 HAI</span>}
            {selected.date && <span className="text-gray-500 px-1 py-0.5">{selected.date}</span>}
          </div>
          <Link to={`/paper/${selected.id}`}
            className="mt-4 block text-center text-sm bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 text-white rounded-xl py-2.5 font-medium transition-all shadow-lg shadow-indigo-500/30">
            {selected.has_summary ? '한국어 요약 보기 →' : '논문 상세 →'}
          </Link>
        </div>
      )}

      <div id="explore-tip"
        className="fixed z-50 hidden max-w-xs bg-[#0e1428]/95 backdrop-blur-md border border-white/10 text-white text-sm rounded-xl px-3.5 py-2.5 pointer-events-none shadow-2xl"
        style={{ display: 'none' }} />
    </main>
  )
}

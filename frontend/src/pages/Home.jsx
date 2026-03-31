import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import SearchBar from '../components/SearchBar.jsx'
import PaperCard from '../components/PaperCard.jsx'
import { PaperCardSkeleton } from '../components/Skeleton.jsx'
import MiniGraph from '../components/MiniGraph.jsx'
import HotTopics from '../components/HotTopics.jsx'
import { getStats, getGraph, getTrends } from '../api/client.js'

export default function Home() {
  const [trending, setTrending] = useState([])
  const [stats, setStats] = useState(null)
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getStats().catch(() => null),
      getGraph({ max_nodes: 60 }).catch(() => null),
      getTrends(60).catch(() => null),
    ]).then(([statsRes, graphRes, trendsRes]) => {
      setTrending(trendsRes?.trending_papers || statsRes?.top_papers || [])
      setStats(statsRes)
      setGraphData(graphRes)
      setLoading(false)
    })
  }, [])

  return (
    <main className="max-w-5xl mx-auto px-4 py-16 space-y-16">
      {/* Hero */}
      <section className="text-center space-y-6">
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white leading-tight mb-4">
          Find AI Research Papers
          <span className="text-primary"> That Matter</span>
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-300 max-w-xl mx-auto">
          AI-powered recommendations • 논문 연결 그래프 • 실시간 트렌드
        </p>
        <div className="max-w-2xl mx-auto">
          <SearchBar large />
        </div>
        <div className="flex flex-wrap justify-center gap-2 text-sm">
          <span className="text-gray-500 dark:text-gray-400">Try:</span>
          {['transformer', 'diffusion', 'BERT', 'computer vision'].map((q) => (
            <Link
              key={q}
              to={`/search?q=${encodeURIComponent(q)}`}
              className="text-primary hover:underline"
            >
              {q}
            </Link>
          ))}
        </div>
      </section>

      {/* Hot Topics */}
      <HotTopics />

      {/* Stats */}
      {stats && (
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Papers', value: stats.total_papers?.toLocaleString() },
            { label: 'Categories', value: stats.total_categories },
            { label: 'Graph Edges', value: stats.graph_edges?.toLocaleString() },
            { label: 'Indexed Today', value: stats.indexed_today?.toLocaleString() },
          ].filter(s => s.value != null).map((s) => (
            <div key={s.label} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-primary">{s.value}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{s.label}</p>
            </div>
          ))}
        </section>
      )}

      {/* Trending */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Trending Papers</h2>
          <Link to="/search?sort=citations" className="text-sm text-primary hover:underline">View all</Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading
            ? Array.from({ length: 6 }).map((_, i) => <PaperCardSkeleton key={i} />)
            : trending.slice(0, 6).map((p) => <PaperCard key={p.arxiv_id || p.id} paper={p} />)
          }
        </div>
      </section>

      {/* Mini graph preview */}
      {graphData && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Knowledge Graph Preview</h2>
            <Link to="/graph" className="text-sm text-primary hover:underline">Full Graph</Link>
          </div>
          <MiniGraph data={graphData} />
        </section>
      )}
    </main>
  )
}

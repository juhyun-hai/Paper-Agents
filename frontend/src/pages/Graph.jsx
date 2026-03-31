import React, { useEffect, useState } from 'react'
import KnowledgeGraph from '../components/KnowledgeGraph.jsx'
import { getGraph, getCategories } from '../api/client.js'
import { getCategoryLabel, CATEGORY_COLORS, ALL_CATEGORIES } from '../utils/categories.js'

export default function Graph() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterCategory, setFilterCategory] = useState('')
  const [filterMinCitations, setFilterMinCitations] = useState(0)
  const [maxNodes, setMaxNodes] = useState(200)

  useEffect(() => {
    setLoading(true)
    setError(null)
    const params = { max_nodes: maxNodes }
    if (filterCategory) params.category = filterCategory
    getGraph(params)
      .then((res) => {
        setData(res)
        setLoading(false)
      })
      .catch((e) => {
        setError(typeof e === 'string' ? e : 'Failed to load graph.')
        setLoading(false)
      })
  }, [maxNodes, filterCategory])

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Controls toolbar */}
      <div className="flex-shrink-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-2 flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Knowledge Graph</span>

        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 dark:bg-gray-800 dark:text-white focus:outline-none focus:border-primary"
        >
          <option value="">All Categories</option>
          {ALL_CATEGORIES.map((c) => <option key={c} value={c}>{getCategoryLabel(c)}</option>)}
        </select>

        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500 dark:text-gray-400">Min Citations:</label>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={filterMinCitations}
            onChange={(e) => setFilterMinCitations(Number(e.target.value))}
            className="w-24 accent-primary"
          />
          <span className="text-xs text-gray-600 dark:text-gray-300 w-6">{filterMinCitations}</span>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500 dark:text-gray-400">Max Nodes:</label>
          <select
            value={maxNodes}
            onChange={(e) => setMaxNodes(Number(e.target.value))}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1 dark:bg-gray-800 dark:text-white focus:outline-none focus:border-primary"
          >
            {[50, 100, 200, 300].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>

        {/* Legend */}
        <div className="ml-auto flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
          {ALL_CATEGORIES.map((cat) => (
            <span key={cat} className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: CATEGORY_COLORS[cat] }} />
              <span className="truncate max-w-[120px]">{getCategoryLabel(cat)}</span>
            </span>
          ))}
        </div>
      </div>

      {/* Graph area */}
      <div className="flex-1 relative overflow-hidden">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50 dark:bg-gray-900 z-10">
            <div className="text-center space-y-3">
              <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-sm text-gray-500 dark:text-gray-400">Loading graph…</p>
            </div>
          </div>
        )}

        {error && !loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50 dark:bg-gray-900 z-10">
            <div className="text-center text-red-500 dark:text-red-400 space-y-2">
              <p className="font-medium">{error}</p>
              <button onClick={() => window.location.reload()} className="text-sm text-primary hover:underline">Retry</button>
            </div>
          </div>
        )}

        {!loading && !error && data && (
          <KnowledgeGraph
            data={data}
            filterCategory={filterCategory}
            filterMinCitations={filterMinCitations}
          />
        )}

        {/* Usage hints */}
        <div className="absolute bottom-4 left-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-500 dark:text-gray-400 space-y-0.5 shadow">
          <p>Scroll to zoom • Drag nodes</p>
          <p>Click node for details • Double-click to filter</p>
        </div>
      </div>
    </div>
  )
}

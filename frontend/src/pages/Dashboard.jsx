import React, { useEffect, useState } from 'react'
import CategoryChart from '../components/CategoryChart.jsx'
import { StatCardSkeleton } from '../components/Skeleton.jsx'
import { getStats, getTrends, getCategories } from '../api/client.js'
import { getCategoryName } from '../utils/categories.js'

function StatCard({ label, value, sub, icon, color = 'text-primary' }) {
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 flex items-start gap-4">
      {icon && (
        <div className={`w-10 h-10 rounded-full flex items-center justify-center bg-blue-50 dark:bg-blue-900/30 ${color} flex-shrink-0`}>
          {icon}
        </div>
      )}
      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
        <p className={`text-2xl font-bold mt-0.5 ${color}`}>{value ?? '—'}</p>
        {sub && <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [trends, setTrends] = useState([])
  const [keywords, setKeywords] = useState({})
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [trendDays, setTrendDays] = useState(30)

  useEffect(() => {
    Promise.all([
      getStats().catch(() => null),
      getTrends(trendDays).catch(() => []),
      getCategories().catch(() => []),
    ]).then(([statsRes, trendsRes, catsRes]) => {
      setStats(statsRes)
      setTrends(trendsRes?.trending_papers || [])
      setKeywords(trendsRes?.trending_keywords || {})
      setCategories(catsRes?.categories || catsRes || [])
      setLoading(false)
    })
  }, [trendDays])

  return (
    <main className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>

      {/* Stat cards */}
      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)
          : (<>
              <StatCard
                label="Total Papers"
                value={stats?.total_papers?.toLocaleString()}
                icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
              />
              <StatCard
                label="Graph Edges"
                value={stats?.graph_edges?.toLocaleString()}
                color="text-green-600 dark:text-green-400"
                icon={<svg className="w-5 h-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>}
              />
              <StatCard
                label="Categories"
                value={stats?.total_categories}
                color="text-purple-600 dark:text-purple-400"
                icon={<svg className="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>}
              />
              <StatCard
                label="Indexed Today"
                value={stats?.indexed_today?.toLocaleString()}
                color="text-orange-600 dark:text-orange-400"
                icon={<svg className="w-5 h-5 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
              />
            </>)
        }
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Trending keywords chart */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 dark:text-white">Trending Keywords</h2>
            <select
              value={trendDays}
              onChange={(e) => setTrendDays(Number(e.target.value))}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1 dark:bg-gray-700 dark:text-white focus:outline-none focus:border-primary"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
          {Object.keys(keywords).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(keywords).slice(0, 8).map(([kw, count]) => {
                const max = Math.max(...Object.values(keywords))
                const pct = max > 0 ? (count / max) * 100 : 0
                return (
                  <div key={kw} className="flex items-center gap-3">
                    <span className="text-xs text-gray-600 dark:text-gray-300 w-32 truncate flex-shrink-0">{kw}</span>
                    <div className="flex-1 bg-gray-100 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                      <div className="bg-primary h-full rounded-full transition-all" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs text-gray-400 w-8 text-right">{count}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
              {loading ? (
                <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              ) : 'No trend data available yet'}
            </div>
          )}
        </div>

        {/* Category pie chart */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Papers by Category</h2>
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <CategoryChart data={categories} />
          )}
        </div>
      </div>

      {/* Category breakdown table */}
      {categories.length > 0 && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="font-semibold text-gray-900 dark:text-white">Category Breakdown</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50">
                <tr>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Category</th>
                  <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Papers</th>
                  <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {categories.map((cat, i) => {
                  const total = categories.reduce((s, c) => s + (c.count || c.value || 0), 0)
                  const count = cat.count || cat.value || 0
                  const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0
                  return (
                    <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                      <td className="px-6 py-3 text-gray-800 dark:text-gray-200 font-medium">
                        {getCategoryName(cat.id || cat.category || cat.name)}
                        <span className="text-xs text-gray-400 ml-1">({cat.id || cat.category})</span>
                      </td>
                      <td className="px-6 py-3 text-right text-gray-600 dark:text-gray-300">{count.toLocaleString()}</td>
                      <td className="px-6 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 bg-gray-200 dark:bg-gray-600 rounded-full h-1.5 overflow-hidden">
                            <div className="bg-primary h-full rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-gray-500 dark:text-gray-400 w-10 text-right">{pct}%</span>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  )
}

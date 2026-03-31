import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import PaperCard from '../components/PaperCard.jsx'
import MiniGraph from '../components/MiniGraph.jsx'
import { PaperCardSkeleton, SkeletonLine } from '../components/Skeleton.jsx'
import { getPaper, getRecommendations, getMiniGraph } from '../api/client.js'
import { getCategoryLabel, CATEGORY_TAILWIND } from '../utils/categories.js'

export default function Paper() {
  const { arxiv_id } = useParams()
  const [paper, setPaper] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      getPaper(arxiv_id),
      getRecommendations(arxiv_id).catch(() => []),
      getMiniGraph(arxiv_id).catch(() => null),
    ]).then(([paperRes, recsRes, graphRes]) => {
      setPaper(paperRes?.paper || paperRes)
      setRecommendations(recsRes?.recommendations || recsRes?.papers || recsRes || [])
      setGraphData(graphRes)
      setLoading(false)
    }).catch((e) => {
      setError(typeof e === 'string' ? e : 'Failed to load paper.')
      setLoading(false)
    })
  }, [arxiv_id])

  if (loading) return (
    <main className="max-w-4xl mx-auto px-4 py-10 space-y-6">
      <SkeletonLine className="h-8 w-3/4" />
      <SkeletonLine className="h-4 w-1/2" />
      <SkeletonLine className="h-4 w-full" />
      <SkeletonLine className="h-4 w-full" />
      <SkeletonLine className="h-4 w-5/6" />
    </main>
  )

  if (error) return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
        <p className="font-medium">{error}</p>
        <Link to="/" className="mt-3 inline-block text-sm text-primary hover:underline">Back to Home</Link>
      </div>
    </main>
  )

  if (!paper) return null

  const {
    title = 'Untitled',
    authors = [],
    abstract = '',
    categories = [],
    date = '',
    citation_count = 0,
    summary_ko,
    venue,
    arxiv_url,
    pdf_url,
  } = paper

  const dateStr = date ? new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : ''
  const displayAuthors = authors.join(', ')

  return (
    <main className="max-w-4xl mx-auto px-4 py-10 space-y-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
        <Link to="/" className="hover:text-primary">Home</Link>
        <span>/</span>
        <Link to="/search" className="hover:text-primary">Search</Link>
        <span>/</span>
        <span className="text-gray-700 dark:text-gray-200 truncate max-w-xs">{arxiv_id}</span>
      </nav>

      {/* Header */}
      <div className="space-y-4">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white leading-tight">{title}</h1>

        <p className="text-sm text-gray-500 dark:text-gray-400">{displayAuthors}</p>

        <div className="flex flex-wrap items-center gap-2">
          {categories.map((cat) => (
            <span key={cat} className={`text-xs px-2 py-0.5 rounded font-medium ${CATEGORY_TAILWIND[cat] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}`}>
              {getCategoryLabel(cat)}
            </span>
          ))}
          {dateStr && <span className="text-xs text-gray-400">{dateStr}</span>}
          {venue && <span className="text-xs bg-indigo-50 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 px-2 py-0.5 rounded font-medium">{venue}</span>}
          {citation_count > 0 && (
            <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded-full">
              {citation_count.toLocaleString()} citations
            </span>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          {arxiv_url && (
            <a href={arxiv_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm bg-primary hover:bg-primary-dark text-white px-4 py-2 rounded-lg font-medium transition">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              arXiv
            </a>
          )}
          {pdf_url && (
            <a href={pdf_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 px-4 py-2 rounded-lg font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
              </svg>
              PDF
            </a>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {/* Abstract */}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
            <h2 className="font-semibold text-gray-900 dark:text-white mb-3">Abstract</h2>
            <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{abstract}</p>
          </div>

          {/* Korean summary */}
          {summary_ko && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6">
              <h2 className="font-semibold text-blue-900 dark:text-blue-200 mb-3 flex items-center gap-2">
                <span>한국어 요약</span>
                <span className="text-xs font-normal text-blue-500 dark:text-blue-400">AI-generated</span>
              </h2>
              <p className="text-sm text-blue-800 dark:text-blue-200 leading-relaxed">{summary_ko}</p>
            </div>
          )}
        </div>

        {/* Side: mini graph */}
        <div className="space-y-4">
          {graphData && (
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white text-sm mb-3">Related Paper Graph</h3>
              <MiniGraph data={graphData} focusId={arxiv_id} />
              <Link to="/graph" className="block text-xs text-center text-primary hover:underline mt-2">Open full graph</Link>
            </div>
          )}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 text-sm space-y-2">
            <h3 className="font-semibold text-gray-900 dark:text-white">Paper Info</h3>
            <div className="flex justify-between text-gray-500 dark:text-gray-400">
              <span>ID</span><span className="font-mono text-xs text-gray-700 dark:text-gray-200">{arxiv_id}</span>
            </div>
            {dateStr && <div className="flex justify-between text-gray-500 dark:text-gray-400"><span>Published</span><span>{dateStr}</span></div>}
            {citation_count > 0 && <div className="flex justify-between text-gray-500 dark:text-gray-400"><span>Citations</span><span>{citation_count.toLocaleString()}</span></div>}
          </div>
        </div>
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Related Papers</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {recommendations.slice(0, 6).map((p) => (
              <PaperCard key={p.arxiv_id || p.id} paper={p} showSimilarity />
            ))}
          </div>
        </section>
      )}
    </main>
  )
}

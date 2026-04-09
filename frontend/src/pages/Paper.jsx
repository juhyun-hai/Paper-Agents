import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import PaperCard from '../components/PaperCard.jsx'
import PaperSummary from '../components/PaperSummary.jsx'
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
  const [activeTab, setActiveTab] = useState('abstract')

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
    <main className="max-w-6xl mx-auto px-4 py-10 space-y-6">
      <SkeletonLine className="h-8 w-3/4" />
      <SkeletonLine className="h-4 w-1/2" />
      <SkeletonLine className="h-4 w-full" />
      <SkeletonLine className="h-4 w-full" />
      <SkeletonLine className="h-4 w-5/6" />
    </main>
  )

  if (error) return (
    <main className="max-w-6xl mx-auto px-4 py-10">
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

  const tabs = [
    { id: 'abstract', label: '📄 Abstract', icon: '📄' },
    { id: 'summary', label: '🤖 AI 요약', icon: '🤖' },
    { id: 'related', label: '🔗 Related Papers', icon: '🔗' },
  ]

  return (
    <main className="max-w-6xl mx-auto px-4 py-10 space-y-8">
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

        <p className="text-lg text-gray-600 dark:text-gray-300">{displayAuthors}</p>

        <div className="flex flex-wrap items-center gap-3">
          {categories.map((cat) => (
            <span key={cat} className={`text-xs px-2 py-1 rounded font-medium ${CATEGORY_TAILWIND[cat] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}`}>
              {getCategoryLabel(cat)}
            </span>
          ))}
          {dateStr && <span className="text-sm text-gray-500">📅 {dateStr}</span>}
          {venue && <span className="text-sm bg-indigo-50 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 px-3 py-1 rounded-full font-medium">🏛️ {venue}</span>}
          {citation_count > 0 && (
            <span className="text-sm bg-yellow-50 dark:bg-yellow-900 text-yellow-600 dark:text-yellow-300 px-3 py-1 rounded-full font-medium">
              📊 {citation_count.toLocaleString()} citations
            </span>
          )}
        </div>

        <div className="flex flex-wrap gap-3">
          {arxiv_url && (
            <a href={arxiv_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition">
              📚 arXiv
            </a>
          )}
          {pdf_url && (
            <a href={pdf_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium transition">
              📄 PDF
            </a>
          )}
          <a
            href={`https://arxiv.org/pdf/${arxiv_id}.pdf`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg font-medium transition">
            📋 Download PDF
          </a>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Main content */}
        <div className="lg:col-span-3">
          {/* Tabs */}
          <div className="border-b border-gray-200 mb-6">
            <nav className="flex space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="min-h-[500px]">
            {activeTab === 'abstract' && (
              <div className="space-y-6">
                {/* Abstract */}
                <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">📄 Abstract</h2>
                  <p className="text-gray-700 dark:text-gray-300 leading-relaxed text-base">{abstract}</p>
                </div>

                {/* Korean summary if exists */}
                {summary_ko && (
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6">
                    <h2 className="text-xl font-semibold text-blue-900 dark:text-blue-200 mb-4 flex items-center gap-2">
                      <span>🇰🇷 한국어 요약</span>
                      <span className="text-xs font-normal text-blue-500 dark:text-blue-400 bg-blue-100 px-2 py-1 rounded">AI-generated</span>
                    </h2>
                    <p className="text-blue-800 dark:text-blue-200 leading-relaxed text-base">{summary_ko}</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'summary' && (
              <PaperSummary arxivId={arxiv_id} paper={paper} />
            )}

            {activeTab === 'related' && (
              <div className="space-y-6">
                {recommendations.length > 0 ? (
                  <div className="grid grid-cols-1 gap-4">
                    {recommendations.map((p) => (
                      <PaperCard key={p.arxiv_id || p.id} paper={p} showSimilarity />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <div className="text-4xl mb-4">🔍</div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      관련 논문을 찾고 있습니다
                    </h3>
                    <p className="text-gray-600">
                      유사한 연구나 관련 논문들을 분석 중입니다.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Paper Info Card */}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-3">📊 Paper Info</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">arXiv ID</span>
                <span className="font-mono text-xs text-gray-700 dark:text-gray-200 bg-gray-100 px-2 py-1 rounded">
                  {arxiv_id}
                </span>
              </div>
              {dateStr && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Published</span>
                  <span className="text-gray-700 dark:text-gray-200">{dateStr}</span>
                </div>
              )}
              {citation_count > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Citations</span>
                  <span className="text-gray-700 dark:text-gray-200">{citation_count.toLocaleString()}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-500">Authors</span>
                <span className="text-gray-700 dark:text-gray-200">{authors.length}</span>
              </div>
            </div>
          </div>

          {/* Mini Graph */}
          {graphData && (
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
              <h3 className="font-semibold text-gray-900 dark:text-white text-sm mb-3">🕸️ Related Graph</h3>
              <MiniGraph data={graphData} focusId={arxiv_id} />
            </div>
          )}

          {/* Quick Actions */}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
            <h3 className="font-semibold text-gray-900 dark:text-white text-sm mb-3">⚡ Quick Actions</h3>
            <div className="space-y-2 text-sm">
              <button
                onClick={() => setActiveTab('summary')}
                className="w-full text-left px-3 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg transition"
              >
                🤖 AI 요약 생성
              </button>
              <button
                onClick={() => setActiveTab('related')}
                className="w-full text-left px-3 py-2 bg-green-50 hover:bg-green-100 text-green-700 rounded-lg transition"
              >
                🔗 관련 논문 찾기
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

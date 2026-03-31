import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import PaperCard from '../components/PaperCard.jsx'
import { PaperCardSkeleton } from '../components/Skeleton.jsx'
import {
  getSavedPapers,
  getCollections,
  getPapersByCollection,
  searchSavedPapers,
  movePaper,
  removePaper,
  getStorageStats,
  exportCollections
} from '../utils/collections.js'

const COLLECTION_COLORS = {
  'saved': { bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-200 dark:border-blue-800' },
  'to-read': { bg: 'bg-orange-50 dark:bg-orange-900/20', text: 'text-orange-700 dark:text-orange-300', border: 'border-orange-200 dark:border-orange-800' },
  'favorites': { bg: 'bg-red-50 dark:bg-red-900/20', text: 'text-red-700 dark:text-red-300', border: 'border-red-200 dark:border-red-800' }
}

export default function Collections() {
  const [collections, setCollections] = useState({})
  const [papers, setPapers] = useState([])
  const [activeCollection, setActiveCollection] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({})

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    filterPapers()
  }, [activeCollection, searchQuery])

  const loadData = () => {
    setLoading(true)
    const collectionsData = getCollections()
    const allPapers = getSavedPapers()
    const storageStats = getStorageStats()

    setCollections(collectionsData)
    setPapers(allPapers)
    setStats(storageStats)
    setLoading(false)
  }

  const filterPapers = () => {
    let filteredPapers

    if (searchQuery.trim()) {
      filteredPapers = searchSavedPapers(searchQuery)
    } else if (activeCollection === 'all') {
      filteredPapers = getSavedPapers()
    } else {
      filteredPapers = getPapersByCollection(activeCollection)
    }

    // Sort by saved date (newest first)
    filteredPapers.sort((a, b) => new Date(b.savedAt) - new Date(a.savedAt))
    setPapers(filteredPapers)
  }

  const handleMoveToCollection = (arxivId, newCollectionId) => {
    const result = movePaper(arxivId, newCollectionId)
    if (result.success) {
      loadData() // Reload to update counts
      filterPapers()
    }
  }

  const handleRemovePaper = (arxivId) => {
    const result = removePaper(arxivId)
    if (result.success) {
      loadData()
      filterPapers()
    }
  }

  if (loading) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-6 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <PaperCardSkeleton key={i} />
          ))}
        </div>
      </main>
    )
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              📚 내 컬렉션
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              저장한 논문들을 관리하세요
            </p>
          </div>

          {stats.totalPapers > 0 && (
            <button
              onClick={exportCollections}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-sm flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              백업
            </button>
          )}
        </div>

        {/* Stats */}
        {stats.totalPapers > 0 && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="text-2xl font-bold text-primary">{stats.totalPapers}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">저장된 논문</div>
            </div>
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="text-2xl font-bold text-primary">{stats.collections}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">컬렉션</div>
            </div>
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="text-2xl font-bold text-orange-500">{stats.storagePercent}%</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">저장소 사용량</div>
            </div>
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="text-2xl font-bold text-green-500">
                {stats.oldestPaper ? Math.floor((Date.now() - new Date(stats.oldestPaper)) / (1000 * 60 * 60 * 24)) : 0}일
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">가장 오래된 저장</div>
            </div>
          </div>
        )}
      </div>

      {stats.totalPapers === 0 ? (
        // Empty State
        <div className="text-center py-16">
          <div className="text-6xl mb-4">📚</div>
          <h3 className="text-xl font-medium text-gray-900 dark:text-gray-100 mb-2">
            아직 저장된 논문이 없습니다
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-6">
            관심 있는 논문의 북마크 버튼을 클릭해서 저장해보세요
          </p>
          <Link
            to="/"
            className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
          >
            논문 둘러보기
          </Link>
        </div>
      ) : (
        <>
          {/* Search and Filters */}
          <div className="mb-6 space-y-4">
            {/* Search */}
            <div className="relative max-w-md">
              <input
                type="text"
                placeholder="저장된 논문 검색..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 pl-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <svg
                className="absolute left-3 top-2.5 h-4 w-4 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>

            {/* Collection Tabs */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setActiveCollection('all')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeCollection === 'all'
                    ? 'bg-gray-800 dark:bg-gray-200 text-white dark:text-gray-900'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                전체 ({stats.totalPapers})
              </button>

              {Object.entries(collections).map(([id, collection]) => {
                const colors = COLLECTION_COLORS[id] || COLLECTION_COLORS['saved']
                return (
                  <button
                    key={id}
                    onClick={() => setActiveCollection(id)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
                      activeCollection === id
                        ? `${colors.bg} ${colors.text} ${colors.border}`
                        : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    {collection.name} ({collection.count || 0})
                  </button>
                )
              })}
            </div>
          </div>

          {/* Papers Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {papers.map((paper) => (
              <div key={paper.arxiv_id} className="relative">
                <PaperCard paper={paper} />

                {/* Collection Actions Overlay */}
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-2 min-w-32">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">이동</div>
                    {Object.entries(collections).map(([id, collection]) => (
                      <button
                        key={id}
                        onClick={() => handleMoveToCollection(paper.arxiv_id, id)}
                        disabled={paper.collection === id}
                        className={`block w-full text-left px-2 py-1 text-xs rounded hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed ${
                          paper.collection === id ? 'bg-gray-100 dark:bg-gray-700' : ''
                        }`}
                      >
                        {collection.name}
                      </button>
                    ))}
                    <hr className="my-1 border-gray-200 dark:border-gray-700" />
                    <button
                      onClick={() => handleRemovePaper(paper.arxiv_id)}
                      className="block w-full text-left px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                    >
                      삭제
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {papers.length === 0 && (searchQuery || activeCollection !== 'all') && (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">🔍</div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                검색 결과가 없습니다
              </h3>
              <p className="text-gray-500 dark:text-gray-400">
                다른 검색어나 컬렉션을 시도해보세요
              </p>
            </div>
          )}
        </>
      )}
    </main>
  )
}
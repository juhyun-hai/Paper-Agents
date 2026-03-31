import React, { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import SearchBar from '../components/SearchBar.jsx'
import PaperCard from '../components/PaperCard.jsx'
import Sidebar from '../components/Sidebar.jsx'
import { PaperCardSkeleton } from '../components/Skeleton.jsx'
import { searchPapers } from '../api/client.js'

const PAGE_SIZE = 10

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') || ''

  const [papers, setPapers] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [filters, setFilters] = useState({
    categories: [],
    sort: searchParams.get('sort') || 'relevance',
    dateFrom: '',
    dateTo: '',
  })

  const doSearch = useCallback(async (query, newFilters, newOffset, append = false) => {
    if (!query.trim() && !newFilters.categories.length) return
    setLoading(true)
    setError(null)
    try {
      const params = {
        q: query,
        limit: PAGE_SIZE,
        offset: newOffset,
        sort: newFilters.sort,
      }
      if (newFilters.categories.length) params.category = newFilters.categories.join(',')
      if (newFilters.dateFrom) params.date_from = newFilters.dateFrom
      if (newFilters.dateTo) params.date_to = newFilters.dateTo

      const res = await searchPapers(params)
      const results = res?.papers || res || []
      const tot = res?.total || results.length

      setPapers((prev) => append ? [...prev, ...results] : results)
      setTotal(tot)
      setHasMore(newOffset + PAGE_SIZE < tot)
    } catch (e) {
      setError(typeof e === 'string' ? e : 'Search failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    setPapers([])
    setOffset(0)
    doSearch(q, filters, 0, false)
  }, [q, filters])

  function handleSearch(newQ) {
    setSearchParams({ q: newQ })
  }

  function handleFiltersChange(newFilters) {
    setFilters(newFilters)
    setOffset(0)
  }

  function loadMore() {
    const next = offset + PAGE_SIZE
    setOffset(next)
    doSearch(q, filters, next, true)
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <div className="max-w-2xl">
        <SearchBar initialQuery={q} onSearch={handleSearch} />
      </div>

      {q && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {loading ? 'Searching…' : `${total.toLocaleString()} results for `}
          {!loading && <span className="font-medium text-gray-700 dark:text-gray-200">"{q}"</span>}
        </p>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        <Sidebar filters={filters} onChange={handleFiltersChange} />

        <div className="flex-1 space-y-4">
          {!q && !filters.categories.length && !loading && (
            <div className="flex flex-col items-center justify-center py-24 text-center space-y-6">
              <div className="w-20 h-20 bg-gradient-to-br from-primary/10 to-purple-500/10 rounded-2xl flex items-center justify-center">
                <svg className="w-10 h-10 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">논문을 찾아보세요</h3>
                <p className="text-gray-600 dark:text-gray-300 mb-4 max-w-sm">키워드, 저자명, arXiv ID로 검색할 수 있습니다</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {['transformer', 'diffusion', 'BERT', 'computer vision'].map(hint => (
                    <button
                      key={hint}
                      onClick={() => handleSearch(hint)}
                      className="px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-full text-sm text-primary hover:bg-gray-200 dark:hover:bg-gray-700 transition"
                    >
                      {hint}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-xl p-4 text-sm">
              {error}
            </div>
          )}

          {!loading && !error && papers.length === 0 && q && (
            <div className="text-center py-16 text-gray-400 dark:text-gray-500">
              <svg className="w-12 h-12 mx-auto mb-4 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-lg font-medium">No results found</p>
              <p className="text-sm mt-1">Try different keywords or remove filters</p>
            </div>
          )}

          {papers.map((p) => (
            <PaperCard key={p.arxiv_id || p.id} paper={p} query={q} />
          ))}

          {loading && Array.from({ length: 4 }).map((_, i) => <PaperCardSkeleton key={i} />)}

          {!loading && hasMore && (
            <div className="text-center pt-4">
              <button
                onClick={loadMore}
                className="px-6 py-2.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 rounded-full text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition"
              >
                Load More
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}

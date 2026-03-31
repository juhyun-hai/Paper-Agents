import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { autocomplete } from '../api/client.js'

function debounce(fn, delay) {
  let timer
  return (...args) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }
}

export default function SearchBar({ initialQuery = '', large = false, onSearch }) {
  const [query, setQuery] = useState(initialQuery)
  const [suggestions, setSuggestions] = useState([])
  const [open, setOpen] = useState(false)
  const [activeIdx, setActiveIdx] = useState(-1)
  const navigate = useNavigate()
  const inputRef = useRef(null)
  const containerRef = useRef(null)

  const fetchSuggestions = useCallback(
    debounce(async (q) => {
      if (q.trim().length < 2) { setSuggestions([]); return }
      try {
        const data = await autocomplete(q)
        setSuggestions(data?.suggestions || data || [])
        setOpen(true)
      } catch {
        setSuggestions([])
      }
    }, 300),
    []
  )

  useEffect(() => {
    fetchSuggestions(query)
  }, [query])

  useEffect(() => {
    function handleClick(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function doSearch(q) {
    const term = q.trim()
    if (!term) return
    setOpen(false)
    if (onSearch) {
      onSearch(term)
    } else {
      navigate(`/search?q=${encodeURIComponent(term)}`)
    }
  }

  function handleKeyDown(e) {
    if (!open || suggestions.length === 0) {
      if (e.key === 'Enter') doSearch(query)
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIdx((i) => Math.max(i - 1, -1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (activeIdx >= 0) {
        const s = suggestions[activeIdx]
        const text = typeof s === 'string' ? s : s.title || s.query || s
        setQuery(text)
        doSearch(text)
      } else {
        doSearch(query)
      }
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const inputCls = large
    ? 'w-full pl-12 pr-4 py-4 text-lg rounded-full border-2 border-gray-300 dark:border-gray-600 focus:outline-none focus:border-primary dark:bg-gray-800 dark:text-white shadow-md transition'
    : 'w-full pl-10 pr-4 py-2.5 text-sm rounded-full border border-gray-300 dark:border-gray-600 focus:outline-none focus:border-primary dark:bg-gray-800 dark:text-white transition'

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative">
        <svg
          className={`absolute ${large ? 'left-4 top-1/2 -translate-y-1/2 w-5 h-5' : 'left-3 top-1/2 -translate-y-1/2 w-4 h-4'} text-gray-400`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setActiveIdx(-1) }}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          placeholder="Search papers, authors, topics…"
          className={inputCls}
        />
        {query && (
          <button
            onClick={() => { setQuery(''); setSuggestions([]); setOpen(false); inputRef.current?.focus() }}
            className="absolute right-14 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
        <button
          onClick={() => doSearch(query)}
          className={`absolute right-2 top-1/2 -translate-y-1/2 bg-primary hover:bg-primary-dark text-white rounded-full transition ${large ? 'px-5 py-2 text-sm font-medium' : 'px-3 py-1.5 text-xs font-medium'}`}
        >
          Search
        </button>
      </div>

      {open && suggestions.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg max-h-60 overflow-auto">
          {suggestions.map((s, i) => {
            const text = typeof s === 'string' ? s : s.title || s.query || String(s)
            return (
              <li
                key={i}
                className={`px-4 py-2.5 cursor-pointer text-sm flex items-center gap-2 ${
                  i === activeIdx ? 'bg-blue-50 dark:bg-gray-700 text-primary' : 'hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200'
                }`}
                onMouseDown={() => { setQuery(text); doSearch(text) }}
                onMouseEnter={() => setActiveIdx(i)}
              >
                <svg className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                {text}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

import React from 'react'
import { getCategoryLabel, ALL_CATEGORIES } from '../utils/categories.js'
const SORT_OPTIONS = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'date', label: 'Newest First' },
  { value: 'citations', label: 'Most Cited' },
]

export default function Sidebar({ filters, onChange }) {
  const { categories = [], sort = 'relevance', dateFrom = '', dateTo = '' } = filters
  // sort is comma-separated string, e.g. "relevance,citations"
  const activeSorts = sort ? sort.split(',').filter(Boolean) : ['relevance']

  function toggleSort(value) {
    let next = activeSorts.includes(value)
      ? activeSorts.filter((s) => s !== value)
      : [...activeSorts, value]
    if (next.length === 0) next = ['relevance']
    onChange({ ...filters, sort: next.join(',') })
  }

  function toggleCategory(cat) {
    const next = categories.includes(cat)
      ? categories.filter((c) => c !== cat)
      : [...categories, cat]
    onChange({ ...filters, categories: next })
  }

  return (
    <aside className="w-full lg:w-64 flex-shrink-0 space-y-4 lg:space-y-6">
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
        <h3 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Sort By</h3>
        <div className="space-y-2">
          {SORT_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={activeSorts.includes(opt.value)}
                onChange={() => toggleSort(opt.value)}
                className="accent-primary"
              />
              <span className="text-sm text-gray-600 dark:text-gray-300">{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
        <h3 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Categories</h3>
        <div className="space-y-2">
          {ALL_CATEGORIES.map((cat) => (
            <label key={cat} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={categories.includes(cat)}
                onChange={() => toggleCategory(cat)}
                className="accent-primary"
              />
              <span className="text-sm text-gray-600 dark:text-gray-300">{getCategoryLabel(cat)}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
        <h3 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Date Range</h3>
        <div className="space-y-2">
          <div>
            <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => onChange({ ...filters, dateFrom: e.target.value })}
              className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 dark:bg-gray-700 dark:text-white focus:outline-none focus:border-primary"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => onChange({ ...filters, dateTo: e.target.value })}
              className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 dark:bg-gray-700 dark:text-white focus:outline-none focus:border-primary"
            />
          </div>
        </div>
      </div>

      <button
        onClick={() => onChange({ categories: [], sort: 'relevance', dateFrom: '', dateTo: '' })}
        className="w-full text-sm text-gray-500 dark:text-gray-400 hover:text-primary py-2 border border-gray-200 dark:border-gray-600 rounded-xl transition-colors"
      >
        Clear Filters
      </button>
    </aside>
  )
}

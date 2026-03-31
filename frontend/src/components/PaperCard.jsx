import React from 'react'
import { Link } from 'react-router-dom'
import { getCategoryLabel, CATEGORY_TAILWIND } from '../utils/categories.js'

function CategoryBadge({ cat }) {
  const cls = CATEGORY_TAILWIND[cat] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {getCategoryLabel(cat)}
    </span>
  )
}

function highlight(text, query) {
  if (!query || !text) return text
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const parts = text.split(new RegExp(`(${escaped})`, 'gi'))
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase()
      ? `<mark class="bg-yellow-200 dark:bg-yellow-700 rounded px-0.5">${part}</mark>`
      : part
  ).join('')
}

export default function PaperCard({ paper, query = '', showSimilarity = false }) {
  if (!paper) return null

  const {
    arxiv_id,
    title = 'Untitled',
    authors = [],
    abstract = '',
    categories = [],
    date = '',
    citation_count = 0,
    similarity_score,
    venue,
  } = paper

  const displayAuthors = authors.length > 3
    ? [...authors.slice(0, 3), 'et al.'].join(', ')
    : authors.join(', ')

  const snippet = abstract.length > 150 ? abstract.slice(0, 150) + '…' : abstract
  const highlightedTitle = query ? highlight(title, query) : title
  const highlightedSnippet = query ? highlight(snippet, query) : snippet

  const dateStr = date ? new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'short' }) : ''

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5 hover:shadow-md transition-shadow group">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <Link
            to={`/paper/${arxiv_id}`}
            className="block text-lg font-semibold text-gray-900 dark:text-gray-100 group-hover:text-primary transition-colors leading-snug mb-1"
            dangerouslySetInnerHTML={{ __html: highlightedTitle }}
          />
          <p className="text-sm text-gray-600 dark:text-gray-400">{displayAuthors}</p>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          {citation_count > 0 && (
            <span className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              {citation_count.toLocaleString()}
            </span>
          )}
          {showSimilarity && similarity_score != null && (
            <span className="text-xs bg-primary text-white px-2 py-0.5 rounded-full">
              {Math.round(similarity_score * 100)}% match
            </span>
          )}
        </div>
      </div>

      <p
        className="mt-2 text-sm text-gray-600 dark:text-gray-300 leading-relaxed"
        dangerouslySetInnerHTML={{ __html: highlightedSnippet }}
      />

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {categories.slice(0, 4).map((cat) => (
          <CategoryBadge key={cat} cat={cat} />
        ))}
        {dateStr && (
          <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto font-medium">{dateStr}</span>
        )}
        {venue && (
          <span className="text-xs bg-indigo-50 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 px-2 py-0.5 rounded font-medium">
            {venue}
          </span>
        )}
      </div>
    </div>
  )
}

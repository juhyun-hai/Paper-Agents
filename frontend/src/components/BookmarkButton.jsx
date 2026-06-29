import { useEffect, useState } from 'react'
import { isBookmarked, toggleBookmark } from '../utils/bookmarks'

export default function BookmarkButton({ arxivId, size = 'md' }) {
  const [on, setOn] = useState(false)

  useEffect(() => {
    setOn(isBookmarked(arxivId))
    const handler = () => setOn(isBookmarked(arxivId))
    window.addEventListener('bookmarks-changed', handler)
    return () => window.removeEventListener('bookmarks-changed', handler)
  }, [arxivId])

  const cls = size === 'sm'
    ? 'text-base px-2 py-1'
    : 'text-lg px-3 py-1.5'

  return (
    <button
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); toggleBookmark(arxivId) }}
      title={on ? '북마크 해제' : '북마크에 추가'}
      className={`${cls} rounded-lg transition-colors ${
        on
          ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300 hover:bg-yellow-200'
          : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
      }`}
    >
      {on ? '★' : '☆'}
    </button>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE } from '../api/client'

/**
 * Home에 표시하는 인기 동적 tag chip cloud.
 * - /api/tags/popular 에서 paper_count 내림차순 가져옴
 * - tag 크기는 paper_count 비례 (시각적으로 더 인기 있는 게 큼)
 * - 클릭하면 /tag/<tag> 로 이동 (tag-filtered paper list)
 */
export default function PopularTags({ limit = 40, minCount = 2 }) {
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/tags/popular?limit=${limit}&min_count=${minCount}`)
      .then(r => r.json())
      .then(d => {
        setTags(d.tags || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [limit, minCount])

  if (loading) {
    return <div className="h-32 animate-pulse bg-gray-100 dark:bg-gray-800 rounded-xl" />
  }
  if (!tags.length) return null

  const maxCount = Math.max(...tags.map(t => t.count))

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <h2 className="font-bold text-gray-900 dark:text-white">🏷 인기 키워드</h2>
        <span className="text-[10px] bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300 px-1.5 py-0.5 rounded-full font-medium">
          자동 추출
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {tags.map(t => {
          // size mapping: 작은 것 11px, 큰 것 15px (paper_count 비례)
          const ratio = t.count / maxCount
          const fontSize = 11 + Math.round(ratio * 4)
          // Tailwind JIT는 동적 클래스명을 추출 못 하므로 정적 매핑 사용
          const strong = ratio > 0.5
          const cls = strong
            ? 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/50 dark:text-indigo-100'
            : 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/20 dark:text-indigo-300'
          return (
            <Link
              key={t.name}
              to={`/tag/${encodeURIComponent(t.name)}`}
              style={{ fontSize: `${fontSize}px` }}
              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border transition-colors
                ${cls} border-indigo-200 dark:border-indigo-800
                hover:bg-indigo-200 dark:hover:bg-indigo-900/60`}
            >
              <span className="font-medium">{t.name}</span>
              <span className="text-[10px] opacity-60">{t.count}</span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

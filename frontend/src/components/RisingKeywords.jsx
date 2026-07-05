import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE } from '../api/client'

/**
 * 급상승 키워드 카드 (Home 사이드바용).
 * - /api/trends/keywords 에서 최근 7일 vs 이전 30일 baseline 대비 상승 배율을 가져옴
 * - 키워드 chip + 배율(×2.3) + baseline 없으면 NEW 뱃지
 * - 클릭하면 /tag/<name> 으로 이동
 */
export default function RisingKeywords({ days = 7, limit = 10 }) {
  const [keywords, setKeywords] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/trends/keywords?days=${days}&limit=${limit}`)
      .then(r => r.json())
      .then(d => {
        setKeywords(d.keywords || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [days, limit])

  if (loading) {
    return <div className="h-32 animate-pulse bg-gray-100 dark:bg-gray-800 rounded-xl" />
  }
  if (!keywords.length) return null

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <h2 className="font-bold text-gray-900 dark:text-white">📈 급상승 키워드</h2>
        <span className="text-[10px] bg-rose-100 text-rose-700 dark:bg-rose-900 dark:text-rose-300 px-1.5 py-0.5 rounded-full font-medium">
          최근 {days}일
        </span>
      </div>
      <ul className="space-y-1.5">
        {keywords.map(k => (
          <li key={k.name}>
            <Link
              to={`/tag/${encodeURIComponent(k.name)}`}
              className="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-lg text-sm
                bg-rose-50 dark:bg-rose-900/20 border border-rose-100 dark:border-rose-900/40
                hover:bg-rose-100 dark:hover:bg-rose-900/40 transition-colors"
            >
              <span className="font-medium text-gray-800 dark:text-gray-100 truncate">
                {k.name}
              </span>
              <span className="flex items-center gap-1.5 shrink-0">
                {k.new && (
                  <span className="text-[10px] font-bold bg-rose-600 text-white px-1.5 py-0.5 rounded-full">
                    NEW
                  </span>
                )}
                <span className="text-xs font-semibold text-rose-600 dark:text-rose-400">
                  ×{k.score.toFixed(1)}
                </span>
                <span className="text-[10px] text-gray-400 dark:text-gray-500">
                  {k.recent}편
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE } from '../api/client'

/**
 * HF Daily Papers 스타일 daily feed.
 * - 날짜 네비게이션 (← 이전 / 다음 →)
 * - 랭크된 featured 리스트: 제목 + 한국어 one-liner + tags + meta badges
 */
export default function DailyFeed() {
  const [data, setData] = useState(null)
  const [date, setDate] = useState(null) // null = 최신
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const qs = date ? `?date=${date}&limit=25` : '?limit=25'
    fetch(`${API_BASE}/feed/daily${qs}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [date])

  if (loading && !data) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
        ))}
      </div>
    )
  }
  if (!data || !data.papers) return null

  const { available_dates: dates = [], papers } = data
  const cur = data.date
  const idx = dates.indexOf(cur)
  const newer = idx > 0 ? dates[idx - 1] : null
  const older = idx >= 0 && idx < dates.length - 1 ? dates[idx + 1] : null

  const fmtDate = (d) => {
    if (!d) return ''
    const [y, m, day] = d.split('-')
    const dow = ['일', '월', '화', '수', '목', '금', '토'][new Date(d).getDay()]
    return `${m}월 ${day}일 (${dow})`
  }

  return (
    <div>
      {/* Date navigation */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-baseline gap-3">
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            {fmtDate(cur)}
          </h2>
          <span className="text-sm text-gray-500 dark:text-gray-400">{papers.length}편 큐레이션</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => older && setDate(older)}
            disabled={!older}
            className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            ← {older ? fmtDate(older).split(' ')[0] + ' ' + fmtDate(older).split(' ')[1] : '이전'}
          </button>
          <button
            onClick={() => newer && setDate(newer)}
            disabled={!newer}
            className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            {newer ? fmtDate(newer).split(' ')[0] + ' ' + fmtDate(newer).split(' ')[1] : '다음'} →
          </button>
        </div>
      </div>

      {/* Feed list */}
      <ol className="space-y-2.5">
        {papers.map(p => (
          <li key={p.arxiv_id}>
            <Link
              to={`/paper/${p.arxiv_id}`}
              className="group block bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-3.5 hover:border-indigo-300 dark:hover:border-indigo-700 hover:shadow-md transition-all"
            >
              <div className="flex gap-3.5">
                {/* Rank */}
                <div className="flex-shrink-0 w-8 text-center">
                  <span className={`text-lg font-bold ${p.rank <= 3 ? 'text-orange-500' : 'text-gray-300 dark:text-gray-600'}`}>
                    {p.rank}
                  </span>
                  {p.upvotes > 0 && (
                    <div className="text-[10px] text-gray-400 mt-0.5">▲{p.upvotes}</div>
                  )}
                </div>

                {/* Body */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 dark:text-white leading-snug group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                    {p.title}
                  </h3>

                  {p.one_liner && (
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-300 leading-relaxed line-clamp-2">
                      {p.one_liner}
                    </p>
                  )}

                  <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
                    {p.deep && (
                      <span className="px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 font-medium" title="본문 기반 딥 요약">
                        🧠 딥 요약
                      </span>
                    )}
                    {!p.has_summary && (
                      <span className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500" title="요약 생성 대기 중">
                        ⏳ 요약 예정
                      </span>
                    )}
                    {p.figure_count > 0 && (
                      <span className="text-gray-500 dark:text-gray-400">📊 그림 {p.figure_count}</span>
                    )}
                    {p.is_hai && (
                      <span className="px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium">🎓 HAI</span>
                    )}
                    {p.tags.slice(0, 4).map(t => (
                      <span
                        key={t}
                        className="px-1.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-900/25 text-indigo-600 dark:text-indigo-300"
                      >
                        {t}
                      </span>
                    ))}
                    {p.authors.length > 0 && (
                      <span className="text-gray-400 dark:text-gray-500 truncate">
                        · {p.authors.join(', ')}{p.authors.length >= 3 ? ' 외' : ''}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ol>

      {papers.length === 0 && (
        <div className="text-center py-16 text-gray-500">이 날짜엔 큐레이션이 없습니다.</div>
      )}
    </div>
  )
}

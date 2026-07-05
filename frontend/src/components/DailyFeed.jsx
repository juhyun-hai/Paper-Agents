import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { API_BASE } from '../api/client'

/**
 * HF Daily Papers 스타일 daily feed.
 * - 날짜 네비게이션 (← 이전 / 다음 →) — ?date= URL param으로 관리해
 *   논문 상세 갔다 뒤로 와도 보던 날짜가 유지된다.
 * - 랭크된 featured 리스트: 제목 + 한국어 one-liner + tags + meta badges
 */
export default function DailyFeed() {
  const [data, setData] = useState(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const date = searchParams.get('date') // null = 최신
  const setDate = (d) => setSearchParams(d ? { date: d } : {}, { replace: false })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const qs = date ? `?date=${date}&limit=25` : '?limit=25'
    fetch(`${API_BASE}/feed/daily${qs}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [date])

  // 뒤로가기로 돌아왔을 때 보던 위치 복원
  useEffect(() => {
    if (loading || !data) return
    const saved = sessionStorage.getItem('feed_scroll')
    if (saved) {
      window.scrollTo(0, parseInt(saved, 10))
      sessionStorage.removeItem('feed_scroll')
    }
  }, [loading, data])

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

  const { available_dates: dates = [], papers, overview } = data
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

      {/* 오늘의 연구 흐름 요약 — overview 있을 때만 */}
      {overview && overview.text && (
        <div className="mb-5 rounded-xl border border-indigo-100 dark:border-indigo-900/50 bg-indigo-50/60 dark:bg-indigo-950/30 px-4 py-3.5">
          <div className="flex items-center gap-1.5 mb-1.5 text-xs font-semibold text-indigo-600 dark:text-indigo-400">
            <span>📡</span>
            <span>오늘의 연구 흐름</span>
          </div>
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {overview.text}
          </p>
          {overview.top_themes && overview.top_themes.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              {overview.top_themes.map(t => (
                <span key={t}
                  className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-white dark:bg-gray-900 border border-indigo-100 dark:border-indigo-900/50 text-indigo-600 dark:text-indigo-400">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Feed list */}
      <ol className="space-y-2.5">
        {papers.map(p => (
          <li key={p.arxiv_id}>
            <Link
              to={`/paper/${p.arxiv_id}`}
              onClick={() => sessionStorage.setItem('feed_scroll', String(window.scrollY))}
              className="group block bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-3.5 hover:border-indigo-300 dark:hover:border-indigo-700 hover:shadow-md transition-all"
            >
              <div className="flex gap-3.5">
                {/* Rank */}
                <div className="flex-shrink-0 w-8 text-center">
                  <span className={`text-lg font-bold ${p.rank <= 3 ? 'text-orange-500' : 'text-gray-300 dark:text-gray-600'}`}>
                    {p.rank}
                  </span>
                  {p.upvotes > 0 && (
                    <div className="text-[10px] text-gray-400 mt-0.5" title="HuggingFace Daily Papers upvotes">HF▲{p.upvotes}</div>
                  )}
                </div>

                {/* Body — 밀도 낮게: 제목 + 한 줄 요약 1줄 + 핵심 badge만 */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 dark:text-white leading-snug group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                    {p.title}
                  </h3>

                  {p.one_liner && (
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 leading-relaxed line-clamp-1">
                      {p.one_liner}
                    </p>
                  )}

                  <div className="mt-2 flex items-center gap-2 text-[11px] overflow-hidden">
                    {p.deep && (
                      <span className="flex-shrink-0 px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 font-medium" title="본문 기반 딥 요약">
                        🧠 요약
                      </span>
                    )}
                    {p.is_hai && (
                      <span className="flex-shrink-0 px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium">🎓</span>
                    )}
                    {p.tags.slice(0, 3).map(t => (
                      <span key={t}
                        className="flex-shrink-0 px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                        {t}
                      </span>
                    ))}
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

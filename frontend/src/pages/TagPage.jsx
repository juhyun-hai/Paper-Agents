import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import PaperCard from '../components/PaperCard.jsx'
import { PaperCardSkeleton } from '../components/Skeleton.jsx'
import { API_BASE } from '../api/client.js'

/**
 * Tag-filtered paper list page (route: /tag/:tagname)
 *
 * - LLM이 자동 추출한 동적 키워드(tag)로 논문을 필터링
 * - /api/tags/papers?tag=<name>&limit=50 호출
 * - 관련 popular tag 몇 개를 같이 노출해서 탐색을 돕는다
 */
export default function TagPage() {
  const { tagname } = useParams()
  const decoded = (() => {
    try { return decodeURIComponent(tagname || '') } catch { return tagname || '' }
  })()

  const [papers, setPapers] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [related, setRelated] = useState([])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setPapers([])
    setTotal(0)

    fetch(`${API_BASE}/tags/papers?tag=${encodeURIComponent(decoded)}&limit=50`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(d => {
        if (cancelled) return
        // /api/tags/papers 는 published_date / pdf_url / html_url 키를 쓰지만
        // PaperCard 는 date 키를 기대 → 매핑해서 넘김
        const mapped = (d?.papers || []).map(p => ({
          ...p,
          date: p.published_date || p.date || '',
        }))
        setPapers(mapped)
        setTotal(d?.total || mapped.length)
        setLoading(false)
      })
      .catch(e => {
        if (cancelled) return
        setError(e?.message || 'failed')
        setLoading(false)
      })

    // 관련 인기 tag (현재 tag 제외 12개) — 함께 탐색하기 좋은 키워드
    fetch(`${API_BASE}/tags/popular?limit=24&min_count=2`)
      .then(r => r.ok ? r.json() : { tags: [] })
      .then(d => {
        if (cancelled) return
        const filtered = (d?.tags || [])
          .filter(t => (t.name || '').toLowerCase() !== decoded.toLowerCase())
          .slice(0, 12)
        setRelated(filtered)
      })
      .catch(() => {})

    return () => { cancelled = true }
  }, [decoded])

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          <Link to="/" className="hover:text-indigo-600">Home</Link>
          <span className="mx-2">/</span>
          <span>Tags</span>
        </div>

        <div className="flex flex-wrap items-baseline gap-3">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            <span className="text-indigo-600 dark:text-indigo-400">#</span>{decoded}
          </h1>
          {!loading && (
            <span className="text-sm bg-indigo-50 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-200 px-3 py-1 rounded-full font-medium">
              {total}편
            </span>
          )}
          <span className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded-full">
            자동 추출 키워드
          </span>
        </div>

        <p className="mt-3 text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
          LLM이 수집된 논문의 제목과 초록에서 추출한 동적 토픽 태그입니다.
          최근 발행일 순으로 정렬됩니다.
        </p>
      </div>

      {/* Body */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <PaperCardSkeleton key={i} />
          ))}
        </div>
      )}

      {!loading && error && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 p-6 text-sm text-red-700 dark:text-red-300">
          태그 검색에 실패했어요: {error}
        </div>
      )}

      {!loading && !error && papers.length === 0 && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-10 text-center">
          <div className="text-4xl mb-3">🪄</div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
            아직 이 태그에 연결된 논문이 없어요
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            관련 논문이 곧 추가됩니다. 매일 새벽 자동 수집 + 태그 추출이 돌아갑니다.
          </p>
          <Link to="/" className="inline-block mt-5 text-sm text-indigo-600 hover:text-indigo-700 font-medium">
            ← 홈으로 돌아가기
          </Link>
        </div>
      )}

      {!loading && !error && papers.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {papers.map(p => (
            <PaperCard key={p.arxiv_id} paper={p} />
          ))}
        </div>
      )}

      {/* Related tags */}
      {related.length > 0 && (
        <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-700">
          <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
            함께 둘러보기
          </h2>
          <div className="flex flex-wrap gap-2">
            {related.map(t => (
              <Link
                key={t.name}
                to={`/tag/${encodeURIComponent(t.name)}`}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-full border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-200 text-xs hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition-colors"
              >
                <span className="font-medium">{t.name}</span>
                <span className="opacity-70">{t.count}</span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

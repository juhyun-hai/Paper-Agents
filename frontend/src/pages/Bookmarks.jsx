import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PaperCard from '../components/PaperCard.jsx'
import { getBookmarks, clearBookmarks } from '../utils/bookmarks'
import { getPaper } from '../api/client'

export default function Bookmarks() {
  const [papers, setPapers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const ids = getBookmarks()
    if (!ids.length) { setLoading(false); return }
    Promise.all(ids.map(id => getPaper(id).then(d => d?.paper || d).catch(() => null)))
      .then(rs => {
        setPapers(rs.filter(Boolean))
        setLoading(false)
      })
  }, [])

  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
            🔖 내 북마크
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            브라우저에 저장됨 · 서버에 전송 안 함 · {papers.length}편
          </p>
        </div>
        {papers.length > 0 && (
          <button
            onClick={() => { if (confirm('모두 삭제할까?')) { clearBookmarks(); setPapers([]) } }}
            className="text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
          >
            모두 지우기
          </button>
        )}
      </div>

      {loading && <p className="text-gray-500">로딩 중…</p>}
      {!loading && papers.length === 0 && (
        <div className="text-center py-20">
          <div className="text-6xl mb-4">🔖</div>
          <p className="text-gray-600 dark:text-gray-300 mb-2">아직 북마크가 없어요</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
            논문 상세 페이지에서 ☆ 버튼을 누르면 여기로 모입니다.
          </p>
          <Link to="/" className="inline-block px-5 py-2.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700">
            홈으로 가서 둘러보기
          </Link>
        </div>
      )}

      {!loading && papers.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {papers.map(p => <PaperCard key={p.arxiv_id} paper={p} />)}
        </div>
      )}
    </main>
  )
}

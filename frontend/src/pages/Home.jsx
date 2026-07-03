import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import SearchBar from '../components/SearchBar.jsx'
import DailyFeed from '../components/DailyFeed.jsx'
import PopularTags from '../components/PopularTags.jsx'
import { API_BASE, getStats } from '../api/client.js'

/**
 * Content-first 홈 (HF Daily Papers 스타일).
 * 구조: 컴팩트 헤더 → [메인: daily feed | 사이드바: tags·HAI·구독] → 짧은 footer 소개.
 * 마케팅 히어로/기능 설명/점수 설명 섹션은 제거 — 논문이 주인공.
 */
export default function Home() {
  const [stats, setStats] = useState(null)
  const [haiPapers, setHaiPapers] = useState([])

  useEffect(() => {
    getStats().then(setStats).catch(() => {})
    fetch(`${API_BASE}/hai/papers?limit=5`)
      .then(r => r.json())
      .then(d => setHaiPapers(d?.papers || []))
      .catch(() => {})
  }, [])

  return (
    <main>
      {/* Compact header */}
      <section className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
        <div className="max-w-6xl mx-auto px-4 py-8 sm:py-10">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 dark:text-white tracking-tight">
                오늘의 AI 논문
              </h1>
              <p className="mt-1.5 text-sm text-gray-600 dark:text-gray-400">
                매일 새벽 자동 큐레이션 Top 25 · 본문 기반 한국어 딥 요약 · 무광고
                {stats?.total_papers && (
                  <span className="ml-2 text-gray-400">— 누적 {stats.total_papers.toLocaleString()}편</span>
                )}
              </p>
            </div>
            <div className="w-full sm:w-80">
              <SearchBar />
            </div>
          </div>
        </div>
      </section>

      {/* Main: feed + sidebar */}
      <section className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Feed (2/3) */}
          <div className="lg:col-span-2">
            <DailyFeed />
          </div>

          {/* Sidebar (1/3) */}
          <aside className="space-y-6">
            {/* Popular tags */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
              <PopularTags limit={24} minCount={3} />
            </div>

            {/* HAI Picks compact */}
            {haiPapers.length > 0 && (
              <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-bold text-gray-900 dark:text-white">🎓 HAI Lab Picks</h2>
                  <Link to="/hai" className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline">
                    전체 →
                  </Link>
                </div>
                <ul className="space-y-2.5">
                  {haiPapers.slice(0, 5).map(p => (
                    <li key={p.arxiv_id}>
                      <Link
                        to={`/paper/${p.arxiv_id}`}
                        className="block text-sm text-gray-700 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 leading-snug line-clamp-2"
                      >
                        {p.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Subscribe */}
            <div className="bg-gradient-to-br from-indigo-50 to-blue-50 dark:from-indigo-950/40 dark:to-blue-950/30 border border-indigo-100 dark:border-indigo-900 rounded-xl p-5">
              <h2 className="font-bold text-gray-900 dark:text-white mb-2">매일 받아보기</h2>
              <div className="space-y-2 text-sm">
                <Link to="/alerts" className="flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400">
                  <span>🔔</span> 관심 키워드 알림 등록
                </Link>
                <a href="/api/feed/rss" target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-orange-500">
                  <span>📡</span> RSS 피드 (Feedly 등)
                </a>
                <a href="https://github.com/juhyun-hai/Paper-Agents/tree/master/mcp_server" target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-indigo-500">
                  <span>🔌</span> Claude/Cursor MCP 연동
                </a>
              </div>
            </div>

            {/* About (짧게) */}
            <div className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed px-1">
              <p>
                <a href="https://hai.snu.ac.kr/" target="_blank" rel="noopener noreferrer" className="font-semibold text-gray-700 dark:text-gray-300 hover:text-indigo-600">SNU HAI Lab</a>이
                운영하는 논문 큐레이션. HuggingFace·arXiv·학회 데이터를 종합해 매일 25편을
                선정하고 본문(ar5iv) 기반으로 한국어 요약을 생성합니다. 광고·스폰서 랭킹 없음.
              </p>
              <p className="mt-1.5">
                Developed by{' '}
                <a href="https://hai.snu.ac.kr/bbs/board.php?bo_table=sub2_2&wr_id=43&sca=2Ph.D.+student&page=2"
                  target="_blank" rel="noopener noreferrer" className="text-gray-700 dark:text-gray-300 hover:text-indigo-600">
                  Juhyun Kim
                </a>
              </p>
            </div>
          </aside>
        </div>
      </section>
    </main>
  )
}

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
    // 사이드바 HAI Picks = 최근 arXiv 중 HAI 연구 분야 관련 논문.
    // (lab 자체 출판물 아카이브는 /hai 페이지에서 — 여긴 '요즘 뭐가 나오나')
    fetch(`${API_BASE}/hai/papers?limit=5&source=arxiv&sort=recent`)
      .then(r => r.json())
      .then(d => setHaiPapers(d?.papers || []))
      .catch(() => {})
  }, [])

  return (
    <main>
      {/* Hero — 기존의 예쁜 gradient 유지, 높이만 압축해서 feed가 바로 보이게 */}
      <section className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-indigo-700 to-purple-800 text-white">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 w-72 h-72 bg-white rounded-full blur-3xl animate-pulse" />
          <div className="absolute bottom-10 right-10 w-96 h-96 bg-blue-300 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        </div>

        <div className="relative max-w-5xl mx-auto px-4 py-12 sm:py-16 text-center space-y-6">
          <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-full px-4 py-1.5 text-sm font-medium">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            Curated by{' '}
            <a href="https://hai.snu.ac.kr/" target="_blank" rel="noopener noreferrer"
              className="font-semibold text-yellow-200 hover:text-yellow-100 transition-colors">
              SNU HAI Lab
            </a>
            {stats?.total_papers && (
              <>
                <span className="text-blue-200">·</span>
                <span className="text-blue-100">{stats.total_papers.toLocaleString()}편 수집</span>
              </>
            )}
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold leading-tight tracking-tight">
            Discover What's
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-yellow-300 to-orange-400"> Hot </span>
            in AI Research
          </h1>

          <p className="text-base sm:text-lg text-blue-100 max-w-2xl mx-auto">
            매일 <span className="font-semibold text-yellow-200">Top 25</span>편 자동 큐레이션 · 본문 기반 한국어 딥 요약
          </p>

          <div className="max-w-2xl mx-auto">
            <SearchBar large />
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
                선정하고 본문(ar5iv) 기반으로 한국어 요약을 생성합니다.
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

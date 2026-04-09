import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import SearchBar from '../components/SearchBar.jsx'
import PaperCard from '../components/PaperCard.jsx'
import { PaperCardSkeleton } from '../components/Skeleton.jsx'
import HotTopics from '../components/HotTopics.jsx'
import { getStats, getTrends } from '../api/client.js'

const FEATURES = [
  {
    icon: '🔍',
    title: 'Smart Search',
    desc: '시맨틱 검색으로 키워드가 아닌 의미 기반으로 관련 논문을 찾아줍니다.',
  },
  {
    icon: '🤖',
    title: 'AI 요약',
    desc: 'Claude Opus가 직접 분석한 한국어 논문 요약. 핵심 기여도, 방법론, 결과를 한눈에.',
  },
  {
    icon: '🔥',
    title: 'Trending',
    desc: 'HuggingFace, arXiv 등 다중 소스에서 실시간 인기 논문을 수집하고 점수화합니다.',
  },
  {
    icon: '🔗',
    title: '유사 논문 추천',
    desc: '임베딩 기반 시맨틱 유사도로 관련 논문을 자동 추천. 연구 맥락을 빠르게 파악합니다.',
  },
]

const SAMPLE_QUERIES = [
  'transformer attention mechanism',
  'diffusion model image generation',
  'reinforcement learning from human feedback',
  'large language model reasoning',
  'vision language model',
  'federated learning privacy',
]

export default function Home() {
  const [trending, setTrending] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [animatedStat, setAnimatedStat] = useState(0)

  useEffect(() => {
    Promise.all([
      getStats().catch(() => null),
      getTrends(60).catch(() => null),
    ]).then(([statsRes, trendsRes]) => {
      setTrending(trendsRes?.trending_papers || statsRes?.top_papers || [])
      setStats(statsRes)
      setLoading(false)
    })
  }, [])

  // Animate paper count
  useEffect(() => {
    if (!stats?.total_papers) return
    const target = stats.total_papers
    const duration = 1500
    const step = target / (duration / 16)
    let current = 0
    const timer = setInterval(() => {
      current += step
      if (current >= target) {
        setAnimatedStat(target)
        clearInterval(timer)
      } else {
        setAnimatedStat(Math.floor(current))
      }
    }, 16)
    return () => clearInterval(timer)
  }, [stats])

  return (
    <main className="space-y-0">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-indigo-700 to-purple-800 text-white">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 w-72 h-72 bg-white rounded-full blur-3xl animate-pulse" />
          <div className="absolute bottom-10 right-10 w-96 h-96 bg-blue-300 rounded-full blur-3xl animate-pulse" style={{animationDelay: '1s'}} />
        </div>

        <div className="relative max-w-5xl mx-auto px-4 py-20 sm:py-28 text-center space-y-8">
          <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-full px-4 py-2 text-sm font-medium">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            {stats ? `${stats.total_papers?.toLocaleString()}+ papers indexed` : 'Live updating'}
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold leading-tight tracking-tight">
            Discover What's
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-yellow-300 to-orange-400"> Hot </span>
            in AI Research
          </h1>

          <p className="text-lg sm:text-xl text-blue-100 max-w-2xl mx-auto leading-relaxed">
            AI가 분석하는 최신 arXiv 논문 트렌드. 한국어 요약, 유사 논문 추천, 실시간 인기 논문까지.
          </p>

          <div className="max-w-2xl mx-auto">
            <SearchBar large />
          </div>

          <div className="flex flex-wrap justify-center gap-2 text-sm">
            <span className="text-blue-200">Try:</span>
            {SAMPLE_QUERIES.slice(0, 4).map((q) => (
              <Link
                key={q}
                to={`/search?q=${encodeURIComponent(q)}`}
                className="bg-white/10 hover:bg-white/20 backdrop-blur-sm px-3 py-1 rounded-full transition-colors"
              >
                {q}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      {stats && (
        <section className="bg-gray-900 text-white py-6">
          <div className="max-w-5xl mx-auto px-4 grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
            {[
              { label: '논문 수', value: animatedStat.toLocaleString(), suffix: '+' },
              { label: '카테고리', value: stats.total_categories || '30+' },
              { label: '그래프 엣지', value: stats.graph_edges?.toLocaleString() || '500+' },
              { label: 'AI 요약', value: stats.total_papers?.toLocaleString(), suffix: '+' },
            ].map((s) => (
              <div key={s.label}>
                <p className="text-2xl sm:text-3xl font-bold text-blue-400">
                  {s.value}{s.suffix || ''}
                </p>
                <p className="text-xs text-gray-400 mt-1">{s.label}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Features Section */}
      <section className="max-w-5xl mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
            How It Works
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Hot Paper가 제공하는 핵심 기능들
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl p-6 hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
            >
              <div className="text-4xl mb-4">{f.icon}</div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-2">{f.title}</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Hot Topics */}
      <section className="bg-gray-50 dark:bg-gray-900 py-16">
        <div className="max-w-5xl mx-auto px-4">
          <HotTopics />
        </div>
      </section>

      {/* Trending Papers */}
      <section className="max-w-5xl mx-auto px-4 py-16">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">🔥 Trending Papers</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              다중 소스 기반 실시간 인기 논문
            </p>
          </div>
          <Link
            to="/trending"
            className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
          >
            View All →
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading
            ? Array.from({ length: 6 }).map((_, i) => <PaperCardSkeleton key={i} />)
            : trending.slice(0, 6).map((p) => <PaperCard key={p.arxiv_id || p.id} paper={p} />)
          }
        </div>
      </section>

      {/* Trending Score Explanation */}
      <section className="bg-gradient-to-r from-orange-50 to-amber-50 dark:from-gray-800 dark:to-gray-900 py-16">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 text-center">
            📊 Trending Score 계산 방식
          </h2>
          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
                <div className="text-2xl mb-2">📡</div>
                <h3 className="font-semibold text-sm mb-1">다중 소스 수집</h3>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  HuggingFace Papers, arXiv 등에서 인기 논문을 실시간 수집
                </p>
              </div>
              <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-xl">
                <div className="text-2xl mb-2">⚖️</div>
                <h3 className="font-semibold text-sm mb-1">가중 점수 합산</h3>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  각 소스별 가중치를 적용하여 점수를 합산. 소스가 많을수록 높은 점수
                </p>
              </div>
              <div className="text-center p-4 bg-orange-50 dark:bg-orange-900/20 rounded-xl">
                <div className="text-2xl mb-2">🔥</div>
                <h3 className="font-semibold text-sm mb-1">크로스 플랫폼 보너스</h3>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  2개 이상 플랫폼에서 동시 인기 → 1.3x 보너스 적용
                </p>
              </div>
            </div>
            <div className="text-center text-sm text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-200 dark:border-gray-700">
              <code className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-xs">
                final_score = (Σ source_weighted_score + multi_source_bonus) × cross_platform_multiplier
              </code>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-5xl mx-auto px-4 py-16 text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Start Exploring
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-lg mx-auto">
          지금 바로 최신 AI 연구 트렌드를 탐색하고, AI가 분석한 논문 요약을 확인해보세요.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <Link
            to="/search"
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-medium transition-colors shadow-lg shadow-blue-600/25"
          >
            🔍 논문 검색
          </Link>
          <Link
            to="/trending"
            className="bg-orange-500 hover:bg-orange-600 text-white px-8 py-3 rounded-xl font-medium transition-colors shadow-lg shadow-orange-500/25"
          >
            🔥 트렌딩 보기
          </Link>
        </div>
      </section>
    </main>
  )
}

import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import SearchBar from '../components/SearchBar.jsx'
import PaperCard from '../components/PaperCard.jsx'
import { PaperCardSkeleton } from '../components/Skeleton.jsx'
import HotTopics from '../components/HotTopics.jsx'
import FeaturedSection from '../components/FeaturedSection.jsx'
import PopularTags from '../components/PopularTags.jsx'
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
    desc: '논문의 핵심 기여도, 방법론, 결과를 한눈에 볼 수 있는 한국어 요약.',
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
            Curated by{' '}
            <a
              href="https://hai.snu.ac.kr/"
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-yellow-200 hover:text-yellow-100 transition-colors"
            >
              SNU HAI Lab
            </a>
            <span className="text-blue-200">·</span>
            <a
              href="https://hai.snu.ac.kr/bbs/board.php?bo_table=sub2_2&wr_id=43&sca=2Ph.D.+student&page=2"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-100 hover:text-white transition-colors"
            >
              by Juhyun Kim
            </a>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold leading-tight tracking-tight">
            Discover What's
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-yellow-300 to-orange-400"> Hot </span>
            in AI Research
          </h1>

          <p className="text-lg sm:text-xl text-blue-100 max-w-2xl mx-auto leading-relaxed">
            매일 <span className="font-semibold text-yellow-200">Top 25</span>편을 엄선해 한국어 요약과 핵심 그림·표를 제공합니다.
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

      {/* About SNU HAI Lab */}
      <section className="bg-gradient-to-br from-indigo-50 to-blue-50 dark:from-gray-800 dark:to-gray-900 py-12 border-y border-gray-200 dark:border-gray-700">
        <div className="max-w-5xl mx-auto px-4 grid grid-cols-1 md:grid-cols-3 gap-8 items-center">
          <div className="md:col-span-1 flex flex-col items-center md:items-start gap-3">
            <img
              src="https://usecloud.s3-us-west-1.amazonaws.com/snu_logo.png"
              alt="SNU"
              className="h-16 w-16 rounded-lg bg-white p-2 shadow-md"
              onError={(e) => { e.target.style.display = 'none' }}
            />
            <div>
              <p className="text-xs uppercase tracking-wider text-blue-600 dark:text-blue-400 font-semibold">Curated by</p>
              <a
                href="https://hai.snu.ac.kr/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xl font-bold text-gray-900 dark:text-white hover:text-blue-600 transition-colors"
              >
                Hyperautonomy AI Lab
              </a>
              <p className="text-sm text-gray-600 dark:text-gray-400">Seoul National University</p>
            </div>
          </div>
          <div className="md:col-span-2 space-y-3">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              About SNU HAI Lab
            </h2>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
              HAI Lab은 <strong>Industrial Foundation Models</strong>, <strong>Industrial Physical AI</strong>를 중심으로, <strong>Manufacturing AI</strong>, <strong>Physics-Informed ML</strong>, <strong>Signal Processing</strong>, <strong>Digital Twin</strong>, <strong>Reliability</strong>까지 자율 지능 시스템을 연구합니다. HotPaper.ai는 매일 후보 논문 풀에서 HF Daily 큐레이션·다중 소스 합의·연구실 관심도를 결합해 25편만 선정하고, 핵심 그림·결과 표와 함께 한국어로 요약합니다.
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed pt-1">
              Built and maintained by{' '}
              <a
                href="https://hai.snu.ac.kr/bbs/board.php?bo_table=sub2_2&wr_id=43&sca=2Ph.D.+student&page=2"
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-blue-600 hover:text-blue-700 underline-offset-2 hover:underline"
              >
                Juhyun Kim
              </a>
              , Ph.D. student at HAI Lab.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <a
                href="https://hai.snu.ac.kr/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Visit HAI Lab Website →
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Hot Topics */}
      <section className="bg-gray-50 dark:bg-gray-900 py-16">
        <div className="max-w-5xl mx-auto px-4">
          <HotTopics />
          <PopularTags limit={40} minCount={2} />
        </div>
      </section>

      {/* Today's Top 25 (Curated) */}
      <FeaturedSection
        endpoint="/featured/today"
        title="🌟 Today's Top 25"
        subtitle="HAI Lab이 매일 엄선한 임팩트 있는 논문들 — 핵심 그림과 표가 포함된 한국어 요약 제공"
        accent="orange"
        count={6}
        badge="Featured"
      />

      {/* HAI Lab Picks */}
      <section className="bg-blue-50/40 dark:bg-blue-950/10">
        <FeaturedSection
          endpoint="/hai/papers"
          title="🎓 HAI Lab Picks"
          subtitle="Industrial Foundation Models · Industrial Physical AI · Manufacturing AI · Physics-Informed ML · Signal Processing · Digital Twin · Reliability — HAI Lab 자체 발표 및 관련 분야 논문"
          accent="indigo"
          count={6}
          badge="HAI"
          viewAllPath="/hai"
        />
      </section>

      {/* Trending Papers */}
      <section className="max-w-5xl mx-auto px-4 py-12 hidden">
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

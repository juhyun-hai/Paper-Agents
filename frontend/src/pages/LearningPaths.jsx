import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const DIFFICULTY_COLORS = {
  'beginner': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  'intermediate': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  'advanced': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
}

const DIFFICULTY_LABELS = {
  'beginner': 'Beginner',
  'intermediate': 'Intermediate',
  'advanced': 'Advanced'
}

const DIFFICULTY_BAR_COLORS = {
  'beginner': 'bg-green-400',
  'intermediate': 'bg-yellow-400',
  'advanced': 'bg-red-400'
}

function RoadmapCard({ roadmap }) {
  const [expanded, setExpanded] = useState(false)
  const [papers, setPapers] = useState(roadmap.papers || [])
  const [loading, setLoading] = useState(false)

  const loadPapers = async () => {
    if (papers.length > 0) return // Already loaded (including pre-loaded from search)

    setLoading(true)
    try {
      const response = await fetch(`/api/learning-roadmaps/${roadmap.track_name}`)
      const data = await response.json()
      setPapers(data.papers || [])
    } catch (error) {
      console.error('Failed to load roadmap papers:', error)
    }
    setLoading(false)
  }

  const handleExpand = () => {
    if (!expanded) {
      loadPapers()
    }
    setExpanded(!expanded)
  }

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {roadmap.track_title}
          </h3>
          <div className="flex items-center gap-2 mb-2">
            <span className={`text-xs font-medium px-2 py-1 rounded-full ${DIFFICULTY_COLORS[roadmap.difficulty]}`}>
              {roadmap.difficulty}
            </span>
            {roadmap.estimated_time && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                ⏱️ {roadmap.estimated_time}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
            {roadmap.description}
          </p>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 border-t border-gray-200 dark:border-gray-700 pt-4">
          {/* Difficulty progression bar */}
          {papers.length > 0 && (
            <div className="mb-4">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                  학습 순서 ({papers.length}단계)
                </h4>
                <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-400 inline-block" /> Beginner</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" /> Intermediate</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400 inline-block" /> Advanced</span>
                </div>
              </div>
              <div className="flex gap-0.5 h-1.5 rounded-full overflow-hidden bg-gray-200 dark:bg-gray-600">
                {papers.map((paper, i) => (
                  <div
                    key={i}
                    className={`flex-1 ${DIFFICULTY_BAR_COLORS[paper.difficulty] || 'bg-gray-300'}`}
                  />
                ))}
              </div>
            </div>
          )}

          {loading ? (
            <div className="space-y-2">
              {[1,2,3].map(i => (
                <div key={i} className="h-16 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="relative">
              {/* Vertical timeline line */}
              <div className="absolute left-[15px] top-6 bottom-6 w-px bg-gray-200 dark:bg-gray-600" />

              <div className="space-y-3">
                {papers.map((paper) => {
                  const concepts = (() => {
                    try {
                      const c = typeof paper.concepts === 'string' ? JSON.parse(paper.concepts) : paper.concepts
                      return Array.isArray(c) ? c : []
                    } catch { return [] }
                  })()
                  const difficulty = paper.difficulty || 'beginner'

                  return (
                    <div key={paper.arxiv_id} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg relative">
                      {/* Step number with difficulty color ring */}
                      <div className={`flex-shrink-0 w-7 h-7 text-white text-xs font-bold rounded-full flex items-center justify-center ring-2 relative z-10 ${
                        difficulty === 'advanced' ? 'bg-red-500 ring-red-200 dark:ring-red-800' :
                        difficulty === 'intermediate' ? 'bg-yellow-500 ring-yellow-200 dark:ring-yellow-800' :
                        'bg-green-500 ring-green-200 dark:ring-green-800'
                      }`}>
                        {paper.step_order}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Link
                            to={`/paper/${paper.arxiv_id}`}
                            className="text-sm font-medium text-gray-900 dark:text-white hover:text-primary transition-colors truncate"
                          >
                            {paper.title}
                          </Link>
                          <span className={`flex-shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded ${DIFFICULTY_COLORS[difficulty]}`}>
                            {DIFFICULTY_LABELS[difficulty]}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {paper.why_important}
                        </p>
                        <div className="flex flex-wrap items-center gap-2 mt-1.5">
                          <span className="text-xs text-gray-400">{paper.estimated_read_time}</span>
                          {paper.date && <span className="text-xs text-gray-400">{paper.date}</span>}
                          {paper.prerequisites && (
                            <span className="text-[10px] text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 px-1.5 py-0.5 rounded">
                              Prereq: {paper.prerequisites}
                            </span>
                          )}
                        </div>
                        {concepts.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            {concepts.map((concept) => (
                              <span key={concept} className="text-[10px] bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300 px-1.5 py-0.5 rounded">
                                {concept}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      <button
        onClick={handleExpand}
        className="mt-4 w-full text-center text-sm text-primary hover:underline font-medium"
      >
        {expanded ? '▲ 접기' : '▼ 학습 로드맵 보기'}
      </button>
    </div>
  )
}

function QuickStart() {
  return (
    <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-xl p-6 mb-8">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
        🚀 빠른 시작 가이드
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
        <div>
          <h4 className="font-medium text-gray-800 dark:text-gray-200 mb-2">💡 처음 시작한다면:</h4>
          <ul className="space-y-1 text-gray-600 dark:text-gray-400">
            <li>• LLM 입문 로드맵부터 시작</li>
            <li>• 각 논문을 순서대로 읽어보세요</li>
            <li>• 이해 안되는 부분은 관련 논문으로 이동</li>
          </ul>
        </div>
        <div>
          <h4 className="font-medium text-gray-800 dark:text-gray-200 mb-2">🎯 목표가 있다면:</h4>
          <ul className="space-y-1 text-gray-600 dark:text-gray-400">
            <li>• Computer Vision → CV 로드맵</li>
            <li>• 이미지 생성 → Generative AI</li>
            <li>• 실무 활용 → LLM 고급</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default function LearningPaths() {
  const [roadmaps, setRoadmaps] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTopic, setSearchTopic] = useState('')

  useEffect(() => {
    fetch('/api/learning-roadmaps')
      .then(r => r.json())
      .then(data => {
        setRoadmaps(data.roadmaps || [])
        setLoading(false)
      })
      .catch(error => {
        console.error('Failed to load roadmaps:', error)
        setLoading(false)
      })
  }, [])

  const [searchResult, setSearchResult] = useState(null)
  const [searching, setSearching] = useState(false)

  const handleSearchPath = async () => {
    if (!searchTopic.trim()) return

    setSearching(true)
    setSearchResult(null)
    try {
      const response = await fetch(`/api/research-path?topic=${encodeURIComponent(searchTopic)}&level=beginner`)
      const data = await response.json()

      if (data && data.papers && data.papers.length > 0) {
        // Show the result as a search result card (separate from curated roadmaps)
        setSearchResult(data)
      } else if (data && data.suggested_roadmaps) {
        setSearchResult({ ...data, no_results: true })
      } else {
        setSearchResult({ no_results: true, track_title: searchTopic, papers: [] })
      }
    } catch (error) {
      console.error('Failed to search research path:', error)
      setSearchResult({ no_results: true, track_title: searchTopic, papers: [] })
    }
    setSearching(false)
  }

  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
          🗺️ AI 연구 학습 로드맵
        </h1>
        <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          체계적인 학습 경로를 따라 AI 논문을 읽고, 분야별 핵심 개념을 단계적으로 이해해보세요.
          각 로드맵은 난이도별로 구성되어 있으며, 논문 간의 연관관계를 고려해 설계되었습니다.
        </p>
      </div>

      <QuickStart />

      {/* Custom Learning Path Search */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 mb-8">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
          🔍 맞춤형 학습 경로 찾기
        </h3>
        <div className="flex gap-3">
          <input
            type="text"
            value={searchTopic}
            onChange={(e) => setSearchTopic(e.target.value)}
            placeholder="관심 주제를 입력하세요 (예: transformer, diffusion, reinforcement learning)"
            className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
            onKeyPress={(e) => e.key === 'Enter' && handleSearchPath()}
          />
          <button
            onClick={handleSearchPath}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors text-sm font-medium"
          >
            경로 찾기
          </button>
        </div>
      </div>

      {/* Search Results */}
      {searching && (
        <div className="mb-8 text-center py-6">
          <div className="inline-block h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-2" />
          <p className="text-sm text-gray-500 dark:text-gray-400">'{searchTopic}' 관련 학습 경로를 찾고 있습니다...</p>
        </div>
      )}

      {searchResult && !searching && (
        <div className="mb-8">
          {searchResult.no_results ? (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-6 text-center">
              <p className="text-sm text-yellow-800 dark:text-yellow-200 mb-2">
                '{searchResult.track_title}'에 대한 직접적인 결과를 찾지 못했습니다.
              </p>
              <p className="text-xs text-yellow-600 dark:text-yellow-400">
                아래 추천 로드맵을 확인하거나, 다른 키워드로 검색해보세요 (예: transformer, diffusion, llm, vision)
              </p>
            </div>
          ) : (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                🎯 '{searchTopic}' 검색 결과
              </h2>
              <RoadmapCard roadmap={searchResult} />
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[1,2,3,4].map(i => (
            <div key={i} className="h-64 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {roadmaps.map(roadmap => (
            <RoadmapCard key={roadmap.track_name} roadmap={roadmap} />
          ))}
        </div>
      )}

      {!loading && roadmaps.length === 0 && (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">📚</div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            학습 로드맵이 없습니다
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            로드맵을 설정하거나 관심 주제로 맞춤형 경로를 검색해보세요.
          </p>
        </div>
      )}
    </main>
  )
}
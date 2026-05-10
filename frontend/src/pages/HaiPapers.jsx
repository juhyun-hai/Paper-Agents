import React, { useEffect, useState } from 'react'
import PaperCard from '../components/PaperCard.jsx'
import { PaperCardSkeleton } from '../components/Skeleton.jsx'
import { API_BASE } from '../api/client'

export default function HaiPapers() {
  const [papers, setPapers] = useState([])
  const [labInfo, setLabInfo] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/hai/papers?limit=100`).then((r) => r.json()),
      fetch(`${API_BASE}/hai/info`).then((r) => r.json()),
    ])
      .then(([papersRes, infoRes]) => {
        setPapers(papersRes.papers || [])
        setLabInfo(infoRes)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <section className="bg-gradient-to-br from-indigo-600 via-blue-700 to-purple-800 text-white py-14">
        <div className="max-w-5xl mx-auto px-4">
          <div className="flex items-center gap-3 text-sm text-blue-200 mb-3">
            <a href="https://hai.snu.ac.kr/" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">
              SNU HAI Lab
            </a>
            <span>›</span>
            <span>Featured Papers</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold mb-3">🎓 HAI Lab Picks</h1>
          <p className="text-blue-100 max-w-3xl leading-relaxed">
            {labInfo?.description ||
              'Manufacturing AI · physics-informed ML · physical AI · foundation models. HAI Lab의 연구 분야와 직결되는 논문들만 모았습니다.'}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {(labInfo?.keywords || ['manufacturing', 'physics-informed', 'fault diagnosis', 'digital twin', 'remaining useful life']).slice(0, 10).map((kw) => (
              <span key={kw} className="text-xs px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full">
                {kw}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Papers grid */}
      <section className="max-w-5xl mx-auto px-4 py-10">
        <div className="flex items-center justify-between mb-6">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {loading
              ? 'Loading...'
              : papers.length > 0
                ? `${papers.length}편의 HAI Lab 관련 논문`
                : '아직 매칭된 논문이 없습니다.'}
          </p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 9 }).map((_, i) => <PaperCardSkeleton key={i} />)}
          </div>
        ) : papers.length === 0 ? (
          <div className="text-center py-20 text-gray-500 dark:text-gray-400">
            새로운 매칭 논문이 곧 들어옵니다.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {papers.map((p) => (
              <PaperCard key={p.arxiv_id || p.id} paper={p} />
            ))}
          </div>
        )}
      </section>
    </main>
  )
}

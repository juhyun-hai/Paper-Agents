import React, { useState, useEffect } from 'react'

const SOURCE_CONFIG = {
  'HuggingFace Papers': { color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200', icon: '🤗' },
  'HuggingFace Papers (Yesterday)': { color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200', icon: '🤗' },
  'GitHub Trending': { color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200', icon: '⭐' },
  'Papers With Code': { color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200', icon: '📄' },
}

function TopicCard({ topic }) {
  const [expanded, setExpanded] = useState(false)
  const src = SOURCE_CONFIG[topic.source] || { color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200', icon: '🔥' }

  const keyResultLines = (topic.key_results || '').split('\n').filter(Boolean)

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${src.color}`}>
              {src.icon} {topic.source}
            </span>
            <span className="text-xs text-gray-400 dark:text-gray-500">{topic.date}</span>
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-white text-base leading-snug">
            {topic.tech_name || topic.title}
          </h3>
          {topic.tech_name && topic.tech_name !== topic.title && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{topic.title}</p>
          )}
        </div>
        {topic.upvotes > 0 && (
          <div className="flex flex-col items-center justify-center bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg px-2 py-1.5 min-w-[44px]">
            <span className="text-sm font-bold text-orange-600 dark:text-orange-400 leading-none">{topic.upvotes}</span>
            <span className="text-[10px] text-orange-400 dark:text-orange-500 mt-0.5">▲ votes</span>
          </div>
        )}
      </div>

      <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed mb-3">
        {expanded ? topic.summary : `${(topic.summary || '').slice(0, 200)}${(topic.summary || '').length > 200 ? '...' : ''}`}
      </p>

      {keyResultLines.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 mb-3">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">Key Results</p>
          <ul className="space-y-1">
            {(expanded ? keyResultLines : keyResultLines.slice(0, 3)).map((line, i) => (
              <li key={i} className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                {line.startsWith('•') ? line : `• ${line}`}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex gap-2 flex-wrap">
          {topic.paper_url && (
            <a href={topic.paper_url} target="_blank" rel="noopener noreferrer"
              className="text-xs text-primary hover:underline font-medium">
              📄 Paper
            </a>
          )}
          {topic.github_url && (
            <a href={topic.github_url} target="_blank" rel="noopener noreferrer"
              className="text-xs text-gray-600 dark:text-gray-400 hover:text-primary hover:underline font-medium">
              ⭐ GitHub
            </a>
          )}
          {topic.hf_url && topic.hf_url !== topic.paper_url && (
            <a href={topic.hf_url} target="_blank" rel="noopener noreferrer"
              className="text-xs text-gray-600 dark:text-gray-400 hover:text-primary hover:underline font-medium">
              🤗 HuggingFace
            </a>
          )}
        </div>
        {((topic.summary || '').length > 200 || keyResultLines.length > 3) && (
          <button onClick={() => setExpanded(!expanded)}
            className="text-xs text-primary hover:underline">
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>
    </div>
  )
}

export default function HotTopics() {
  const [topics, setTopics] = useState([])
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(1)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/hot-topics?days=${days}`)
      .then(r => r.json())
      .then(data => {
        setTopics(data.topics || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [days])

  if (loading) {
    return (
      <div className="mb-8">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-40 mb-4 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3].map(i => <div key={i} className="h-48 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />)}
        </div>
      </div>
    )
  }

  if (!topics.length) return null

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xl">🔥</span>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">Hot Topics</h2>
          <span className="text-xs bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300 px-2 py-0.5 rounded-full font-medium">Today</span>
        </div>
        <div className="flex gap-1">
          {[1, 3, 7].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`text-xs px-2 py-1 rounded-lg transition-colors ${days === d
                ? 'bg-primary text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}`}>
              {d === 1 ? 'Today' : `${d}d`}
            </button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {topics.map(topic => <TopicCard key={topic.id} topic={topic} />)}
      </div>
    </div>
  )
}

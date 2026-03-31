import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PaperCard from '../components/PaperCard.jsx'
import { PaperCardSkeleton } from '../components/Skeleton.jsx'
import { getTrendingPapers, getHotTopics } from '../api/client.js'

function HotTopicCard({ topic }) {
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {topic.tech_name}
            </h3>
            {topic.upvotes > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 text-xs font-medium rounded-full">
                🔥 {topic.upvotes} upvotes
              </span>
            )}
          </div>
          <h4 className="text-md font-medium text-gray-800 dark:text-gray-200 mb-3">
            {topic.title}
          </h4>
          <p className="text-gray-600 dark:text-gray-300 text-sm mb-4 leading-relaxed">
            {topic.summary || topic.key_results || "No description available"}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4 pt-4 border-t border-gray-100 dark:border-gray-700">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          📍 {topic.source}
        </span>
        {topic.date && (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            📅 {topic.date}
          </span>
        )}
        <div className="flex gap-2 ml-auto">
          {topic.paper_url && (
            <a
              href={topic.paper_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
            >
              📄 Paper
            </a>
          )}
          {topic.github_url && (
            <a
              href={topic.github_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              💻 Code
            </a>
          )}
          {topic.hf_url && (
            <a
              href={topic.hf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs px-2 py-1 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full hover:bg-orange-200 dark:hover:bg-orange-900/50 transition-colors"
            >
              🤗 HF
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Trending() {
  const [papers, setPapers] = useState([])
  const [repos, setRepos] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('papers')

  useEffect(() => {
    // Load trending papers and hot topics
    Promise.all([
      getTrendingPapers({ limit: 12 }).catch(() => ({ papers: [] })),
      getHotTopics({ limit: 10 }).catch(() => ({ topics: [] }))
    ]).then(([papersRes, hotTopicsRes]) => {
      setPapers(papersRes.papers || [])
      setRepos(hotTopicsRes.topics || [])
      setLoading(false)
    }).catch(() => {
      setLoading(false)
    })
  }, [])

  const TabButton = ({ tab, label, count }) => (
    <button
      onClick={() => setActiveTab(tab)}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        activeTab === tab
          ? 'bg-primary text-white'
          : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
      }`}
    >
      {label} {count > 0 && `(${count})`}
    </button>
  )

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          🔥 Trending Research
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-300">
          Hottest papers and repositories from HuggingFace Papers and GitHub
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <TabButton tab="papers" label="🔥 Trending Papers" count={papers.length} />
        <TabButton tab="repos" label="⚡ Hot Topics" count={repos.length} />
      </div>

      {/* Content */}
      {activeTab === 'papers' && (
        <div>
          <div className="mb-4 text-sm text-gray-600 dark:text-gray-400">
            Papers ranked by combined score: HuggingFace upvotes + GitHub stars + recency
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {loading
              ? Array.from({ length: 8 }).map((_, i) => <PaperCardSkeleton key={i} />)
              : papers.map((paper) => (
                  <PaperCard
                    key={paper.arxiv_id}
                    paper={paper}
                    showTrendingMetrics={true}
                  />
                ))
            }
          </div>
        </div>
      )}

      {activeTab === 'repos' && (
        <div>
          <div className="mb-4 text-sm text-gray-600 dark:text-gray-400">
            Hot topics from HuggingFace Papers and GitHub trending AI/ML projects
          </div>
          <div className="space-y-4">
            {loading
              ? Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 h-32"></div>
                  </div>
                ))
              : repos.map((topic, index) => (
                  <HotTopicCard key={topic.id || index} topic={topic} />
                ))
            }
          </div>
        </div>
      )}

    </main>
  )
}

function RepoCard({ repo }) {
  const {
    repo_full_name,
    description,
    stars,
    forks,
    language,
    topics = [],
    today_stars,
    arxiv_id,
    paper_url,
    last_updated,
  } = repo

  const updatedDate = new Date(last_updated).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <a
              href={`https://github.com/${repo_full_name}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-lg font-semibold text-primary hover:underline"
            >
              {repo_full_name}
            </a>
            {arxiv_id && (
              <Link
                to={`/paper/${arxiv_id}`}
                className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 px-2 py-1 rounded-full hover:underline"
              >
                📄 Paper
              </Link>
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-3 leading-relaxed">
            {description}
          </p>
          <div className="flex flex-wrap gap-2">
            {topics.slice(0, 6).map((topic) => (
              <span
                key={topic}
                className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>

        <div className="flex flex-col items-end gap-2">
          {today_stars > 0 && (
            <span className="text-xs bg-gradient-to-r from-orange-400 to-red-500 text-white px-2 py-1 rounded-full font-medium">
              🚀 +{today_stars} today
            </span>
          )}
          <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-1">
              <svg className="w-4 h-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              {stars.toLocaleString()}
            </div>
            <div className="flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
              </svg>
              {forks.toLocaleString()}
            </div>
            {language && (
              <span className="text-xs bg-indigo-50 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 px-2 py-1 rounded">
                {language}
              </span>
            )}
            <span className="text-xs">{updatedDate}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
import React, { useState, useEffect } from 'react'

const CATEGORY_LABEL = {
  general: '일반',
  bug: '버그',
  feature: '기능 요청',
  paper: '논문',
}

const CATEGORY_COLOR = {
  general: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  bug: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  feature: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  paper: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
}

export default function AdminFeedback() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    fetch('/api/feedback')
      .then(r => r.json())
      .then(d => { setItems(d.feedback || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const filtered = filter === 'all' ? items : items.filter(i => i.category === filter)

  const copyAll = () => {
    const text = filtered.map(i =>
      `[${i.created_at}] [${CATEGORY_LABEL[i.category] || i.category}] ${i.name || '익명'}${i.email ? ` <${i.email}>` : ''}\n${i.message}`
    ).join('\n\n---\n\n')
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-12">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">피드백 관리</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">총 {items.length}건</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {['all', 'general', 'bug', 'feature', 'paper'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                filter === f
                  ? 'bg-primary text-white border-primary'
                  : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary'
              }`}
            >
              {f === 'all' ? '전체' : CATEGORY_LABEL[f]}
              {f === 'all' ? ` (${items.length})` : ` (${items.filter(i => i.category === f).length})`}
            </button>
          ))}
          <button
            onClick={copyAll}
            disabled={filtered.length === 0}
            className="text-xs px-3 py-1.5 rounded-full border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary hover:text-primary disabled:opacity-40 transition-colors"
          >
            {copied ? '✅ 복사됨' : '📋 Claude에 붙여넣기용 복사'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => <div key={i} className="h-24 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-gray-400 dark:text-gray-600">
          <div className="text-4xl mb-3">💬</div>
          <p>피드백이 없습니다</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(item => (
            <div key={item.id} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${CATEGORY_COLOR[item.category] || CATEGORY_COLOR.general}`}>
                    {CATEGORY_LABEL[item.category] || item.category}
                  </span>
                  <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {item.name || '익명'}
                  </span>
                  {item.email && (
                    <span className="text-xs text-gray-400">{item.email}</span>
                  )}
                </div>
                <span className="text-xs text-gray-400 whitespace-nowrap">{item.created_at?.slice(0, 16)}</span>
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">{item.message}</p>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE } from '../api/client'
import { getClientId } from '../utils/clientId'

export default function Alerts() {
  const cid = getClientId()
  const [searches, setSearches] = useState([])
  const [matches, setMatches] = useState({})  // sid → matches[]
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ name: '', tag: '', keyword: '' })
  const [allTags, setAllTags] = useState([])       // 자동완성용
  // 마지막 방문 시각 — 이후 발행된 논문에 NEW 뱃지
  const [lastSeen] = useState(() => localStorage.getItem('alerts_last_seen') || '')
  useEffect(() => {
    localStorage.setItem('alerts_last_seen', new Date().toISOString().slice(0, 10))
  }, [])
  useEffect(() => {
    fetch(`${API_BASE}/tags/popular?limit=200&min_count=2`)
      .then(r => r.json())
      .then(d => setAllTags((d.tags || []).map(t => t.name)))
      .catch(() => {})
  }, [])

  const refresh = () => {
    setLoading(true)
    fetch(`${API_BASE}/saved-searches?client_id=${cid}`)
      .then(r => r.json())
      .then(d => {
        const list = d.saved_searches || []
        setSearches(list)
        setLoading(false)
        // 각 검색에 대해 매칭 로드
        list.forEach(s => {
          fetch(`${API_BASE}/saved-searches/${s.id}/matches?days=60`)
            .then(r => r.json())
            .then(md => setMatches(prev => ({ ...prev, [s.id]: md.matches || [] })))
        })
      })
  }
  useEffect(refresh, [])

  const add = async () => {
    if (!form.name || (!form.tag && !form.keyword)) {
      alert('이름 + tag 또는 keyword 필요')
      return
    }
    setAdding(true)
    const body = { client_id: cid, name: form.name }
    if (form.tag) body.tag = form.tag.trim().toLowerCase()
    if (form.keyword) body.keyword = form.keyword.trim()
    await fetch(`${API_BASE}/saved-searches`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    setForm({ name: '', tag: '', keyword: '' })
    setAdding(false)
    refresh()
  }

  const del = async (sid) => {
    if (!confirm('이 알림 삭제할까?')) return
    await fetch(`${API_BASE}/saved-searches/${sid}?client_id=${cid}`, { method: 'DELETE' })
    refresh()
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
        🔔 내 알림
      </h1>
      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 mb-6">
        관심 tag / 키워드 저장 → 매일 매칭되는 새 논문 모음 (브라우저 식별 기반)
      </p>

      {/* Add form */}
      <div className="bg-gray-50 dark:bg-gray-800/30 rounded-xl p-4 mb-8 border border-gray-200 dark:border-gray-700">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-3">새 알림 추가</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            type="text" placeholder="이름 (예: 'VLA 논문')"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-sm"
          />
          <div>
            <input
              type="text" placeholder="tag (예: vision-language-action)"
              value={form.tag} list="tag-options"
              onChange={(e) => setForm({ ...form, tag: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-sm"
            />
            <datalist id="tag-options">
              {allTags.map(t => <option key={t} value={t} />)}
            </datalist>
            {form.tag && allTags.length > 0 && !allTags.includes(form.tag.trim().toLowerCase()) && (
              <p className="mt-1 text-[11px] text-amber-600 dark:text-amber-400">
                ⚠ 등록된 tag 목록에 없어요 — 입력 중이면 무시, 오타면 자동완성에서 선택
              </p>
            )}
          </div>
          <input
            type="text" placeholder="키워드 (free-text)"
            value={form.keyword}
            onChange={(e) => setForm({ ...form, keyword: e.target.value })}
            className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-sm"
          />
        </div>
        <button
          onClick={add} disabled={adding}
          className="mt-3 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {adding ? '추가 중…' : '+ 추가'}
        </button>
      </div>

      {/* List */}
      {loading && <p className="text-gray-500">로딩 중…</p>}
      {!loading && searches.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          아직 알림 없음. 위에서 tag (예: <code className="px-1 bg-gray-100 dark:bg-gray-800 rounded">transformer</code>)
          또는 키워드를 추가하세요.
        </div>
      )}

      <div className="space-y-6">
        {searches.map(s => (
          <div key={s.id} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-bold text-gray-900 dark:text-white">{s.name}</h3>
              <button
                onClick={() => del(s.id)}
                className="text-xs text-red-500 hover:text-red-700"
              >
                삭제
              </button>
            </div>
            <div className="text-xs text-gray-500 mb-3 space-x-2">
              {s.tag && <span>🏷 <code>{s.tag}</code></span>}
              {s.keyword && <span>🔍 "<code>{s.keyword}</code>"</span>}
              {s.category && <span>📂 <code>{s.category}</code></span>}
              {matches[s.id] && <span className="ml-2 text-indigo-600 dark:text-indigo-400 font-semibold">최근 60일 {matches[s.id].length}편</span>}
            </div>
            <ul className="space-y-2">
              {(matches[s.id] || []).slice(0, 5).map(m => {
                const isNew = lastSeen && m.published_date && m.published_date > lastSeen
                return (
                  <li key={m.arxiv_id} className="text-sm">
                    {isNew && (
                      <span className="mr-1.5 text-[10px] font-bold text-white bg-rose-500 px-1.5 py-0.5 rounded">NEW</span>
                    )}
                    <Link to={`/paper/${m.arxiv_id}`}
                      className="text-gray-900 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400">
                      {m.title}
                    </Link>
                    <span className="text-xs text-gray-500 ml-2">({m.published_date || '?'})</span>
                  </li>
                )
              })}
            </ul>
            {matches[s.id] && matches[s.id].length > 5 && (
              <p className="text-xs text-gray-500 mt-2">… 외 {matches[s.id].length - 5}편</p>
            )}
          </div>
        ))}
      </div>
    </main>
  )
}

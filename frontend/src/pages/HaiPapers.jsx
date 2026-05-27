import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE } from '../api/client'

// Compact paper card tuned for the /hai list view.
function HaiPaperCard({ paper }) {
  const isLab = paper.is_lab_publication
  const date = paper.published_date
    ? new Date(paper.published_date).toISOString().slice(0, 10)
    : (paper.year || '')
  // Lab papers (hai:NNN, openalex:WID) link out to the publisher; arXiv papers
  // open in our paper detail page.
  const isExternal = paper.arxiv_id?.startsWith('openalex:') || paper.arxiv_id?.startsWith('hai:')
  const detailHref = isExternal
    ? (paper.html_url || '#')
    : `/paper/${paper.arxiv_id}`

  const venue = paper.venue
  const authorPreview = (paper.authors || []).slice(0, 4).join(', ')
  const moreAuthors = Math.max(0, (paper.authors || []).length - 4)

  // Related-paper state — only used for lab papers
  const [expanded, setExpanded] = useState(false)
  const [related, setRelated] = useState(null) // null=not loaded
  const [loadingRel, setLoadingRel] = useState(false)
  const [relReason, setRelReason] = useState(null)

  async function toggleRelated() {
    if (!expanded && related === null) {
      setLoadingRel(true)
      try {
        const url = `${API_BASE}/hai/related?lab_id=${encodeURIComponent(paper.arxiv_id)}&limit=5&days=30`
        const r = await fetch(url)
        const d = await r.json()
        setRelated(d.papers || [])
        setRelReason(d.reason || null)
      } catch {
        setRelated([])
        setRelReason('error')
      } finally {
        setLoadingRel(false)
      }
    }
    setExpanded(!expanded)
  }

  const headerAndBody = (
    <>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex flex-wrap items-center gap-2">
          {isLab && (
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-200">
              🎓 HAI Lab
            </span>
          )}
          {paper.hai_topic && (
            <span className="inline-flex text-[11px] font-medium px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-200">
              {paper.hai_topic.replace('-', ' ')}
            </span>
          )}
          {date && (
            <span className="text-[11px] text-gray-500 dark:text-gray-400">{date}</span>
          )}
        </div>
        {paper.citation_count > 0 && (
          <span className="text-[11px] text-gray-500 dark:text-gray-400 whitespace-nowrap">
            {paper.citation_count.toLocaleString()} citations
          </span>
        )}
      </div>

      <h3 className="text-base font-semibold text-gray-900 dark:text-white leading-snug mb-2 group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors">
        {paper.title}
      </h3>

      {authorPreview && (
        <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
          {authorPreview}{moreAuthors > 0 && ` +${moreAuthors}`}
        </p>
      )}

      {venue && (
        <p className="text-xs text-gray-500 dark:text-gray-500 italic mb-2">
          {venue}
        </p>
      )}

      {paper.abstract && (
        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed line-clamp-3">
          {paper.abstract}
        </p>
      )}
    </>
  )

  const titleLink = isExternal
    ? <a href={detailHref} target="_blank" rel="noopener noreferrer" className="block">{headerAndBody}</a>
    : <Link to={detailHref} className="block">{headerAndBody}</Link>

  return (
    <article className="group bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5 hover:border-indigo-400 hover:shadow-md transition-all">
      {titleLink}

      {isLab && (
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          <button
            onClick={toggleRelated}
            className="w-full flex items-center justify-between text-xs font-medium text-indigo-600 dark:text-indigo-300 hover:text-indigo-800 dark:hover:text-indigo-200"
          >
            <span>🔗 관련 최신 arXiv 논문 (30일 이내)</span>
            <span>{expanded ? '▲' : '▼'}</span>
          </button>

          {expanded && (
            <div className="mt-3 space-y-2">
              {loadingRel && (
                <div className="text-xs text-gray-500 dark:text-gray-400">로딩 중…</div>
              )}
              {!loadingRel && related && related.length === 0 && (
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {relReason === 'no embedding yet'
                    ? '이 논문의 임베딩이 아직 생성되지 않았습니다.'
                    : '최근 30일 이내 유사한 논문을 찾지 못했습니다.'}
                </div>
              )}
              {!loadingRel && related && related.length > 0 && related.map((r) => (
                <Link
                  key={r.arxiv_id}
                  to={`/paper/${r.arxiv_id}`}
                  className="block px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-indigo-400 hover:bg-indigo-50/40 dark:hover:bg-indigo-900/10 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="text-sm font-medium text-gray-900 dark:text-white leading-snug line-clamp-2">
                      {r.title}
                    </div>
                    <span className="shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-200">
                      {Math.round((r.similarity || 0) * 100)}%
                    </span>
                  </div>
                  <div className="mt-1 text-[11px] text-gray-500 dark:text-gray-400">
                    {(r.authors || []).slice(0, 2).join(', ')}
                    {r.authors && r.authors.length > 2 && ` +${r.authors.length - 2}`}
                    {r.published_date && <span className="ml-2">{r.published_date.slice(0, 10)}</span>}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  )
}

export default function HaiPapers() {
  const [papers, setPapers] = useState([])
  const [topics, setTopics] = useState([])
  const [labInfo, setLabInfo] = useState(null)
  const [loading, setLoading] = useState(true)

  // Filter state
  const [topic, setTopic] = useState('all')   // 'all' or topic key
  const [source, setSource] = useState('all') // 'all' | 'lab' | 'arxiv'
  const [sort, setSort] = useState('recent')  // 'recent' | 'score'
  const [search, setSearch] = useState('')

  // Initial load
  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/hai/info`).then(r => r.json()),
      fetch(`${API_BASE}/hai/topics`).then(r => r.json()),
    ]).then(([info, t]) => {
      setLabInfo(info)
      setTopics(t.topics || [])
    })
  }, [])

  // Re-query papers when filters change
  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ limit: '200', sort })
    if (topic !== 'all') params.set('topic', topic)
    if (source !== 'all') params.set('source', source)
    fetch(`${API_BASE}/hai/papers?${params}`)
      .then(r => r.json())
      .then(d => {
        setPapers(d.papers || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [topic, source, sort])

  // Client-side title search
  const filtered = useMemo(() => {
    if (!search.trim()) return papers
    const q = search.toLowerCase()
    return papers.filter(p =>
      (p.title || '').toLowerCase().includes(q) ||
      (p.authors || []).some(a => a.toLowerCase().includes(q))
    )
  }, [papers, search])

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Hero */}
      <section className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-10">
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-3">
            <a href="https://hai.snu.ac.kr/" target="_blank" rel="noopener noreferrer"
               className="hover:text-indigo-600 transition-colors">SNU HAI Lab</a>
            <span>›</span>
            <span>Featured Papers</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white mb-3">
            🎓 HAI Lab Picks
          </h1>
          <p className="text-base text-gray-600 dark:text-gray-300 max-w-3xl leading-relaxed">
            HAI Lab은 <strong>Industrial Foundation Models</strong>, <strong>Industrial Physical AI</strong>를 중심으로, <strong>Manufacturing AI</strong>, <strong>Physics-Informed ML</strong>, <strong>Signal Processing</strong>, <strong>Digital Twin</strong>, <strong>Reliability</strong>까지 자율 지능 시스템을 연구합니다.
            <br />
            HAI Lab <span className="text-purple-600 dark:text-purple-400 font-medium">자체 발표 논문</span>과
            arXiv 신규 논문 중 <span className="text-indigo-600 dark:text-indigo-400 font-medium">관련 분야</span>를 한 곳에서 봅니다.
          </p>
        </div>
      </section>

      {/* Filters */}
      <section className="sticky top-0 z-10 bg-white/90 dark:bg-gray-900/90 backdrop-blur border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-4 space-y-3">
          {/* Source + sort + search row */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="inline-flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-700 text-sm">
              {[
                { v: 'all', label: '전체' },
                { v: 'lab', label: '🎓 HAI Lab' },
                { v: 'arxiv', label: 'arXiv 매칭' },
              ].map(opt => (
                <button key={opt.v} onClick={() => setSource(opt.v)}
                  className={`px-3 py-1.5 transition-colors ${source === opt.v
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
                  {opt.label}
                </button>
              ))}
            </div>

            <div className="inline-flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-700 text-sm">
              {[
                { v: 'recent', label: '최신순' },
                { v: 'score', label: '관련도순' },
              ].map(opt => (
                <button key={opt.v} onClick={() => setSort(opt.v)}
                  className={`px-3 py-1.5 transition-colors ${sort === opt.v
                    ? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
                    : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
                  {opt.label}
                </button>
              ))}
            </div>

            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="제목 / 저자 검색…"
                className="w-full px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Topic chips */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setTopic('all')}
              className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                topic === 'all'
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-700 hover:border-indigo-400'
              }`}
            >
              All ({topics.reduce((s, t) => s + t.total, 0)})
            </button>
            {topics.map(t => (
              <button
                key={t.key}
                onClick={() => setTopic(t.key)}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  topic === t.key
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-700 hover:border-indigo-400'
                }`}
              >
                {t.label} ({t.total})
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* List */}
      <section className="max-w-6xl mx-auto px-4 py-6">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          {loading ? 'Loading...' : `${filtered.length}편 표시 중`}
        </p>
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-40 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 text-gray-500 dark:text-gray-400">
            조건에 맞는 논문이 없습니다.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filtered.map((p) => <HaiPaperCard key={p.arxiv_id} paper={p} />)}
          </div>
        )}
      </section>
    </main>
  )
}

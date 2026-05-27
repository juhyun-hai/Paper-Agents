import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { API_BASE } from '../api/client'

// 토픽 chip — 명시적 필터 + 토픽별 예시 질문 (DB 매칭이 잘 되는 것들로 검증)
const TOPICS = [
  {
    key: '',  // 전체
    label: '전체',
    icon: '🌐',
    examples: [
      'HAI Lab의 최근 fault diagnosis 연구는?',
      'Physics-Informed ML을 PHM에 어떻게 적용하나?',
      'Bearing fault diagnosis에서 자주 쓰이는 신호 처리 기법은?',
      'Domain adaptation으로 변동 운영 조건을 어떻게 다루나?',
    ],
  },
  {
    key: 'lab',
    label: 'HAI Lab',
    icon: '🎓',
    examples: [
      'HAI Lab은 요즘 어떤 논문이 나와?',
      'HAI Lab의 fault diagnosis 연구 정리해줘',
      'HAI Lab의 signal processing 연구는?',
      'HAI Lab의 generative design 관련 연구는?',
    ],
  },
  {
    key: 'fault-diagnosis',
    label: 'Fault Diagnosis',
    icon: '⚙️',
    examples: [
      'Bearing fault diagnosis 최신 기법은?',
      'Unseen fault 식별을 위한 접근법은?',
      'Variable speed 환경에서 결함 진단 핵심 아이디어',
      'Hybrid signal processing + deep learning fault diagnosis 사례',
    ],
  },
  {
    key: 'rul-phm',
    label: 'PHM / RUL',
    icon: '📈',
    examples: [
      'Remaining useful life 예측 최근 트렌드',
      'Uncertainty-aware prognostics 핵심 아이디어',
      'Few-shot RUL 예측 접근법은?',
      'PHM 시스템에서 데이터 부족을 다루는 방법',
    ],
  },
  {
    key: 'signal-processing',
    label: 'Signal Processing',
    icon: '📡',
    examples: [
      '진동 신호 디노이징 최신 기법은?',
      'Multi-scale signal analysis 접근법',
      'Time-frequency representation을 ML과 결합하는 방법',
      'Signal processing 기반 attention 메커니즘은?',
    ],
  },
  {
    key: 'physics-informed',
    label: 'Physics-Informed ML',
    icon: '🔬',
    examples: [
      'Physics-informed neural network 핵심 아이디어',
      'PINN을 fault diagnosis에 적용한 사례',
      'Physics-guided data augmentation 기법',
      'Hybrid physics + data-driven 모델 트렌드',
    ],
  },
  {
    key: 'manufacturing',
    label: 'Manufacturing',
    icon: '🏭',
    examples: [
      'Manufacturing AI 최신 동향',
      'Smart manufacturing에서 AI 적용 사례',
      '제조 공정 최적화 ML 기법',
      'Quality inspection AI 트렌드',
    ],
  },
  {
    key: 'digital-twin',
    label: 'Digital Twin',
    icon: '👯',
    examples: [
      'Digital twin과 ML 결합 연구',
      'Digital twin 기반 예측 정비 접근법',
      'Real-time digital twin 구현 핵심 기술',
      'Physics-informed digital twin 사례',
    ],
  },
]

export default function PaperAgentModal({ isOpen, onClose }) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState('')
  const [topicKey, setTopicKey] = useState('')  // '' = 전체
  const inputRef = useRef(null)
  const endRef = useRef(null)
  const abortRef = useRef(null)

  const activeTopic = TOPICS.find(t => t.key === topicKey) || TOPICS[0]

  useEffect(() => {
    if (isOpen) {
      const t = setTimeout(() => inputRef.current?.focus(), 80)
      return () => clearTimeout(t)
    }
  }, [isOpen])

  useEffect(() => {
    if (isOpen) endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming, isOpen])

  // ESC closes
  useEffect(() => {
    if (!isOpen) return
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  async function ask(q) {
    if (!q.trim() || streaming) return
    setError('')
    setMessages(prev => [...prev,
      { role: 'user', content: q },
      { role: 'assistant', content: '', sources: [] }
    ])
    setQuestion('')
    setStreaming(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const resp = await fetch(`${API_BASE}/agent/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, topic: topicKey || undefined }),
        signal: controller.signal,
      })
      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(text || `HTTP ${resp.status}`)
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop()
        for (const ev of events) {
          const line = ev.split('\n').find(l => l.startsWith('data: '))
          if (!line) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') continue
          try {
            const obj = JSON.parse(data)
            if (obj.type === 'sources') {
              setMessages(prev => {
                const copy = [...prev]
                copy[copy.length - 1] = { ...copy[copy.length - 1], sources: obj.sources }
                return copy
              })
            } else if (obj.type === 'token') {
              setMessages(prev => {
                const copy = [...prev]
                const last = copy[copy.length - 1]
                copy[copy.length - 1] = { ...last, content: last.content + obj.content }
                return copy
              })
            } else if (obj.type === 'error') {
              setError(obj.message || 'LLM 오류')
            }
          } catch { /* ignore */ }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') setError(e.message || '요청 실패')
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  function stop() { abortRef.current?.abort() }
  function clearChat() { setMessages([]); setError('') }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 z-40 transition-opacity" onClick={onClose} />

      {/* Right-side drawer (desktop) / fullscreen (mobile) */}
      <div className="fixed inset-0 sm:inset-auto sm:top-0 sm:right-0 sm:h-screen sm:w-[640px] bg-white dark:bg-gray-900 z-50 shadow-2xl flex flex-col">
        {/* Header */}
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              🤖 Paper Agent
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-200">beta</span>
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              7천여 편 임베딩 검색 + 로컬 LLM(Qwen3 14B)
            </p>
          </div>
          <div className="flex items-center gap-1">
            {messages.length > 0 && (
              <button onClick={clearChat} title="대화 지우기"
                className="px-2 py-1.5 text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
                🗑️
              </button>
            )}
            <button onClick={onClose} title="닫기 (ESC)"
              className="px-2 py-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
              ✕
            </button>
          </div>
        </div>

        {/* Topic chip row (always visible) */}
        <div className="px-5 pt-3 pb-2 border-b border-gray-100 dark:border-gray-800">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5 font-semibold">
            주제 필터
          </p>
          <div className="flex flex-wrap gap-1.5">
            {TOPICS.map(t => (
              <button key={t.key || 'all'} onClick={() => setTopicKey(t.key)}
                className={`text-[11px] px-2.5 py-1 rounded-full border transition-colors ${
                  topicKey === t.key
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-700 hover:border-indigo-400'
                }`}>
                <span className="mr-1">{t.icon}</span>{t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="space-y-3">
              <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                {activeTopic.icon} {activeTopic.label} 예시 질문
              </p>
              <div className="grid grid-cols-1 gap-2">
                {activeTopic.examples.map((s) => (
                  <button key={s} onClick={() => ask(s)} disabled={streaming}
                    className="text-left text-sm px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-indigo-400 hover:bg-indigo-50/40 dark:hover:bg-indigo-900/10 transition-colors disabled:opacity-50">
                    {s}
                  </button>
                ))}
              </div>
              <div className="text-[11px] text-gray-400 dark:text-gray-500 pt-2 border-t border-gray-100 dark:border-gray-800">
                💡 답변에 인용된 arXiv ID를 클릭하면 한국어 요약 + 핵심 그림이 있는 상세 페이지로 이동합니다. 주제 필터를 바꾸면 그 분야 논문만 검색합니다.
              </div>
            </div>
          )}

          {messages.map((m, i) => <Bubble key={i} message={m} onSelect={onClose} />)}

          {streaming && (
            <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
              <span className="inline-block h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
              답변 생성 중…
            </div>
          )}

          {error && (
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-xs text-red-700 dark:text-red-300">
              {error}
            </div>
          )}

          <div ref={endRef} />
        </div>

        {/* Composer */}
        <div className="border-t border-gray-200 dark:border-gray-800 px-4 py-3 bg-white dark:bg-gray-900">
          <form onSubmit={(e) => { e.preventDefault(); ask(question) }}
            className="flex gap-2 items-end bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl p-2 focus-within:border-indigo-400">
            <textarea ref={inputRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(question) }
              }}
              placeholder="연구 주제 질문 (Enter 전송 · Shift+Enter 줄바꿈)"
              rows={1}
              maxLength={500}
              className="flex-1 resize-none bg-transparent text-sm text-gray-900 dark:text-white placeholder-gray-400 px-3 py-2 focus:outline-none max-h-32"
            />
            {streaming ? (
              <button type="button" onClick={stop}
                className="px-4 py-2 rounded-xl bg-red-500 text-white text-sm font-medium hover:bg-red-600 transition-colors">
                중단
              </button>
            ) : (
              <button type="submit" disabled={!question.trim()}
                className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-40">
                전송
              </button>
            )}
          </form>
          <div className="mt-1.5 flex justify-between text-[10px] text-gray-400 dark:text-gray-500 px-2">
            <span>IP당 분당 3회 / 일당 30회</span>
            <span>{question.length}/500</span>
          </div>
        </div>
      </div>
    </>
  )
}

// Splits an LLM answer into:
//   - a "핵심 요약" summary line (visually highlighted box)
//   - the rest of the body
// Then renders inline [N] citation tokens as small clickable chips.
function AnswerBody({ text, sources }) {
  // Pull the "**핵심 요약:** ..." line if present
  let summary = ''
  let body = text
  const m = text.match(/^\s*\*\*핵심\s*요약\s*[:：]\*\*\s*([^\n]+)\n?/)
  if (m) {
    summary = m[1].trim()
    body = text.slice(m[0].length).trim()
  }

  return (
    <div>
      {summary && (
        <div className="mb-3 px-3 py-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 border-l-4 border-indigo-500">
          <div className="text-[10px] uppercase tracking-wider text-indigo-700 dark:text-indigo-300 font-bold mb-0.5">
            핵심 요약
          </div>
          <div className="text-sm text-gray-900 dark:text-gray-100 leading-snug">
            {renderWithCitations(summary, sources)}
          </div>
        </div>
      )}
      <div className="prose prose-sm dark:prose-invert max-w-none
                      prose-p:my-1.5 prose-p:leading-relaxed
                      prose-ul:my-1.5 prose-ul:pl-5
                      prose-li:my-1 prose-li:leading-snug prose-li:marker:text-indigo-500
                      prose-strong:text-indigo-700 dark:prose-strong:text-indigo-300 prose-strong:font-semibold
                      prose-code:text-pink-600 dark:prose-code:text-pink-300
                      prose-code:bg-gray-100 dark:prose-code:bg-gray-900 prose-code:px-1 prose-code:rounded prose-code:before:content-none prose-code:after:content-none">
        <ReactMarkdown
          components={{
            p: ({ children }) => <p>{processChildren(children, sources)}</p>,
            li: ({ children }) => <li>{processChildren(children, sources)}</li>,
            strong: ({ children }) => <strong>{children}</strong>,
            // 헤더 토큰이 들어와도 시각 노이즈 줄이기
            h2: ({ children }) => <p className="font-semibold mt-2 mb-1">{children}</p>,
            h3: ({ children }) => <p className="font-semibold mt-2 mb-1">{children}</p>,
          }}
        >
          {body}
        </ReactMarkdown>
      </div>
    </div>
  )
}

// Replace [N] tokens in a plain string with citation chip elements.
function renderWithCitations(text, sources) {
  if (typeof text !== 'string') return text
  const parts = []
  const re = /\[(\d+)\]/g
  let last = 0
  let match
  let key = 0
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    const idx = parseInt(match[1], 10) - 1
    parts.push(<CiteChip key={`c${key++}`} index={idx + 1} src={sources[idx]} />)
    last = match.index + match[0].length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

// React children pass-through that runs renderWithCitations on string parts.
function processChildren(children, sources) {
  const arr = Array.isArray(children) ? children : [children]
  const out = []
  arr.forEach((c, i) => {
    if (typeof c === 'string') {
      out.push(...[].concat(renderWithCitations(c, sources)).map((el, j) => (
        typeof el === 'string' ? <span key={`s${i}-${j}`}>{el}</span> : el
      )))
    } else {
      out.push(c)
    }
  })
  return out
}

function CiteChip({ index, src }) {
  if (!src) {
    return <span className="inline-flex items-center text-[10px] font-mono align-baseline mx-0.5 px-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">{index}</span>
  }
  const isArxiv = src.is_arxiv
  const inner = (
    <span className={`inline-flex items-center text-[10px] font-mono font-semibold align-baseline mx-0.5 px-1.5 rounded ${
      isArxiv
        ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-200 hover:bg-indigo-200 dark:hover:bg-indigo-800/60'
        : 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-200'
    }`} title={src.title || ''}>
      {index}
    </span>
  )
  if (isArxiv) {
    return <Link to={`/paper/${src.arxiv_id}`}>{inner}</Link>
  }
  return inner
}

function Bubble({ message, onSelect }) {
  const isUser = message.role === 'user'
  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-indigo-600 text-white rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    )
  }
  return (
    <div className="flex justify-start">
      <div className="max-w-[92%] bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl px-4 py-3">
        {/* Source citations */}
        {message.sources && message.sources.length > 0 && (
          <div className="mb-3 pb-3 border-b border-gray-200 dark:border-gray-700">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5 font-semibold">
              📚 검색된 논문 {message.sources.length}편
            </p>
            <div className="space-y-1">
              {message.sources.map((s) => (
                s.is_arxiv ? (
                  <Link key={s.arxiv_id} to={`/paper/${s.arxiv_id}`} onClick={onSelect}
                    className="block text-[11px] hover:underline truncate">
                    <span className="font-mono text-indigo-600 dark:text-indigo-300">[{s.arxiv_id}]</span>
                    <span className="text-gray-700 dark:text-gray-300 ml-1">{s.title}</span>
                    <span className="ml-1.5 text-[10px] text-gray-400">{Math.round((s.similarity || 0) * 100)}%</span>
                  </Link>
                ) : (
                  <div key={s.arxiv_id} className="text-[11px] truncate">
                    <span className="font-mono text-purple-600 dark:text-purple-300">[{s.arxiv_id}]</span>
                    <span className="text-gray-700 dark:text-gray-300 ml-1">{s.title}</span>
                    <span className="ml-1.5 text-[10px] text-gray-400">{Math.round((s.similarity || 0) * 100)}%</span>
                  </div>
                )
              ))}
            </div>
          </div>
        )}

        {/* Markdown rendered answer with summary box + citation chips */}
        {message.content ? (
          <AnswerBody text={message.content} sources={message.sources || []} />
        ) : (
          <span className="text-gray-400">…</span>
        )}
      </div>
    </div>
  )
}

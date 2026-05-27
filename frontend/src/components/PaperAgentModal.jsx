import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { API_BASE } from '../api/client'

const SUGGESTIONS = [
  '최근 산업용 Foundation Model 트렌드 정리해줘',
  'PHM에서 uncertainty-aware fault diagnosis 접근법은?',
  'Physics-Informed ML로 baseline 깨는 핵심 아이디어가 뭐야?',
  'Digital twin과 signal processing을 결합한 최근 연구는?',
]

export default function PaperAgentModal({ isOpen, onClose }) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)
  const endRef = useRef(null)
  const abortRef = useRef(null)

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
        body: JSON.stringify({ question: q }),
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

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="space-y-3">
              <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                예시 질문
              </p>
              <div className="grid grid-cols-1 gap-2">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => ask(s)} disabled={streaming}
                    className="text-left text-sm px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-indigo-400 hover:bg-indigo-50/40 dark:hover:bg-indigo-900/10 transition-colors disabled:opacity-50">
                    {s}
                  </button>
                ))}
              </div>
              <div className="text-[11px] text-gray-400 dark:text-gray-500 pt-2 border-t border-gray-100 dark:border-gray-800">
                💡 답변에 인용된 arXiv ID를 클릭하면 한국어 요약 + 핵심 그림이 있는 상세 페이지로 이동합니다.
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

        {/* Markdown rendered answer */}
        {message.content ? (
          <div className="prose prose-sm dark:prose-invert max-w-none
                          prose-headings:font-semibold prose-headings:text-gray-900 dark:prose-headings:text-white
                          prose-h2:text-base prose-h2:mt-3 prose-h2:mb-1.5
                          prose-h3:text-sm prose-h3:mt-2 prose-h3:mb-1
                          prose-p:my-1.5 prose-p:leading-relaxed
                          prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5
                          prose-strong:text-indigo-700 dark:prose-strong:text-indigo-300
                          prose-code:text-pink-600 dark:prose-code:text-pink-300
                          prose-code:bg-gray-100 dark:prose-code:bg-gray-900 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        ) : (
          <span className="text-gray-400">…</span>
        )}
      </div>
    </div>
  )
}

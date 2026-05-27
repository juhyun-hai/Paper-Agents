import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE } from '../api/client'

const SUGGESTIONS = [
  '최근 산업용 Foundation Model 트렌드 정리해줘',
  'PHM에서 uncertainty-aware fault diagnosis 접근법은?',
  'Physics-Informed ML로 baseline 깨는 핵심 아이디어가 뭐야?',
  'Digital twin과 signal processing을 결합한 최근 논문 소개',
]

export default function Ask() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([]) // [{role, content, sources?}]
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState('')
  const endRef = useRef(null)
  const abortRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  async function ask(q) {
    if (!q.trim() || streaming) return
    setError('')
    const userMsg = { role: 'user', content: q }
    const assistantMsg = { role: 'assistant', content: '', sources: [] }
    setMessages(prev => [...prev, userMsg, assistantMsg])
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

        // Split SSE events by blank line
        const events = buffer.split('\n\n')
        buffer = events.pop() // remainder

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
          } catch {/* ignore */ }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') setError(e.message || '요청 실패')
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  function stop() {
    abortRef.current?.abort()
  }

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Hero */}
      <section className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-3xl mx-auto px-4 py-8">
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-2">
            <span>HotPaper.ai</span><span>›</span><span>Research Agent</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">
            🤖 Research Agent <span className="text-sm font-normal text-gray-500 ml-2">beta</span>
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
            DB에 수집된 논문(임베딩 7천여 편)에서 관련 자료를 의미 기반으로 검색하고,
            로컬 LLM(Qwen3 14B)이 한국어로 답변합니다. 답변에 인용된 논문의 arXiv ID를 클릭해
            상세 페이지에서 한국어 요약과 그림을 확인할 수 있습니다.
          </p>
        </div>
      </section>

      {/* Chat area */}
      <section className="max-w-3xl mx-auto px-4 py-6">
        {messages.length === 0 && (
          <div className="space-y-3 mb-6">
            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              예시 질문
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  disabled={streaming}
                  className="text-left text-sm px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-indigo-400 hover:bg-indigo-50/40 dark:hover:bg-indigo-900/10 transition-colors disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-4">
          {messages.map((m, i) => (
            <Bubble key={i} message={m} />
          ))}
          {streaming && (
            <div className="text-xs text-gray-500 dark:text-gray-400 animate-pulse">
              답변 생성 중…
            </div>
          )}
          <div ref={endRef} />
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}
      </section>

      {/* Composer */}
      <div className="sticky bottom-0 bg-gradient-to-t from-gray-50 dark:from-gray-950 pt-4 pb-6">
        <div className="max-w-3xl mx-auto px-4">
          <form
            onSubmit={(e) => { e.preventDefault(); ask(question) }}
            className="flex gap-2 items-end bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-2xl p-2 shadow-sm focus-within:border-indigo-400"
          >
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  ask(question)
                }
              }}
              placeholder="연구 주제를 한국어로 자유롭게 질문해보세요 (Enter로 전송, Shift+Enter 줄바꿈)"
              rows={1}
              maxLength={500}
              className="flex-1 resize-none bg-transparent text-sm text-gray-900 dark:text-white placeholder-gray-400 px-3 py-2 focus:outline-none"
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
          <div className="mt-2 flex justify-between text-[11px] text-gray-400 dark:text-gray-500 px-2">
            <span>분당 3회 / 일당 30회 제한</span>
            <span>{question.length}/500</span>
          </div>
        </div>
      </div>
    </main>
  )
}

function Bubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
        isUser
          ? 'bg-indigo-600 text-white'
          : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'
      }`}>
        {message.sources && message.sources.length > 0 && (
          <div className="mb-2 pb-2 border-b border-gray-200 dark:border-gray-700">
            <p className="text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
              검색된 논문 ({message.sources.length}편)
            </p>
            <div className="space-y-1">
              {message.sources.map((s) => (
                s.is_arxiv ? (
                  <Link
                    key={s.arxiv_id}
                    to={`/paper/${s.arxiv_id}`}
                    className="block text-xs hover:underline text-indigo-600 dark:text-indigo-300 truncate"
                  >
                    <span className="font-mono">[{s.arxiv_id}]</span> {s.title}
                    <span className="ml-2 text-[10px] text-gray-500">sim {Math.round((s.similarity || 0) * 100)}%</span>
                  </Link>
                ) : (
                  <div key={s.arxiv_id} className="text-xs text-gray-700 dark:text-gray-300 truncate">
                    <span className="font-mono">[{s.arxiv_id}]</span> {s.title}
                    <span className="ml-2 text-[10px] text-gray-500">sim {Math.round((s.similarity || 0) * 100)}%</span>
                  </div>
                )
              ))}
            </div>
          </div>
        )}
        <div className={`whitespace-pre-wrap text-sm leading-relaxed ${isUser ? '' : 'text-gray-800 dark:text-gray-200'}`}>
          {message.content || <span className="text-gray-400">…</span>}
        </div>
      </div>
    </div>
  )
}

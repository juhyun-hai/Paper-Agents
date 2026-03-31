import React, { useState } from 'react'

const CATEGORIES = [
  { value: 'general', label: '일반 의견' },
  { value: 'bug', label: '버그 신고' },
  { value: 'feature', label: '기능 요청' },
  { value: 'paper', label: '논문 관련' },
]

export default function Feedback() {
  const [form, setForm] = useState({ name: '', email: '', category: 'general', message: '' })
  const [status, setStatus] = useState(null) // 'loading' | 'success' | 'error'

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.message.trim()) return
    setStatus('loading')
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error()
      setStatus('success')
      setForm({ name: '', email: '', category: 'general', message: '' })
    } catch {
      setStatus('error')
    }
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-16">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">피드백</h1>
        <p className="text-gray-500 dark:text-gray-400">버그 신고, 기능 요청, 의견을 남겨주세요. 익명으로도 작성 가능합니다.</p>
      </div>

      {status === 'success' ? (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-8 text-center">
          <div className="text-4xl mb-3">✅</div>
          <h2 className="text-lg font-semibold text-green-800 dark:text-green-300 mb-1">피드백이 전송되었습니다</h2>
          <p className="text-sm text-green-600 dark:text-green-400 mb-4">소중한 의견 감사합니다!</p>
          <button
            onClick={() => setStatus(null)}
            className="text-sm text-primary hover:underline"
          >
            다시 작성하기
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 space-y-5 shadow-sm">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">이름 (선택)</label>
              <input
                type="text"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="홍길동"
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">이메일 (선택)</label>
              <input
                type="email"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                placeholder="example@email.com"
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">유형</label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map(c => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setForm(f => ({ ...f, category: c.value }))}
                  className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
                    form.category === c.value
                      ? 'bg-primary text-white border-primary'
                      : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary hover:text-primary'
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              내용 <span className="text-red-500">*</span>
            </label>
            <textarea
              value={form.message}
              onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
              placeholder="의견을 자유롭게 작성해주세요..."
              rows={6}
              required
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            />
          </div>

          {status === 'error' && (
            <p className="text-sm text-red-600 dark:text-red-400">전송 실패. 다시 시도해주세요.</p>
          )}

          <button
            type="submit"
            disabled={status === 'loading' || !form.message.trim()}
            className="w-full py-2.5 px-4 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white font-medium rounded-lg transition-colors text-sm"
          >
            {status === 'loading' ? '전송 중...' : '피드백 보내기'}
          </button>
        </form>
      )}
    </main>
  )
}

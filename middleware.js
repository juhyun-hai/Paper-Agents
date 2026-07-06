// Vercel Edge Middleware — 봇/크롤러에게 서버렌더 HTML 제공.
// vercel.json의 has(UA) 조건 rewrite가 실환경에서 매칭되지 않아
// 미들웨어에서 직접 판단한다. 사람 트래픽은 즉시 통과 (SPA 그대로).
//
// matcher: '/'와 '/paper/*'만 — 나머지 경로는 미들웨어 자체가 안 탐.

export const config = {
  matcher: ['/', '/paper/:path*'],
}

const BOT_RE = /bot|crawler|spider|slurp|facebookexternalhit|twitterbot|linkedinbot|telegrambot|whatsapp|discordbot|gptbot|claudebot|claude-web|perplexitybot|bytespider|applebot|bingpreview|yeti|daum/i

export default async function middleware(request) {
  const ua = request.headers.get('user-agent') || ''
  if (!BOT_RE.test(ua)) return // 사람 → 정적 SPA로 계속

  const url = new URL(request.url)
  let target
  if (url.pathname === '/') {
    const date = url.searchParams.get('date')
    target = date
      ? `https://api.hotpaper.ai/api/seo/daily/${encodeURIComponent(date)}`
      : 'https://api.hotpaper.ai/api/seo/home'
  } else {
    const id = url.pathname.replace(/^\/paper\//, '')
    target = `https://api.hotpaper.ai/api/seo/paper/${encodeURIComponent(id)}`
  }

  try {
    const res = await fetch(target, {
      headers: { 'user-agent': 'hotpaper-seo-proxy' },
    })
    if (!res.ok) return // SEO 렌더 실패 → SPA로 fallback
    const html = await res.text()
    return new Response(html, {
      status: 200,
      headers: {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'public, max-age=1800',
        'x-seo-rendered': '1',
      },
    })
  } catch {
    return // 네트워크 오류 → SPA fallback
  }
}

// Cloudflare Pages Function — '/' (홈)
// 봇에게는 서버렌더 목록 HTML (?date= 지원), 사람에게는 SPA.

const BOT_RE = /bot|crawler|spider|slurp|facebookexternalhit|twitterbot|linkedinbot|telegrambot|whatsapp|discordbot|gptbot|claudebot|claude-web|perplexitybot|bytespider|applebot|bingpreview|yeti|daum|kakaotalk/i

export async function onRequest({ request, env }) {
  const ua = request.headers.get('user-agent') || ''
  if (BOT_RE.test(ua)) {
    try {
      const url = new URL(request.url)
      const date = url.searchParams.get('date')
      const target = date
        ? `https://api.hotpaper.ai/api/seo/daily/${encodeURIComponent(date)}`
        : 'https://api.hotpaper.ai/api/seo/home'
      const res = await fetch(target, { headers: { 'user-agent': 'hotpaper-seo-proxy' } })
      if (res.ok) {
        return new Response(await res.text(), {
          status: 200,
          headers: {
            'content-type': 'text/html; charset=utf-8',
            'cache-control': 'public, max-age=1800',
            'x-seo-rendered': '1',
          },
        })
      }
    } catch (_) { /* fallback */ }
  }
  return env.ASSETS.fetch(request)
}

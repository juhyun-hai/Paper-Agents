// Cloudflare Pages Function — /paper/:id
// 봇/크롤러에게는 서버렌더 SEO HTML, 사람에게는 SPA(index.html).
// (호스팅이 Cloudflare Pages라 vercel.json/middleware.js는 무시됨 — 이게 실제 경로)

const BOT_RE = /bot|crawler|spider|slurp|facebookexternalhit|twitterbot|linkedinbot|telegrambot|whatsapp|discordbot|gptbot|claudebot|claude-web|perplexitybot|bytespider|applebot|bingpreview|yeti|daum|kakaotalk/i

export async function onRequest({ request, params, env }) {
  const ua = request.headers.get('user-agent') || ''
  if (BOT_RE.test(ua)) {
    try {
      const res = await fetch(
        `https://api.hotpaper.ai/api/seo/paper/${encodeURIComponent(params.id)}`,
        { headers: { 'user-agent': 'hotpaper-seo-proxy' } },
      )
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
    } catch (_) { /* SEO 실패 → SPA fallback */ }
  }
  // 사람 or fallback: SPA 셸 반환
  return env.ASSETS.fetch(new Request(new URL('/', request.url), request))
}

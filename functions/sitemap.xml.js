// /sitemap.xml → 백엔드 동적 sitemap proxy
export async function onRequest() {
  const res = await fetch('https://api.hotpaper.ai/api/seo/sitemap.xml')
  return new Response(await res.text(), {
    status: res.status,
    headers: {
      'content-type': 'application/xml; charset=utf-8',
      'cache-control': 'public, max-age=3600',
    },
  })
}

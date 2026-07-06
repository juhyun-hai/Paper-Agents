// /rss.xml → RSS feed proxy (루트에서 구독 가능하게)
export async function onRequest() {
  const res = await fetch('https://api.hotpaper.ai/api/feed/rss')
  return new Response(await res.text(), {
    status: res.status,
    headers: {
      'content-type': 'application/rss+xml; charset=utf-8',
      'cache-control': 'public, max-age=600',
    },
  })
}

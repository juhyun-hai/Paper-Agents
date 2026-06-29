// localStorage 기반 북마크 — 사용자 계정 없이도 작동.
// 서버에 저장 X (privacy + 단순). 브라우저 한정.

const KEY = 'hotpaper_bookmarks_v1'

export function getBookmarks() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function isBookmarked(arxivId) {
  return getBookmarks().includes(arxivId)
}

export function toggleBookmark(arxivId) {
  const list = getBookmarks()
  const i = list.indexOf(arxivId)
  if (i >= 0) {
    list.splice(i, 1)
  } else {
    list.unshift(arxivId)
  }
  localStorage.setItem(KEY, JSON.stringify(list))
  // 다른 컴포넌트에서 listen 가능하도록 이벤트 발사
  window.dispatchEvent(new CustomEvent('bookmarks-changed', { detail: list }))
  return list
}

export function clearBookmarks() {
  localStorage.removeItem(KEY)
  window.dispatchEvent(new CustomEvent('bookmarks-changed', { detail: [] }))
}

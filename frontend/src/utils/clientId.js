// 사용자 식별용 client_id — localStorage에 1번 생성, 영구 보존.
// 계정 시스템 없이도 saved search 같은 personalization 가능.
const KEY = 'hotpaper_client_id_v1'

export function getClientId() {
  let id = localStorage.getItem(KEY)
  if (!id) {
    id = 'c' + Math.random().toString(36).slice(2, 12) + Date.now().toString(36)
    localStorage.setItem(KEY, id)
  }
  return id
}

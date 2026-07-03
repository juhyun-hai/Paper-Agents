#!/bin/bash
# 서비스 watchdog — 15분마다 cron. 죽은 서비스 자동 재시작 + ntfy 알림.
#
# 감시 대상 (6/30 사고: Ollama 3일 무음 다운 재발 방지):
#  - Ollama (localhost:11434)
#  - Backend API (localhost:8000/health)
#  - Postgres (docker)
#  - Cloudflared tunnel (systemd)

set -u
ENV_FILE=/home/juhyun/agent/paper-agent-github/.env
NTFY_TOPIC=$(grep '^NTFY_TOPIC=' "$ENV_FILE" 2>/dev/null | cut -d= -f2)

notify() {
  local title="$1" msg="$2"
  echo "[watchdog] $title: $msg"
  if [ -n "$NTFY_TOPIC" ]; then
    curl -s -m 10 -H "Title: $title" -H "Priority: high" \
      -d "$msg" "https://ntfy.sh/$NTFY_TOPIC" > /dev/null || true
  fi
}

# 1. Ollama
if ! curl -s -m 5 http://localhost:11434/api/tags > /dev/null; then
  systemctl --user start ollama
  sleep 5
  if curl -s -m 5 http://localhost:11434/api/tags > /dev/null; then
    notify "HotPaper watchdog" "Ollama was down — auto-restarted OK"
  else
    notify "HotPaper watchdog" "Ollama DOWN and restart FAILED — manual check needed"
  fi
fi

# 2. Backend API
if ! curl -s -m 5 http://localhost:8000/health > /dev/null; then
  systemctl --user restart hotpaper-backend.service
  sleep 8
  if curl -s -m 5 http://localhost:8000/health > /dev/null; then
    notify "HotPaper watchdog" "Backend was down — auto-restarted OK"
  else
    notify "HotPaper watchdog" "Backend DOWN and restart FAILED"
  fi
fi

# 3. Postgres (docker)
if ! docker exec paper-agent-github-postgres-1 pg_isready -U research_agent -q 2>/dev/null; then
  docker start paper-agent-github-postgres-1 2>/dev/null
  sleep 10
  if docker exec paper-agent-github-postgres-1 pg_isready -U research_agent -q 2>/dev/null; then
    notify "HotPaper watchdog" "Postgres was down — auto-restarted OK"
  else
    notify "HotPaper watchdog" "Postgres DOWN and restart FAILED — 사이트 전체 중단 상태"
  fi
fi

# 4. Cloudflared tunnel
if ! systemctl --user is-active --quiet hotpaper-tunnel.service; then
  systemctl --user restart hotpaper-tunnel.service
  notify "HotPaper watchdog" "Tunnel was down — restarted"
fi

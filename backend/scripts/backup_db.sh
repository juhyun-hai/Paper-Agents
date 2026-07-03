#!/bin/bash
# HotPaper DB 백업 — 매일 05시 cron.
#
# 전략 (DB 8GB 중 7.6GB가 paper_summaries.figures base64):
#  - daily: figures 컬럼 제외 백업 (~수백MB) — 스키마 전체 + 데이터
#  - sunday: full dump 1회 (figures 포함)
#  - 보관: daily 14개, full 4개
#  - 실패 시 ntfy 알림
#
# 오프사이트 권장: rclone 설정 후 아래 RCLONE_REMOTE 채우면 자동 업로드.

set -u
BACKUP_DIR=/home/juhyun/backups/hotpaper
CONTAINER=paper-agent-github-postgres-1
DB=research_intelligence
DBUSER=research_agent
STAMP=$(date +%Y%m%d)
RCLONE_REMOTE=""   # 예: "gdrive:hotpaper-backups" — 설정 시 자동 업로드

# .env에서 NTFY_TOPIC 로드
ENV_FILE=/home/juhyun/agent/paper-agent-github/.env
NTFY_TOPIC=$(grep '^NTFY_TOPIC=' "$ENV_FILE" 2>/dev/null | cut -d= -f2)

notify_fail() {
  local msg="$1"
  echo "❌ $msg"
  if [ -n "$NTFY_TOPIC" ]; then
    curl -s -m 10 -H "Title: HotPaper backup FAIL" -H "Priority: high" \
      -d "$msg" "https://ntfy.sh/$NTFY_TOPIC" > /dev/null || true
  fi
}

mkdir -p "$BACKUP_DIR"

# ── daily: figures 제외 ──────────────────────────────────────────
# 1) 전체 스키마 + paper_summaries 데이터 제외
DAILY="$BACKUP_DIR/daily-$STAMP.dump"
docker exec "$CONTAINER" pg_dump -U "$DBUSER" -d "$DB" -Fc \
  --exclude-table-data=paper_summaries > "$DAILY" 2>/tmp/backup_err.log \
  || { notify_fail "pg_dump base failed: $(tail -1 /tmp/backup_err.log)"; exit 1; }

# 2) paper_summaries에서 figures 컬럼만 제외한 CSV
SUMM="$BACKUP_DIR/daily-$STAMP-summaries.csv.gz"
docker exec "$CONTAINER" psql -U "$DBUSER" -d "$DB" -c "\
COPY (SELECT id, paper_id, arxiv_id, summary_text, summary_type, \
       generation_model, word_count, figure_count, has_full_text, \
       generated_at, created_at, updated_at \
FROM paper_summaries) TO STDOUT WITH CSV HEADER" 2>/tmp/backup_err.log \
  | gzip > "$SUMM" \
  || { notify_fail "summaries CSV failed"; exit 1; }

# ── sunday: full dump ────────────────────────────────────────────
if [ "$(date +%u)" = "7" ]; then
  FULL="$BACKUP_DIR/full-$STAMP.dump"
  docker exec "$CONTAINER" pg_dump -U "$DBUSER" -d "$DB" -Fc > "$FULL" \
    || notify_fail "weekly full dump failed"
fi

# ── rotation ─────────────────────────────────────────────────────
ls -t "$BACKUP_DIR"/daily-*.dump 2>/dev/null | tail -n +15 | xargs -r rm
ls -t "$BACKUP_DIR"/daily-*-summaries.csv.gz 2>/dev/null | tail -n +15 | xargs -r rm
ls -t "$BACKUP_DIR"/full-*.dump 2>/dev/null | tail -n +5 | xargs -r rm

# ── (선택) 오프사이트 ─────────────────────────────────────────────
if [ -n "$RCLONE_REMOTE" ] && command -v rclone > /dev/null; then
  rclone copy "$DAILY" "$RCLONE_REMOTE/" || notify_fail "rclone upload failed"
  rclone copy "$SUMM" "$RCLONE_REMOTE/" || true
fi

SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "✅ backup done: $(basename $DAILY) + summaries.csv.gz (dir total: $SIZE)"

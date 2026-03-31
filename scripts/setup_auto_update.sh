#!/bin/bash
# Auto-update setup script

echo "🔧 자동 업데이트 스케줄링 설정..."

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Create log directory
mkdir -p "$PROJECT_DIR/logs"

# Add cron job (daily at 9 AM)
CRON_JOB="0 9 * * * cd '$PROJECT_DIR' && python3 scripts/daily_update_system.py >> logs/daily_update.log 2>&1"

# Check if cron job already exists
if ! crontab -l 2>/dev/null | grep -F "daily_update_system.py" > /dev/null; then
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ 자동 업데이트 스케줄 설정 완료 (매일 오전 9시)"
    echo "📝 로그 파일: $PROJECT_DIR/logs/daily_update.log"
else
    echo "⚠️ 자동 업데이트 스케줄이 이미 설정되어 있습니다."
fi

# Show current cron jobs
echo ""
echo "📋 현재 설정된 스케줄:"
crontab -l | grep -F "paper-agent" || echo "  (paper-agent 관련 스케줄 없음)"

echo ""
echo "🔄 수동 실행 명령어:"
echo "  cd '$PROJECT_DIR' && python3 scripts/daily_update_system.py"
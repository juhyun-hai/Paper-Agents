#!/bin/bash

# Paper Agent - 매일 오전 5시 자동 수집 크론잡 설정

echo "📅 Setting up daily cron job for Paper Agent..."

# 로그 디렉토리 생성
mkdir -p /home/juhyun/agent/1.paper-agent/logs

# 현재 크론탭 백업
crontab -l > /tmp/current_cron_backup 2>/dev/null || touch /tmp/current_cron_backup

# 기존 paper-agent 크론잡 제거 (있다면)
grep -v "paper-agent" /tmp/current_cron_backup > /tmp/new_cron

# 새로운 크론잡 추가 (매일 오전 5시)
echo "0 5 * * * cd /home/juhyun/agent/1.paper-agent && source .venv/bin/activate && python -c \"from src.collector.daily_collect import DailyCollector; DailyCollector().run()\" >> logs/daily_collection.log 2>&1" >> /tmp/new_cron

# 크론탭 적용
crontab /tmp/new_cron

echo "✅ Cron job set up successfully!"
echo "📋 Current cron jobs:"
crontab -l | grep -E "(paper-agent|minute.*hour.*day)"
echo ""
echo "📊 Collection will run daily at 5:00 AM"
echo "📄 Logs will be saved to: logs/daily_collection.log"
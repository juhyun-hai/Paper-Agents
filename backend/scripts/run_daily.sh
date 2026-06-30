#!/bin/bash
# Daily pipeline: collect papers + score featured + backfill figures for any
# summaries still missing them.
cd /home/juhyun/agent/paper-agent-github/backend
# venv python에 모든 필수 모듈 있음 (asyncpg, httpx, pgvector, …).
# /usr/bin/python3 쓰면 모듈 부족으로 cron 실패하니 venv python 강제.
PY=/home/juhyun/agent/paper-agent-github/venv/bin/python3
export HF_HOME=/home/juhyun/agent/paper-agent-github/backend/hf_cache

# Optional: Semantic Scholar API key (raises rate limit; works without it too)
# export S2_API_KEY=...

# 1. Collect papers + featured scoring (now v4 — venue + citation bonuses).
#    Internally also runs:
#      • Top-venue S2 rotation (weekday-scheduled, ~2 venues/day)
#      • Citation refresh for papers from the last 30 days
#      • OpenReview sweep only on Mondays (weekday == 0)
$PY -u scripts/daily_cron.py

# 2. Backfill any missing figures (new papers + leftovers from previous days)
#    Caps at 50 per run so we never block the cron for too long.
$PY -u scripts/backfill_figures.py --all --limit 50 || true

# 3. Generate embeddings for any papers missing them so new featured 25 enter
#    the /api/hai/related recommendation pool the same morning.
$PY -u scripts/generate_embeddings.py || true

# ─────────────────────────────────────────────────────────────────
# Recommended cron entries (add these to crontab -e):
#
#   # Daily collector at 03:00 KST
#   0 3 * * *  /home/juhyun/agent/paper-agent-github/backend/scripts/run_daily.sh \
#     >> /home/juhyun/agent/paper-agent-github/backend/logs/daily_cron.log 2>&1
#
#   # Weekly OpenReview deep sweep — Monday 02:00 KST.
#   # (daily_cron already triggers a 14-day sweep on Mondays, so this is
#   #  optional. Use it for a longer since-days window before paper-decision
#   #  release dates: ICLR ~ Jan 22, NeurIPS ~ Sep 25, etc.)
#   0 2 * * 1  cd /home/juhyun/agent/paper-agent-github/backend && \
#     /usr/bin/python3 -u scripts/fetch_top_venues.py --mode=openreview \
#       --since-days=30 \
#     >> /home/juhyun/agent/paper-agent-github/backend/logs/openreview_weekly.log 2>&1
#
#   # On-demand: fetch a specific venue + year after a decision drops, e.g.
#   #   python3 scripts/fetch_top_venues.py --mode=openreview \
#   #     --venue=ICLR.cc/2026/Conference --since-days=7
# ─────────────────────────────────────────────────────────────────

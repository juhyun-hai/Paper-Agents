#!/bin/bash
# Daily pipeline: collect papers + score featured + backfill figures for any
# summaries still missing them.
cd /home/juhyun/agent/paper-agent-github/backend
export PYTHONPATH=/home/juhyun/.local/lib/python3.12/site-packages
export HF_HOME=/home/juhyun/agent/paper-agent-github/backend/hf_cache

# 1. Collect papers + featured scoring
/usr/bin/python3 -u scripts/daily_cron.py

# 2. Backfill any missing figures (new papers + leftovers from previous days)
#    Caps at 50 per run so we never block the cron for too long.
/usr/bin/python3 -u scripts/backfill_figures.py --all --limit 50 || true

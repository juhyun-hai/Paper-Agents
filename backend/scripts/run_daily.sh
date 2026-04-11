#!/bin/bash
cd /home/juhyun/agent/paper-agent-github/backend
export PYTHONPATH=/home/juhyun/.local/lib/python3.12/site-packages
export HF_HOME=/home/juhyun/hf_cache
/usr/bin/python3 scripts/daily_cron.py

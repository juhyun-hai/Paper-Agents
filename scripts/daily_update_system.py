#!/usr/bin/env python3
"""
Daily Update System - 매일 자동으로 hot topics와 trending papers 업데이트
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import subprocess

def run_command(command, description):
    """Run a command and return success status"""
    try:
        print(f"🔄 {description}...")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ {description} 성공")
            return True
        else:
            print(f"  ❌ {description} 실패: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ {description} 오류: {e}")
        return False

def daily_update():
    """Run daily update process"""
    print(f"📅 일일 업데이트 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    success_count = 0

    # 1. Hot Topics 수집
    if run_command("python3 scripts/run_hot_topics.py", "Hot Topics 수집"):
        success_count += 1

    # 2. 최신 논문 수집 (arXiv daily)
    if run_command("python3 -m src.collector.daily_collect", "최신 논문 수집"):
        success_count += 1

    # 3. Embeddings 생성 (누락된 것들)
    if run_command("python3 scripts/generate_missing_embeddings.py", "Embeddings 생성"):
        success_count += 1

    print(f"\n🎉 일일 업데이트 완료!")
    print(f"📊 성공한 작업: {success_count}/3")

    # 현재 상태 확인
    print(f"\n📈 현재 시스템 상태:")
    run_command(
        "curl -s http://localhost:8000/api/health | python3 -c \"import json,sys; data=json.load(sys.stdin); print(f'논문: {data[\\\"database\\\"][\\\"total_papers\\\"]}개, 상태: {data[\\\"status\\\"]}')\"",
        "시스템 상태 확인"
    )
    run_command(
        "curl -s http://localhost:8000/api/hot-topics | python3 -c \"import json,sys; data=json.load(sys.stdin); print(f'Hot Topics: {len(data[\\\"topics\\\"])}개')\"",
        "Hot Topics 상태 확인"
    )

if __name__ == "__main__":
    daily_update()
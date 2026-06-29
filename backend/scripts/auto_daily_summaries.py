#!/usr/bin/env python3
"""매일 새벽 04시 KST cron: 최근 featured 25편 + 누락분 한국어 요약 자동 생성.

설계 원칙:
- **로컬 Ollama** (qwen3:32b) 사용 → 외부 API 의존 0, 비용 0
- **per-paper transaction**: 1편 실패해도 다음 편 계속
- **7일 lookback**: 오늘만 아니라 최근 누락분도 자동 백필
- **heartbeat ping**: HEARTBEAT_URL 환경변수 있으면 끝나고 ping
- **idempotent**: 이미 요약 있는 것은 skip (DELETE+INSERT 멱등)
- SSH 끊김 무관 — cron daemon이 띄움
"""
from __future__ import annotations
import asyncio
import json
import os
import re
import sys
import time
import traceback
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))  # scripts/ 자체 (ar5iv_extract import)
os.environ.setdefault('HF_HOME', '/home/juhyun/agent/paper-agent-github/backend/hf_cache')

# .env 로드 (HEARTBEAT_URL, 기타 설정)
ENV_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(ENV_PATH):
    for line in open(ENV_PATH):
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import asyncpg
import httpx
import requests

from app.services.figure_extractor import extract_figures
import ar5iv_extract  # 본문 추출 (ar5iv / arxiv.org HTML)

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'

# 로컬 Ollama 설정 (외부 API 의존 0)
OLLAMA_URL = 'http://localhost:11434'
MODEL = os.environ.get('SUMMARY_MODEL', 'qwen3:32b')

# Heartbeat (healthchecks.io 또는 비슷한 dead-man-switch).
# 없으면 ping 안 하고 silently continue.
HEARTBEAT_URL = os.environ.get('HEARTBEAT_URL', '').strip()

# 최근 며칠 lookback (오늘만이 아니라 누락분도 같이 처리)
LOOKBACK_DAYS = int(os.environ.get('SUMMARY_LOOKBACK_DAYS', '7'))

SYSTEM_PROMPT = """당신은 학술 논문을 한국어로 깊이 있게 정리하는 전문가입니다.
주어진 자료(영문 초록 또는 ar5iv 본문 발췌)를 근거로 7섹션 한국어 요약을 작성합니다.

[엄격한 규칙]
- 입력에 명시된 사실·수치·모듈명만 사용. 추측·일반화 금지.
- 입력에 없는 정보는 '명시되지 않음'으로 표기.
- 수치는 원문에 등장한 그대로 인용 (예: 정확도 73.2%, 1.6× 가속).
- 각 섹션마다 입력의 **구체적 모듈명·데이터셋명·수치**를 1개 이상 명시.
- 추상적 일반론('성능이 향상됨', '신뢰성을 높임')만 쓰지 말 것.
- 본문(## Method, ## Experiments 등)이 함께 주어진 경우 본문에 명시된
  구체적 모듈명·알고리즘 단계·수치를 적극 인용해 깊이 있게 작성할 것.

[7섹션 구조 — 반드시 ## 헤더 한국어 그대로]

## 한 줄 요약
한 문장 (50자 내외).

## 핵심 기여도
3~4개 불릿. 각 불릿은 abstract의 구체적 방법/수치 포함.

## 핵심 아이디어
2~3 문단. 왜 이 접근이 새로운지 + 핵심 통찰. 모듈명/공식이 있으면 명시.

## 기술적 접근법
구체적 모델·알고리즘·데이터·하이퍼파라미터를 정리. 불릿 또는 짧은 단락.
abstract에 method 세부가 있으면 그대로 인용.

## 주요 결과
초록에 명시된 metric·dataset·비교 결과만. 베이스라인 대비 개선폭(%) 포함.
"X 데이터셋에서 Y% (베이스라인 대비 +Z%)" 같은 형태.

## 의의 및 한계
2~3 문단. 학술적·실용적 가치 + abstract에 언급된 한계점.

## 실용적 활용
어떤 산업·연구 상황에 적용 가능한지 2~3 문장.

[길이]
- 최소 280 단어, 목표 300~340 단어.
- 짧으면 각 섹션에 구체 수치/방법명을 더 인용해 채울 것.

마크다운 형식."""


async def fetch_targets(conn):
    """오늘 + LOOKBACK_DAYS 안의 featured + semantic_bridge 중 요약 누락분 모두.

    - is_featured = TRUE 는 항상 처리 (Top 25)
    - sources에 'semantic_bridge' 포함도 처리 (conf seed 의미 검색 결과)
    - featured 먼저, 그 다음 semantic bridge
    """
    today = date.today()
    cutoff = today - timedelta(days=LOOKBACK_DAYS)
    rows = await conn.fetch("""
        SELECT DISTINCT p.id, p.arxiv_id, p.title,
               COALESCE(p.abstract, '') AS abstract, p.pdf_url,
               tp.date AS feat_date,
               (tp.is_featured = TRUE) AS is_featured
        FROM papers p
        JOIN trending_papers tp ON tp.arxiv_id = p.arxiv_id
        WHERE tp.date >= $1
          AND (tp.is_featured = TRUE OR tp.sources::text LIKE '%semantic_bridge%')
          AND NOT EXISTS (SELECT 1 FROM paper_summaries s WHERE s.arxiv_id = p.arxiv_id)
          AND p.arxiv_id ~ '^[0-9]{4}\\.[0-9]{4,5}$'
          AND p.abstract IS NOT NULL AND length(p.abstract) > 50
        ORDER BY (tp.is_featured = TRUE) DESC, tp.date DESC, p.id ASC
    """, cutoff)
    return [dict(r) for r in rows]


def _try_extract_body(arxiv_id: str) -> tuple[str | None, str | None]:
    """ar5iv 본문을 LLM-ready 포맷으로 반환. 실패 시 (None, None).

    Returns: (formatted_text, source)  e.g. ('## Method\\n...', 'ar5iv')
    """
    try:
        paper = ar5iv_extract.extract_paper_text(arxiv_id)
        if not paper or not paper.get('sections'):
            return None, None
        body = ar5iv_extract.format_for_llm(paper, max_total_chars=14000)
        if not body or len(body) < 500:
            return None, None
        return body, paper.get('source', 'ar5iv')
    except Exception as e:
        print(f"    ar5iv err: {e}")
        return None, None


def generate_summary(arxiv_id: str, title: str, abstract: str) -> tuple[str | None, bool, str | None]:
    """Ollama (qwen3:32b) 로컬 호출.

    1) ar5iv 본문 추출 시도 → 성공 시 본문 포함 prompt
    2) 실패 시 abstract-only fallback (기존 동작)

    Returns: (summary_text, used_ar5iv, body_text)
      body_text — verifier가 수치 매칭에 쓸 원본 본문 (없으면 None)
    """
    body, src = _try_extract_body(arxiv_id)
    if body:
        user_msg = (
            f"제목: {title}\n\n"
            f"영문 초록:\n{abstract[:2000]}\n\n"
            f"본문 발췌 (출처: {src}):\n{body}\n\n"
            "위 자료를 근거로 7섹션 한국어 요약을 작성하세요. "
            "본문에 명시된 구체적 모듈명·알고리즘 단계·수치를 적극 인용하세요."
        )
        num_ctx = 16384
        used_ar5iv = True
    else:
        user_msg = (
            f"제목: {title}\n\n영문 초록:\n{abstract[:3000]}\n\n"
            "위 정보만 근거로 7섹션 한국어 요약을 작성하세요."
        )
        num_ctx = 8192
        used_ar5iv = False

    try:
        with httpx.Client(timeout=600) as cli:
            r = cli.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL,
                    "stream": False,
                    "think": False,         # Qwen3 reasoning 끄기 (RAG와 동일)
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "options": {
                        "num_predict": 1500,
                        "num_ctx": num_ctx,
                        "temperature": 0.3,
                        "top_p": 0.9,
                    },
                },
            )
            r.raise_for_status()
            text = r.json().get('message', {}).get('content', '').strip() or None
            return text, used_ar5iv, body
    except Exception as e:
        print(f"  ⚠️ Ollama err: {e}")
        return None, used_ar5iv, body


# ---------------------------------------------------------------------------
# P6: Verifier loop — minimal hallucination guard.
# 요약에 등장한 수치(73.2%, 1.6×, 100K …)가 abstract 또는 ar5iv 본문에
# 실제로 등장하는지 grep. 매칭 안 되는 비율이 UNVERIFIED_THRESHOLD 이상이면
# +unverified 태그만 붙이고 통과 (사이트에서 사용자가 직접 판단 가능).
# 절대 paper를 reject 하지 않음 — 가시화가 목적.
# ---------------------------------------------------------------------------
UNVERIFIED_THRESHOLD = float(os.environ.get('VERIFIER_THRESHOLD', '0.30'))

# 의미있는 수치만: 소수점 / % / 3자리+ / ×배수
_NUM_PATTERN = re.compile(r'\d+(?:\.\d+)?%?')


def _candidate_numbers(text: str) -> list[str]:
    """검증 가치가 있는 수치만 추출. 한 자리 정수(1, 2, 3) 같은 노이즈 제외."""
    out: list[str] = []
    for m in _NUM_PATTERN.finditer(text):
        s = m.group(0)
        core = s.rstrip('%')
        # 소수점 포함 / % 포함 / 3자리 이상 정수만 검증 대상
        if '.' in core or s.endswith('%') or len(core) >= 3:
            out.append(s)
    return out


def verify_summary_numbers(
    summary_text: str, abstract: str, body: str | None,
) -> tuple[bool, float, list[str], int]:
    """요약 내 수치가 abstract/body에 등장하는지 grep.

    Returns:
        verified: True면 통과 (unmatched < threshold)
        unmatched_ratio: 매칭 실패 비율 (0.0~1.0)
        unmatched_examples: 매칭 실패 수치 샘플 (최대 5개)
        checked_count: 검증한 수치 총 개수
    """
    nums = _candidate_numbers(summary_text)
    if not nums:
        # 검증할 수치 없음 → 안전 통과 (false positive 방지)
        return True, 0.0, [], 0

    source = (abstract or '') + '\n' + (body or '')
    unmatched: list[str] = []
    for n in nums:
        core = n.rstrip('%')
        # exact substring 또는 % 떼고 등장하면 매칭 인정
        if n in source or core in source:
            continue
        unmatched.append(n)

    ratio = len(unmatched) / len(nums)
    verified = ratio < UNVERIFIED_THRESHOLD
    return verified, ratio, unmatched[:5], len(nums)


async def save_summary(conn, arxiv_id: str, summary_text: str, figures: list,
                        used_ar5iv: bool = False, verified: bool = True):
    """Per-paper transaction. 멱등 (DELETE+INSERT).

    used_ar5iv: True면 generation_model 태그에 '+ar5iv' 표시 (소스 추적용).
    verified:   False면 '+unverified' 태그 (수치 grep 매칭률 < threshold).
                schema에 별도 컬럼 없으므로 generation_model 문자열로 가시화.
    """
    async with conn.transaction():
        await conn.execute("DELETE FROM paper_summaries WHERE arxiv_id = $1", arxiv_id)
        word_count = len(summary_text.split())
        tags = ''
        if used_ar5iv:
            tags += '+ar5iv'
        if not verified:
            tags += '+unverified'
        model_tag = f"Ollama {MODEL}{tags} (auto-cron)"
        await conn.execute("""
            INSERT INTO paper_summaries (
                arxiv_id, summary_text, summary_type, generation_model,
                word_count, figures, figure_count, generated_at, created_at, updated_at
            )
            VALUES ($1, $2, 'comprehensive', $3, $4, $5::jsonb, $6, NOW(), NOW(), NOW())
        """, arxiv_id, summary_text, model_tag, word_count,
            json.dumps(figures), len(figures))


def heartbeat(state: str = "", payload: dict | None = None):
    """healthchecks.io 같은 dead-man-switch. URL 없으면 silently skip.

    state: '' (success), '/fail', '/start'
    """
    if not HEARTBEAT_URL:
        return
    url = HEARTBEAT_URL.rstrip('/') + state
    try:
        body = json.dumps(payload, ensure_ascii=False) if payload else None
        requests.post(url, data=body, timeout=10)
    except Exception:
        pass  # heartbeat 실패가 본 작업을 막으면 안 됨


async def main():
    started = time.time()
    heartbeat('/start')

    # Ollama 사전 체크 — 모델 미로딩이면 즉시 종료
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        tags = r.json().get('models', [])
        if not any(MODEL in (m.get('name') or '') for m in tags):
            msg = f"❌ Ollama 모델 '{MODEL}' 미로딩. `ollama pull {MODEL}` 필요."
            print(msg)
            heartbeat('/fail', {'error': msg})
            sys.exit(1)
    except Exception as e:
        msg = f"❌ Ollama 서버 unreachable: {e}"
        print(msg)
        heartbeat('/fail', {'error': msg})
        sys.exit(1)

    conn = await asyncpg.connect(DB_URL)
    summary_for = None  # 실패한 마지막 paper id (디버그용)
    try:
        targets = await fetch_targets(conn)
        print(f"🎯 {len(targets)} featured papers without summary (lookback {LOOKBACK_DAYS}d)")
        if not targets:
            elapsed = time.time() - started
            heartbeat('', {
                'processed': 0, 'failed': 0, 'lookback_days': LOOKBACK_DAYS,
                'message': 'no work to do', 'elapsed_sec': round(elapsed, 1),
            })
            return

        ok, fail, unverified_count, fail_ids = 0, 0, 0, []
        for i, t in enumerate(targets, 1):
            aid = t['arxiv_id']
            summary_for = aid
            t0 = time.time()
            print(f"  [{i}/{len(targets)}] {aid} ({t['feat_date']}) — {t['title'][:60]}")

            # 1) Generate (network/llm error는 fail 처리, 다음 paper로)
            #    ar5iv 본문 활용 시도 → 실패 시 abstract-only fallback
            summary, used_ar5iv, body = generate_summary(aid, t['title'], t['abstract'])
            if not summary or len(summary) < 200:
                fail += 1
                fail_ids.append(aid)
                continue

            # 1.5) Verifier (P6): 수치 grep — abstract/body에 없으면 +unverified 태그
            verified, unmatched_ratio, unmatched_ex, checked = verify_summary_numbers(
                summary, t['abstract'], body,
            )
            if not verified:
                unverified_count += 1
                print(
                    f"    ⚠️ verify fail: {unmatched_ratio:.0%} unmatched "
                    f"({len(unmatched_ex)}/{checked} shown) e.g. {unmatched_ex}"
                )

            # 2) Figures (실패해도 빈 list로 진행)
            try:
                figs = extract_figures(aid, max_figures=5)
            except Exception as e:
                print(f"    figure err: {e}")
                figs = []

            # 3) DB 저장 (per-paper transaction)
            try:
                await save_summary(
                    conn, aid, summary, figs,
                    used_ar5iv=used_ar5iv, verified=verified,
                )
                ok += 1
                src_tag = '+ar5iv' if used_ar5iv else 'abstract-only'
                ver_tag = '' if verified else ' +unverified'
                print(
                    f"    ✅ saved [{src_tag}{ver_tag}] "
                    f"({len(summary)} chars, {len(figs)} figs, {time.time()-t0:.1f}s)"
                )
            except Exception as e:
                fail += 1
                fail_ids.append(aid)
                print(f"    ❌ db err: {e}")

        elapsed = time.time() - started
        print(
            f"\n✅ Done — success {ok}, fail {fail}, "
            f"unverified {unverified_count}, elapsed {elapsed:.0f}s"
        )
        # P0 핵심 fix: 0편 처리는 fail로 간주 → healthchecks가 자동 alarm 발송.
        # 그동안 무음 4일 실패는 cron이 'success ping with processed=0' 보내서
        # dashboard만 보면 정상으로 보였기 때문.
        if ok == 0:
            heartbeat('/fail', {
                'reason': 'zero_processed',
                'targets': len(targets), 'failed': fail, 'fail_ids': fail_ids[:10],
                'lookback_days': LOOKBACK_DAYS, 'model': MODEL,
            })
        else:
            heartbeat('', {
                'processed': ok, 'failed': fail, 'fail_ids': fail_ids[:10],
                'unverified': unverified_count,
                'lookback_days': LOOKBACK_DAYS, 'elapsed_sec': round(elapsed, 1),
                'model': MODEL,
            })
    except Exception as e:
        # 전체 process가 죽는 케이스 — heartbeat에 fail ping
        tb = traceback.format_exc()
        print(f"❌ fatal: {e}\n{tb}")
        heartbeat('/fail', {
            'error': str(e), 'last_paper': summary_for,
            'elapsed_sec': round(time.time() - started, 1),
        })
        sys.exit(1)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

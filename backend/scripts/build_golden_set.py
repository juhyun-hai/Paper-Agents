#!/usr/bin/env python3
"""Golden set 50편 자동 선정 + abstract-only baseline summary dump.

목적
----
ar5iv 본문 활용으로 deep summary quality가 정말 향상되는지 객관적으로 평가하려면
"같은 50편을 두 버전(abstract-only / ar5iv)으로 비교" 할 수 있는 고정 셋이 필요.

이 스크립트는:
1) DB에서 다음 기준으로 50편을 자동 선정한다.
   - 25편: 최근 30일 featured 중 figure_count >= 3 (실제 사용자 노출/영향력)
   - 15편: HAI 관련 (is_hai=TRUE) — hai_topic 분포를 다양하게
   - 10편: oral/best/top-tier conference (venue_acceptances) — 없으면
            citation_count 상위 paper로 fallback
   중복 arxiv_id는 한 번만, 우선순위는 25 → 15 → 10 순.

2) 각 paper의 **현재** paper_summaries.summary_text를 baseline_summary로 dump.
   ar5iv 통합 후 다시 요약을 돌려 동일 50편에 대해 diff를 비교한다.

3) backend/golden_set/<arxiv_id>.json 으로 저장.
   끝에 backend/golden_set/_index.json (분포·ar5iv fetch 가능 여부 등 메타).

원칙
----
- side-effect 0 (read-only DB + 파일 쓰기만). cron/auto pipeline은 건드리지 않음.
- per-paper try/except — 한 편 실패해도 전체 진행.
- ar5iv 가용성은 HEAD만 빠르게 찍어 메타에 기록 (실제 본문 fetch는 평가 단계에서).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncpg
import requests

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'golden_set')

FEATURED_QUOTA = 25
HAI_QUOTA = 15
CONF_QUOTA = 10
TOTAL_QUOTA = FEATURED_QUOTA + HAI_QUOTA + CONF_QUOTA  # 50

LOOKBACK_DAYS_FEATURED = 30
HEADERS = {'User-Agent': 'HotPaper-GoldenSet/1.0 (https://hotpaper.ai)'}


# ──────────────────────────────────────────
# Selection queries
# ──────────────────────────────────────────
async def pick_featured(conn, limit: int, exclude: set[str]) -> list[dict]:
    """최근 30일 featured 중 figure_count >= 3, summary 존재."""
    cutoff = date.today() - timedelta(days=LOOKBACK_DAYS_FEATURED)
    rows = await conn.fetch("""
        SELECT DISTINCT ON (p.arxiv_id)
               p.arxiv_id, p.title, COALESCE(p.abstract,'') AS abstract,
               p.pdf_url, p.is_hai, p.hai_topic, p.venue, p.citation_count,
               ps.summary_text, ps.generation_model, ps.figure_count,
               tp.date AS feat_date, tp.featured_score
        FROM papers p
        JOIN trending_papers tp ON tp.arxiv_id = p.arxiv_id
        JOIN paper_summaries ps ON ps.arxiv_id = p.arxiv_id
        WHERE tp.date >= $1
          AND tp.is_featured = TRUE
          AND ps.figure_count >= 3
          AND p.arxiv_id ~ '^[0-9]{4}\\.[0-9]{4,5}$'
          AND p.abstract IS NOT NULL AND length(p.abstract) > 50
          AND length(COALESCE(ps.summary_text,'')) > 200
        ORDER BY p.arxiv_id, tp.featured_score DESC NULLS LAST, tp.date DESC
    """, cutoff)
    # 다시 score 정렬 후 dedupe
    rows = sorted(
        (dict(r) for r in rows),
        key=lambda r: (-(r.get('featured_score') or 0), -(r.get('figure_count') or 0)),
    )
    out = []
    for r in rows:
        if r['arxiv_id'] in exclude:
            continue
        r['picked_reason'] = (
            f"featured-fig{r['figure_count']}-score{r.get('featured_score') or 0:.1f}"
            f"-{r['feat_date']}"
        )
        r['bucket'] = 'featured'
        out.append(r)
        exclude.add(r['arxiv_id'])
        if len(out) >= limit:
            break
    return out


async def pick_hai(conn, limit: int, exclude: set[str]) -> list[dict]:
    """HAI papers — hai_topic 다양성을 위해 topic당 균등 분배."""
    rows = await conn.fetch("""
        SELECT p.arxiv_id, p.title, COALESCE(p.abstract,'') AS abstract,
               p.pdf_url, p.is_hai, p.hai_topic, p.venue, p.citation_count,
               ps.summary_text, ps.generation_model, ps.figure_count
        FROM papers p
        JOIN paper_summaries ps ON ps.arxiv_id = p.arxiv_id
        WHERE p.is_hai = TRUE
          AND p.arxiv_id ~ '^[0-9]{4}\\.[0-9]{4,5}$'
          AND p.abstract IS NOT NULL AND length(p.abstract) > 50
          AND length(COALESCE(ps.summary_text,'')) > 200
        ORDER BY p.hai_score DESC NULLS LAST, p.citation_count DESC NULLS LAST
    """)
    # topic별 라운드로빈 (다양성)
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        r = dict(r)
        if r['arxiv_id'] in exclude:
            continue
        by_topic[r.get('hai_topic') or 'unknown'].append(r)

    out: list[dict] = []
    topics = sorted(by_topic.keys(), key=lambda t: -len(by_topic[t]))
    idx = 0
    while len(out) < limit and any(by_topic[t] for t in topics):
        t = topics[idx % len(topics)]
        if by_topic[t]:
            r = by_topic[t].pop(0)
            r['picked_reason'] = f"hai-topic:{t}-cite{r.get('citation_count') or 0}"
            r['bucket'] = 'hai'
            out.append(r)
            exclude.add(r['arxiv_id'])
        idx += 1
        # safety stop — 모든 topic이 빌 때
        if idx > len(topics) * (limit + 5):
            break
    return out


async def pick_conf(conn, limit: int, exclude: set[str]) -> list[dict]:
    """oral/best/spotlight from venue_acceptances. 없으면 citation_count 상위 fallback."""
    # 1차: venue_acceptances 기반
    rows = await conn.fetch("""
        SELECT p.arxiv_id, p.title, COALESCE(p.abstract,'') AS abstract,
               p.pdf_url, p.is_hai, p.hai_topic, p.venue, p.citation_count,
               ps.summary_text, ps.generation_model, ps.figure_count,
               va.venue AS va_venue, va.track, va.decision, va.year
        FROM venue_acceptances va
        JOIN papers p ON p.id = va.paper_id
        JOIN paper_summaries ps ON ps.arxiv_id = p.arxiv_id
        WHERE (va.track ILIKE '%oral%' OR va.track ILIKE '%spotlight%'
               OR va.track ILIKE '%best%' OR va.decision ILIKE '%best%')
          AND p.arxiv_id ~ '^[0-9]{4}\\.[0-9]{4,5}$'
          AND p.abstract IS NOT NULL AND length(p.abstract) > 50
          AND length(COALESCE(ps.summary_text,'')) > 200
        ORDER BY va.year DESC NULLS LAST, p.citation_count DESC NULLS LAST
    """)
    out: list[dict] = []
    for r in rows:
        r = dict(r)
        if r['arxiv_id'] in exclude:
            continue
        tag = r.get('track') or r.get('decision') or 'top'
        r['picked_reason'] = f"conf:{r.get('va_venue') or ''}-{tag}-y{r.get('year') or ''}"
        r['bucket'] = 'conf'
        out.append(r)
        exclude.add(r['arxiv_id'])
        if len(out) >= limit:
            break

    if len(out) >= limit:
        return out

    # Fallback: citation_count 상위 (top-tier 대용)
    need = limit - len(out)
    rows = await conn.fetch("""
        SELECT p.arxiv_id, p.title, COALESCE(p.abstract,'') AS abstract,
               p.pdf_url, p.is_hai, p.hai_topic, p.venue, p.citation_count,
               ps.summary_text, ps.generation_model, ps.figure_count
        FROM papers p
        JOIN paper_summaries ps ON ps.arxiv_id = p.arxiv_id
        WHERE p.arxiv_id ~ '^[0-9]{4}\\.[0-9]{4,5}$'
          AND p.abstract IS NOT NULL AND length(p.abstract) > 50
          AND length(COALESCE(ps.summary_text,'')) > 200
          AND p.citation_count IS NOT NULL
        ORDER BY p.citation_count DESC NULLS LAST
        LIMIT $1
    """, need * 4)  # 여유분 확보
    for r in rows:
        r = dict(r)
        if r['arxiv_id'] in exclude:
            continue
        r['picked_reason'] = (
            f"conf-fallback:cite{r.get('citation_count') or 0}"
            f"-venue:{(r.get('venue') or '')[:40]}"
        )
        r['bucket'] = 'conf-fallback'
        out.append(r)
        exclude.add(r['arxiv_id'])
        if len(out) >= limit:
            break
    return out


# ──────────────────────────────────────────
# ar5iv probe (HEAD only — 본문 fetch는 안 함)
# ──────────────────────────────────────────
def probe_ar5iv(arxiv_id: str, timeout: float = 6.0) -> str | None:
    """200 응답 주는 URL을 반환. 둘 다 실패하면 None."""
    for url in (f'https://ar5iv.labs.arxiv.org/html/{arxiv_id}',
                f'https://arxiv.org/html/{arxiv_id}'):
        try:
            r = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                return url
        except Exception:
            continue
    return None


# ──────────────────────────────────────────
# Dump
# ──────────────────────────────────────────
def dump_paper(rec: dict, ar5iv_url: str | None) -> str:
    arxiv_id = rec['arxiv_id']
    payload = {
        'arxiv_id': arxiv_id,
        'title': rec.get('title') or '',
        'abstract': rec.get('abstract') or '',
        'pdf_url': rec.get('pdf_url') or '',
        'venue': rec.get('venue') or '',
        'citation_count': rec.get('citation_count'),
        'is_hai': bool(rec.get('is_hai')),
        'hai_topic': rec.get('hai_topic'),
        'figure_count': rec.get('figure_count'),
        'baseline_summary': rec.get('summary_text') or '',
        'baseline_generation_model': rec.get('generation_model') or '',
        'baseline_word_count': len((rec.get('summary_text') or '').split()),
        'bucket': rec.get('bucket'),
        'picked_reason': rec.get('picked_reason'),
        'ar5iv_url': ar5iv_url,
        'ar5iv_available': ar5iv_url is not None,
    }
    path = os.path.join(OUT_DIR, f'{arxiv_id}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


async def main():
    started = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"📂 output → {os.path.abspath(OUT_DIR)}")

    conn = await asyncpg.connect(DB_URL)
    try:
        chosen: list[dict] = []
        seen: set[str] = set()

        feat = await pick_featured(conn, FEATURED_QUOTA, seen)
        print(f"  featured (fig>=3, 30d): picked {len(feat)}/{FEATURED_QUOTA}")
        chosen.extend(feat)

        hai = await pick_hai(conn, HAI_QUOTA, seen)
        print(f"  HAI diverse: picked {len(hai)}/{HAI_QUOTA}")
        chosen.extend(hai)

        conf = await pick_conf(conn, CONF_QUOTA, seen)
        print(f"  conf (oral/best→cite fallback): picked {len(conf)}/{CONF_QUOTA}")
        chosen.extend(conf)

        # 만약 어떤 버킷이 부족해서 50편이 안 되면 featured에서 추가 보충
        if len(chosen) < TOTAL_QUOTA:
            need = TOTAL_QUOTA - len(chosen)
            print(f"  ⚠️  total {len(chosen)} < {TOTAL_QUOTA} → top-up featured by {need}")
            extra = await pick_featured(conn, need, seen)
            chosen.extend(extra)

        print(f"\n🎯 final pool: {len(chosen)} papers")
    finally:
        await conn.close()

    # ar5iv 가용성 probe + dump
    ar5iv_ok = 0
    fail_dump: list[str] = []
    by_bucket: Counter[str] = Counter()
    by_topic: Counter[str] = Counter()
    written: list[str] = []

    for i, rec in enumerate(chosen, 1):
        aid = rec['arxiv_id']
        by_bucket[rec.get('bucket') or 'unknown'] += 1
        by_topic[rec.get('hai_topic') or '_none_'] += 1
        print(f"  [{i}/{len(chosen)}] {aid} ({rec.get('bucket')}) — {(rec.get('title') or '')[:70]}")
        ar5iv_url = None
        try:
            ar5iv_url = probe_ar5iv(aid)
            if ar5iv_url:
                ar5iv_ok += 1
        except Exception as e:
            print(f"    ar5iv probe err: {e}")
        try:
            path = dump_paper(rec, ar5iv_url)
            written.append(path)
        except Exception as e:
            print(f"    ❌ dump err: {e}")
            fail_dump.append(aid)

    # Index file
    index = {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'total_picked': len(chosen),
        'total_written': len(written),
        'failed_dump': fail_dump,
        'ar5iv_available': ar5iv_ok,
        'ar5iv_ratio': round(ar5iv_ok / max(len(chosen), 1), 3),
        'by_bucket': dict(by_bucket),
        'by_hai_topic': dict(by_topic),
        'quotas': {
            'featured': FEATURED_QUOTA, 'hai': HAI_QUOTA, 'conf': CONF_QUOTA,
            'total': TOTAL_QUOTA,
        },
        'arxiv_ids': [r['arxiv_id'] for r in chosen],
    }
    idx_path = os.path.join(OUT_DIR, '_index.json')
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - started
    print("\n" + "=" * 60)
    print(f"✅ Golden set built — {len(written)} files in {elapsed:.0f}s")
    print(f"   ar5iv 본문 fetch 가능: {ar5iv_ok}/{len(chosen)} "
          f"({100*ar5iv_ok/max(len(chosen),1):.0f}%)")
    print(f"   버킷 분포: {dict(by_bucket)}")
    print(f"   HAI 토픽 분포: {dict(by_topic)}")
    print(f"   index: {idx_path}")
    if fail_dump:
        print(f"   ⚠️  dump 실패: {fail_dump}")


if __name__ == '__main__':
    asyncio.run(main())

#!/usr/bin/env python3
"""Tag synonym merge.

흔한 alias 자동 발견:
- 단/복수 (llm / llms, transformer / transformers)
- 약어 vs 전체 (llm / large-language-models, vla / vision-language-action)
- 하이픈 변형 (long-context / longcontext / long_context)
- 동의어 hardcoded (deep-learning ↔ deep-neural-networks)

전략:
1. Hardcoded alias map (수동 큐레이션, 가장 정확)
2. 자동 룰: 끝의 's'/'-models' 제거 (단수 정규화)
3. canonical = 그룹 안 paper_count 최대인 것
4. paper_concepts: alias concept_id → canonical concept_id 로 일괄 이전
   (ON CONFLICT 시 weight 합산은 skip — 단순히 무시)
5. alias row는 삭제 (concepts.aliases JSONB에 흔적 남김)
"""
from __future__ import annotations
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncpg

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'


# 수동 큐레이션 alias — 가장 신뢰. 왼쪽 = canonical, 오른쪽 = aliases.
MANUAL_ALIASES: dict[str, list[str]] = {
    'llm': ['llms', 'large-language-model', 'large-language-models', 'language-model', 'language-models'],
    'vla': ['vision-language-action', 'vision-language-action-models', 'vlas'],
    'vlm': ['vision-language', 'vision-language-models', 'vision-language-model'],
    'mllm': ['multimodal-llm', 'multimodal-llms', 'multimodal-large-language-models', 'multimodal-language-models'],
    'transformer': ['transformers', 'transformer-architecture'],
    'diffusion-models': ['diffusion-model', 'diffusion'],
    'reinforcement-learning': ['rl', 'deep-reinforcement-learning', 'drl'],
    'rag': ['retrieval-augmented-generation', 'retrieval-augmentation'],
    'video-generation': ['text-to-video', 'video-synthesis'],
    'text-to-image': ['t2i', 'text2image', 'image-generation'],
    'vision-transformer': ['vit'],
    'flow-matching': ['rectified-flow'],
    'world-models': ['world-model'],
    'in-context-learning': ['icl'],
    'long-context': ['long-context-models', 'long-context-llm'],
    'agent': ['agents', 'ai-agent', 'ai-agents'],
    'robot-manipulation': ['robotic-manipulation', 'manipulation'],
    'imitation-learning': ['behavior-cloning'],
    'continual-learning': ['lifelong-learning'],
    'self-supervised-learning': ['ssl', 'self-supervised'],
    'graph-neural-networks': ['gnn', 'gnns', 'graph-neural-network'],
    'speech-recognition': ['asr', 'automatic-speech-recognition'],
    'object-detection': ['detection'],
    'knowledge-graph': ['knowledge-graphs', 'kg'],
    'neural-architecture-search': ['nas'],
    'mixture-of-experts': ['moe'],
}


async def main():
    conn = await asyncpg.connect(DB_URL)

    # 1. canonical tag 보장 (없으면 생성)
    merged = 0
    edges_moved = 0
    deleted = 0
    for canonical, aliases in MANUAL_ALIASES.items():
        # canonical concept 보장
        row = await conn.fetchrow(
            "SELECT id, aliases FROM concepts WHERE name = $1 AND type='keyword'", canonical
        )
        if not row:
            # alias 중 하나라도 있을 때만 canonical 만듦
            any_alias = await conn.fetchrow(
                "SELECT 1 FROM concepts WHERE name = ANY($1::text[]) AND type='keyword' LIMIT 1",
                aliases,
            )
            if not any_alias:
                continue
            cid = await conn.fetchval(
                "INSERT INTO concepts (name, type, paper_count, aliases) "
                "VALUES ($1, 'keyword', 0, '[]'::jsonb) RETURNING id", canonical
            )
            existing_aliases: list = []
        else:
            cid = row['id']
            existing_aliases = row['aliases'] if isinstance(row['aliases'], list) else []

        # 각 alias 처리
        for alias in aliases:
            alias_row = await conn.fetchrow(
                "SELECT id FROM concepts WHERE name = $1 AND type='keyword'", alias
            )
            if not alias_row:
                continue
            alias_id = alias_row['id']
            if alias_id == cid:
                continue
            # paper_concepts: alias_id → cid 이전 (ON CONFLICT 시 alias edge 그냥 skip)
            r = await conn.execute("""
                INSERT INTO paper_concepts (paper_id, concept_id, weight, confidence, extraction_method)
                SELECT pc.paper_id, $1, pc.weight, pc.confidence, pc.extraction_method
                FROM paper_concepts pc WHERE pc.concept_id = $2
                ON CONFLICT (paper_id, concept_id) DO NOTHING
            """, cid, alias_id)
            # 이동 카운트 (정확하진 않으나 대략)
            edges_moved += int(r.split()[-1]) if r.startswith('INSERT') else 0
            # 옛 edge 삭제
            await conn.execute("DELETE FROM paper_concepts WHERE concept_id = $1", alias_id)
            # alias concept row 삭제
            await conn.execute("DELETE FROM concepts WHERE id = $1", alias_id)
            existing_aliases.append(alias)
            deleted += 1

        # canonical row의 aliases JSON 갱신
        if existing_aliases:
            await conn.execute(
                "UPDATE concepts SET aliases = $1::jsonb, updated_at = NOW() WHERE id = $2",
                json.dumps(sorted(set(existing_aliases))), cid,
            )
            merged += 1

    # 2. paper_count 일괄 갱신
    await conn.execute("""
        UPDATE concepts c SET paper_count = (
          SELECT COUNT(*) FROM paper_concepts pc WHERE pc.concept_id = c.id
        ) WHERE c.type = 'keyword'
    """)

    print(f"✅ merged {merged} canonical groups, moved {edges_moved} edges, deleted {deleted} alias rows")

    # 결과 확인
    rows = await conn.fetch(
        "SELECT name, paper_count, aliases FROM concepts WHERE type='keyword' "
        "AND jsonb_array_length(COALESCE(aliases, '[]'::jsonb)) > 0 "
        "ORDER BY paper_count DESC LIMIT 10"
    )
    print("\n=== Top merged groups ===")
    for r in rows:
        ali = r['aliases'] if isinstance(r['aliases'], list) else json.loads(r['aliases'] or '[]')
        print(f"  {r['name']}: {r['paper_count']}편 (← {', '.join(ali[:3])}…)")

    await conn.close()


if __name__ == '__main__':
    asyncio.run(main())

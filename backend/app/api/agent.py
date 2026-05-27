"""HotPaper Research Agent — RAG over the paper DB.

Pipeline:
  1. BGE-m3 encode question  →  pgvector cosine search (top-K papers)
  2. Stream Ollama (Qwen3 14B) response over SSE, citing arXiv IDs
  3. Rate-limit per IP (in-memory sliding window)
"""
from __future__ import annotations
import json
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import AsyncIterator

import httpx
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session
from ..models import Paper
from ..services.embedding_service import get_embedding_service

router = APIRouter(prefix="/api/agent", tags=["Agent"])

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen3:14b"  # default Q4_K_M, ~9GB on GB10
TOP_K = 8

# Per-IP sliding window: 3 / minute, 30 / day
_rate: dict[str, deque] = defaultdict(deque)
_PER_MIN = 3
_PER_DAY = 30


def _rate_ok(ip: str) -> bool:
    now = datetime.now()
    bucket = _rate[ip]
    while bucket and (now - bucket[0]) > timedelta(days=1):
        bucket.popleft()
    if len(bucket) >= _PER_DAY:
        return False
    last_minute = sum(1 for t in bucket if (now - t) < timedelta(minutes=1))
    if last_minute >= _PER_MIN:
        return False
    bucket.append(now)
    return True


SYSTEM_PROMPT = """당신은 HotPaper.ai의 연구 보조 에이전트입니다. SNU HAI Lab의 연구 분야(Industrial Foundation Models, Manufacturing AI, PHM, Signal Processing, Physics-Informed ML, Robotics 등)와 관련된 질문을 받습니다.

규칙:
- 제공된 논문 발췌(Context)만 근거로 답변하세요.
- 발췌에 없는 사실은 절대 만들어내지 마세요. 모르면 "제공된 자료에는 명시되지 않았습니다"라고 답변하세요.
- 인용한 논문의 arXiv ID를 본문에 [2605.xxxxx] 형식으로 표기하세요.
- 한국어로 자연스럽게 답변하세요.
- 답변은 5~10문장 이내로 간결하게 정리하세요."""


def _format_context(papers: list[tuple[Paper, float]]) -> str:
    lines = []
    for i, (p, sim) in enumerate(papers, 1):
        lines.append(
            f"[논문 {i}] arXiv:{p.arxiv_id} | 유사도 {sim:.2f}\n"
            f"제목: {p.title}\n"
            f"초록: {(p.abstract or '')[:600]}\n"
        )
    return "\n".join(lines)


@router.post("/ask")
async def ask(
    request: Request,
    payload: dict,
    session: AsyncSession = Depends(get_async_session),
):
    """RAG endpoint with streaming SSE response.

    Body:
        { "question": str, "k": Optional[int] }
    Stream:
        data: {"type":"sources","sources":[...]}\n\n
        data: {"type":"token","content":"..."} ...  (many)
        data: [DONE]\n\n
    """
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "question is required")
    if len(question) > 500:
        raise HTTPException(400, "question must be 500 characters or fewer")

    ip = request.client.host if request.client else "unknown"
    if not _rate_ok(ip):
        raise HTTPException(429, "잠시 후 다시 시도해주세요 (분당 3회, 일당 30회 제한)")

    k = max(1, min(int(payload.get("k") or TOP_K), 12))

    # 1) Retrieve
    svc = get_embedding_service()
    q_emb = (await svc.encode_texts_async([question]))[0]
    q_vec = np.array(q_emb).tolist()

    sim_expr = (1 - Paper.full_embedding.cosine_distance(q_vec)).label("sim")
    rows = await session.execute(
        select(Paper, sim_expr)
        .where(Paper.full_embedding.is_not(None))
        .order_by(sim_expr.desc())
        .limit(k)
    )
    papers = rows.all()
    if not papers:
        raise HTTPException(503, "검색 결과가 없습니다 (임베딩 풀 비어있음)")

    user_msg = (
        f"다음은 사용자 질문과 의미적으로 가장 가까운 논문 발췌입니다.\n\n"
        f"{_format_context(papers)}\n"
        f"---\n사용자 질문: {question}\n\n"
        f"위 발췌만 근거로 한국어로 답변하세요. 인용한 논문은 [arXiv ID] 형식으로 본문에 명시하세요."
    )

    async def event_stream() -> AsyncIterator[bytes]:
        # 1) Emit sources first so the UI can render citations right away
        sources_payload = {
            "type": "sources",
            "sources": [
                {
                    "arxiv_id": p.arxiv_id,
                    "title": p.title,
                    "similarity": round(float(s), 3),
                    "is_arxiv": bool(p.arxiv_id and not p.arxiv_id.startswith(("hai:", "openalex:"))),
                }
                for p, s in papers
            ],
        }
        yield f"data: {json.dumps(sources_payload, ensure_ascii=False)}\n\n".encode()

        # 2) Stream Ollama response
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_URL}/api/chat",
                    json={
                        "model": MODEL,
                        "stream": True,
                        # Qwen3은 thinking 모델 — RAG에선 fast first-token이 우선이라
                        # reasoning trace는 끄고 본문만 받는다.
                        "think": False,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_msg},
                        ],
                        "options": {
                            "num_predict": 800,
                            "temperature": 0.3,
                            "top_p": 0.9,
                        },
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            token = {"type": "token", "content": content}
                            yield f"data: {json.dumps(token, ensure_ascii=False)}\n\n".encode()
                        if chunk.get("done"):
                            yield b"data: [DONE]\n\n"
                            return
        except Exception as e:
            err = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx/cf buffering for SSE
        },
    )


@router.get("/health")
async def agent_health():
    """Quick check: is Ollama up and the model loaded."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            r.raise_for_status()
            tags = r.json().get("models", [])
            model_loaded = any(MODEL in (m.get("name") or "") for m in tags)
        return {"ollama": "ok", "model": MODEL, "loaded": model_loaded}
    except Exception as e:
        return {"ollama": "down", "error": str(e)}

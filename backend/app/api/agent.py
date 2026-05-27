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
from ..models import Paper, PaperSummary
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


SYSTEM_PROMPT = """당신은 HotPaper.ai의 Paper Agent입니다. SNU HAI Lab의 연구 분야(Industrial Foundation Models, Manufacturing AI, PHM, Signal Processing, Physics-Informed ML, Robotics 등) 관련 질문을 받습니다.

답변 규칙:
- 제공된 논문 발췌(Context)만 근거로 답변. Context에 없는 사실은 절대 만들지 말 것. 모르면 "제공된 자료에는 명시되지 않았습니다."
- 인용은 **반드시 [1], [2] 같은 번호만** 사용하세요. (Context에 '[논문 N]' 으로 번호가 매겨져 있습니다. 그 N을 그대로 사용.)
- 절대로 [arxiv:xxxx]·[hai:xxx]·논문 제목 등 다른 형식의 인용을 본문에 넣지 마세요. UI에 이미 출처 카드가 따로 보입니다.
- 한국어로 답변.

답변 형식 (반드시 마크다운):
1. 첫 줄: `**핵심 요약:**` 한 문장 (한국어, 80자 내외).
2. 빈 줄 후, 본문은 불릿 5~8개.
3. 각 불릿:
   - **굵은 핵심어/방법명**으로 시작 → 그 다음에 구체적인 설명 (방법론·핵심 아이디어·결과·한계 중 1~2개를 포함, 1~2 줄).
   - Context에 한국어 요약이 있으면 그 안의 **구체적인 모듈명/데이터셋/수치/장단점**을 가능한 한 인용. 추상적 일반론(예: "신뢰성을 높인다")만 쓰지 말 것.
   - 인용은 불릿 끝에 [1], [2] 형태.
4. 헤더(##/###) 금지, 산문 단락 금지. 핵심 요약 박스 + 불릿 리스트만.
5. "참고 논문" 같은 섹션 만들지 말 것 (UI에 이미 있음).

수식·표기 규칙:
- **LaTeX 절대 금지** ($...$, \\frac, \\sigma 같은 표기 금지). 사이트는 LaTeX를 렌더링하지 않음.
- 그리스 문자·수학 기호가 필요하면 유니코드 사용: α β γ σ μ Σ Π λ θ φ ∂ ∇ ≈ ≤ ≥ × ÷ √ ∞.
- 분수는 'a/b', 지수는 'x^2', 합은 'Σ', 평균은 '평균' 같이 일반 텍스트로.

좋은 답변 예시:
**핵심 요약:** PHM은 불확실성을 명시적으로 모델링해 진단 신뢰도를 높이는 방향으로 발전 중.

- **Aleatory vs Epistemic 분리** — 측정 잡음과 모델 한계를 다르게 처리 [1]
- **Bayesian 추정** — 사후분포로 confidence interval 제공, fault 분류에 신뢰도 부여 [2]
- **Domain shift 대응** — 운영 조건이 바뀔 때 epistemic 증가를 감지해 재학습 트리거 [3]
- **Unseen fault 식별** — Center margin loss로 학습되지 않은 클래스 거부 [4]"""


def _format_context(papers: list[tuple[Paper, float]], ko_map: dict[str, str]) -> str:
    """검색된 논문 발췌를 LLM에게 보낼 형태로 정리.

    영문 abstract뿐 아니라 paper_summaries의 한국어 7섹션 요약(있으면)을
    함께 보내 LLM이 깊이 있는 답변을 생성할 수 있도록 한다.
    """
    lines = []
    for i, (p, sim) in enumerate(papers, 1):
        tag = "🎓 HAI Lab" if p.is_lab_publication else "arXiv"
        year = p.year or (p.published_date.year if p.published_date else "n/a")
        ko = (ko_map.get(p.arxiv_id) or "").strip()

        header = f"[논문 {i}] {p.arxiv_id} | {tag} | {year}\n제목: {p.title}\n"
        if ko:
            # 7섹션 한국어 요약은 평균 1,200~1,500자라 1,600자에서 자른다
            lines.append(header + f"한국어 요약:\n{ko[:1600]}\n")
        else:
            lines.append(header + f"초록(영문): {(p.abstract or '')[:700]}\n")
    return "\n".join(lines)


_LAB_KEYWORDS = (
    'hai lab', 'haı', 'hai-lab', 'hai랩', 'snu hai',
    '연구실', '랩 논문', '랩이', '랩은', '랩에서', '랩의',
    'lab 논문', 'lab이', 'lab은', 'lab에서',
)
_RECENT_KEYWORDS = ('요즘', '최근', '최신', '이번', '근래', 'recent', 'latest')


def detect_intent(question: str) -> dict:
    """Lightweight keyword-based intent extraction."""
    q = question.lower()
    return {
        'lab_only': any(kw in q for kw in _LAB_KEYWORDS),
        'recent': any(kw in question for kw in _RECENT_KEYWORDS),
    }


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

    # 1) Intent 감지
    intent = detect_intent(question)

    # 2) Retrieve — intent에 따라 검색 풀 분기
    svc = get_embedding_service()
    q_emb = (await svc.encode_texts_async([question]))[0]
    q_vec = np.array(q_emb).tolist()
    sim_expr = (1 - Paper.full_embedding.cosine_distance(q_vec)).label("sim")

    stmt = select(Paper, sim_expr).where(Paper.full_embedding.is_not(None))

    if intent['lab_only']:
        stmt = stmt.where(Paper.is_lab_publication.is_(True))
    if intent['recent']:
        # 최근 = 작년 + 올해 (HAI Lab은 연 단위 출판 패턴이라 year 기준이 더 신뢰)
        from datetime import date as _date
        this_year = _date.today().year
        stmt = stmt.where(Paper.year >= this_year - 1)

    # 정렬: 'recent' 의도면 최신순 우선, 아니면 유사도 우선
    if intent['recent']:
        stmt = stmt.order_by(
            Paper.year.desc().nullslast(),
            Paper.published_date.desc().nullslast(),
            sim_expr.desc(),
        )
    else:
        stmt = stmt.order_by(sim_expr.desc())

    rows = await session.execute(stmt.limit(k))
    papers = rows.all()

    # Fallback: lab+recent 조건이 너무 엄격해 결과 0인 경우 lab 조건만 남기고 재시도
    if not papers and (intent['lab_only'] or intent['recent']):
        relax = select(Paper, sim_expr).where(Paper.full_embedding.is_not(None))
        if intent['lab_only']:
            relax = relax.where(Paper.is_lab_publication.is_(True))
        rows = await session.execute(
            relax.order_by(Paper.year.desc().nullslast(), sim_expr.desc()).limit(k)
        )
        papers = rows.all()

    if not papers:
        raise HTTPException(503, "검색 결과가 없습니다")

    # 3) 한국어 요약 일괄 조회 (각 논문당 7섹션 ~1,500자)
    arxiv_ids = [p.arxiv_id for p, _ in papers]
    sum_rows = await session.execute(
        select(PaperSummary.arxiv_id, PaperSummary.summary_text)
        .where(PaperSummary.arxiv_id.in_(arxiv_ids))
    )
    ko_map: dict[str, str] = {}
    for aid, txt in sum_rows.all():
        if txt and (aid not in ko_map or len(txt) > len(ko_map[aid])):
            ko_map[aid] = txt

    # 4) Intent를 LLM에 알려서 답변 톤 조정
    intent_note = ""
    if intent['lab_only'] and intent['recent']:
        intent_note = "참고: 사용자는 SNU HAI Lab이 최근 발표한 연구를 묻고 있습니다. 아래 발췌는 모두 HAI Lab 발표 논문입니다.\n\n"
    elif intent['lab_only']:
        intent_note = "참고: 사용자는 SNU HAI Lab이 발표한 연구를 묻고 있습니다. 아래 발췌는 모두 HAI Lab 발표 논문입니다.\n\n"
    elif intent['recent']:
        intent_note = "참고: 사용자는 최근 동향을 묻고 있습니다. 아래 발췌는 최신 논문 순으로 정렬돼 있습니다.\n\n"

    user_msg = (
        f"{intent_note}"
        f"다음은 검색된 논문 발췌입니다. 각 논문에는 영문 초록 또는 한국어 7섹션 요약이 포함돼 있습니다.\n\n"
        f"{_format_context(papers, ko_map)}\n"
        f"---\n사용자 질문: {question}\n\n"
        f"위 발췌만 근거로 한국어 마크다운으로 답변하세요. 인용은 [1], [2] 번호만 사용."
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
                            # 깊이 있는 답변 허용 (불릿 5-8개 + 각 1-2줄)
                            "num_predict": 1500,
                            "temperature": 0.3,
                            "top_p": 0.9,
                            "num_ctx": 8192,  # 한국어 요약 8편 ≈ 12K chars ≈ ~3K tokens
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

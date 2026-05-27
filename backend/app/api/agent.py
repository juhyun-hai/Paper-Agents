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
- 제공된 논문 발췌(Context)만 근거로 답변. Context에 없는 사실은 절대 만들지 말 것.
- **약한 매칭 거부 규칙 (중요)**:
  · 각 발췌에 '관련성 강함/보통/약함' 라벨이 붙어 있습니다.
  · '약함(주제 다를 수 있음)' 발췌는 가능한 한 답변에서 인용하지 마세요.
  · 8개 발췌가 모두 '보통' 이하이면, 솔직히 다음과 같이 답변하세요:
    "사용자의 질문 '...'을 직접 다루는 논문을 검색 풀에서 찾지 못했습니다. 다만 인접한 주제의 논문을 소개하면 다음과 같습니다." 그 후 가장 가까운 1~3편만 인용.
  · '강함' 또는 '보통' 매칭이 3편 이상 있으면 그것들 위주로 깊이 있게 정리.
- 8편 모두 다루려고 하지 말 것. 진짜 관련 있는 3~5편만 깊이 있게.
- 인용은 **반드시 [1], [2] 같은 번호만** 사용. Context의 '[논문 N]' N을 그대로 사용.
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
    """검색된 논문 발췌를 LLM에게 보낼 형태로 정리. 각 발췌에 유사도 점수와
    관련성 등급을 표시해 LLM이 약한 매칭을 거를 수 있게 한다."""
    lines = []
    for i, (p, sim) in enumerate(papers, 1):
        tag = "🎓 HAI Lab" if p.is_lab_publication else "arXiv"
        year = p.year or (p.published_date.year if p.published_date else "n/a")
        ko = (ko_map.get(p.arxiv_id) or "").strip()
        # 관련성 등급 (LLM이 판단할 수 있게 명시적 라벨)
        if sim >= 0.55:
            grade = "강함"
        elif sim >= 0.45:
            grade = "보통"
        else:
            grade = "약함(주제 다를 수 있음)"

        header = (
            f"[논문 {i}] {p.arxiv_id} | {tag} | {year} | 관련성 {grade} (유사도 {sim:.2f})\n"
            f"제목: {p.title}\n"
        )
        if ko:
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

# Industrial / HAI 도메인 키워드 — '산업용 Foundation Model' 같은 질문에서
# 일반 ML 논문 대신 산업 AI / PHM / 제조 / fault 관련 논문으로 좁힐 때 사용
_INDUSTRIAL_KEYWORDS = (
    '산업', 'industrial', 'manufacturing', '제조',
    'phm', 'fault', '결함', '고장', '진단', 'diagnosis',
    'rul', 'prognostic', '잔여수명', 'health management',
    'physics-informed', 'physics informed', 'pinn', '물리 정보', '물리정보',
    'digital twin', '디지털 트윈',
    'signal processing', '신호 처리', '진동', 'vibration',
    'reliability', '신뢰성', 'shm', 'condition monitoring',
    '베어링', 'bearing', '기어박스', 'gearbox', 'motor', '모터',
    'battery', '배터리', 'semiconductor', '반도체',
    'foundation model' if False else '',  # 일반 FM 매칭은 너무 광범위해서 제외
)


def detect_intent(question: str) -> dict:
    """Lightweight keyword-based intent extraction."""
    q = question.lower()
    industrial_hit = any(kw and kw in q for kw in _INDUSTRIAL_KEYWORDS)
    # 'industrial foundation model', '산업용 ...', '제조 AI' 같은 표현 보강
    if 'foundation model' in q and (
        '산업' in q or 'industrial' in q or '제조' in q or 'manufacturing' in q
    ):
        industrial_hit = True
    return {
        'lab_only': any(kw in q for kw in _LAB_KEYWORDS),
        'recent': any(kw in question for kw in _RECENT_KEYWORDS),
        'industrial': industrial_hit,
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
    topic = (payload.get("topic") or "").strip().lower() or None  # 사용자가 chip으로 선택한 토픽

    # 1) Intent 감지
    intent = detect_intent(question)

    # 2) Retrieve — topic chip + intent에 따라 검색 풀 분기
    svc = get_embedding_service()
    q_emb = (await svc.encode_texts_async([question]))[0]
    q_vec = np.array(q_emb).tolist()
    sim_expr = (1 - Paper.full_embedding.cosine_distance(q_vec)).label("sim")

    stmt = select(Paper, sim_expr).where(Paper.full_embedding.is_not(None))

    # 명시적 topic chip이 가장 우선. 'lab'이면 lab_only 의도로 변환.
    if topic == "lab":
        stmt = stmt.where(Paper.is_lab_publication.is_(True))
        intent['lab_only'] = True
    elif topic:
        # hai_topic = 'fault-diagnosis' 같은 값
        stmt = stmt.where(Paper.hai_topic == topic, Paper.is_hai.is_(True))
        intent['industrial'] = True
    elif intent['lab_only']:
        stmt = stmt.where(Paper.is_lab_publication.is_(True))
    elif intent['industrial']:
        # lab_only가 아닌 industrial 키워드만 있는 경우 (예: '산업용 FM', 'PHM 트렌드')
        # → HAI 키워드 매칭 풀(is_hai=True, ~441편)로 좁혀서 일반 ML 논문 노이즈 제거
        stmt = stmt.where(Paper.is_hai.is_(True))
    if intent['recent']:
        # 최근 = 작년 + 올해 (HAI Lab은 연 단위 출판 패턴이라 year 기준이 더 신뢰)
        from datetime import date as _date
        this_year = _date.today().year
        stmt = stmt.where(Paper.year >= this_year - 1)

    # 정렬:
    #  - recent → 최신순 우선
    #  - 명시 토픽 chip(fault-diagnosis 등) → lab 우선 (hai_topic 분류가
    #    abstract 기반이라 lab 논문이 더 신뢰 가능)
    #  - 기본 → 유사도
    if intent['recent']:
        stmt = stmt.order_by(
            Paper.year.desc().nullslast(),
            Paper.published_date.desc().nullslast(),
            sim_expr.desc(),
        )
    elif topic and topic != "lab":
        stmt = stmt.order_by(
            Paper.is_lab_publication.desc(),
            sim_expr.desc(),
        )
    else:
        stmt = stmt.order_by(sim_expr.desc())

    rows = await session.execute(stmt.limit(k))
    papers = rows.all()

    # Fallback: 조건이 너무 엄격해 결과 0인 경우 lab/industrial 조건만 남기고 재시도
    if not papers and (intent['lab_only'] or intent['recent'] or intent['industrial']):
        relax = select(Paper, sim_expr).where(Paper.full_embedding.is_not(None))
        if intent['lab_only']:
            relax = relax.where(Paper.is_lab_publication.is_(True))
        elif intent['industrial']:
            relax = relax.where(Paper.is_hai.is_(True))
        rows = await session.execute(
            relax.order_by(Paper.year.desc().nullslast(), sim_expr.desc()).limit(k)
        )
        papers = rows.all()

    if not papers:
        raise HTTPException(503, "검색 결과가 없습니다")

    # 2-bis) 약한 매칭 필터링 — sim 0.45 미만은 LLM에 보내지 않는다.
    # LLM이 약한 매칭을 '관련된 척' 합성하는 hallucination을 원천 차단.
    # 단 모든 결과가 약하면 가장 강한 1~3편만 남기고 "weak_only" 플래그를 켠다.
    STRONG_THRESHOLD = 0.45
    strong = [(p, s) for p, s in papers if s >= STRONG_THRESHOLD]
    weak_only = False
    if strong:
        papers = strong
    else:
        # 전부 약한 매칭 — 상위 3편만 남기고 솔직한 답변 유도
        papers = papers[:3]
        weak_only = True

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

    # 4) Intent + 매칭 강도를 LLM에 알려서 답변 톤 조정
    intent_note = ""
    if weak_only:
        intent_note = (
            "**중요**: 검색 풀에서 사용자 질문을 **직접 다루는 논문**을 찾지 못했습니다. "
            "아래 발췌는 의미적으로 가장 가까운 후보일 뿐, 핵심 주제가 다를 가능성이 높습니다. "
            "이 경우 답변 첫 줄을 정확히 다음과 같이 작성하세요:\n"
            "`**핵심 요약:** 사용자의 질문을 직접 다루는 논문을 검색 풀에서 찾지 못했습니다.`\n"
            "그 후 빈 줄, 그리고 '다만 인접 주제의 논문은 다음과 같습니다:' 라고 적은 뒤, "
            "발췌 중 가장 가까운 1~3편만 **사실 그대로** (잘못 일반화하지 말고) 요약하세요. "
            "절대 그 논문들을 사용자가 물어본 주제와 직접 연결하지 마세요.\n\n"
        )
    elif intent['lab_only'] and intent['recent']:
        intent_note = "참고: 사용자는 SNU HAI Lab이 최근 발표한 연구를 묻고 있습니다. 아래 발췌는 모두 HAI Lab 발표 논문입니다.\n\n"
    elif intent['lab_only']:
        intent_note = "참고: 사용자는 SNU HAI Lab이 발표한 연구를 묻고 있습니다. 아래 발췌는 모두 HAI Lab 발표 논문입니다.\n\n"
    elif intent['industrial']:
        intent_note = "참고: 사용자는 산업 AI/제조/PHM 같은 도메인 질문을 하고 있습니다. 아래 발췌는 모두 HAI Lab 관심 분야 키워드와 매칭된 논문(랩 발표 + 산업 AI 관련 arXiv)입니다. 일반 ML 트렌드가 아니라 **산업·제조 응용** 관점에서 답변하세요.\n\n"
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

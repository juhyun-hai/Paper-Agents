"""
Paper Summary API endpoints.
"""

import os
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from ..core.database import get_async_session
from ..models import Paper, PaperSummary, SummaryFeedback
from ..services.summary_service import get_summary_service

router = APIRouter(prefix="/api/summary", tags=["Summary"])

# 쓰기 라우트 (generate/delete/save) 보호 — 공개 API로 요약 자산이
# 무인증 삭제/덮어쓰기되는 것 차단. .env의 ADMIN_TOKEN과 대조.
_ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', '').strip()


async def require_admin(x_admin_token: str = Header(default='')):
    if not _ADMIN_TOKEN:
        # 토큰 미설정 서버(예: fork 초기 상태)는 쓰기 라우트 자체를 잠근다.
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
    if x_admin_token != _ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")


class SummaryFeedbackRequest(BaseModel):
    """Request model for summary feedback."""
    rating: int  # 1-5
    feedback_text: Optional[str] = None
    accuracy_rating: Optional[int] = None
    clarity_rating: Optional[int] = None
    completeness_rating: Optional[int] = None


@router.get("/generate/{arxiv_id}")
async def generate_summary(
    arxiv_id: str,
    background_tasks: BackgroundTasks,
    force_regenerate: bool = False,
    session: AsyncSession = Depends(get_async_session),
    _admin: None = Depends(require_admin),
):
    """
    Generate or retrieve paper summary.

    If summary exists and force_regenerate=False, returns cached version.
    Otherwise generates new summary in background.
    """
    try:
        # Check if paper exists
        paper_result = await session.execute(
            select(Paper).where(Paper.arxiv_id == arxiv_id)
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=404,
                detail=f"Paper {arxiv_id} not found"
            )

        # Check for existing summary
        if not force_regenerate:
            summary_result = await session.execute(
                select(PaperSummary)
                .where(PaperSummary.arxiv_id == arxiv_id)
                .order_by(desc(PaperSummary.created_at))
                .limit(1)
            )
            existing_summary = summary_result.scalar_one_or_none()

            if existing_summary:
                return {
                    "status": "cached",
                    "summary": {
                        "arxiv_id": existing_summary.arxiv_id,
                        "title": paper.title,
                        "authors": paper.authors or [],
                        "summary_text": existing_summary.summary_text,
                        "figures": existing_summary.figures or [],
                        "summary_type": existing_summary.summary_type,
                        "generated_at": existing_summary.generated_at.isoformat(),
                        "word_count": existing_summary.word_count,
                        "figure_count": existing_summary.figure_count
                    }
                }

        # Generate new summary in background
        background_tasks.add_task(
            _generate_and_save_summary,
            arxiv_id,
            paper.id
        )

        return {
            "status": "generating",
            "message": f"Summary generation started for {arxiv_id}",
            "arxiv_id": arxiv_id,
            "estimated_time": "2-3 minutes"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Summary generation failed: {str(e)}"
        )


@router.get("/{arxiv_id}")
async def get_summary(
    arxiv_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Get existing summary for a paper."""
    try:
        # Get paper info
        paper_result = await session.execute(
            select(Paper).where(Paper.arxiv_id == arxiv_id)
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=404,
                detail=f"Paper {arxiv_id} not found"
            )

        # Get most recent summary
        summary_result = await session.execute(
            select(PaperSummary)
            .where(PaperSummary.arxiv_id == arxiv_id)
            .order_by(desc(PaperSummary.created_at))
            .limit(1)
        )
        summary = summary_result.scalar_one_or_none()

        if not summary:
            return {
                "status": "not_found",
                "message": f"No summary available for {arxiv_id}",
                "arxiv_id": arxiv_id
            }

        # figures의 base64 data(편당 ~500KB)는 응답에서 제외 —
        # 메타(캡션)만 보내고 이미지는 /figure/{n} 엔드포인트로 lazy load.
        # (브라우저 이미지 캐시 + Cloudflare 캐시 활용)
        fig_meta = []
        for f in (summary.figures or []):
            if isinstance(f, dict):
                fig_meta.append({
                    "id": f.get("id"),
                    "number": f.get("number"),
                    "caption": f.get("caption", ""),
                    "page": f.get("page"),
                    "image_url": f"/api/summary/{arxiv_id}/figure/{f.get('number', 0)}",
                })

        return {
            "status": "found",
            "summary": {
                "id": summary.id,
                "arxiv_id": summary.arxiv_id,
                "title": paper.title,
                "authors": paper.authors or [],
                "summary_text": summary.summary_text,
                "figures": fig_meta,
                "summary_type": summary.summary_type,
                "generated_at": summary.generated_at.isoformat(),
                "word_count": summary.word_count,
                "figure_count": summary.figure_count,
                "has_full_text": summary.has_full_text
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve summary: {str(e)}"
        )


@router.post("/{arxiv_id}/feedback")
async def submit_feedback(
    arxiv_id: str,
    feedback: SummaryFeedbackRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Submit feedback for a summary."""
    try:
        # Validate rating
        if not 1 <= feedback.rating <= 5:
            raise HTTPException(
                status_code=400,
                detail="Rating must be between 1 and 5"
            )

        # Get summary
        summary_result = await session.execute(
            select(PaperSummary)
            .where(PaperSummary.arxiv_id == arxiv_id)
            .order_by(desc(PaperSummary.created_at))
            .limit(1)
        )
        summary = summary_result.scalar_one_or_none()

        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"No summary found for {arxiv_id}"
            )

        # Create feedback record
        feedback_record = SummaryFeedback(
            summary_id=summary.id,
            rating=feedback.rating,
            feedback_text=feedback.feedback_text,
            accuracy_rating=feedback.accuracy_rating,
            clarity_rating=feedback.clarity_rating,
            completeness_rating=feedback.completeness_rating
        )

        session.add(feedback_record)
        await session.commit()

        return {
            "status": "success",
            "message": "Feedback submitted successfully",
            "feedback_id": feedback_record.id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/list/recent")
async def get_recent_summaries(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_async_session)
):
    """Get list of recently generated summaries."""
    try:
        # Get recent summaries with paper info
        result = await session.execute(
            select(PaperSummary, Paper)
            .join(Paper, PaperSummary.paper_id == Paper.id)
            .order_by(desc(PaperSummary.created_at))
            .offset(offset)
            .limit(limit)
        )

        summaries_with_papers = result.all()

        summary_list = []
        for summary, paper in summaries_with_papers:
            summary_list.append({
                "id": summary.id,
                "arxiv_id": summary.arxiv_id,
                "title": paper.title,
                "authors": paper.authors or [],
                "summary_type": summary.summary_type,
                "figure_count": summary.figure_count,
                "word_count": summary.word_count,
                "generated_at": summary.generated_at.isoformat(),
                "has_full_text": summary.has_full_text
            })

        return {
            "summaries": summary_list,
            "total": len(summary_list),
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recent summaries: {str(e)}"
        )


@router.get("/{arxiv_id}/figure/{number}")
async def get_summary_figure(
    arxiv_id: str,
    number: int,
    session: AsyncSession = Depends(get_async_session),
):
    """개별 figure 이미지 — base64를 즉시 디코드해 PNG로 반환.

    summary 응답에서 분리해 상세 페이지 로드를 513KB→수KB로 줄이고,
    이미지는 브라우저/Cloudflare가 1일 캐시.
    """
    import base64
    from fastapi.responses import Response as RawResponse

    summary_result = await session.execute(
        select(PaperSummary)
        .where(PaperSummary.arxiv_id == arxiv_id)
        .order_by(desc(PaperSummary.created_at))
        .limit(1)
    )
    summary = summary_result.scalar_one_or_none()
    if not summary or not summary.figures:
        raise HTTPException(404, "no figures")

    for f in summary.figures:
        if isinstance(f, dict) and f.get("number") == number:
            data = f.get("data", "")
            if data.startswith("data:"):
                data = data.split(",", 1)[-1]
            try:
                raw = base64.b64decode(data)
            except Exception:
                raise HTTPException(500, "figure decode failed")
            return RawResponse(
                content=raw,
                media_type=f.get("mime", "image/png"),
                headers={"Cache-Control": "public, max-age=86400, immutable"},
            )
    raise HTTPException(404, f"figure {number} not found")


@router.delete("/{arxiv_id}")
async def delete_summary(
    arxiv_id: str,
    session: AsyncSession = Depends(get_async_session),
    _admin: None = Depends(require_admin),
):
    """Delete summary for a paper."""
    try:
        # Find and delete summary
        summary_result = await session.execute(
            select(PaperSummary).where(PaperSummary.arxiv_id == arxiv_id)
        )
        summary = summary_result.scalar_one_or_none()

        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"No summary found for {arxiv_id}"
            )

        await session.delete(summary)
        await session.commit()

        return {
            "status": "deleted",
            "message": f"Summary for {arxiv_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete summary: {str(e)}"
        )


class SaveSummaryRequest(BaseModel):
    """Request to save a summary via API."""
    arxiv_id: str
    summary_text: str
    generation_model: str = "Claude Opus 4 (remote)"
    figures: Optional[list] = None  # Optional list of figure dicts (base64-encoded PNGs + captions)


@router.get("/unsummarized/list")
async def get_unsummarized_papers(
    limit: int = 50,
    session: AsyncSession = Depends(get_async_session)
):
    """Get papers that don't have Opus summaries yet."""
    try:
        from sqlalchemy import text
        result = await session.execute(text("""
            SELECT p.arxiv_id, p.title, p.abstract, p.categories
            FROM papers p
            LEFT JOIN paper_summaries ps ON p.arxiv_id = ps.arxiv_id
            WHERE ps.id IS NULL
            ORDER BY p.id DESC
            LIMIT :lim
        """), {"lim": limit})

        papers = []
        for row in result:
            papers.append({
                "arxiv_id": row[0],
                "title": row[1],
                "abstract": (row[2] or "")[:500],
                "categories": row[3],
            })

        return {"papers": papers, "total": len(papers)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extract-figures/{arxiv_id}")
async def extract_paper_figures(
    arxiv_id: str,
    max_figures: int = 5,
    session: AsyncSession = Depends(get_async_session),
):
    """Extract figures from a paper PDF (arXiv or accessible publisher PDF).

    Academic indexing / educational summarization is a standard transformative
    use; we limit to <=5 figures per paper and link to the publisher page so
    readers can access the original work. Paywalled publisher PDFs typically
    block automated downloads, so this mostly returns figures for arXiv +
    open-access sources.
    """
    try:
        from ..services.figure_extractor import extract_figures

        pdf_url = None
        if not (arxiv_id[:1].isdigit() and "." in arxiv_id):
            # Non-arXiv source (hai:NNN, openalex:Wxxx). Use stored pdf_url
            # from the paper row, if any.
            paper_row = await session.execute(
                select(Paper).where(Paper.arxiv_id == arxiv_id)
            )
            paper = paper_row.scalar_one_or_none()
            if not paper or not paper.pdf_url:
                return {"arxiv_id": arxiv_id, "figure_count": 0, "figures": []}
            pdf_url = paper.pdf_url

        figures = extract_figures(arxiv_id, max_figures=max_figures, pdf_url=pdf_url)
        return {
            "arxiv_id": arxiv_id,
            "figure_count": len(figures),
            "figures": figures,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_summary(
    req: SaveSummaryRequest,
    session: AsyncSession = Depends(get_async_session),
    _admin: None = Depends(require_admin),
):
    """Save a summary for a paper (used by remote agents)."""
    try:
        paper_result = await session.execute(
            select(Paper).where(Paper.arxiv_id == req.arxiv_id)
        )
        paper = paper_result.scalar_one_or_none()
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper {req.arxiv_id} not found")

        word_count = len(req.summary_text.split())

        existing_result = await session.execute(
            select(PaperSummary).where(PaperSummary.arxiv_id == req.arxiv_id)
        )
        existing = existing_result.scalar_one_or_none()

        figures = req.figures or []
        figure_count = len(figures)

        if existing:
            existing.summary_text = req.summary_text
            existing.summary_type = "comprehensive"
            existing.generation_model = req.generation_model
            existing.word_count = word_count
            if figures:
                existing.figures = figures
                existing.figure_count = figure_count
            await session.commit()
            return {
                "status": "updated",
                "arxiv_id": req.arxiv_id,
                "word_count": word_count,
                "figure_count": figure_count,
            }
        else:
            summary = PaperSummary(
                paper_id=paper.id,
                arxiv_id=req.arxiv_id,
                summary_text=req.summary_text,
                summary_type="comprehensive",
                generation_model=req.generation_model,
                figures=figures,
                word_count=word_count,
                figure_count=figure_count,
                has_full_text=False,
            )
            session.add(summary)
            await session.commit()
            return {
                "status": "created",
                "arxiv_id": req.arxiv_id,
                "word_count": word_count,
                "figure_count": figure_count,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_and_save_summary(arxiv_id: str, paper_id: int):
    """Background task to generate and save summary."""
    start_time = time.time()

    try:
        # Generate summary
        summary_service = get_summary_service()
        summary_data = await summary_service.generate_summary(arxiv_id)

        processing_time = int((time.time() - start_time) * 1000)

        # Save to database — get_async_session은 FastAPI Depends용 async
        # generator라 async with로 못 쓴다. 세션 팩토리를 직접 사용.
        from ..core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            # Count words
            word_count = len(summary_data["summary_text"].split()) if summary_data["summary_text"] else 0

            summary = PaperSummary(
                paper_id=paper_id,
                arxiv_id=arxiv_id,
                summary_text=summary_data["summary_text"],
                summary_type=summary_data["summary_type"],
                figures=summary_data["figures"],
                processing_time_ms=processing_time,
                word_count=word_count,
                figure_count=len(summary_data["figures"]),
                has_full_text=summary_data["summary_type"] == "comprehensive"
            )

            session.add(summary)
            await session.commit()

            print(f"✅ Summary saved for {arxiv_id} (processing time: {processing_time}ms)")

    except Exception as e:
        print(f"❌ Background summary generation failed for {arxiv_id}: {e}")
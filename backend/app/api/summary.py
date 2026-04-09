"""
Paper Summary API endpoints.
"""

import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from ..core.database import get_async_session
from ..models import Paper, PaperSummary, SummaryFeedback
from ..services.summary_service import get_summary_service

router = APIRouter(prefix="/api/summary", tags=["Summary"])


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
    session: AsyncSession = Depends(get_async_session)
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

        return {
            "status": "found",
            "summary": {
                "id": summary.id,
                "arxiv_id": summary.arxiv_id,
                "title": paper.title,
                "authors": paper.authors or [],
                "summary_text": summary.summary_text,
                "figures": summary.figures or [],
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


@router.delete("/{arxiv_id}")
async def delete_summary(
    arxiv_id: str,
    session: AsyncSession = Depends(get_async_session)
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


@router.post("/save")
async def save_summary(
    req: SaveSummaryRequest,
    session: AsyncSession = Depends(get_async_session)
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

        if existing:
            existing.summary_text = req.summary_text
            existing.summary_type = "comprehensive"
            existing.generation_model = req.generation_model
            existing.word_count = word_count
            await session.commit()
            return {"status": "updated", "arxiv_id": req.arxiv_id, "word_count": word_count}
        else:
            summary = PaperSummary(
                paper_id=paper.id,
                arxiv_id=req.arxiv_id,
                summary_text=req.summary_text,
                summary_type="comprehensive",
                generation_model=req.generation_model,
                word_count=word_count,
                figure_count=0,
                has_full_text=False,
            )
            session.add(summary)
            await session.commit()
            return {"status": "created", "arxiv_id": req.arxiv_id, "word_count": word_count}

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

        # Save to database
        async with get_async_session() as session:
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
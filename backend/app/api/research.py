"""
Research Intelligence API endpoints.
"""

import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session
from ..schemas.research import (
    ResearchAnalyzeRequest, ResearchAnalyzeResponse,
    CompareRequest, CompareResponse,
    ResearchQuestionsRequest, ResearchQuestionsResponse
)
from ..services.research_service import get_research_service
from ..ai.llm_client import get_available_providers

router = APIRouter(prefix="/api/research", tags=["Research Intelligence"])


@router.post("/analyze", response_model=ResearchAnalyzeResponse)
async def analyze_research_idea(
    request: ResearchAnalyzeRequest,
    session: AsyncSession = Depends(get_async_session),
    background_tasks: BackgroundTasks = None
):
    """
    Analyze research idea and provide comprehensive recommendations.

    This is the core endpoint of the Research Intelligence Platform.
    It transforms user ideas into structured paper discovery with reasoning.
    """
    try:
        research_service = get_research_service()
        response = await research_service.analyze_research_idea(session, request)

        # Optional: Cache results in background
        if background_tasks:
            background_tasks.add_task(
                _cache_analysis_results,
                request.idea,
                response
            )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/compare", response_model=CompareResponse)
async def compare_papers(
    request: CompareRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Compare multiple papers side-by-side with AI-powered analysis.

    Provides detailed comparison across method, task, dataset, results
    with strengths/limitations analysis and recommendations.
    """
    try:
        research_service = get_research_service()
        response = await research_service.compare_papers(session, request)
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(e)}"
        )


@router.post("/questions", response_model=ResearchQuestionsResponse)
async def generate_research_questions(
    request: ResearchQuestionsRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Generate research questions from paper analysis.

    Identifies gaps, contradictions, and extension opportunities
    to guide future research directions.
    """
    try:
        research_service = get_research_service()
        response = await research_service.generate_research_questions(session, request)
        return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Question generation failed: {str(e)}"
        )


@router.get("/capabilities")
async def get_research_capabilities():
    """
    Get available research analysis capabilities.

    Returns information about available AI models and features.
    """
    available_providers = get_available_providers()

    return {
        "ai_providers": available_providers,
        "embedding_model": "BAAI/bge-m3",
        "embedding_dimension": 1024,
        "max_papers_per_analysis": 100,
        "max_papers_per_comparison": 10,
        "supported_question_types": [
            "gap", "contradiction", "extension", "application", "methodology"
        ],
        "analysis_goals": ["novelty", "survey", "implementation"],
        "features": [
            "semantic_search",
            "hybrid_search",
            "explanation_generation",
            "research_gap_analysis",
            "trend_analysis",
            "paper_categorization",
            "comparative_analysis",
            "question_generation"
        ]
    }


@router.get("/status")
async def get_research_status(session: AsyncSession = Depends(get_async_session)):
    """
    Get research platform status and statistics.
    """
    try:
        # Get basic stats from database
        from sqlalchemy import select, func
        from ..models import Paper, Concept, Explanation

        paper_count = await session.scalar(select(func.count(Paper.id)))
        concept_count = await session.scalar(select(func.count(Concept.id)))
        explanation_count = await session.scalar(select(func.count(Explanation.id)))

        # Check embedding coverage
        embedded_papers = await session.scalar(
            select(func.count(Paper.id)).where(Paper.full_embedding.is_not(None))
        )

        return {
            "status": "operational",
            "database": {
                "total_papers": paper_count or 0,
                "total_concepts": concept_count or 0,
                "total_explanations": explanation_count or 0,
                "embedding_coverage": f"{embedded_papers or 0}/{paper_count or 0}"
            },
            "ai_services": {
                "providers_available": get_available_providers(),
                "embedding_service": "active"
            },
            "features": {
                "research_analysis": "active",
                "paper_comparison": "active",
                "question_generation": "active",
                "hybrid_search": "active"
            }
        }

    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "database": {"status": "unknown"},
            "ai_services": {"status": "unknown"}
        }


# Helper functions

async def _cache_analysis_results(idea: str, response: ResearchAnalyzeResponse):
    """Cache analysis results for faster retrieval."""
    # This could store results in Redis for caching
    # Implementation depends on caching strategy
    pass


@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "research_intelligence"}
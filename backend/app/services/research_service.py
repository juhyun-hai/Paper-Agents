"""
Research intelligence service - core analysis engine.
"""

import time
import asyncio
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ..models import Paper, Concept, PaperConcept, Explanation
from ..schemas.research import (
    ResearchAnalyzeRequest, ResearchAnalyzeResponse, PaperRecommendation,
    CompareRequest, CompareResponse, PaperComparison,
    ResearchQuestionsRequest, ResearchQuestionsResponse, ResearchQuestion
)
from ..ai.llm_client import get_default_client
from ..ai.prompts import ResearchPrompts, ComparisonSchema, QuestionsSchema
from .embedding_service import get_embedding_service
from ..core.config import settings


class ResearchService:
    """Core research intelligence service."""

    def __init__(self):
        self.embedding_service = get_embedding_service()

    async def analyze_research_idea(
        self,
        session: AsyncSession,
        request: ResearchAnalyzeRequest
    ) -> ResearchAnalyzeResponse:
        """Main research analysis endpoint."""
        start_time = time.time()

        # Step 1: Generate query embedding and search papers
        papers_with_scores = await self._search_relevant_papers(
            session, request.idea, limit=100
        )

        if not papers_with_scores:
            return ResearchAnalyzeResponse(
                query=request.idea,
                goal=request.goal,
                core_papers=[],
                method_neighbors=[],
                task_neighbors=[],
                recent_trends=[],
                gap_candidates=[],
                contrasting_papers=[],
                key_insights=["No relevant papers found"],
                research_gaps=["Insufficient data to identify gaps"],
                recommended_direction="Explore foundational literature in related areas",
                total_papers_found=0,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

        # Step 2: Categorize papers using LLM
        categorized_papers = await self._categorize_papers(
            request.idea, papers_with_scores
        )

        # Step 3: Generate explanations for top papers
        explained_papers = await self._generate_paper_explanations(
            request.idea, request.goal, papers_with_scores[:30]
        )

        # Step 4: Generate strategic insights
        insights = await self._generate_research_insights(
            request.idea, request.goal, papers_with_scores[:20]
        )

        # Step 5: Build response
        response = ResearchAnalyzeResponse(
            query=request.idea,
            goal=request.goal,
            **categorized_papers,
            **insights,
            total_papers_found=len(papers_with_scores),
            processing_time_ms=int((time.time() - start_time) * 1000)
        )

        return response

    async def compare_papers(
        self,
        session: AsyncSession,
        request: CompareRequest
    ) -> CompareResponse:
        """Compare multiple papers side-by-side."""

        # Get papers from database
        result = await session.execute(
            select(Paper).where(Paper.id.in_(request.paper_ids))
        )
        papers = result.scalars().all()

        if len(papers) < 2:
            raise ValueError("At least 2 papers required for comparison")

        # Prepare papers data for LLM
        papers_data = []
        for paper in papers:
            papers_data.append({
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "categories": paper.categories,
                "year": paper.year
            })

        # Generate comparison using LLM
        llm_client = await get_default_client()
        messages = ResearchPrompts.compare_papers(papers_data, request.focus_aspects)

        try:
            comparison_result = await llm_client.generate_structured(
                messages, ComparisonSchema.get_schema()
            )
        except Exception as e:
            # Fallback to text generation
            comparison_text = await llm_client.generate(messages)
            return await self._parse_comparison_fallback(
                papers_data, comparison_text, request.focus_aspects
            )

        # Build response
        response = CompareResponse(
            **comparison_result
        )
        # Set focus_aspects if not in comparison_result
        if not hasattr(response, 'focus_aspects') or response.focus_aspects is None:
            response.focus_aspects = request.focus_aspects

        return response

    async def generate_research_questions(
        self,
        session: AsyncSession,
        request: ResearchQuestionsRequest
    ) -> ResearchQuestionsResponse:
        """Generate research questions from papers."""

        # Get papers from database
        result = await session.execute(
            select(Paper).where(Paper.id.in_(request.paper_ids))
        )
        papers = result.scalars().all()

        # Prepare papers data
        papers_data = []
        for paper in papers:
            papers_data.append({
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "year": paper.year
            })

        # Generate questions using LLM
        llm_client = await get_default_client()
        messages = ResearchPrompts.generate_research_questions(
            papers_data, request.focus_area, request.question_types
        )

        try:
            questions_result = await llm_client.generate_structured(
                messages, QuestionsSchema.get_schema()
            )
        except Exception as e:
            # Fallback
            questions_text = await llm_client.generate(messages)
            return await self._parse_questions_fallback(papers_data, questions_text)

        # Add metadata
        confidence_dist = {}
        for question in questions_result.get("questions", []):
            conf_level = "high" if question.get("confidence", 0) > 0.7 else "medium" if question.get("confidence", 0) > 0.4 else "low"
            confidence_dist[conf_level] = confidence_dist.get(conf_level, 0) + 1

        response = ResearchQuestionsResponse(
            **questions_result,
            papers_analyzed=len(papers),
            confidence_distribution=confidence_dist
        )

        return response

    # Helper methods

    async def _search_relevant_papers(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 50
    ) -> List[Tuple[Paper, float]]:
        """Search for relevant papers using hybrid search."""
        return await self.embedding_service.search_papers_hybrid(
            session, query, limit=limit
        )

    async def _categorize_papers(
        self,
        user_idea: str,
        papers_with_scores: List[Tuple[Paper, float]]
    ) -> Dict[str, List[PaperRecommendation]]:
        """Categorize papers into different types using LLM."""

        # Prepare papers for LLM
        papers_data = []
        for paper, score in papers_with_scores[:30]:  # Limit for LLM context
            papers_data.append({
                "title": paper.title,
                "similarity_score": score,
                "abstract": paper.abstract[:200] + "..." if paper.abstract else ""
            })

        try:
            llm_client = await get_default_client()
            messages = ResearchPrompts.categorize_papers(user_idea, papers_data)
            categorization_text = await llm_client.generate(messages)

            # Parse categorization (simple parsing for now)
            categories = {
                "core_papers": [],
                "method_neighbors": [],
                "task_neighbors": [],
                "recent_trends": [],
                "gap_candidates": [],
                "contrasting_papers": []
            }

            # Simple category assignment based on scores and recency
            for paper, score in papers_with_scores:
                paper_rec = PaperRecommendation(
                    id=paper.id,  # Add database ID
                    arxiv_id=paper.arxiv_id,
                    title=paper.title,
                    authors=paper.authors,
                    abstract=paper.abstract or "",
                    categories=paper.categories,
                    date=paper.published_date.isoformat() if paper.published_date else "",
                    venue=paper.venue,
                    citation_count=paper.citation_count,
                    similarity_score=score,
                    relevance_score=score,
                    relevance_reason=f"Similarity score: {score:.3f}"
                )

                # Simple categorization logic (can be improved with LLM parsing)
                if score > 0.8:
                    categories["core_papers"].append(paper_rec)
                elif score > 0.6:
                    if paper.year and paper.year >= 2023:
                        categories["recent_trends"].append(paper_rec)
                    else:
                        categories["method_neighbors"].append(paper_rec)
                else:
                    categories["gap_candidates"].append(paper_rec)

                # Limit per category
                if len(categories["core_papers"]) >= 10:
                    break

            return categories

        except Exception as e:
            # Fallback categorization
            return await self._fallback_categorization(papers_with_scores)

    async def _generate_paper_explanations(
        self,
        user_idea: str,
        goal: str,
        papers_with_scores: List[Tuple[Paper, float]]
    ) -> Dict[str, Any]:
        """Generate explanations for paper relevance."""

        explanations = {}

        # Generate explanations for top papers
        for paper, score in papers_with_scores[:10]:
            try:
                llm_client = await get_default_client()
                messages = ResearchPrompts.explain_paper_relevance(
                    user_idea, paper.title, paper.abstract or "", score
                )
                explanation = await llm_client.generate(messages, temperature=0.3)
                explanations[paper.arxiv_id] = explanation
            except Exception:
                explanations[paper.arxiv_id] = f"High similarity score: {score:.3f}"

        return explanations

    async def _generate_research_insights(
        self,
        user_idea: str,
        goal: str,
        papers_with_scores: List[Tuple[Paper, float]]
    ) -> Dict[str, Any]:
        """Generate strategic research insights."""

        papers_context = []
        for paper, score in papers_with_scores[:15]:
            papers_context.append({
                "title": paper.title,
                "abstract": paper.abstract or "",
                "score": score
            })

        try:
            llm_client = await get_default_client()
            messages = ResearchPrompts.analyze_research_direction(
                user_idea, goal, papers_context
            )
            insights_text = await llm_client.generate(messages)

            # Parse insights (simplified)
            return {
                "key_insights": [insights_text[:200] + "..."],
                "research_gaps": ["Advanced analysis requires more detailed review"],
                "recommended_direction": "Focus on high-similarity papers for implementation guidance"
            }

        except Exception:
            return {
                "key_insights": ["Found relevant literature in the field"],
                "research_gaps": ["Analysis pending"],
                "recommended_direction": "Review top papers for detailed insights"
            }

    async def _fallback_categorization(
        self,
        papers_with_scores: List[Tuple[Paper, float]]
    ) -> Dict[str, List[PaperRecommendation]]:
        """Fallback categorization without LLM."""

        categories = {
            "core_papers": [],
            "method_neighbors": [],
            "task_neighbors": [],
            "recent_trends": [],
            "gap_candidates": [],
            "contrasting_papers": []
        }

        for paper, score in papers_with_scores[:30]:
            paper_rec = PaperRecommendation(
                id=paper.id,  # Add database ID
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                authors=paper.authors,
                abstract=paper.abstract or "",
                categories=paper.categories,
                date=paper.published_date.isoformat() if paper.published_date else "",
                venue=paper.venue,
                citation_count=paper.citation_count,
                similarity_score=score,
                relevance_score=score,
                relevance_reason=f"Similarity: {score:.3f}"
            )

            if score > 0.8:
                categories["core_papers"].append(paper_rec)
            elif score > 0.6:
                categories["method_neighbors"].append(paper_rec)
            else:
                categories["gap_candidates"].append(paper_rec)

        return categories

    async def _parse_comparison_fallback(
        self,
        papers_data: List[Dict[str, Any]],
        comparison_text: str,
        focus_aspects: List[str]
    ) -> CompareResponse:
        """Fallback comparison parsing."""
        # Simplified fallback
        comparison = []
        for paper in papers_data:
            comparison.append(PaperComparison(
                arxiv_id=paper["arxiv_id"],
                title=paper["title"],
                authors=paper["authors"],
                strengths=["Analysis pending"],
                limitations=["Analysis pending"],
                novelty_aspects=["Analysis pending"],
                relevance_to_user="Analysis pending",
                priority="medium"
            ))

        return CompareResponse(
            comparison=comparison,
            common_themes=["Analysis pending"],
            key_differences=["Analysis pending"],
            complementary_aspects=["Analysis pending"],
            conflicting_findings=[],
            comparison_matrix={},
            focus_aspects=focus_aspects
        )

    async def _parse_questions_fallback(
        self,
        papers_data: List[Dict[str, Any]],
        questions_text: str
    ) -> ResearchQuestionsResponse:
        """Fallback questions parsing."""
        return ResearchQuestionsResponse(
            questions=[
                ResearchQuestion(
                    question="What are the key limitations in current approaches?",
                    type="gap",
                    confidence=0.7,
                    novelty_score=0.6,
                    difficulty="medium",
                    evidence="Based on paper analysis",
                    related_papers=[p["title"] for p in papers_data[:3]],
                    suggested_approaches=["Systematic review", "Empirical analysis"],
                    potential_impact="Medium impact on field understanding"
                )
            ],
            most_promising_direction="Further analysis needed",
            research_landscape_summary="Multiple approaches identified",
            knowledge_gaps_identified=["Analysis pending"],
            papers_analyzed=len(papers_data),
            confidence_distribution={"medium": 1}
        )


# Global service instance
_research_service = None


def get_research_service() -> ResearchService:
    """Get global research service instance."""
    global _research_service
    if _research_service is None:
        _research_service = ResearchService()
    return _research_service
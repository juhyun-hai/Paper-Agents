"""
Research Intelligence API schemas.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class ResearchAnalyzeRequest(BaseModel):
    """Request for research analysis."""

    idea: str = Field(..., description="Research idea description")
    task: Optional[str] = Field(None, description="Specific task")
    method: Optional[str] = Field(None, description="Preferred method")
    constraints: Optional[str] = Field(None, description="Constraints or requirements")
    exclude: Optional[str] = Field(None, description="What to exclude")
    goal: Literal["novelty", "survey", "implementation"] = Field("novelty", description="Analysis goal")


class PaperRecommendation(BaseModel):
    """Individual paper recommendation."""

    id: Optional[int] = None  # Database ID for frontend compatibility
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    date: str
    venue: Optional[str] = None
    citation_count: int = 0
    similarity_score: float
    relevance_score: float
    novelty_score: Optional[float] = None

    # Explanation fields
    relevance_reason: str
    method_similarity: Optional[str] = None
    task_similarity: Optional[str] = None
    gap_analysis: Optional[str] = None
    trend_analysis: Optional[str] = None


class ResearchAnalyzeResponse(BaseModel):
    """Response for research analysis."""

    query: str
    goal: str

    # Categorized recommendations
    core_papers: List[PaperRecommendation]
    method_neighbors: List[PaperRecommendation]
    task_neighbors: List[PaperRecommendation]
    recent_trends: List[PaperRecommendation]
    gap_candidates: List[PaperRecommendation]
    contrasting_papers: List[PaperRecommendation]

    # Analysis summary
    key_insights: List[str]
    research_gaps: List[str]
    recommended_direction: str

    # Metadata
    total_papers_found: int
    processing_time_ms: int


class CompareRequest(BaseModel):
    """Request for paper comparison."""

    paper_ids: List[int] = Field(..., min_length=2, max_length=10, description="Paper IDs to compare")
    focus_aspects: List[str] = Field(
        default=["method", "task", "dataset", "results"],
        description="Aspects to focus comparison on"
    )


class PaperComparison(BaseModel):
    """Individual paper in comparison."""

    arxiv_id: str
    title: str
    authors: List[str]

    # Comparison aspects
    task: Optional[str] = None
    method: Optional[str] = None
    dataset: Optional[str] = None
    metric: Optional[str] = None
    key_results: Optional[str] = None

    # Analysis
    strengths: List[str]
    limitations: List[str]
    novelty_aspects: List[str]
    relevance_to_user: str
    priority: Literal["high", "medium", "low"]


class CompareResponse(BaseModel):
    """Response for paper comparison."""

    comparison: List[PaperComparison]

    # Cross-paper analysis
    common_themes: List[str]
    key_differences: List[str]
    complementary_aspects: List[str]
    conflicting_findings: List[str]

    # Recommendations
    best_for_implementation: Optional[str] = None
    best_for_theoretical_foundation: Optional[str] = None
    most_recent_approach: Optional[str] = None

    # Metadata
    comparison_matrix: Dict[str, Dict[str, str]]
    focus_aspects: List[str]


class ResearchQuestionsRequest(BaseModel):
    """Request for research questions generation."""

    paper_ids: List[int] = Field(..., min_length=1, description="Paper IDs to analyze")
    focus_area: Optional[str] = Field(None, description="Specific focus area")
    question_types: List[Literal["gap", "contradiction", "extension", "application", "methodology"]] = Field(
        default=["gap", "extension", "methodology"],
        description="Types of questions to generate"
    )


class ResearchQuestion(BaseModel):
    """Individual research question."""

    question: str
    type: Literal["gap", "contradiction", "extension", "application", "methodology"]
    confidence: float = Field(..., ge=0, le=1, description="Confidence in the question")
    novelty_score: float = Field(..., ge=0, le=1, description="Expected novelty if pursued")
    difficulty: Literal["low", "medium", "high"]

    # Supporting evidence
    evidence: str
    related_papers: List[str]
    suggested_approaches: List[str]
    potential_impact: str


class ResearchQuestionsResponse(BaseModel):
    """Response for research questions."""

    questions: List[ResearchQuestion]

    # Meta-analysis
    most_promising_direction: str
    research_landscape_summary: str
    knowledge_gaps_identified: List[str]

    # Metadata
    papers_analyzed: int
    confidence_distribution: Dict[str, int]
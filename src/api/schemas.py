from pydantic import BaseModel
from typing import List, Optional, Any


class PaperOut(BaseModel):
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: Optional[str] = ""
    categories: List[str]
    date: Optional[str] = ""
    pdf_url: Optional[str] = ""
    citation_count: Optional[int] = 0
    venue: Optional[str] = ""
    status: Optional[str] = "unread"
    rating: Optional[int] = None
    similarity_score: Optional[float] = None


class SearchResult(BaseModel):
    papers: List[PaperOut]
    total: int
    query: str
    highlights: Optional[dict] = None


class GraphNode(BaseModel):
    id: str
    title: str
    category: str
    citation_count: int
    date: Optional[str] = ""
    venue: Optional[str] = ""
    x: Optional[float] = None
    y: Optional[float] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float
    type: str  # "similar", "same_author", "same_keyword"


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class StatsOut(BaseModel):
    total_papers: int
    category_stats: dict
    recent_count: int
    top_venues: List[dict]
    top_papers: List[PaperOut]

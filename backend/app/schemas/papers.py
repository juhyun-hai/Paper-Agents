"""
Paper API schemas for basic search functionality.
"""

from typing import List, Optional
from pydantic import BaseModel


class PaperResponse(BaseModel):
    """Individual paper response."""

    id: int
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    published_date: str
    venue: Optional[str] = None
    citation_count: int = 0
    year: Optional[int] = None


class PapersSearchResponse(BaseModel):
    """Search response containing papers and metadata."""

    papers: List[PaperResponse]
    total: int
    query: str
    limit: int
    offset: int
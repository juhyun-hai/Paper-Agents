"""
Trending papers model for tracking daily trending papers.
"""

from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Text, JSON
from datetime import date, datetime

from .base import Base

class TrendingPaper(Base):
    """Model for tracking trending papers daily."""
    __tablename__ = 'trending_papers'

    id = Column(Integer, primary_key=True)
    arxiv_id = Column(String(50), nullable=False)
    title = Column(String(500))
    trending_score = Column(Float)
    final_score = Column(Float)
    rank = Column(Integer)
    sources = Column(String(200))  # comma-separated source names
    source_details = Column(JSON)  # detailed info from each source
    multi_source_bonus = Column(Float, default=0.0)
    date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TrendingPaper {self.arxiv_id}: {self.title[:50]}... (rank {self.rank})>"
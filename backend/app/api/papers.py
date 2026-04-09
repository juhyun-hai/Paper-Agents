"""
Paper search and retrieval API endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, String
from sqlalchemy.orm import selectinload

from ..core.database import get_async_session
from ..models import Paper, PaperSummary
from ..schemas.papers import PaperResponse, PapersSearchResponse

router = APIRouter(prefix="/api", tags=["Papers"])


@router.get("/search", response_model=PapersSearchResponse)
async def search_papers(
    q: str = Query("", description="Search query"),
    limit: int = Query(10, le=100, description="Number of results per page"),
    offset: int = Query(0, description="Number of results to skip"),
    category: Optional[str] = Query(None, description="Filter by categories (comma-separated)"),
    sort: str = Query("relevance", description="Sort by: relevance, date, citations"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Search papers with filtering and sorting options.

    This endpoint provides the classic paper search functionality
    that works with keyword matching, category filtering, and sorting.
    """
    try:
        # Build base query
        query = select(Paper)
        count_query = select(func.count(Paper.id))

        # Add search conditions
        conditions = []

        # Text search in title and abstract (each word must match)
        if q.strip():
            words = q.strip().split()
            for word in words:
                term = f"%{word}%"
                conditions.append(or_(
                    Paper.title.ilike(term),
                    Paper.abstract.ilike(term)
                ))

        # Category filter - simplified approach
        if category:
            categories = [cat.strip() for cat in category.split(",") if cat.strip()]
            if categories:
                # Use simple text matching on category array as string
                category_conditions = []
                for cat in categories:
                    # Cast array to text and search
                    category_conditions.append(
                        func.cast(Paper.categories, String).like(f'%{cat}%')
                    )
                if category_conditions:
                    conditions.append(or_(*category_conditions))

        # Date filters
        if date_from:
            try:
                from datetime import datetime
                date_obj = datetime.fromisoformat(date_from)
                conditions.append(Paper.published_date >= date_obj)
            except ValueError:
                pass

        if date_to:
            try:
                from datetime import datetime
                date_obj = datetime.fromisoformat(date_to)
                conditions.append(Paper.published_date <= date_obj)
            except ValueError:
                pass

        # Apply conditions
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Sorting
        if sort == "date":
            query = query.order_by(Paper.published_date.desc())
        elif sort == "citations":
            query = query.order_by(Paper.citation_count.desc())
        else:  # relevance (default)
            if q.strip():
                # Simple relevance: title matches first, then abstract
                query = query.order_by(
                    Paper.title.ilike(f"%{q.strip()}%").desc(),
                    Paper.published_date.desc()
                )
            else:
                query = query.order_by(Paper.published_date.desc())

        # Pagination
        query = query.offset(offset).limit(limit)

        # Execute queries
        papers_result = await session.execute(query)
        papers = papers_result.scalars().all()

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Convert to response format
        paper_responses = []
        for paper in papers:
            paper_responses.append(PaperResponse(
                id=paper.id,
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                authors=paper.authors or [],
                abstract=paper.abstract or "",
                categories=paper.categories or [],
                published_date=paper.published_date.isoformat() if paper.published_date else "",
                venue=paper.venue,
                citation_count=paper.citation_count or 0,
                year=paper.year
            ))

        return PapersSearchResponse(
            papers=paper_responses,
            total=total,
            query=q,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/papers/{arxiv_id}")
async def get_paper(
    arxiv_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific paper by arXiv ID with summary."""
    try:
        # Get paper
        paper_result = await session.execute(
            select(Paper).where(Paper.arxiv_id == arxiv_id)
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=404,
                detail=f"Paper with arXiv ID {arxiv_id} not found"
            )

        # Get summary
        summary_result = await session.execute(
            select(PaperSummary)
            .where(PaperSummary.arxiv_id == arxiv_id)
            .order_by(PaperSummary.created_at.desc())
            .limit(1)
        )
        summary = summary_result.scalar_one_or_none()

        # Build response
        response = {
            "id": paper.id,
            "arxiv_id": paper.arxiv_id,
            "title": paper.title,
            "authors": paper.authors or [],
            "abstract": paper.abstract or "",
            "categories": paper.categories or [],
            "published_date": paper.published_date.isoformat() if paper.published_date else "",
            "venue": paper.venue,
            "citation_count": paper.citation_count or 0,
            "year": paper.year
        }

        # Add summary if available
        if summary:
            response["summary"] = {
                "summary_text": summary.summary_text,
                "summary_type": summary.summary_type,
                "generation_model": summary.generation_model,
                "word_count": summary.word_count,
                "figures": summary.figures or [],
                "figure_count": summary.figure_count,
                "has_full_text": summary.has_full_text,
                "generated_at": summary.generated_at.isoformat() if summary.generated_at else None
            }
        else:
            response["summary"] = None

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve paper: {str(e)}"
        )


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query("", description="Query for autocomplete"),
    session: AsyncSession = Depends(get_async_session)
):
    """Provide autocomplete suggestions based on paper titles."""
    if not q.strip() or len(q.strip()) < 2:
        return {"suggestions": []}

    try:
        # Get distinct title words that match the query
        search_term = f"%{q.strip()}%"

        result = await session.execute(
            select(Paper.title)
            .where(Paper.title.ilike(search_term))
            .limit(10)
        )

        titles = result.scalars().all()

        # Extract relevant keywords
        suggestions = []
        query_lower = q.strip().lower()

        for title in titles:
            if title:
                words = title.lower().split()
                for word in words:
                    if (query_lower in word and
                        len(word) > 2 and
                        word not in suggestions):
                        suggestions.append(word)
                        if len(suggestions) >= 10:
                            break
                if len(suggestions) >= 10:
                    break

        return {"suggestions": suggestions[:10]}

    except Exception as e:
        return {"suggestions": []}


@router.get("/recommend/{arxiv_id}")
async def get_recommendations(
    arxiv_id: str,
    limit: int = Query(10, description="Number of recommendations"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get paper recommendations based on similarity."""
    try:
        # Get the target paper
        result = await session.execute(
            select(Paper).where(Paper.arxiv_id == arxiv_id)
        )
        target_paper = result.scalar_one_or_none()

        if not target_paper:
            raise HTTPException(
                status_code=404,
                detail=f"Paper with arXiv ID {arxiv_id} not found"
            )

        # Get similar papers using embedding service
        from ..services.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()

        # Search for similar papers
        similar_papers = await embedding_service.search_papers_hybrid(
            session,
            target_paper.title + " " + (target_paper.abstract or "")[:200],
            limit=limit + 1  # +1 to exclude the paper itself
        )

        # Filter out the target paper and convert to response format
        recommendations = []
        for paper, score in similar_papers:
            if paper.arxiv_id != arxiv_id:  # Exclude the target paper
                recommendations.append(PaperResponse(
                    id=paper.id,
                    arxiv_id=paper.arxiv_id,
                    title=paper.title,
                    authors=paper.authors or [],
                    abstract=paper.abstract or "",
                    categories=paper.categories or [],
                    published_date=paper.published_date.isoformat() if paper.published_date else "",
                    venue=paper.venue,
                    citation_count=paper.citation_count or 0,
                    year=paper.year
                ))
                if len(recommendations) >= limit:
                    break

        return {
            "recommendations": recommendations,
            "total": len(recommendations),
            "target_paper": arxiv_id
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "recommendations": [],
            "total": 0,
            "target_paper": arxiv_id,
            "error": str(e)
        }


@router.get("/graph/mini/{arxiv_id}")
async def get_mini_graph(
    arxiv_id: str,
    depth: int = Query(1, description="Graph depth"),
    max_nodes: int = Query(10, description="Maximum nodes"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get mini knowledge graph around a paper."""
    try:
        # Get the target paper
        result = await session.execute(
            select(Paper).where(Paper.arxiv_id == arxiv_id)
        )
        target_paper = result.scalar_one_or_none()

        if not target_paper:
            raise HTTPException(
                status_code=404,
                detail=f"Paper with arXiv ID {arxiv_id} not found"
            )

        # Get similar papers as graph nodes
        from ..services.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()

        similar_papers = await embedding_service.search_papers_hybrid(
            session,
            target_paper.title + " " + (target_paper.abstract or "")[:100],
            limit=max_nodes
        )

        # Build mini graph structure
        nodes = []
        edges = []

        # Add center node
        center_cats = target_paper.categories or []
        if isinstance(center_cats, str):
            import json as _json
            try: center_cats = _json.loads(center_cats)
            except: center_cats = []
        nodes.append({
            "id": target_paper.arxiv_id,
            "label": target_paper.title,
            "type": "paper",
            "group": "center",
            "categories": center_cats,
            "properties": {
                "authors": target_paper.authors or [],
                "categories": center_cats
            }
        })

        # Add similar nodes and edges
        for paper, score in similar_papers[:max_nodes-1]:
            if paper.arxiv_id != arxiv_id:
                sim_cats = paper.categories or []
                if isinstance(sim_cats, str):
                    import json as _json
                    try: sim_cats = _json.loads(sim_cats)
                    except: sim_cats = []
                nodes.append({
                    "id": paper.arxiv_id,
                    "label": paper.title,
                    "type": "paper",
                    "group": "similar",
                    "categories": sim_cats,
                    "properties": {
                        "authors": paper.authors or [],
                        "categories": sim_cats,
                        "similarity": score
                    }
                })

                edges.append({
                    "source": target_paper.arxiv_id,
                    "target": paper.arxiv_id,
                    "type": "similar",
                    "weight": score,
                    "properties": {"similarity": score}
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "center": target_paper.arxiv_id,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "nodes": [],
            "edges": [],
            "center": arxiv_id,
            "total_nodes": 0,
            "total_edges": 0,
            "error": str(e)
        }


@router.get("/categories")
async def get_categories(session: AsyncSession = Depends(get_async_session)):
    """Get all available paper categories."""
    try:
        # Get unique categories
        result = await session.execute(
            select(func.unnest(Paper.categories).label('category'))
            .distinct()
        )

        categories = [row[0] for row in result.all() if row[0]]
        categories.sort()

        return {"categories": categories}

    except Exception as e:
        return {"categories": []}


@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_async_session)):
    """Get platform statistics."""
    try:
        # Total papers
        total_result = await session.execute(
            select(func.count(Paper.id))
        )
        total_papers = total_result.scalar() or 0

        # Recent papers (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)

        recent_result = await session.execute(
            select(func.count(Paper.id))
            .where(Paper.published_date >= thirty_days_ago)
        )
        recent_papers = recent_result.scalar() or 0

        return {
            "total_papers": total_papers,
            "recent_papers": recent_papers,
            "categories_count": 0,  # Would need to compute
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "total_papers": 0,
            "recent_papers": 0,
            "categories_count": 0,
            "last_updated": datetime.now().isoformat()
        }


@router.get("/trends")
async def get_trending_papers(
    days: int = Query(30, description="Days to look back for trending"),
    limit: int = Query(20, description="Number of trending papers"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get trending papers based on various metrics."""
    try:
        from datetime import datetime
        # Simple trending: most recent papers with good scores
        result = await session.execute(
            select(Paper)
            .where(Paper.published_date.is_not(None))
            .order_by(
                Paper.published_date.desc(),
                Paper.citation_count.desc(),
                Paper.id.desc()
            )
            .limit(limit)
        )

        trending_papers = result.scalars().all()

        # Convert to response format with trending score
        papers_response = []
        for i, paper in enumerate(trending_papers):
            # Simple trending score based on recency and citations
            trending_score = 1.0 - (i * 0.05)  # Decreasing score by rank
            trending_score = max(0.1, trending_score)  # Minimum score

            papers_response.append({
                "id": paper.id,
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors or [],
                "abstract": (paper.abstract or "")[:200] + ("..." if len(paper.abstract or "") > 200 else ""),
                "categories": paper.categories or [],
                "published_date": paper.published_date.isoformat() if paper.published_date else "",
                "venue": paper.venue,
                "citation_count": paper.citation_count or 0,
                "year": paper.year,
                "trending_score": round(trending_score, 3),
                "rank": i + 1
            })

        return {
            "trending_papers": papers_response,
            "total": len(papers_response),
            "period_days": days,
            "algorithm": "recency_based",
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "trending_papers": [],
            "total": 0,
            "period_days": days,
            "error": str(e),
            "last_updated": datetime.now().isoformat()
        }
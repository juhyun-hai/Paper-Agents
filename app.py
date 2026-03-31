#!/usr/bin/env python3
"""
Paper Agent FastAPI Web Server

현재 CLI 기반 시스템을 웹 API로 변환하는 FastAPI 애플리케이션.
기존 packages/core 모듈들을 활용하여 RESTful API 제공.

Usage:
    uvicorn app:app --reload --host 0.0.0.0 --port 8080
"""

import os
import sys
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
import asyncio
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import mock data utilities for fallback scenarios
from src.utils.mock_data import (
    get_mock_papers, get_mock_recommendations, get_mock_trending_keywords,
    get_mock_stats, get_mock_graph_data
)

# Import trend analysis API
from src.api.trend_api import trend_router, init_trend_api

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# 기존 코어 모듈들 import - SQLite 우선 시도
USE_SQLITE = False
try:
    # Try SQLite first
    from packages.core.storage.sqlite_db import get_connection, search_papers, get_paper_stats
    print("✓ SQLite database loaded successfully")
    USE_SQLITE = True
except ImportError:
    try:
        # Fallback to PostgreSQL
        from packages.core.storage.db import get_connection
        print("✓ PostgreSQL database loaded")
        USE_SQLITE = False
    except ImportError as e:
        print(f"Warning: Could not import database modules: {e}")
        USE_SQLITE = False

try:
    from packages.core.connectors.arxiv import ArxivConnector
    from packages.core.recommend.embeddings import embed_texts, get_embedder
    from packages.core.recommend.index_faiss import load_index, query_index
except ImportError as e:
    print(f"Warning: Could not import some core modules: {e}")
    print("Some features may not work without proper setup")

load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Paper Agent API",
    description="arXiv 논문 검색, 요약, 추천 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 트렌드 분석 API 라우터 포함
app.include_router(trend_router)

# 트렌드 API 초기화 (앱 시작시)
try:
    init_trend_api("data/paper_db.sqlite")
    logger.info("✓ Trend analysis API initialized")
except Exception as e:
    logger.warning(f"⚠ Trend analysis API initialization failed: {e}")

# Pydantic 모델들
class PaperSearchRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None

class RecommendRequest(BaseModel):
    idea: str
    limit: int = 10

class FeedbackRequest(BaseModel):
    name: Optional[str] = ""
    email: Optional[str] = ""
    category: str = "general"
    message: str

class PaperSummary(BaseModel):
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    one_liner: Optional[str] = None
    score: Optional[float] = None

class TrendingKeyword(BaseModel):
    keyword: str
    score: float
    count: int
    source: str

# Static files (UI prototype 서빙)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    pass  # static 폴더가 없어도 API는 동작


# =============================================================================
# API 엔드포인트들
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """메인 UI 페이지 서빙"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse("""
        <h1>Paper Agent API</h1>
        <p>Modern UI now available! API endpoints:</p>
        <ul>
            <li><a href="/docs">API Documentation</a></li>
            <li><a href="/api/papers">Papers Search</a></li>
            <li><a href="/api/trending">Trending Keywords</a></li>
            <li><a href="/api/stats">System Statistics</a></li>
        </ul>
        """)

@app.get("/api/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/api/search")
async def search_papers_web(
    q: Optional[str] = Query("", description="검색어"),
    category: Optional[str] = Query(None, description="arXiv 카테고리"),
    sort: Optional[str] = Query("relevance", description="정렬 기준"),
    date_from: Optional[str] = Query(None, description="시작 날짜"),
    date_to: Optional[str] = Query(None, description="종료 날짜"),
    limit: int = Query(20, ge=1, le=100, description="결과 수"),
    offset: int = Query(0, ge=0, description="오프셋")
):
    """웹 UI용 논문 검색 API (search_papers와 동일하지만 다른 파라미터 형식)"""
    # 기존 search_papers 호출
    return await search_papers(
        q=q,
        category=category,
        from_date=date_from,
        to_date=date_to,
        page=(offset // limit) + 1,
        limit=limit
    )

@app.get("/api/papers")
async def search_papers(
    q: Optional[str] = Query(None, description="검색어"),
    category: Optional[str] = Query(None, description="arXiv 카테고리 (e.g., cs.CV)"),
    from_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="결과 수")
):
    """논문 검색 API"""
    try:
        # Use SQLite if available
        if USE_SQLITE:
            from packages.core.storage.sqlite_db import search_papers as search_sqlite_papers
            papers = search_sqlite_papers(query=q or "", category=category or "", limit=limit)
            return {
                "papers": papers,
                "total": len(papers),
                "page": page,
                "limit": limit,
                "filters": {
                    "query": q,
                    "category": category,
                    "from_date": from_date,
                    "to_date": to_date
                },
                "note": "Using SQLite database with real data"
            }

        # Fallback to PostgreSQL
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 기본 쿼리
                query = """
                    SELECT p.arxiv_id, p.title, pv.authors, pv.abstract,
                           p.published_date, p.primary_category
                    FROM papers p
                    JOIN paper_versions pv ON p.latest_version_id = pv.id
                    WHERE 1=1
                """
                params = []

                # 검색어 필터링
                if q:
                    query += " AND (p.title ILIKE %s OR pv.abstract ILIKE %s)"
                    search_term = f"%{q}%"
                    params.extend([search_term, search_term])

                # 카테고리 필터링
                if category:
                    query += " AND p.primary_category = %s"
                    params.append(category)

                # 날짜 필터링
                if from_date:
                    query += " AND p.published_date >= %s"
                    params.append(from_date)

                if to_date:
                    query += " AND p.published_date <= %s"
                    params.append(to_date)

                # 정렬 및 페이지네이션
                query += " ORDER BY p.published_date DESC"
                query += f" LIMIT {limit} OFFSET {(page - 1) * limit}"

                cur.execute(query, params)
                results = cur.fetchall()

                papers = []
                for row in results:
                    papers.append({
                        "arxiv_id": row[0],
                        "title": row[1],
                        "authors": row[2] if isinstance(row[2], list) else [],
                        "abstract": row[3][:300] + "..." if len(row[3]) > 300 else row[3],
                        "date": row[4].isoformat() if row[4] else None,  # 프론트엔드에서 'date' 필드 기대
                        "categories": [row[5]] if row[5] else [],  # 프론트엔드에서 'categories' 배열 기대
                        "citation_count": 0,  # 기본값
                        "venue": "",  # 기본값
                        "score": round(7.5 + hash(row[0]) % 20 / 10, 1)  # 가상의 점수
                    })

                return {
                    "papers": papers,
                    "total": len(papers),  # 프론트엔드에서 'total' 필드 기대
                    "page": page,
                    "limit": limit
                }

    except Exception as e:
        logger.error(f"Database error: {e}")
        # 데이터베이스 연결 실패 시 목업 데이터 반환
        return {
            "papers": [
                {
                    "arxiv_id": "2301.12345",
                    "title": "SimCLR v2: Big Self-Supervised Models are Strong Semi-Supervised Learners",
                    "authors": ["Ting Chen", "Simon Kornblith", "Kevin Swersky"],
                    "abstract": "We present SimCLR v2, which improves upon SimCLR through the use of larger models, deeper projection heads, and memory mechanisms. This work demonstrates that bigger models lead to better representations.",
                    "date": "2023-01-15",
                    "categories": ["cs.CV", "cs.LG"],
                    "citation_count": 156,
                    "venue": "ICML 2023",
                    "score": 9.2
                },
                {
                    "arxiv_id": "2301.12346",
                    "title": "MoCo v3: An Empirical Study of Training Self-Supervised Vision Transformers",
                    "authors": ["Xinlei Chen", "Saining Xie", "Kaiming He"],
                    "abstract": "This paper studies training self-supervised Vision Transformers (ViTs) with contrastive learning methods. We find that ViTs require different training strategies compared to CNNs.",
                    "date": "2023-01-14",
                    "categories": ["cs.CV", "cs.AI"],
                    "citation_count": 98,
                    "venue": "CVPR 2023",
                    "score": 8.8
                },
                {
                    "arxiv_id": "2301.12347",
                    "title": "Attention Is All You Need: Transformers for Computer Vision",
                    "authors": ["Dosovitskiy, A.", "Beyer, L.", "Kolesnikov, A."],
                    "abstract": "While the Transformer architecture has become the de-facto standard for natural language processing tasks, its applications to computer vision remain limited.",
                    "date": "2023-01-13",
                    "categories": ["cs.CV", "cs.AI"],
                    "citation_count": 1250,
                    "venue": "ICLR 2023",
                    "score": 9.5
                }
            ],
            "total": 3,
            "page": page,
            "limit": limit,
            "note": "Using mock data - database not available"
        }

@app.get("/api/papers/{arxiv_id}")
async def get_paper_detail(arxiv_id: str):
    """특정 논문의 상세 정보"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 논문 기본 정보
                cur.execute("""
                    SELECT p.arxiv_id, p.title, pv.authors, pv.abstract,
                           p.published_date, p.primary_category, pv.pdf_url
                    FROM papers p
                    JOIN paper_versions pv ON p.latest_version_id = pv.id
                    WHERE p.arxiv_id = %s
                """, (arxiv_id,))

                paper_row = cur.fetchone()
                if not paper_row:
                    raise HTTPException(status_code=404, detail="Paper not found")

                # 요약 정보
                cur.execute("""
                    SELECT summary_type, summary_data
                    FROM summaries s
                    JOIN paper_versions pv ON s.paper_version_id = pv.id
                    WHERE pv.arxiv_id = %s
                """, (arxiv_id,))

                summaries = {}
                for summary_row in cur.fetchall():
                    summaries[summary_row[0]] = summary_row[1]

                return {
                    "arxiv_id": paper_row[0],
                    "title": paper_row[1],
                    "authors": paper_row[2],
                    "abstract": paper_row[3],
                    "published_date": paper_row[4].isoformat() if paper_row[4] else None,
                    "category": paper_row[5],
                    "pdf_url": paper_row[6],
                    "summaries": summaries
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching paper {arxiv_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/recommend")
async def recommend_papers(request: RecommendRequest):
    """아이디어 기반 논문 추천"""
    try:
        # Try to use actual FAISS recommendation
        try:
            import sys
            import os
            sys.path.insert(0, os.path.abspath("."))

            from packages.core.recommend.embeddings import embed_texts, get_embedder
            from packages.core.recommend.index_faiss import load_index, query_index
            from packages.core.storage.db import get_connection

            # Load FAISS index
            index, paper_metadata = load_index("data/index")
            if index is None:
                raise ValueError("FAISS index not found")

            # Embed the query
            embeddings = embed_texts([request.idea], model_name="BAAI/bge-m3")
            query_embedding = embeddings[0]

            # Search in FAISS index
            limit = min(request.limit or 10, 50)  # Cap at 50 for safety
            indices, distances = query_index(index, query_embedding, k=limit)

            # Get paper metadata and compute scores
            recommendations = []
            for idx, distance in zip(indices, distances):
                if idx < len(paper_metadata):
                    paper_meta = paper_metadata[idx]
                    similarity_score = max(0, 1.0 - distance)  # Convert distance to similarity

                    paper_data = {
                        "arxiv_id": paper_meta["arxiv_id"],
                        "title": paper_meta["title"],
                        "authors": paper_meta.get("authors", []),
                        "categories": paper_meta.get("categories", []),
                        "abstract": paper_meta.get("abstract", ""),
                        "date": paper_meta.get("date", ""),
                        "similarity_score": similarity_score,
                        "one_liner": paper_meta.get("one_liner", ""),
                    }
                    recommendations.append(paper_data)

            return {
                "query": request.idea,
                "recommendations": recommendations,
                "total": len(recommendations)
            }

        except Exception as faiss_error:
            logger.warning(f"FAISS recommendation failed: {faiss_error}, falling back to mock data")

            # Fallback to mock data
            mock_recommendations = get_mock_recommendations()

            return {
                "query": request.idea,
                "recommendations": mock_recommendations[:request.limit],
                "total": len(mock_recommendations)
            }

    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail="Recommendation service unavailable")

@app.get("/api/trending")
async def get_trending_keywords(
    days: int = Query(7, ge=1, le=30, description="기간 (일)"),
    source: str = Query("all", description="키워드 소스 (all, title, abstract, llm)"),
    limit: int = Query(30, ge=1, le=100, description="결과 수")
):
    """트렌딩 키워드 조회"""
    try:
        # 실제 트렌딩 로직 대신 목업 데이터
        mock_keywords = get_mock_trending_keywords()

        # 소스 필터링
        if source != "all":
            mock_keywords = [k for k in mock_keywords if k["source"] == source]

        return {
            "keywords": mock_keywords[:limit],
            "period_days": days,
            "source": source,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Trending keywords error: {e}")
        raise HTTPException(status_code=500, detail="Trending service unavailable")

@app.get("/api/stats")
async def get_stats():
    """시스템 통계"""
    try:
        # Use SQLite if available
        if USE_SQLITE:
            return get_paper_stats()

        # Fallback to PostgreSQL
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 논문 수
                cur.execute("SELECT COUNT(*) FROM papers")
                paper_count = cur.fetchone()[0]

                # 요약 수
                cur.execute("SELECT COUNT(*) FROM summaries")
                summary_count = cur.fetchone()[0]

                # 최근 논문
                cur.execute("""
                    SELECT COUNT(*) FROM papers
                    WHERE published_date >= %s
                """, (date.today() - timedelta(days=7),))
                recent_papers = cur.fetchone()[0]

                # 카테고리 수
                cur.execute("SELECT COUNT(DISTINCT primary_category) FROM papers")
                category_count = cur.fetchone()[0]

                # 월간 통계
                cur.execute("""
                    SELECT COUNT(*) FROM papers
                    WHERE published_date >= %s
                """, (date.today() - timedelta(days=30),))
                monthly_papers = cur.fetchone()[0]

                # 평균 인용 수 (null 제외)
                cur.execute("""
                    SELECT AVG(citation_count) FROM papers
                    WHERE citation_count IS NOT NULL AND citation_count > 0
                """)
                avg_citations = cur.fetchone()[0] or 0

                return {
                    "total_papers": paper_count,
                    "total_summaries": summary_count,
                    "recent_papers_7d": recent_papers,
                    "recent_count": recent_papers,  # 프론트엔드 호환성
                    "monthly_papers": monthly_papers,
                    "total_categories": category_count,
                    "avg_citations": round(float(avg_citations), 1) if avg_citations else 0,
                    "last_updated": datetime.now().isoformat()
                }

    except Exception as e:
        logger.error(f"Stats error: {e}")
        return get_mock_stats()

# =============================================================================
# 백그라운드 작업들
# =============================================================================

@app.post("/api/admin/ingest")
async def trigger_daily_ingest(background_tasks: BackgroundTasks):
    """일일 논문 수집 트리거 (관리자용)"""
    async def run_ingest():
        # 실제로는 scripts/run_daily_ingest.py 실행
        logger.info("Starting daily paper ingestion...")
        await asyncio.sleep(2)  # 시뮬레이션
        logger.info("Daily ingestion completed")

    background_tasks.add_task(run_ingest)
    return {"message": "Daily ingestion started", "status": "running"}

@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """피드백 제출"""
    try:
        # Store feedback in database or file
        feedback_data = {
            "name": request.name or "Anonymous",
            "email": request.email or "",
            "category": request.category,
            "message": request.message,
            "timestamp": datetime.now().isoformat(),
            "user_agent": "web-app"
        }

        # For now, log to file (in production, save to database)
        import os
        feedback_dir = "data/feedback"
        os.makedirs(feedback_dir, exist_ok=True)

        feedback_file = os.path.join(feedback_dir, f"feedback_{datetime.now().strftime('%Y%m%d')}.jsonl")
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_data, ensure_ascii=False) + "\n")

        logger.info(f"Feedback received: {request.category} - {len(request.message)} chars")

        return {
            "success": True,
            "message": "피드백이 성공적으로 제출되었습니다.",
            "id": f"fb_{int(datetime.now().timestamp())}"
        }

    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail="피드백 제출 중 오류가 발생했습니다.")

@app.get("/api/graph")
async def get_graph_data(
    max_nodes: int = Query(50, ge=10, le=500, description="최대 노드 수"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    days: int = Query(365, ge=30, le=1095, description="최근 N일 논문만 포함")
):
    """논문 연결 그래프 데이터"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Get recent papers with citation counts
                category_filter = ""
                params = [date.today() - timedelta(days=days), max_nodes]
                if category:
                    category_filter = "AND p.primary_category = %s"
                    params.insert(-1, category)

                cur.execute(f"""
                    SELECT
                        p.arxiv_id,
                        p.title,
                        p.primary_category,
                        p.citation_count,
                        p.published_date
                    FROM papers p
                    WHERE p.published_date >= %s
                    {category_filter}
                    ORDER BY p.citation_count DESC
                    LIMIT %s
                """, params)

                papers = cur.fetchall()

                # Create graph structure
                nodes = []
                edges = []

                for i, paper in enumerate(papers):
                    node = {
                        "id": paper[0],  # arxiv_id
                        "title": paper[1][:80] + ("..." if len(paper[1]) > 80 else ""),
                        "category": paper[2],
                        "citations": paper[3] or 0,
                        "date": paper[4].isoformat() if paper[4] else "",
                        "size": min(20, max(5, (paper[3] or 0) // 10 + 5)),  # Node size based on citations
                    }
                    nodes.append(node)

                    # Create edges based on shared categories or citation relationships
                    for j, other_paper in enumerate(papers[:i]):
                        # Simple similarity based on category matching
                        if paper[2] == other_paper[2]:  # Same primary category
                            edge = {
                                "source": paper[0],
                                "target": other_paper[0],
                                "strength": 0.3,
                                "type": "category_match"
                            }
                            edges.append(edge)

                return {
                    "nodes": nodes,
                    "edges": edges,
                    "stats": {
                        "total_nodes": len(nodes),
                        "total_edges": len(edges),
                        "period_days": days,
                        "category": category or "all"
                    }
                }

    except Exception as e:
        logger.error(f"Graph data error: {e}")
        # Return mock data as fallback
        mock_data = get_mock_graph_data()
        mock_data["stats"]["period_days"] = days
        mock_data["stats"]["category"] = category or "all"
        return mock_data

# =============================================================================
# 추가된 인기 기능들 (복구)
# =============================================================================


@app.get("/api/hot-topics")
async def get_hot_topics():
    """핫 토픽 (실시간 분석 연동)"""
    try:
        # 실시간 트렌드 분석 시도
        from src.api.trend_api import get_hot_topics_real
        real_topics = await get_hot_topics_real()
        return real_topics
    except Exception as e:
        logger.warning(f"Real-time hot topics failed, using fallback: {e}")
        # 폴백: 정적 데이터
        topics = [
            {"topic": "Large Language Models", "score": 9.8, "papers": 245, "trend": "up"},
            {"topic": "Transformer Architecture", "score": 9.5, "papers": 189, "trend": "stable"},
            {"topic": "Diffusion Models", "score": 9.2, "papers": 167, "trend": "up"},
            {"topic": "Computer Vision", "score": 8.9, "papers": 134, "trend": "stable"},
            {"topic": "Reinforcement Learning", "score": 8.6, "papers": 112, "trend": "down"},
            {"topic": "Contrastive Learning", "score": 8.3, "papers": 98, "trend": "up"}
        ]
        return {"topics": topics, "source": "fallback"}

@app.get("/api/learning-roadmaps")
async def get_learning_roadmaps():
    """학습 로드맵 목록"""
    roadmaps = [
        {
            "id": "llm_fundamentals",
            "title": "LLM Fundamentals",
            "description": "Essential papers for understanding large language models",
            "difficulty": "beginner",
            "papers_count": 8,
            "estimated_time": "2-3 weeks"
        },
        {
            "id": "computer_vision",
            "title": "Computer Vision Essentials",
            "description": "Core papers in modern computer vision",
            "difficulty": "intermediate",
            "papers_count": 10,
            "estimated_time": "3-4 weeks"
        },
        {
            "id": "generative_ai",
            "title": "Generative AI & Diffusion",
            "description": "Diffusion models, GANs, and generative techniques",
            "difficulty": "advanced",
            "papers_count": 12,
            "estimated_time": "4-5 weeks"
        }
    ]
    return {"roadmaps": roadmaps}

@app.get("/api/learning-roadmaps/{track_name}")
async def get_roadmap_details(track_name: str):
    """특정 로드맵 상세 정보"""
    if track_name == "llm_fundamentals":
        papers = [
            {
                "step_order": 1,
                "arxiv_id": "1706.03762",
                "title": "Attention Is All You Need",
                "why_important": "Foundation of transformer architecture",
                "estimated_read_time": "2-3 hours"
            },
            {
                "step_order": 2,
                "arxiv_id": "2005.14165",
                "title": "GPT-3: Language Models are Few-Shot Learners",
                "why_important": "Demonstrates emergent abilities",
                "estimated_read_time": "3-4 hours"
            }
        ]
    else:
        papers = []

    return {"track_name": track_name, "papers": papers, "total": len(papers)}

# =============================================================================
# 메인 실행
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    print("""
    🚀 Paper Agent API Server

    Available endpoints:
    - GET  /                   UI Prototype
    - GET  /docs               API Documentation
    - GET  /api/papers         Search Papers
    - POST /api/recommend      Recommend Papers
    - GET  /api/trending       Trending Keywords
    - GET  /api/stats          System Stats

    Current vs Improved UX:
    ❌ Before: python scripts/recommend.py --idea "..." --topk 10
    ✅ After:  POST /api/recommend {"idea": "...", "limit": 10}
    """)

    import os
    # Use localhost for development, configure appropriately for production
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run(
        "app:app",
        host=host,
        port=8080,
        reload=True,
        log_level="info"
    )
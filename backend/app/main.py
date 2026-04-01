"""
Research Intelligence Platform - Main FastAPI Application
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.database import check_db_connection, init_db
from .api.research import router as research_router
from .api.graph import router as graph_router
from .api.papers import router as papers_router
from .api.trending import router as trending_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting Research Intelligence Platform...")

    # Check database connection
    try:
        db_connected = await check_db_connection()
        if not db_connected:
            print("❌ Database connection failed!")
        else:
            print("✅ Database connected successfully")
    except Exception as e:
        print(f"⚠️  Database check failed: {e}")

    # Initialize embedding service
    try:
        from .services.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()
        print(f"✅ Embedding service ready ({embedding_service.model_name})")
    except Exception as e:
        print(f"⚠️  Embedding service initialization failed: {e}")

    # Check AI services
    try:
        from .ai.llm_client import get_available_providers
        providers = get_available_providers()
        if providers:
            print(f"✅ AI providers available: {', '.join(providers)}")
        else:
            print("⚠️  No AI providers configured")
    except Exception as e:
        print(f"⚠️  AI service check failed: {e}")

    print("✅ Research Intelligence Platform ready!")

    yield

    # Shutdown
    print("👋 Shutting down Research Intelligence Platform...")


# Create FastAPI application
app = FastAPI(
    title="Research Intelligence Platform",
    description="""
    **Transform research ideas into structured knowledge discovery**

    This platform provides AI-powered research intelligence capabilities:
    - **Idea Analysis**: Transform research ideas into categorized paper recommendations
    - **Paper Comparison**: Side-by-side analysis with strengths/limitations
    - **Question Generation**: Identify research gaps and opportunities
    - **Knowledge Graph**: Visual exploration of paper relationships
    - **Obsidian Export**: Transform discoveries into research assets

    Built with PostgreSQL + pgvector, BAAI/bge-m3 embeddings, and LLM reasoning.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)


# Middleware for logging and timing
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log requests and add timing information."""
    start_time = time.time()

    # Skip logging for health checks
    if request.url.path in ["/health", "/api/research/health"]:
        return await call_next(request)

    print(f"📥 {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        print(f"📤 {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")
        return response

    except Exception as e:
        process_time = time.time() - start_time
        print(f"💥 {request.method} {request.url.path} - ERROR ({process_time:.3f}s): {e}")
        raise


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"Endpoint {request.url.path} not found",
            "available_endpoints": [
                "/docs - API Documentation",
                "--- Paper Search ---",
                "/api/search - Search papers with filters",
                "/api/papers/{arxiv_id} - Get specific paper",
                "/api/autocomplete - Search suggestions",
                "/api/recommend/{arxiv_id} - Paper recommendations",
                "/api/categories - Available categories",
                "/api/stats - Platform statistics",
                "/api/trends - Trending papers",
                "--- Research Intelligence ---",
                "/api/research/analyze - Research Idea Analysis",
                "/api/research/compare - Paper Comparison",
                "/api/research/questions - Research Question Generation",
                "/api/research/status - Platform Status",
                "--- Knowledge Graph ---",
                "/api/graph/build - Build Knowledge Graph",
                "/api/graph/stats - Graph Statistics",
                "/api/graph/subgraph - Get Subgraph",
                "/api/graph/mini/{arxiv_id} - Mini graph around paper",
                "--- Trending ---",
                "/api/trending/today - Today's Trending Papers",
                "/api/trending/week - Weekly Trending Papers",
                "/api/trending/stats - Trending Statistics"
            ]
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Custom 500 handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "request_path": str(request.url.path)
        }
    )


# Include routers
app.include_router(research_router)
app.include_router(graph_router)
app.include_router(papers_router)
app.include_router(trending_router)


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint with platform information."""
    return {
        "platform": "Research Intelligence Platform",
        "version": "1.0.0",
        "description": "AI-powered research discovery and analysis",
        "endpoints": {
            "documentation": "/docs",
            "research_analysis": "/api/research/analyze",
            "paper_comparison": "/api/research/compare",
            "question_generation": "/api/research/questions",
            "knowledge_graph": "/api/graph/build",
            "graph_statistics": "/api/graph/stats",
            "subgraph_query": "/api/graph/subgraph",
            "platform_status": "/api/research/status"
        },
        "features": [
            "Semantic paper search",
            "Research idea analysis",
            "AI-powered explanations",
            "Paper categorization",
            "Comparative analysis",
            "Research question generation",
            "Knowledge graph exploration",
            "Obsidian export"
        ]
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        # Quick database check
        db_status = await check_db_connection()

        return {
            "status": "healthy" if db_status else "degraded",
            "timestamp": time.time(),
            "database": "connected" if db_status else "disconnected",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e),
            "version": "1.0.0"
        }


if __name__ == "__main__":
    import uvicorn

    print("""
    🧠 Research Intelligence Platform

    Features:
    • POST /api/research/analyze     - Transform ideas into structured recommendations
    • POST /api/research/compare     - Side-by-side paper analysis
    • POST /api/research/questions   - Generate research questions
    • POST /api/graph/build          - Build knowledge graph
    • POST /api/graph/subgraph       - Explore node neighborhoods
    • GET  /api/graph/stats          - Graph statistics and insights
    • GET  /docs                     - Interactive API documentation

    Architecture:
    • PostgreSQL + pgvector for semantic search
    • BAAI/bge-m3 embeddings (1024-dim)
    • LLM-powered reasoning and explanations
    • Hybrid search (text + semantic)
    """)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
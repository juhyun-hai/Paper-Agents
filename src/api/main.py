"""FastAPI main application — Paper Recommender Service."""
import json
import sqlite3
import os
from typing import Optional, List

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.utils.config import load_config
from src.database import PaperDBManager
from src.api.search import PaperSearchEngine

config = load_config()
DB_PATH = config["database"]["path"]
EMBED_DIR = config["embedding"]["save_path"]

app = FastAPI(title="Paper Recommender API", version="1.0.0")
# Rate limiting: install slowapi for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = PaperDBManager(DB_PATH)
engine = PaperSearchEngine(db_path=DB_PATH, embedding_dir=EMBED_DIR)


def _paper_to_out(p: dict) -> dict:
    for f in ("authors", "categories"):
        if isinstance(p.get(f), str):
            try:
                p[f] = json.loads(p[f])
            except Exception:
                p[f] = []
    p.setdefault("citation_count", 0)
    p.setdefault("venue", "")
    p.setdefault("similarity_score", None)
    return p


# ─────────────────────────────── Search ────────────────────────────────

@app.get("/api/search")
def search(
    q: str = Query("", min_length=0),
    category: Optional[str] = None,
    sort: str = "relevance",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    venue: Optional[str] = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
):
    # Parse comma-separated sort values
    sorts = [s.strip() for s in sort.split(",") if s.strip()] if sort else ["relevance"]

    def _apply_sort(papers: list, sorts: list) -> list:
        """Apply single or compound sort to a list of papers."""
        if len(sorts) == 1:
            if sorts[0] == "citations":
                return sorted(papers, key=lambda x: x.get("citation_count") or 0, reverse=True)
            if sorts[0] == "date":
                return sorted(papers, key=lambda x: x.get("date") or "", reverse=True)
            return papers  # relevance: keep original order
        # Compound sort: normalize and combine
        max_cite = max((p.get("citation_count") or 0 for p in papers), default=1) or 1
        all_dates = sorted(set(p.get("date") or "" for p in papers if p.get("date")))
        date_count = len(all_dates)
        date_rank = {d: i / date_count for i, d in enumerate(all_dates)} if date_count else {}
        max_score = max((p.get("_score", 0) for p in papers), default=1) or 1

        def score(p):
            s, w = 0.0, 0
            if "relevance" in sorts:
                s += p.get("_score", 0) / max_score; w += 1
            if "citations" in sorts:
                s += (p.get("citation_count") or 0) / max_cite; w += 1
            if "date" in sorts:
                s += date_rank.get(p.get("date") or "", 0); w += 1
            return s / w if w else 0
        return sorted(papers, key=score, reverse=True)

    # If no query, browse mode
    if not q.strip():
        all_papers = db.get_all_papers()
        if category:
            all_papers = [p for p in all_papers if category in (p.get("categories") or [])]
        if date_from:
            all_papers = [p for p in all_papers if (p.get("date") or "") >= date_from]
        if date_to:
            all_papers = [p for p in all_papers if (p.get("date") or "") <= date_to]
        if venue:
            all_papers = [p for p in all_papers if venue.lower() in (p.get("venue") or "").lower()]
        all_papers = _apply_sort(all_papers, sorts)
        total = len(all_papers)
        page = all_papers[offset: offset + limit]
        return {"papers": [_paper_to_out(p) for p in page], "total": total, "query": ""}

    result = engine.search(
        query=q,
        category=category,
        sort=sort,
        date_from=date_from,
        date_to=date_to,
        venue=venue,
        limit=limit,
        offset=offset,
        sorts=sorts,
    )
    result["papers"] = [_paper_to_out(p) for p in result["papers"]]
    return result


@app.get("/api/autocomplete")
def autocomplete(q: str = Query(..., min_length=1)):
    suggestions = engine.autocomplete(q, limit=8)
    return {"suggestions": suggestions}


# ─────────────────────────────── Papers ────────────────────────────────

@app.get("/api/papers/top")
def get_top_papers(limit: int = Query(10, le=50), days: int = Query(60)):
    """Return trending papers by velocity + recency + hot-topic score."""
    from src.recommender.trend_recommender import TrendAnalyzer
    analyzer = TrendAnalyzer(db_manager=db, config=config)
    papers = analyzer.get_trending_papers(days=days, top_k=limit)
    return {"papers": [_paper_to_out(p) for p in papers], "total": len(papers)}


@app.get("/api/papers/{arxiv_id:path}")
def get_paper(arxiv_id: str):
    paper = db.get_paper_by_id(arxiv_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return _paper_to_out(paper)


@app.get("/api/recommend/{arxiv_id:path}")
def recommend(arxiv_id: str, top_k: int = 10):
    try:
        from src.recommender.content_recommender import ContentRecommender
        rec = ContentRecommender(db_manager=db, config=config)
        results = rec.recommend(arxiv_id, top_k=top_k)
        return {"recommendations": [_paper_to_out(p) for p in results]}
    except Exception as e:
        return {"recommendations": [], "error": str(e)}


# ─────────────────────────────── Graph ─────────────────────────────────

@app.get("/api/graph")
def get_graph(max_nodes: int = Query(200, le=500), category: Optional[str] = None):
    papers = db.get_all_papers()
    if category:
        papers = [p for p in papers if category in (p.get("categories") or [])]
    papers = papers[:max_nodes]

    # Build nodes
    cat_color = {
        "cs.CL": "#1a73e8", "cs.AI": "#9c27b0", "cs.CV": "#4caf50",
        "cs.LG": "#f44336", "stat.ML": "#ff9800",
        "cs.NE": "#06b6d4", "cs.RO": "#ec4899", "cs.IR": "#84cc16",
        "hai": "#0f766e",
    }
    nodes = []
    for p in papers:
        cats = p.get("categories") or ["cs.AI"]
        primary_cat = cats[0] if cats else "cs.AI"
        nodes.append({
            "id": p["arxiv_id"],
            "title": p["title"],
            "category": primary_cat,
            "color": cat_color.get(primary_cat, "#607d8b"),
            "citation_count": p.get("citation_count") or 0,
            "date": p.get("date") or "",
            "venue": p.get("venue") or "",
            "authors": (p.get("authors") or [])[:3],
        })

    # Build edges from embedding similarity
    edges = _build_similarity_edges(papers, threshold=0.55, max_edges=600)

    return {"nodes": nodes, "edges": edges}


@app.get("/api/graph/mini/{arxiv_id:path}")
def get_mini_graph(arxiv_id: str, top_k: int = 8):
    """Mini graph centered on a specific paper."""
    try:
        from src.recommender.content_recommender import ContentRecommender
        rec = ContentRecommender(db_manager=db, config=config)
        similar = rec.recommend(arxiv_id, top_k=top_k)
    except Exception:
        similar = []
    center = db.get_paper_by_id(arxiv_id)
    if not center:
        raise HTTPException(404, "Paper not found")
    cat_color = {
        "cs.CL": "#1a73e8", "cs.AI": "#9c27b0", "cs.CV": "#4caf50",
        "cs.LG": "#f44336", "stat.ML": "#ff9800",
        "cs.NE": "#06b6d4", "cs.RO": "#ec4899", "cs.IR": "#84cc16",
        "hai": "#0f766e",
    }
    def _node(p, is_center=False):
        cats = p.get("categories") or ["cs.AI"]
        cat = cats[0]
        return {
            "id": p["arxiv_id"],
            "title": p["title"],
            "category": cat,
            "color": cat_color.get(cat, "#607d8b"),
            "citation_count": p.get("citation_count") or 0,
            "is_center": is_center,
        }
    nodes = [_node(_paper_to_out(center), is_center=True)]
    edges = []
    for s in similar:
        sp = _paper_to_out(s)
        nodes.append(_node(sp))
        edges.append({
            "source": arxiv_id,
            "target": sp["arxiv_id"],
            "weight": sp.get("similarity_score") or 0.5,
            "type": "similar",
        })
    return {"nodes": nodes, "edges": edges}


def _build_similarity_edges(papers, threshold=0.7, max_edges=400):
    """Build edges from saved embeddings — fast numpy batch."""
    import numpy as np, os
    edges = []
    ids = [p["arxiv_id"] for p in papers]
    embs = []
    valid_ids = []
    for aid in ids:
        safe = aid.replace("/", "_").replace(".", "_")
        path = os.path.join(EMBED_DIR, f"{safe}.npy")
        if os.path.exists(path):
            embs.append(np.load(path))
            valid_ids.append(aid)
    if len(embs) < 2:
        return edges
    mat = np.array(embs)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normed = mat / norms
    sim_mat = normed @ normed.T
    n = len(valid_ids)
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(sim_mat[i, j])
            if sim >= threshold:
                edges.append({
                    "source": valid_ids[i],
                    "target": valid_ids[j],
                    "weight": round(sim, 3),
                    "type": "similar",
                })
                if len(edges) >= max_edges:
                    return edges
    return edges


# ─────────────────────────────── Stats / Trends ────────────────────────

@app.get("/api/stats")
def get_stats():
    from src.recommender.trend_recommender import TrendAnalyzer
    analyzer = TrendAnalyzer(db_manager=db, config=config)
    summary = analyzer.get_weekly_summary()
    # Top papers by citation
    all_papers = db.get_all_papers()
    top_papers = sorted(
        all_papers, key=lambda x: x.get("citation_count") or 0, reverse=True
    )[:10]
    # Top venues
    from collections import Counter
    venue_counter = Counter(
        p.get("venue", "") for p in all_papers if p.get("venue")
    )
    top_venues = [{"venue": v, "count": c} for v, c in venue_counter.most_common(10)]
    # Count categories
    cat_counter = Counter()
    for p in all_papers:
        for c in (p.get("categories") or []):
            cat_counter[c] += 1
    total_categories = len(cat_counter)
    # Recent (last 30 days)
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_count = sum(1 for p in all_papers if (p.get("date") or "") >= cutoff)
    return {
        **summary,
        "top_papers": [_paper_to_out(p) for p in top_papers],
        "top_venues": top_venues,
        "recent_count": recent_count,
        "total_categories": total_categories,
    }


@app.get("/api/trends")
def get_trends(days: int = 30):
    from src.recommender.trend_recommender import TrendAnalyzer
    analyzer = TrendAnalyzer(db_manager=db, config=config)
    return {
        "trending_papers": [
            _paper_to_out(p) for p in analyzer.get_trending_papers(days=days, top_k=20)
        ],
        "trending_keywords": analyzer.get_keyword_trends(days=days),
        "category_stats": analyzer.get_category_stats(),
    }


@app.get("/api/categories")
def get_categories():
    all_papers = db.get_all_papers()
    from collections import Counter
    counter = Counter()
    for p in all_papers:
        for c in (p.get("categories") or []):
            counter[c] += 1
    return {"categories": [{"id": k, "count": v} for k, v in counter.most_common()]}


# ─────────────────────────────── Health ────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "papers": db.count_papers()}


# ─────────────────────────────── Hot Topics ────────────────────────────────

@app.get("/api/hot-topics")
def get_hot_topics(days: int = Query(1, ge=1, le=30)):
    """Return hot topics for today (days=1) or recent N days (days>1)."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    if days == 1:
        topics = db.get_hot_topics(today)
    else:
        topics = db.get_recent_hot_topics(days)
    return {"topics": topics, "date": today, "count": len(topics)}


# ─────────────────────────── Feedback ──────────────────────────────

@app.post("/api/feedback")
def submit_feedback(request: Request, data: dict):
    """Save user feedback to DB."""
    from datetime import datetime
    message = (data.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO feedback (name, email, category, message) VALUES (?, ?, ?, ?)",
            (
                (data.get("name") or "")[:100],
                (data.get("email") or "")[:200],
                (data.get("category") or "general")[:50],
                message[:2000],
            ),
        )
        conn.commit()
    return {"ok": True}


@app.get("/api/feedback")
def get_feedback(limit: int = Query(100, ge=1, le=500)):
    """Return all feedback entries, newest first."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM feedback ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return {"feedback": [dict(r) for r in rows], "count": len(rows)}


# ─────────────────────────── Static files ──────────────────────────────

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")

if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/system_overview.html", include_in_schema=False)
    def serve_system_overview():
        path = os.path.join(FRONTEND_DIST, "system_overview.html")
        return FileResponse(path, media_type="text/html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        index = os.path.join(FRONTEND_DIST, "index.html")
        return FileResponse(index)

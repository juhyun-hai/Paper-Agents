"""Search engine: FTS5 + semantic (embedding cosine) + fuzzy + synonym mapping."""
import re
import sqlite3
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)

SYNONYMS = {
    "강화학습": "reinforcement learning",
    "생성 모델": "generative model",
    "생성모델": "generative model",
    "트랜스포머": "transformer",
    "대형 언어 모델": "large language model",
    "대규모 언어 모델": "large language model",
    "확산 모델": "diffusion model",
    "확산모델": "diffusion model",
    "시계열": "time series",
    "시각 언어 모델": "vision language model",
    "기초 모델": "foundation model",
    "기반 모델": "foundation model",
    "언어 모델": "language model",
    "비전 트랜스포머": "vision transformer",
    "자연어 처리": "natural language processing",
    "컴퓨터 비전": "computer vision",
    "이미지 생성": "image generation",
    "llm": "large language model",
    "nlp": "natural language processing",
}

TYPO_MAP = {
    "transfomer": "transformer",
    "transfromer": "transformer",
    "tranformer": "transformer",
    "diffuison": "diffusion",
    "languge": "language",
    "laguage": "language",
    "genrative": "generative",
    "leraning": "learning",
    "learing": "learning",
    "reinfrocement": "reinforcement",
    "reinforcment": "reinforcement",
}

AUTOCOMPLETE_KEYWORDS = [
    "transformer", "large language model", "LLM", "diffusion model",
    "reinforcement learning", "RLHF", "vision transformer", "ViT",
    "foundation model", "multimodal", "generative model", "GAN",
    "time series", "anomaly detection", "object detection", "segmentation",
    "contrastive learning", "self-supervised", "in-context learning",
    "chain of thought", "retrieval augmented generation", "RAG",
    "instruction tuning", "alignment", "RLHF", "PPO", "GRPO",
    "graph neural network", "GNN", "federated learning",
    "NeurIPS", "ICML", "ICLR", "ACL", "EMNLP", "CVPR",
]


def normalize_query(query: str) -> str:
    q = query.strip().lower()
    # Korean synonym map
    for ko, en in SYNONYMS.items():
        if ko in q:
            q = q.replace(ko, en)
    # Typo correction
    tokens = q.split()
    corrected = [TYPO_MAP.get(t, t) for t in tokens]
    return " ".join(corrected)


def highlight_text(text: str, query_terms: List[str], max_len: int = 300) -> str:
    """Return text snippet with query terms bolded (HTML)."""
    if not text:
        return ""
    snippet = text[:max_len]
    for term in query_terms:
        if len(term) < 2:
            continue
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        snippet = pattern.sub(lambda m: f"<mark>{m.group()}</mark>", snippet)
    return snippet


class PaperSearchEngine:
    def __init__(self, db_path: str, embedding_dir: str = "data/embeddings"):
        self.db_path = db_path
        self.embedding_dir = embedding_dir
        self._embedding_model = None

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_model(self):
        if self._embedding_model is None:
            try:
                import os
                from sentence_transformers import SentenceTransformer
                hf_home = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "hf_cache")
                os.makedirs(hf_home, exist_ok=True)
                os.environ.setdefault("HF_HOME", hf_home)
                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=hf_home)
            except Exception as e:
                logger.warning(f"Could not load embedding model: {e}")
        return self._embedding_model

    def _load_embedding(self, arxiv_id: str) -> Optional[np.ndarray]:
        import os
        safe = arxiv_id.replace("/", "_").replace(".", "_")
        path = f"{self.embedding_dir}/{safe}.npy"
        if os.path.exists(path):
            return np.load(path)
        return None

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def _row_to_dict(self, row) -> Dict[str, Any]:
        import json
        d = dict(row)
        for field in ("authors", "categories"):
            if isinstance(d.get(field), str):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    d[field] = []
        d.setdefault("citation_count", 0)
        d.setdefault("venue", "")
        return d

    def fts_search(self, query: str, limit: int = 50) -> List[Tuple[float, Dict]]:
        """SQLite FTS5 full-text search. Returns (normalized_score, paper) tuples."""
        terms = [t for t in query.split() if len(t) > 1]
        if not terms:
            return []

        raw: List[Tuple[float, Dict]] = []  # (rank, paper) — rank is negative, lower = better

        # Phrase match first for multi-word queries (boost with 2x multiplier later)
        phrase_ids: set = set()
        if len(terms) > 1:
            phrase_query = f'"{query}"'
            try:
                with self._get_conn() as conn:
                    rows = conn.execute(
                        """SELECT p.*, rank FROM papers p
                           JOIN papers_fts f ON p.id = f.rowid
                           WHERE papers_fts MATCH ?
                           ORDER BY rank LIMIT ?""",
                        (phrase_query, limit // 2),
                    ).fetchall()
                for r in rows:
                    d = self._row_to_dict(r)
                    raw.append((float(r["rank"]), d))
                    phrase_ids.add(d["arxiv_id"])
            except Exception:
                pass

        # OR search
        or_query = " OR ".join(f'"{term}"' for term in terms)
        try:
            with self._get_conn() as conn:
                rows = conn.execute(
                    """SELECT p.*, rank FROM papers p
                       JOIN papers_fts f ON p.id = f.rowid
                       WHERE papers_fts MATCH ?
                       ORDER BY rank LIMIT ?""",
                    (or_query, limit),
                ).fetchall()
            seen = {d["arxiv_id"] for _, d in raw}
            for r in rows:
                d = self._row_to_dict(r)
                if d["arxiv_id"] not in seen:
                    raw.append((float(r["rank"]), d))
                    seen.add(d["arxiv_id"])
        except Exception as e:
            logger.warning(f"FTS search error: {e}")

        if not raw:
            return []

        # Normalize: FTS5 rank is negative (more negative = better match)
        # Boost phrase matches by halving their rank value (makes them more negative)
        boosted = [(rank * 2 if d["arxiv_id"] in phrase_ids else rank, d) for rank, d in raw]
        ranks = [r for r, _ in boosted]
        min_rank = min(ranks)  # most relevant (most negative)
        max_rank = max(ranks)  # least relevant (least negative / closest to 0)
        span = max_rank - min_rank if max_rank != min_rank else 1.0
        # Normalize to [0, 1]: best rank → 1.0, worst → 0.0
        normalized = [((max_rank - rank) / span, d) for rank, d in boosted]
        normalized.sort(key=lambda x: x[0], reverse=True)
        return normalized[:limit]

    def semantic_search(self, query: str, top_k: int = 20) -> List[Tuple[float, Dict]]:
        """Embedding cosine similarity search."""
        model = self._load_model()
        if model is None:
            return []
        try:
            query_emb = model.encode(query, convert_to_numpy=True)
        except Exception:
            return []
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM papers").fetchall()
        papers = [self._row_to_dict(r) for r in rows]
        scores = []
        for paper in papers:
            emb = self._load_embedding(paper["arxiv_id"])
            if emb is not None:
                sim = self._cosine_sim(query_emb, emb)
                scores.append((sim, paper))
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[:top_k]

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        sort: str = "relevance",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        venue: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sorts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        # Normalize sort options into a list
        if sorts is None:
            sorts = [s.strip() for s in sort.split(",") if s.strip()] if sort else ["relevance"]
        normalized = normalize_query(query)
        query_terms = [t for t in normalized.split() if len(t) > 2]

        # FTS search — returns (normalized_score, paper) tuples
        fts_results = self.fts_search(normalized, limit=100)
        fts_ids = {p["arxiv_id"]: (score, p) for score, p in fts_results}

        # Semantic search
        sem_results = self.semantic_search(normalized, top_k=50)
        sem_ids = {p["arxiv_id"]: (score, p) for score, p in sem_results}

        # Merge: paper in either result set
        all_ids = set(fts_ids.keys()) | set(sem_ids.keys())
        merged = []
        for aid in all_ids:
            fts_score = fts_ids.get(aid, (0, None))[0]
            sem_score = sem_ids.get(aid, (0, None))[0]
            paper = (fts_ids.get(aid) or (0, None))[1] or sem_ids.get(aid, (0, None))[1]
            if paper is None:
                continue
            combined = 0.4 * sem_score + 0.6 * fts_score
            # Filter out low-relevance results
            if combined < 0.15:
                continue
            paper["_score"] = combined
            paper["similarity_score"] = round(sem_score, 4)
            merged.append(paper)

        # If no results, fallback to DB
        if not merged:
            with self._get_conn() as conn:
                rows = conn.execute(
                    """SELECT * FROM papers WHERE
                       lower(title) LIKE lower(?) OR
                       lower(abstract) LIKE lower(?) OR
                       lower(categories) LIKE lower(?)
                       LIMIT 50""",
                    (f"%{normalized}%", f"%{normalized}%", f"%{normalized}%"),
                ).fetchall()
            merged = [self._row_to_dict(r) for r in rows]
            for p in merged:
                p["_score"] = 0.5

        # Filter
        if category:
            merged = [p for p in merged if category in (p.get("categories") or [])]
        if date_from:
            merged = [p for p in merged if (p.get("date") or "") >= date_from]
        if date_to:
            merged = [p for p in merged if (p.get("date") or "") <= date_to]
        if venue:
            merged = [p for p in merged if venue.lower() in (p.get("venue") or "").lower()]

        # Sort - single or compound
        if len(sorts) == 1:
            if sorts[0] == "citations":
                merged.sort(key=lambda x: x.get("citation_count") or 0, reverse=True)
            elif sorts[0] == "date":
                merged.sort(key=lambda x: x.get("date") or "", reverse=True)
            else:
                merged.sort(key=lambda x: x.get("_score", 0), reverse=True)
        else:
            max_score = max((p.get("_score", 0) for p in merged), default=1) or 1
            max_cite = max((p.get("citation_count") or 0 for p in merged), default=1) or 1
            all_dates = sorted(set(p.get("date") or "" for p in merged if p.get("date")))
            date_rank = {d: i / len(all_dates) for i, d in enumerate(all_dates)} if all_dates else {}

            def compound_score(p):
                s, w = 0.0, 0
                if "relevance" in sorts:
                    s += p.get("_score", 0) / max_score; w += 1
                if "citations" in sorts:
                    s += (p.get("citation_count") or 0) / max_cite; w += 1
                if "date" in sorts:
                    s += date_rank.get(p.get("date") or "", 0); w += 1
                return s / w if w else 0

            merged.sort(key=compound_score, reverse=True)

        total = len(merged)
        page = merged[offset : offset + limit]

        # Add highlights
        for p in page:
            p["abstract_highlight"] = highlight_text(
                p.get("abstract", ""), query_terms, max_len=250
            )

        return {"papers": page, "total": total, "query": query}

    def autocomplete(self, query: str, limit: int = 8) -> List[str]:
        q = query.lower().strip()
        if not q:
            return []
        suggestions = []
        # Match known keywords
        for kw in AUTOCOMPLETE_KEYWORDS:
            if q in kw.lower():
                suggestions.append(kw)
        # Match from DB titles
        try:
            with self._get_conn() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT title FROM papers WHERE lower(title) LIKE ? LIMIT 10",
                    (f"%{q}%",),
                ).fetchall()
            for r in rows:
                title = r["title"]
                if len(title) < 80:
                    suggestions.append(title)
        except Exception:
            pass
        # Deduplicate and limit
        seen = set()
        result = []
        for s in suggestions:
            if s.lower() not in seen:
                seen.add(s.lower())
                result.append(s)
            if len(result) >= limit:
                break
        return result

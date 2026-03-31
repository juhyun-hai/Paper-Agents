import os
import json
import numpy as np
from typing import List, Dict, Any, Optional

from src.database import PaperDBManager
from src.utils.logger import get_logger
from src.utils.config import load_config

logger = get_logger(__name__)


class EmbeddingManager:
    def __init__(self, config: dict = None):
        self.config = config or load_config()
        self.model_name = self.config["embedding"]["model"]
        self.save_path = self.config["embedding"]["save_path"]
        os.makedirs(self.save_path, exist_ok=True)
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                import os
                # Use local HF cache to avoid root-owned system cache
                base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                hf_home = os.path.join(base, "data", "hf_cache")
                os.makedirs(hf_home, exist_ok=True)
                os.environ.setdefault("HF_HOME", hf_home)
                os.environ.setdefault("TRANSFORMERS_CACHE", hf_home)
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name, cache_folder=hf_home)
                logger.info("Embedding model loaded")
            except ImportError:
                logger.error("sentence-transformers not installed")
                raise
        return self._model

    def compute_embedding(self, text: str) -> np.ndarray:
        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding

    def compute_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        model = self._load_model()
        batch_size = self.config["embedding"].get("batch_size", 32)
        embeddings = model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
        return embeddings

    def save_embedding(self, arxiv_id: str, embedding: np.ndarray) -> str:
        safe_id = arxiv_id.replace("/", "_").replace(".", "_")
        path = os.path.join(self.save_path, f"{safe_id}.npy")
        np.save(path, embedding)
        return path

    def load_embedding(self, arxiv_id: str) -> Optional[np.ndarray]:
        safe_id = arxiv_id.replace("/", "_").replace(".", "_")
        path = os.path.join(self.save_path, f"{safe_id}.npy")
        if not os.path.exists(path):
            return None
        return np.load(path)

    def embedding_exists(self, arxiv_id: str) -> bool:
        safe_id = arxiv_id.replace("/", "_").replace(".", "_")
        path = os.path.join(self.save_path, f"{safe_id}.npy")
        return os.path.exists(path)


class ContentRecommender:
    def __init__(self, db_manager: Optional[PaperDBManager] = None, config: dict = None):
        self.config = config or load_config()
        self.db = db_manager or PaperDBManager(self.config["database"]["path"])
        self.embedding_manager = EmbeddingManager(self.config)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def build_embeddings(self, papers: List[Dict[str, Any]] = None) -> int:
        if papers is None:
            papers = self.db.get_all_papers()
        built = 0
        for paper in papers:
            arxiv_id = paper["arxiv_id"]
            if not self.embedding_manager.embedding_exists(arxiv_id):
                text = f"{paper['title']} {paper.get('abstract', '')}"
                emb = self.embedding_manager.compute_embedding(text)
                path = self.embedding_manager.save_embedding(arxiv_id, emb)
                self.db.update_paper(arxiv_id, {"embedding_path": path})
                built += 1
        logger.info(f"Built {built} new embeddings")
        return built

    def recommend(self, query_paper_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        query_paper = self.db.get_paper_by_id(query_paper_id)
        if query_paper is None:
            logger.warning(f"Paper {query_paper_id} not found in DB")
            return []
        query_emb = self.embedding_manager.load_embedding(query_paper_id)
        if query_emb is None:
            text = f"{query_paper['title']} {query_paper.get('abstract', '')}"
            query_emb = self.embedding_manager.compute_embedding(text)
        all_papers = self.db.get_all_papers()
        scores = []
        for paper in all_papers:
            if paper["arxiv_id"] == query_paper_id:
                continue
            emb = self.embedding_manager.load_embedding(paper["arxiv_id"])
            if emb is None:
                text = f"{paper['title']} {paper.get('abstract', '')}"
                emb = self.embedding_manager.compute_embedding(text)
            sim = self._cosine_similarity(query_emb, emb)
            scores.append((sim, paper))
        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, paper in scores[:top_k]:
            paper["similarity_score"] = round(sim, 4)
            results.append(paper)
        return results

    def recommend_by_text(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        query_emb = self.embedding_manager.compute_embedding(query_text)
        all_papers = self.db.get_all_papers()
        scores = []
        for paper in all_papers:
            emb = self.embedding_manager.load_embedding(paper["arxiv_id"])
            if emb is None:
                text = f"{paper['title']} {paper.get('abstract', '')}"
                emb = self.embedding_manager.compute_embedding(text)
            sim = self._cosine_similarity(query_emb, emb)
            scores.append((sim, paper))
        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, paper in scores[:top_k]:
            paper["similarity_score"] = round(sim, 4)
            results.append(paper)
        return results

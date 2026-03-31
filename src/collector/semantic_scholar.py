"""Semantic Scholar API collector — citation-ranked paper collection."""
import time
import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.database import PaperDBManager
from src.summarizer.note_generator import NoteGenerator
from src.utils.logger import get_logger
from src.utils.config import load_config

logger = get_logger(__name__, log_dir="logs")

SS_BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS = "paperId,externalIds,title,abstract,authors,year,citationCount,publicationVenue,fieldsOfStudy,publicationTypes"

VENUE_KEYWORDS = {
    "NeurIPS", "ICML", "ICLR", "ACL", "EMNLP", "NAACL",
    "CVPR", "ICCV", "ECCV", "AAAI", "IJCAI", "SIGKDD", "ICRA",
}

CATEGORY_QUERIES = {
    "cs.CL": [
        "large language model NLP", "LLM instruction tuning", "RLHF alignment",
        "transformer language model", "in-context learning", "chain of thought",
        "retrieval augmented generation RAG", "tokenization tokenizer",
    ],
    "cs.AI": [
        "foundation model AI", "artificial general intelligence",
        "multimodal learning AI", "reasoning AI planning",
        "knowledge graph embedding", "neural symbolic AI",
    ],
    "cs.CV": [
        "diffusion model image generation", "vision transformer ViT",
        "object detection YOLO DETR", "image segmentation",
        "video understanding temporal", "3D reconstruction point cloud",
        "contrastive learning vision CLIP", "image editing inpainting",
    ],
    "cs.LG": [
        "reinforcement learning policy gradient",
        "generative adversarial network GAN",
        "self-supervised representation learning",
        "federated learning privacy", "neural architecture search",
        "graph neural network GNN", "meta-learning few-shot",
        "continual learning catastrophic forgetting",
    ],
    "stat.ML": [
        "time series forecasting deep learning",
        "anomaly detection unsupervised",
        "Bayesian neural network uncertainty",
        "causal inference machine learning",
        "variational autoencoder VAE",
    ],
    "cs.NE": [
        "neural architecture search", "evolutionary algorithm",
        "neuroevolution genetic algorithm", "spiking neural network",
    ],
    "cs.RO": [
        "robot learning reinforcement", "manipulation policy",
        "sim-to-real transfer learning", "autonomous driving",
        "motion planning path planning",
    ],
    "cs.IR": [
        "information retrieval ranking", "dense retrieval embedding",
        "re-ranking learning to rank", "recommendation system collaborative filtering",
        "knowledge graph embedding retrieval",
    ],
}

SYNONYMS = {
    "강화학습": "reinforcement learning",
    "생성 모델": "generative model",
    "트랜스포머": "transformer",
    "대형 언어 모델": "large language model",
    "확산 모델": "diffusion model",
    "시계열": "time series",
    "시각 언어 모델": "vision language model",
    "기초 모델": "foundation model",
}


class SemanticScholarCollector:
    def __init__(
        self,
        db_manager: Optional[PaperDBManager] = None,
        config: Optional[dict] = None,
        api_key: Optional[str] = None,
    ):
        self.config = config or load_config()
        self.db = db_manager or PaperDBManager(self.config["database"]["path"])
        self.note_gen = NoteGenerator(config=self.config)
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers["x-api-key"] = api_key
        self.batch_size = 20
        self.batch_sleep = 5  # seconds between batches

    def _search_ss(self, query: str, limit: int = 50, year_start: int = 2024) -> List[Dict]:
        url = f"{SS_BASE}/paper/search"
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": FIELDS,
            "year": f"{year_start}-",
            "sort": "citationCount:desc",
        }
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            logger.warning(f"SS API error for '{query}': {e}")
            return []

    def _ss_to_paper_dict(self, item: Dict) -> Optional[Dict[str, Any]]:
        external_ids = item.get("externalIds") or {}
        arxiv_id = external_ids.get("ArXiv")
        if not arxiv_id:
            return None
        title = item.get("title", "").strip()
        if not title:
            return None
        abstract = item.get("abstract") or ""
        authors = [a.get("name", "") for a in (item.get("authors") or [])][:10]
        year = item.get("year") or 2024
        citation_count = item.get("citationCount") or 0
        venue_obj = item.get("publicationVenue") or {}
        venue = venue_obj.get("name", "") or ""
        # Detect conference
        detected_venue = ""
        for kw in VENUE_KEYWORDS:
            if kw.lower() in venue.lower():
                detected_venue = kw
                break
        fields = item.get("fieldsOfStudy") or []
        categories = _fields_to_categories(fields)
        return {
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "categories": categories,
            "date": f"{year}-01-01",
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
            "citation_count": citation_count,
            "venue": detected_venue,
        }

    def collect_category(
        self, category: str, target: int = 50, year_start: int = 2024
    ) -> List[Dict]:
        queries = CATEGORY_QUERIES.get(category, [f"cat:{category}"])
        all_papers: Dict[str, Dict] = {}
        per_query = max(target // len(queries) + 10, 25)
        for i, query in enumerate(queries):
            if len(all_papers) >= target * 2:
                break
            logger.info(f"[{category}] Query {i+1}/{len(queries)}: '{query}'")
            items = self._search_ss(query, limit=per_query, year_start=year_start)
            for item in items:
                paper = self._ss_to_paper_dict(item)
                if paper and paper["arxiv_id"] not in all_papers:
                    all_papers[paper["arxiv_id"]] = paper
            if i < len(queries) - 1:
                time.sleep(2)
        # Sort by citation count, take top N
        sorted_papers = sorted(
            all_papers.values(), key=lambda x: x.get("citation_count", 0), reverse=True
        )
        return sorted_papers[:target]

    def run_backfill(
        self,
        target_per_category: int = 60,
        year_start: int = 2024,
    ) -> Dict[str, int]:
        import logging
        fh = logging.FileHandler("logs/backfill.log")
        fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(fh)

        categories = list(CATEGORY_QUERIES.keys())
        results = {}
        total_new = 0
        logger.info(f"=== Backfill started: {len(categories)} categories, target {target_per_category}/cat ===")

        for cat_idx, category in enumerate(categories):
            logger.info(f"\n--- Category {cat_idx+1}/{len(categories)}: {category} ---")
            papers = self.collect_category(category, target=target_per_category, year_start=year_start)
            saved = 0
            for batch_start in range(0, len(papers), self.batch_size):
                batch = papers[batch_start : batch_start + self.batch_size]
                for paper in batch:
                    added = self.db.add_paper(paper)
                    if added:
                        # Update citation_count and venue (add_paper doesn't handle these)
                        self._update_extra_fields(paper)
                        self.note_gen.save_note(paper)
                        saved += 1
                        total_new += 1
                logger.info(f"  Batch {batch_start//self.batch_size + 1}: +{len(batch)} processed, {saved} saved so far")
                if batch_start + self.batch_size < len(papers):
                    time.sleep(self.batch_sleep)
            results[category] = saved
            logger.info(f"  {category}: {saved} new papers saved")
            if cat_idx < len(categories) - 1:
                time.sleep(3)

        logger.info(f"\n=== Backfill complete: {total_new} total new papers ===")
        return results

    def _update_extra_fields(self, paper: Dict):
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            conn.execute(
                "UPDATE papers SET citation_count=?, venue=? WHERE arxiv_id=?",
                (paper.get("citation_count", 0), paper.get("venue", ""), paper["arxiv_id"]),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def build_embeddings_for_new(self) -> int:
        try:
            from src.recommender.content_recommender import ContentRecommender
            rec = ContentRecommender(db_manager=self.db, config=self.config)
            papers = self.db.get_all_papers()
            new_papers = [
                p for p in papers if not rec.embedding_manager.embedding_exists(p["arxiv_id"])
            ]
            logger.info(f"Building embeddings for {len(new_papers)} papers...")
            built = 0
            batch_size = 32
            for i in range(0, len(new_papers), batch_size):
                batch = new_papers[i : i + batch_size]
                texts = [f"{p['title']} {p.get('abstract', '')}" for p in batch]
                embeddings = rec.embedding_manager.compute_embeddings_batch(texts)
                for paper, emb in zip(batch, embeddings):
                    path = rec.embedding_manager.save_embedding(paper["arxiv_id"], emb)
                    rec.db.update_paper(paper["arxiv_id"], {"embedding_path": path})
                    built += 1
            logger.info(f"Built {built} embeddings")
            return built
        except Exception as e:
            logger.error(f"Embedding build failed: {e}")
            return 0


def _fields_to_categories(fields: List[str]) -> List[str]:
    mapping = {
        "Computer Science": "cs.AI",
        "Natural Language Processing": "cs.CL",
        "Computer Vision": "cs.CV",
        "Machine Learning": "cs.LG",
        "Artificial Intelligence": "cs.AI",
        "Statistics": "stat.ML",
    }
    cats = []
    for f in fields:
        if f in mapping and mapping[f] not in cats:
            cats.append(mapping[f])
    return cats or ["cs.AI"]


if __name__ == "__main__":
    collector = SemanticScholarCollector()
    results = collector.run_backfill(target_per_category=60, year_start=2024)
    print("Backfill results:", results)
    total = sum(results.values())
    print(f"Total: {total} new papers")
    if total > 0:
        collector.build_embeddings_for_new()

import time
from typing import List, Dict, Any, Optional

from src.collector.arxiv_collector import ArxivCollector
from src.summarizer.note_generator import NoteGenerator
from src.database import PaperDBManager
from src.utils.logger import get_logger
from src.utils.config import load_config

logger = get_logger(__name__)


class BackfillCollector:
    def __init__(self, db_manager: Optional[PaperDBManager] = None, config: dict = None):
        self.config = config or load_config()
        self.db = db_manager or PaperDBManager(self.config["database"]["path"])
        self.collector = ArxivCollector(db_manager=self.db, config=self.config)
        self.note_gen = NoteGenerator(config=self.config)

    def run_backfill(self, category: str = None, max_papers: int = 50) -> List[Dict[str, Any]]:
        all_saved = []
        if category:
            categories = [{"id": category}]
        else:
            categories = self.config.get("categories", [])
        for cat_info in categories:
            cat_id = cat_info["id"] if isinstance(cat_info, dict) else cat_info
            logger.info(f"Backfilling category: {cat_id}, max={max_papers}")
            try:
                papers = self.collector.search_papers(cat_id, max_results=max_papers)
                saved_count = 0
                for paper in papers:
                    added = self.db.add_paper(paper)
                    if added:
                        self.note_gen.save_note(paper)
                        all_saved.append(paper)
                        saved_count += 1
                    time.sleep(0.1)
                logger.info(f"Backfill {cat_id}: saved {saved_count}/{len(papers)} papers")
            except Exception as e:
                logger.error(f"Backfill failed for {cat_id}: {e}")
            time.sleep(3)
        return all_saved

    def run_backfill_with_embeddings(self, category: str = None, max_papers: int = 50) -> int:
        papers = self.run_backfill(category=category, max_papers=max_papers)
        if not papers:
            logger.info("No new papers to embed")
            return 0
        try:
            from src.recommender import ContentRecommender
            recommender = ContentRecommender(db_manager=self.db, config=self.config)
            built = recommender.build_embeddings(papers)
            logger.info(f"Built {built} embeddings")
            return built
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return 0


if __name__ == "__main__":
    backfiller = BackfillCollector()
    backfiller.run_backfill(max_papers=20)

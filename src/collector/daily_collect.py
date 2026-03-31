import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.collector.arxiv_collector import ArxivCollector
from src.summarizer.note_generator import NoteGenerator
from src.database import PaperDBManager
from src.utils.logger import get_logger
from src.utils.config import load_config

logger = get_logger(__name__)


class DailyCollector:
    def __init__(self, config: dict = None):
        self.config = config or load_config()
        self.db = PaperDBManager(self.config["database"]["path"])
        self.collector = ArxivCollector(db_manager=self.db, config=self.config)
        self.note_gen = NoteGenerator(config=self.config)

    def run(self) -> Dict[str, Any]:
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info(f"Daily collection started: {today}")
        all_collected = []
        categories = self.config.get("categories", [])
        max_daily = self.config["collection"].get("max_results_daily", 20)
        for cat_info in categories:
            cat_id = cat_info["id"] if isinstance(cat_info, dict) else cat_info
            try:
                papers = self.collector.search_papers(cat_id, max_results=max_daily)
                for paper in papers:
                    added = self.db.add_paper(paper)
                    if added:
                        self.note_gen.save_note(paper)
                        all_collected.append(paper)
                    time.sleep(0.1)
                logger.info(f"Collected {len(papers)} papers from {cat_id}")
            except Exception as e:
                logger.error(f"Collection failed for {cat_id}: {e}")
            time.sleep(3)
        daily_log_path = self._save_daily_log(today, all_collected)
        try:
            from src.recommender import ContentRecommender
            rec = ContentRecommender(db_manager=self.db, config=self.config)
            rec.build_embeddings(all_collected)
        except Exception as e:
            logger.warning(f"Embedding update skipped: {e}")

        # Enrich newly collected papers with citation counts from Semantic Scholar
        if all_collected:
            try:
                from src.collector.citation_enricher import CitationEnricher
                enricher = CitationEnricher(self.db)
                enriched = enricher.enrich_papers(all_collected)
                logger.info(f"Citation enrichment: {enriched}/{len(all_collected)} papers updated")
            except Exception as e:
                logger.warning(f"Citation enrichment skipped: {e}")
        result = {
            "date": today,
            "total_collected": len(all_collected),
            "daily_log_path": daily_log_path,
        }
        logger.info(f"Daily collection complete: {len(all_collected)} new papers")
        return result

    def _save_daily_log(self, date: str, papers: List[Dict[str, Any]]) -> str:
        daily_path = self.config["obsidian"]["daily_path"]
        os.makedirs(daily_path, exist_ok=True)
        log_path = os.path.join(daily_path, f"{date}.md")
        lines = [
            f"# Daily Paper Collection — {date}",
            "",
            f"**Total new papers**: {len(papers)}",
            "",
            "## Papers Collected",
            "",
        ]
        for p in papers:
            arxiv_id = p["arxiv_id"]
            title = p["title"]
            cats = ", ".join(p.get("categories", [])[:2])
            lines.append(f"- [[{arxiv_id}]] — {title} `{cats}`")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info(f"Daily log saved: {log_path}")
        return log_path


if __name__ == "__main__":
    collector = DailyCollector()
    result = collector.run()
    print(f"Collected {result['total_collected']} papers")

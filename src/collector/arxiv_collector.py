import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import arxiv

from src.database import PaperDBManager
from src.utils.logger import get_logger
from src.utils.config import load_config

logger = get_logger(__name__)


class ArxivCollector:
    def __init__(self, db_manager: Optional[PaperDBManager] = None, config: Optional[dict] = None):
        self.config = config or load_config()
        self.db = db_manager or PaperDBManager(self.config["database"]["path"])
        self.rate_limit = self.config["collection"].get("rate_limit_seconds", 3)
        self.client = arxiv.Client()

    def search_papers(
        self, category: str, max_results: int = 20, query: str = None
    ) -> List[Dict[str, Any]]:
        search_query = query or f"cat:{category}"
        logger.info(f"Searching arXiv: query='{search_query}', max={max_results}")
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        papers = []
        try:
            for result in self.client.results(search):
                paper = self._result_to_dict(result)
                papers.append(paper)
                time.sleep(0.1)
        except Exception as e:
            logger.error(f"arXiv search failed for {category}: {e}")
        logger.info(f"Found {len(papers)} papers for {category}")
        return papers

    def _result_to_dict(self, result: arxiv.Result) -> Dict[str, Any]:
        arxiv_id = result.entry_id.split("/")[-1]
        if "v" in arxiv_id:
            arxiv_id = arxiv_id.split("v")[0]
        authors = [a.name for a in result.authors]
        categories = result.categories if result.categories else []
        date_str = ""
        if result.published:
            if hasattr(result.published, "astimezone"):
                date_str = result.published.astimezone(timezone.utc).strftime("%Y-%m-%d")
            else:
                date_str = str(result.published)[:10]
        return {
            "arxiv_id": arxiv_id,
            "title": result.title,
            "authors": authors,
            "abstract": result.summary,
            "categories": categories,
            "date": date_str,
            "pdf_url": result.pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
        }

    def collect_and_save(
        self, category: str, max_results: int = 20
    ) -> List[Dict[str, Any]]:
        papers = self.search_papers(category, max_results)
        saved = []
        for paper in papers:
            added = self.db.add_paper(paper)
            if added:
                saved.append(paper)
            time.sleep(0.05)
        logger.info(f"Saved {len(saved)}/{len(papers)} new papers for {category}")
        return saved

    def collect_all_categories(self, max_per_category: int = 20) -> List[Dict[str, Any]]:
        all_saved = []
        categories = self.config.get("categories", [])
        for cat_info in categories:
            cat_id = cat_info["id"] if isinstance(cat_info, dict) else cat_info
            saved = self.collect_and_save(cat_id, max_per_category)
            all_saved.extend(saved)
            time.sleep(self.rate_limit)
        return all_saved

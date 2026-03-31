"""Enrich arXiv papers with citation counts via Semantic Scholar batch API.

Semantic Scholar supports direct arXiv ID lookup:
  POST https://api.semanticscholar.org/graph/v1/paper/batch
  Body: {"ids": ["arXiv:2603.XXXXX", ...]}
  Rate limit: 100 req/min (unauthenticated), batch up to 500 papers
"""
import time
import logging
from typing import List, Dict, Any

import requests

from src.database import PaperDBManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

S2_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
S2_FIELDS = "citationCount,year,venue,externalIds"
BATCH_SIZE = 100   # stay well under 500 limit
DELAY = 1.2        # ~50 req/min to avoid 429


def _s2_ids(arxiv_ids: List[str]) -> List[str]:
    """Convert bare arXiv IDs to Semantic Scholar arXiv: prefix format."""
    result = []
    for aid in arxiv_ids:
        # Skip HAI synthetic IDs
        if aid.startswith("hai."):
            continue
        result.append(f"arXiv:{aid}")
    return result


def fetch_citations_batch(arxiv_ids: List[str]) -> Dict[str, int]:
    """Return {arxiv_id: citation_count} for a list of arXiv IDs."""
    s2_ids = _s2_ids(arxiv_ids)
    if not s2_ids:
        return {}

    results: Dict[str, int] = {}
    for i in range(0, len(s2_ids), BATCH_SIZE):
        chunk = s2_ids[i: i + BATCH_SIZE]
        try:
            resp = requests.post(
                S2_BATCH_URL,
                params={"fields": S2_FIELDS},
                json={"ids": chunk},
                timeout=30,
            )
            if resp.status_code == 429:
                logger.warning("Semantic Scholar rate limit hit, sleeping 60s")
                time.sleep(60)
                resp = requests.post(
                    S2_BATCH_URL,
                    params={"fields": S2_FIELDS},
                    json={"ids": chunk},
                    timeout=30,
                )
            resp.raise_for_status()
            for item in resp.json():
                if not item:
                    continue
                ext = item.get("externalIds") or {}
                aid = ext.get("ArXiv")
                if aid and item.get("citationCount") is not None:
                    results[aid] = item["citationCount"]
                    # Also capture venue if present
                    if item.get("venue"):
                        results[f"__venue__{aid}"] = item["venue"]
        except Exception as e:
            logger.error(f"S2 batch request failed (chunk {i}): {e}")
        time.sleep(DELAY)

    logger.info(f"S2 citation fetch: {len(results)} papers enriched out of {len(s2_ids)} requested")
    return results


class CitationEnricher:
    def __init__(self, db_manager: PaperDBManager):
        self.db = db_manager

    def enrich_papers(self, papers: List[Dict[str, Any]]) -> int:
        """Fetch and store citation counts for a list of paper dicts. Returns count updated."""
        arxiv_ids = [p["arxiv_id"] for p in papers if not p["arxiv_id"].startswith("hai.")]
        if not arxiv_ids:
            return 0

        citations = fetch_citations_batch(arxiv_ids)
        updated = 0
        for aid in arxiv_ids:
            if aid in citations:
                update: Dict[str, Any] = {"citation_count": citations[aid]}
                venue_key = f"__venue__{aid}"
                if venue_key in citations:
                    update["venue"] = citations[venue_key]
                self.db.update_paper(aid, update)
                updated += 1

        logger.info(f"Citation enrichment complete: {updated}/{len(arxiv_ids)} papers updated")
        return updated

    def enrich_recent(self, days: int = 7) -> int:
        """Enrich arXiv papers added in the last N days that still have citation_count=0."""
        import sqlite3
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT arxiv_id FROM papers
               WHERE date >= ? AND (citation_count IS NULL OR citation_count = 0)
               AND arxiv_id NOT LIKE 'hai.%'""",
            (cutoff,),
        ).fetchall()
        conn.close()
        papers = [{"arxiv_id": r["arxiv_id"]} for r in rows]
        if not papers:
            logger.info("No recent papers need citation enrichment")
            return 0
        logger.info(f"Enriching citations for {len(papers)} recent papers (last {days} days)")
        return self.enrich_papers(papers)

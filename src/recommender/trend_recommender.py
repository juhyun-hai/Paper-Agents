import json
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.database import PaperDBManager
from src.utils.logger import get_logger
from src.utils.config import load_config

logger = get_logger(__name__)


class TrendAnalyzer:
    def __init__(self, db_manager: Optional[PaperDBManager] = None, config: dict = None):
        self.config = config or load_config()
        self.db = db_manager or PaperDBManager(self.config["database"]["path"])

    def get_trending_papers(self, days: int = 30, top_k: int = 10) -> List[Dict[str, Any]]:
        """Rank papers by trending score: citation velocity + recency + topic volume + hot keywords.

        For brand-new papers (citation_count=0) topic_volume acts as the main signal:
        papers whose keywords appear frequently among this week's new papers rank higher.
        """
        import math, sqlite3
        all_papers = self.db.get_all_papers()
        now = datetime.now()

        # Collect hot topic keywords from last 7 days
        hot_keywords: set = set()
        try:
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cutoff_ht = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            rows = conn.execute(
                "SELECT title, tech_name FROM hot_topics WHERE date >= ?", (cutoff_ht,)
            ).fetchall()
            conn.close()
            for r in rows:
                for word in (r["title"] + " " + r["tech_name"]).lower().split():
                    if len(word) > 3:
                        hot_keywords.add(word)
        except Exception:
            pass

        # Build topic volume index: word → count among papers in last 14 days
        # This lets us rank citation-less new papers by how "crowded" their topic is
        cutoff_vol = (now - timedelta(days=14)).strftime("%Y-%m-%d")
        recent_texts = [
            (p.get("title", "") + " " + (p.get("abstract") or "")[:200]).lower()
            for p in all_papers
            if p.get("date", "") >= cutoff_vol
        ]
        topic_word_freq: Counter = Counter()
        stopwords = {"the", "and", "for", "with", "this", "that", "from", "are",
                     "paper", "model", "method", "approach", "based", "using", "show"}
        for text in recent_texts:
            for word in text.split():
                word = word.strip(".,;:()[]")
                if len(word) >= 4 and word not in stopwords:
                    topic_word_freq[word] += 1
        max_freq = max(topic_word_freq.values(), default=1)

        def topic_volume_score(paper: dict) -> float:
            """How much is this paper's topic being discussed in recent papers (0-1)."""
            text = (paper.get("title", "") + " " + (paper.get("abstract") or "")[:200]).lower()
            words = [w.strip(".,;:()[]") for w in text.split() if len(w.strip(".,;:()[]")) >= 4]
            if not words:
                return 0.0
            score = sum(topic_word_freq.get(w, 0) for w in words) / len(words)
            return min(1.0, score / max(1, max_freq * 0.3))

        def trending_score(paper: dict) -> float:
            pub_date = paper.get("date", "")
            citations = paper.get("citation_count") or 0
            try:
                pub = datetime.strptime(pub_date, "%Y-%m-%d")
                age_days = max(1, (now - pub).days)
            except Exception:
                age_days = 365

            # Citation velocity: log(citations) / log(age) neutralizes age bias.
            # Papers with 0 citations score 0 here — topic_volume fills the gap.
            velocity = math.log1p(citations) / math.log1p(age_days + 1)

            # Recency: mild decay — 0.88 at 7 days, 0.51 at 30 days, 0.26 at 60 days
            recency = math.exp(-age_days / 30)

            # Topic volume: how many recent papers share this paper's keywords
            # Acts as surrogate for citation velocity when paper is too new to have citations
            topic_vol = topic_volume_score(paper)

            # Hot-topic keyword bonus
            if hot_keywords:
                text = (paper.get("title", "") + " " + (paper.get("abstract") or "")[:300]).lower()
                matches = sum(1 for kw in hot_keywords if kw in text)
                keyword_score = min(1.0, matches / max(1, len(hot_keywords) * 0.1))
            else:
                keyword_score = 0.0

            # Papers with citations: velocity leads. Papers without: topic volume + recency lead.
            if citations > 0:
                return 0.50 * velocity + 0.20 * recency + 0.20 * topic_vol + 0.10 * keyword_score
            else:
                return 0.45 * topic_vol + 0.35 * recency + 0.20 * keyword_score

        # Only consider papers from the last `days` window
        cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        candidates = [p for p in all_papers if p.get("date", "") >= cutoff]
        if len(candidates) < top_k:
            cutoff90 = (now - timedelta(days=90)).strftime("%Y-%m-%d")
            candidates = [p for p in all_papers if p.get("date", "") >= cutoff90]
        candidates.sort(key=trending_score, reverse=True)
        return candidates[:top_k]

    def get_category_stats(self) -> Dict[str, int]:
        all_papers = self.db.get_all_papers()
        cat_counter: Counter = Counter()
        for paper in all_papers:
            for cat in paper.get("categories", []):
                cat_counter[cat] += 1
        return dict(cat_counter.most_common())

    def get_keyword_trends(self, days: int = 30) -> Dict[str, int]:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        all_papers = self.db.get_all_papers()
        recent = [p for p in all_papers if p.get("date", "") >= cutoff]
        keyword_counter: Counter = Counter()
        keywords_config = self.config.get("keywords", {})
        for paper in recent:
            text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
            for group, kws in keywords_config.items():
                for kw in kws:
                    if kw.lower() in text:
                        keyword_counter[kw] += 1
        return dict(keyword_counter.most_common(20))

    def get_weekly_summary(self) -> Dict[str, Any]:
        stats = self.get_category_stats()
        trending = self.get_trending_papers(days=7, top_k=5)
        keywords = self.get_keyword_trends(days=7)
        total = self.db.count_papers()
        return {
            "total_papers": total,
            "category_stats": stats,
            "trending_papers": trending,
            "trending_keywords": keywords,
        }

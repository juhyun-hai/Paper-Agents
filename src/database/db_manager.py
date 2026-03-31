import sqlite3
import json
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

from .models import CREATE_PAPERS_TABLE, CREATE_TAGS_TABLE, CREATE_HOT_TOPICS_TABLE, CREATE_FEEDBACK_TABLE
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PaperDBManager:
    def __init__(self, db_path: str = "data/paper_db.sqlite"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        from .models import MIGRATE_ADD_COLUMNS
        with self._get_conn() as conn:
            conn.execute(CREATE_PAPERS_TABLE)
            conn.execute(CREATE_TAGS_TABLE)
            conn.execute(CREATE_HOT_TOPICS_TABLE)
            conn.execute(CREATE_FEEDBACK_TABLE)
            # Run migrations (idempotent - ignore errors if column already exists)
            for sql in MIGRATE_ADD_COLUMNS:
                try:
                    conn.execute(sql)
                except Exception:
                    pass
            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def add_paper(self, paper: Dict[str, Any]) -> bool:
        if self.paper_exists(paper["arxiv_id"]):
            logger.debug(f"Paper {paper['arxiv_id']} already exists, skipping")
            return False
        authors = json.dumps(paper.get("authors", []), ensure_ascii=False)
        categories = json.dumps(paper.get("categories", []), ensure_ascii=False)
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT INTO papers
                       (arxiv_id, title, authors, abstract, categories, date, pdf_url, status, citation_count, venue)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        paper["arxiv_id"],
                        paper["title"],
                        authors,
                        paper.get("abstract", ""),
                        categories,
                        paper.get("date", ""),
                        paper.get("pdf_url", ""),
                        paper.get("status", "unread"),
                        paper.get("citation_count", 0),
                        paper.get("venue", ""),
                    ),
                )
                conn.commit()
            logger.info(f"Added paper: {paper['arxiv_id']} - {paper['title'][:60]}")
            return True
        except Exception as e:
            logger.error(f"Failed to add paper {paper['arxiv_id']}: {e}")
            return False

    def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)
            ).fetchone()
        if row is None:
            return None
        paper = dict(row)
        paper["authors"] = json.loads(paper["authors"])
        paper["categories"] = json.loads(paper["categories"])
        return paper

    def paper_exists(self, arxiv_id: str) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM papers WHERE arxiv_id = ?", (arxiv_id,)
            ).fetchone()
        return row is not None

    def get_all_papers(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM papers ORDER BY date DESC").fetchall()
        papers = []
        for row in rows:
            p = dict(row)
            p["authors"] = json.loads(p["authors"])
            p["categories"] = json.loads(p["categories"])
            papers.append(p)
        return papers

    def update_paper(self, arxiv_id: str, updates: Dict[str, Any]) -> bool:
        allowed = {"rating", "status", "embedding_path", "citation_count", "venue"}
        fields = {k: v for k, v in updates.items() if k in allowed}
        if not fields:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [arxiv_id]
        try:
            with self._get_conn() as conn:
                conn.execute(
                    f"UPDATE papers SET {set_clause}, updated_at = datetime('now') WHERE arxiv_id = ?",
                    values,
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update paper {arxiv_id}: {e}")
            return False

    def get_papers_by_category(self, category: str) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM papers WHERE categories LIKE ? ORDER BY date DESC",
                (f'%"{category}"%',),
            ).fetchall()
        papers = []
        for row in rows:
            p = dict(row)
            p["authors"] = json.loads(p["authors"])
            p["categories"] = json.loads(p["categories"])
            papers.append(p)
        return papers

    def get_papers_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM papers WHERE date >= ? AND date <= ? ORDER BY date DESC",
                (start_date, end_date),
            ).fetchall()
        papers = []
        for row in rows:
            p = dict(row)
            p["authors"] = json.loads(p["authors"])
            p["categories"] = json.loads(p["categories"])
            papers.append(p)
        return papers

    def count_papers(self) -> int:
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM papers").fetchone()
        return row["cnt"]

    def delete_paper(self, arxiv_id: str) -> bool:
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM papers WHERE arxiv_id = ?", (arxiv_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete paper {arxiv_id}: {e}")
            return False

    def add_hot_topic(self, topic: Dict[str, Any]) -> bool:
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO hot_topics
                       (date, title, tech_name, summary, key_results, github_url, paper_url, hf_url, source, upvotes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        topic.get("date", ""),
                        topic.get("title", ""),
                        topic.get("tech_name", ""),
                        topic.get("summary", ""),
                        topic.get("key_results", ""),
                        topic.get("github_url", ""),
                        topic.get("paper_url", ""),
                        topic.get("hf_url", ""),
                        topic.get("source", ""),
                        topic.get("upvotes", 0),
                    ),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.warning(f"Failed to add hot topic: {e}")
            return False

    def get_hot_topics(self, date: str) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM hot_topics WHERE date=? ORDER BY id ASC", (date,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_recent_hot_topics(self, days: int = 7) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM hot_topics
                   WHERE date >= date('now', ?)
                   ORDER BY date DESC, id ASC""",
                (f"-{days} days",),
            ).fetchall()
        return [dict(r) for r in rows]

"""
Repository for paper ingestion operations.

Handles upsert logic for papers and paper_versions tables.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


class IngestRepository:
    """Repository for ingesting papers into the database."""

    def __init__(self, conn: psycopg.Connection):
        """
        Initialize repository with database connection.

        Args:
            conn: Active psycopg connection
        """
        self.conn = conn

    def ingest_paper(self, paper_data: Dict[str, Any]) -> tuple[int, int]:
        """
        Ingest a paper into the database.

        Performs the following operations in a transaction:
        1. Upsert papers table (by arxiv_id)
        2. Upsert paper_versions table (by arxiv_id + version)
        3. Update papers.latest_version_id

        Args:
            paper_data: Dictionary containing paper metadata from arXiv

        Returns:
            Tuple of (paper_id, paper_version_id)
        """
        arxiv_id = paper_data["arxiv_id"]
        version = paper_data["version"]

        with self.conn.cursor() as cur:
            try:
                # Step 1: Upsert papers table
                paper_id = self._upsert_paper(cur, paper_data)

                # Step 2: Upsert paper_versions table
                version_id = self._upsert_paper_version(cur, paper_id, paper_data)

                # Step 3: Update latest_version_id if this is the newest version
                self._update_latest_version(cur, paper_id, version_id, version)

                self.conn.commit()
                logger.debug(
                    f"Ingested {arxiv_id} {version}: "
                    f"paper_id={paper_id}, version_id={version_id}"
                )

                return paper_id, version_id

            except Exception as e:
                self.conn.rollback()
                logger.error(f"Failed to ingest {arxiv_id} {version}: {e}")
                raise

    def _upsert_paper(
        self, cur: psycopg.Cursor, paper_data: Dict[str, Any]
    ) -> int:
        """
        Upsert papers table (canonical paper entity).

        Args:
            cur: Database cursor
            paper_data: Paper metadata

        Returns:
            paper_id
        """
        arxiv_id = paper_data["arxiv_id"]
        title = paper_data["title"]
        primary_category = paper_data.get("primary_category")
        published_date = paper_data["published_date"]
        updated_date = paper_data.get("updated_date")

        query = """
            INSERT INTO papers (
                arxiv_id, title, primary_category, published_date, updated_date
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (arxiv_id)
            DO UPDATE SET
                title = EXCLUDED.title,
                primary_category = EXCLUDED.primary_category,
                updated_date = EXCLUDED.updated_date,
                updated_at = NOW()
            RETURNING id
        """

        cur.execute(
            query,
            (arxiv_id, title, primary_category, published_date, updated_date),
        )
        result = cur.fetchone()
        return result["id"]

    def _upsert_paper_version(
        self, cur: psycopg.Cursor, paper_id: int, paper_data: Dict[str, Any]
    ) -> int:
        """
        Upsert paper_versions table (version-specific data).

        Args:
            cur: Database cursor
            paper_id: ID from papers table
            paper_data: Paper metadata

        Returns:
            paper_version_id
        """
        arxiv_id = paper_data["arxiv_id"]
        version = paper_data["version"]
        title = paper_data["title"]
        authors = json.dumps(paper_data["authors"])
        abstract = paper_data["abstract"]
        categories = json.dumps(paper_data["categories"])
        pdf_url = paper_data.get("pdf_url")
        html_url = paper_data.get("html_url")
        version_published_date = paper_data["published_date"]
        updated_date = paper_data.get("updated_date")

        query = """
            INSERT INTO paper_versions (
                paper_id, arxiv_id, version, title, authors, abstract,
                categories, pdf_url, html_url, version_published_date, updated_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (arxiv_id, version)
            DO UPDATE SET
                title = EXCLUDED.title,
                authors = EXCLUDED.authors,
                abstract = EXCLUDED.abstract,
                categories = EXCLUDED.categories,
                pdf_url = EXCLUDED.pdf_url,
                html_url = EXCLUDED.html_url,
                updated_date = EXCLUDED.updated_date,
                updated_at = NOW()
            RETURNING id
        """

        cur.execute(
            query,
            (
                paper_id,
                arxiv_id,
                version,
                title,
                authors,
                abstract,
                categories,
                pdf_url,
                html_url,
                version_published_date,
                updated_date,
            ),
        )
        result = cur.fetchone()
        return result["id"]

    def _update_latest_version(
        self, cur: psycopg.Cursor, paper_id: int, version_id: int, version: str
    ):
        """
        Update papers.latest_version_id to point to the newest version.

        Args:
            cur: Database cursor
            paper_id: ID from papers table
            version_id: ID from paper_versions table
            version: Version string (e.g., "v1", "v2")
        """
        # Get current latest version
        cur.execute(
            """
            SELECT pv.version
            FROM papers p
            LEFT JOIN paper_versions pv ON p.latest_version_id = pv.id
            WHERE p.id = %s
            """,
            (paper_id,),
        )
        result = cur.fetchone()
        current_latest = result["version"] if result and result["version"] else None

        # Compare versions (e.g., "v2" > "v1")
        if current_latest is None or self._compare_versions(version, current_latest) > 0:
            cur.execute(
                """
                UPDATE papers
                SET latest_version_id = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (version_id, paper_id),
            )
            logger.debug(
                f"Updated latest_version_id for paper {paper_id}: "
                f"{current_latest} -> {version}"
            )

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.

        Args:
            v1: First version (e.g., "v2")
            v2: Second version (e.g., "v1")

        Returns:
            1 if v1 > v2, -1 if v1 < v2, 0 if equal
        """
        # Extract numeric part (e.g., "v2" -> 2)
        n1 = int(v1[1:])
        n2 = int(v2[1:])

        if n1 > n2:
            return 1
        elif n1 < n2:
            return -1
        else:
            return 0

    def get_stats(self) -> Dict[str, int]:
        """
        Get ingestion statistics.

        Returns:
            Dictionary with counts of papers and versions
        """
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM papers")
            papers_count = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) as count FROM paper_versions")
            versions_count = cur.fetchone()["count"]

            return {
                "total_papers": papers_count,
                "total_versions": versions_count,
            }

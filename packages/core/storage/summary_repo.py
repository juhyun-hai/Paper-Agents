"""
Repository for summary storage operations.
"""

import logging
import json
from typing import Dict, Any, Optional
import psycopg

logger = logging.getLogger(__name__)


class SummaryRepository:
    """Repository for managing paper summaries."""

    def __init__(self, conn: psycopg.Connection):
        """
        Initialize repository with database connection.

        Args:
            conn: Active psycopg connection
        """
        self.conn = conn

    def upsert_summary(
        self,
        paper_version_id: int,
        summary_type: str,
        summary_data: Dict[str, Any],
        model_used: str = "dummy",
        tokens_used: Optional[int] = None,
    ) -> int:
        """
        Insert or update a summary for a paper version.

        Args:
            paper_version_id: ID from paper_versions table
            summary_type: "light" or "deep"
            summary_data: Summary dictionary (must match schema)
            model_used: Model identifier (e.g., "dummy", "claude-sonnet-4-5")
            tokens_used: Optional token count for cost tracking

        Returns:
            summary_id
        """
        if summary_type not in ("light", "deep", "deep_pdf"):
            raise ValueError(
                f"Invalid summary_type: {summary_type!r}. "
                "Must be 'light', 'deep', or 'deep_pdf'."
            )

        with self.conn.cursor() as cur:
            try:
                query = """
                    INSERT INTO summaries (
                        paper_version_id, summary_type, summary_data,
                        model_used, tokens_used
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (paper_version_id, summary_type)
                    DO UPDATE SET
                        summary_data = EXCLUDED.summary_data,
                        model_used = EXCLUDED.model_used,
                        tokens_used = EXCLUDED.tokens_used,
                        updated_at = NOW()
                    RETURNING id
                """

                cur.execute(
                    query,
                    (
                        paper_version_id,
                        summary_type,
                        json.dumps(summary_data),
                        model_used,
                        tokens_used,
                    ),
                )

                result = cur.fetchone()
                self.conn.commit()

                summary_id = result["id"]
                logger.debug(
                    f"Upserted {summary_type} summary for version_id={paper_version_id}, "
                    f"summary_id={summary_id}"
                )

                return summary_id

            except Exception as e:
                self.conn.rollback()
                logger.error(
                    f"Failed to upsert {summary_type} summary for version_id={paper_version_id}: {e}"
                )
                raise

    def upsert_light_summary(
        self,
        paper_version_id: int,
        summary_data: Dict[str, Any],
        model_used: str = "dummy",
        tokens_used: Optional[int] = None,
    ) -> int:
        """
        Insert or update a light summary for a paper version.

        Deprecated: Use upsert_summary() with summary_type="light" instead.

        Args:
            paper_version_id: ID from paper_versions table
            summary_data: Summary dictionary (must match schema)
            model_used: Model identifier (e.g., "dummy", "claude-sonnet-4-5")
            tokens_used: Optional token count for cost tracking

        Returns:
            summary_id
        """
        return self.upsert_summary(
            paper_version_id=paper_version_id,
            summary_type="light",
            summary_data=summary_data,
            model_used=model_used,
            tokens_used=tokens_used,
        )

    def upsert_deep_summary(
        self,
        paper_version_id: int,
        summary_data: Dict[str, Any],
        model_used: str,
        tokens_used: Optional[int] = None,
    ) -> int:
        """
        Insert or update a deep summary for a paper version.

        Deprecated: Use upsert_summary() with summary_type="deep" instead.

        Args:
            paper_version_id: ID from paper_versions table
            summary_data: Summary dictionary (must match schema)
            model_used: Model identifier
            tokens_used: Optional token count for cost tracking

        Returns:
            summary_id
        """
        return self.upsert_summary(
            paper_version_id=paper_version_id,
            summary_type="deep",
            summary_data=summary_data,
            model_used=model_used,
            tokens_used=tokens_used,
        )

    def get_summary(
        self, paper_version_id: int, summary_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a summary for a paper version.

        Args:
            paper_version_id: ID from paper_versions table
            summary_type: "light" or "deep"

        Returns:
            Summary data dictionary or None if not found
        """
        with self.conn.cursor() as cur:
            query = """
                SELECT summary_data
                FROM summaries
                WHERE paper_version_id = %s AND summary_type = %s
            """

            cur.execute(query, (paper_version_id, summary_type))
            result = cur.fetchone()

            if result:
                return result["summary_data"]
            else:
                return None

    def get_versions_without_summary(
        self, summary_type: str, limit: int = 50
    ) -> list[Dict[str, Any]]:
        """
        Get paper versions that don't have a summary of the specified type.

        Args:
            summary_type: "light" or "deep"
            limit: Maximum number of results

        Returns:
            List of paper_version dictionaries
        """
        with self.conn.cursor() as cur:
            query = """
                SELECT
                    pv.id,
                    pv.arxiv_id,
                    pv.version,
                    pv.title,
                    pv.abstract,
                    pv.categories,
                    pv.pdf_url
                FROM paper_versions pv
                LEFT JOIN summaries s ON pv.id = s.paper_version_id
                    AND s.summary_type = %s
                WHERE s.id IS NULL
                ORDER BY pv.version_published_date DESC
                LIMIT %s
            """

            cur.execute(query, (summary_type, limit))
            results = cur.fetchall()

            return results

    def get_stats(self) -> Dict[str, int]:
        """
        Get summary statistics.

        Returns:
            Dictionary with counts
        """
        with self.conn.cursor() as cur:
            # Count light summaries
            cur.execute(
                "SELECT COUNT(*) as count FROM summaries WHERE summary_type = 'light'"
            )
            light_count = cur.fetchone()["count"]

            # Count deep summaries
            cur.execute(
                "SELECT COUNT(*) as count FROM summaries WHERE summary_type = 'deep'"
            )
            deep_count = cur.fetchone()["count"]

            # Count deep_pdf summaries
            cur.execute(
                "SELECT COUNT(*) as count FROM summaries WHERE summary_type = 'deep_pdf'"
            )
            deep_pdf_count = cur.fetchone()["count"]

            # Count paper versions
            cur.execute("SELECT COUNT(*) as count FROM paper_versions")
            versions_count = cur.fetchone()["count"]

            return {
                "total_versions": versions_count,
                "light_summaries": light_count,
                "deep_summaries": deep_count,
                "deep_pdf_summaries": deep_pdf_count,
                "pending_light": versions_count - light_count,
                "pending_deep": versions_count - deep_count,
                "pending_deep_pdf": versions_count - deep_pdf_count,
            }

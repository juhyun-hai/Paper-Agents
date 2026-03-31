"""
Repository for keyword_stats table operations.
"""

import logging
from datetime import date

import psycopg

logger = logging.getLogger(__name__)


def upsert_keyword_counts(
    conn: psycopg.Connection,
    day: date,
    source: str,
    counts: dict[str, int],
) -> int:
    """
    Upsert keyword counts into keyword_stats.

    Idempotent: existing rows for the same (day, keyword, source) are overwritten,
    not accumulated. Caller is responsible for deleting stale rows before calling.

    Args:
        conn:   Active psycopg connection.
        day:    Date the counts belong to.
        source: One of 'title', 'abstract', 'llm'.
        counts: Mapping of keyword -> count to upsert.

    Returns:
        Number of rows processed.
    """
    if not counts:
        return 0

    query = """
        INSERT INTO keyword_stats (day, keyword, source, count)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (day, keyword, source)
        DO UPDATE SET count = EXCLUDED.count
    """

    rows = [(day, keyword, source, cnt) for keyword, cnt in counts.items()]

    with conn.cursor() as cur:
        cur.executemany(query, rows)

    conn.commit()
    logger.debug("Upserted %d keyword_stats rows  day=%s source=%s", len(rows), day, source)
    return len(rows)

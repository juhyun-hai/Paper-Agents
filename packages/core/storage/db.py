"""
Database connection management using psycopg v3.

Loads DATABASE_URL from environment and provides connection utilities.
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """
    Get DATABASE_URL from environment.

    Returns:
        Database connection URL

    Raises:
        ValueError: If DATABASE_URL not set
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL not set. Please set it in .env file or environment."
        )
    return url


@contextmanager
def get_connection() -> Generator[psycopg.Connection, None, None]:
    """
    Get a database connection with automatic cleanup.

    Yields:
        psycopg Connection object

    Example:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    database_url = get_database_url()
    conn = None

    try:
        conn = psycopg.connect(database_url, row_factory=dict_row)
        logger.debug("Database connection established")
        yield conn
    except psycopg.Error as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")


@contextmanager
def get_cursor(conn: psycopg.Connection) -> Generator[psycopg.Cursor, None, None]:
    """
    Get a cursor with automatic cleanup.

    Args:
        conn: Database connection

    Yields:
        psycopg Cursor object
    """
    try:
        with conn.cursor() as cur:
            yield cur
    except psycopg.Error as e:
        logger.error(f"Database cursor error: {e}")
        raise


def test_connection() -> bool:
    """
    Test database connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                logger.info("Database connection test: SUCCESS")
                return result is not None
    except Exception as e:
        logger.error(f"Database connection test: FAILED - {e}")
        return False

#!/usr/bin/env python3
"""
Initialize database schema.

Usage:
    python scripts/init_db.py
"""

import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
import psycopg

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize database schema from schema.sql."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not set in .env")
        sys.exit(1)

    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "schema.sql"
    )

    if not os.path.exists(schema_path):
        logger.error(f"Schema file not found: {schema_path}")
        sys.exit(1)

    logger.info(f"Reading schema from: {schema_path}")
    with open(schema_path, "r") as f:
        schema_sql = f.read()

    logger.info(f"Connecting to database...")
    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                logger.info("Executing schema...")
                cur.execute(schema_sql)
                conn.commit()
                logger.info("✓ Database schema initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Daily arXiv paper ingestion script.

Fetches papers from arXiv based on date range, categories, and optional keywords,
then stores them in PostgreSQL.

Usage:
    # Fetch papers from last 1 day (default categories)
    python scripts/run_daily_ingest.py --since 1d

    # Fetch papers from last 7 days (custom categories)
    python scripts/run_daily_ingest.py --since 7d --categories cs.AI,cs.CL

    # Fetch with keyword filtering
    python scripts/run_daily_ingest.py --since 3d --keywords "large language model,transformer"

    # Limit results
    python scripts/run_daily_ingest.py --since 1d --max-results 100

    # Test database connection
    python scripts/run_daily_ingest.py --test-db

Dependencies:
    pip install psycopg[binary] python-dotenv

Environment:
    DATABASE_URL=postgresql://user:password@localhost:5432/paper_agent
    ARXIV_EMAIL=your.email@example.com  # Optional but recommended
"""

import sys
import os
import logging
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from packages.core.connectors.arxiv import ArxivConnector, parse_since_arg
from packages.core.storage.db import get_connection, test_connection
from packages.core.storage.ingest_repo import IngestRepository

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


DEFAULT_CATEGORIES = ["cs.LG", "cs.CV", "cs.CL", "stat.ML"]


def main():
    """Main ingestion pipeline."""
    parser = argparse.ArgumentParser(
        description="Fetch and ingest arXiv papers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--since",
        type=str,
        default="1d",
        help="Fetch papers from last N days (e.g., 1d, 7d, 30d). Default: 1d",
    )

    parser.add_argument(
        "--categories",
        type=str,
        help=(
            "Comma-separated list of arXiv categories. "
            f"Default: {','.join(DEFAULT_CATEGORIES)}"
        ),
    )

    parser.add_argument(
        "--keywords",
        type=str,
        help="Comma-separated list of keywords to filter papers (AND logic)",
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=1000,
        help="Maximum number of papers to fetch. Default: 1000",
    )

    parser.add_argument(
        "--test-db",
        action="store_true",
        help="Test database connection and exit",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Test database connection if requested
    if args.test_db:
        logger.info("Testing database connection...")
        if test_connection():
            logger.info("✓ Database connection successful")
            sys.exit(0)
        else:
            logger.error("✗ Database connection failed")
            sys.exit(1)

    # Parse arguments
    try:
        since_days = parse_since_arg(args.since)
    except ValueError as e:
        logger.error(f"Invalid --since argument: {e}")
        sys.exit(1)

    categories = (
        args.categories.split(",") if args.categories else DEFAULT_CATEGORIES
    )
    keywords = args.keywords.split(",") if args.keywords else None

    logger.info("=" * 80)
    logger.info("arXiv Paper Ingestion Pipeline")
    logger.info("=" * 80)
    logger.info(f"Since: {since_days} days ago")
    logger.info(f"Categories: {categories}")
    logger.info(f"Keywords: {keywords if keywords else 'None'}")
    logger.info(f"Max results: {args.max_results}")
    logger.info("=" * 80)

    # Step 1: Fetch papers from arXiv
    logger.info("Step 1: Fetching papers from arXiv...")
    arxiv_email = os.getenv("ARXIV_EMAIL")
    connector = ArxivConnector(email=arxiv_email)

    try:
        papers = connector.fetch_papers(
            categories=categories,
            since_days=since_days,
            keywords=keywords,
            max_results=args.max_results,
        )
    except Exception as e:
        logger.error(f"Failed to fetch papers from arXiv: {e}")
        sys.exit(1)

    if not papers:
        logger.warning("No papers fetched. Exiting.")
        sys.exit(0)

    logger.info(f"✓ Fetched {len(papers)} papers from arXiv")

    # Step 2: Ingest papers into database
    logger.info("Step 2: Ingesting papers into database...")

    try:
        with get_connection() as conn:
            repo = IngestRepository(conn)

            ingested_count = 0
            error_count = 0

            for i, paper in enumerate(papers, 1):
                try:
                    paper_id, version_id = repo.ingest_paper(paper)
                    ingested_count += 1

                    if i % 10 == 0:
                        logger.info(
                            f"Progress: {i}/{len(papers)} papers processed "
                            f"({ingested_count} ingested, {error_count} errors)"
                        )

                except Exception as e:
                    error_count += 1
                    logger.error(
                        f"Failed to ingest {paper.get('arxiv_id', 'unknown')}: {e}"
                    )
                    continue

            # Final stats
            logger.info("=" * 80)
            logger.info("Ingestion Complete")
            logger.info("=" * 80)
            logger.info(f"Total fetched: {len(papers)}")
            logger.info(f"Successfully ingested: {ingested_count}")
            logger.info(f"Errors: {error_count}")

            # Database stats
            stats = repo.get_stats()
            logger.info(f"Database stats: {stats['total_papers']} papers, "
                       f"{stats['total_versions']} versions")
            logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)

    logger.info("✓ Ingestion pipeline completed successfully")


if __name__ == "__main__":
    main()

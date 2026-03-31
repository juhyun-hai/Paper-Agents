#!/usr/bin/env python3
"""
Generate summaries for papers without them.

This script selects paper_versions that don't have a summary of the specified type
and generates summaries using the chosen backend (dummy or vLLM).

Usage:
    # Generate light summaries (default)
    python scripts/run_light_summary.py --limit 50

    # Generate deep summaries using vLLM with 70B model
    python scripts/run_light_summary.py --summary-type deep --backend vllm --limit 10

    # Show statistics and exit
    python scripts/run_light_summary.py --stats

    # Debug mode
    python scripts/run_light_summary.py --limit 10 --debug --summary-type light

Dependencies:
    pip install psycopg[binary] python-dotenv

Environment:
    DATABASE_URL=postgresql://user:password@localhost:5432/paper_agent
    SUMMARY_BACKEND=dummy  # or vllm
    VLLM_BASE_URL=http://localhost:8000/v1  # if using vllm
    VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct  # if using vllm
"""

import sys
import os
import logging
import argparse
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from packages.core.storage.db import get_connection
from packages.core.storage.summary_repo import SummaryRepository
from packages.core.summarizers.light import summarize_light, validate_summary

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    """Main summarization pipeline."""
    parser = argparse.ArgumentParser(
        description="Generate summaries for papers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of papers to process. Default: 50",
    )

    parser.add_argument(
        "--summary-type",
        type=str,
        choices=["light", "deep"],
        default="light",
        help="Type of summary to generate. Default: light",
    )

    parser.add_argument(
        "--backend",
        type=str,
        choices=["dummy", "vllm"],
        help=(
            "Summarization backend to use. "
            "If not specified, uses SUMMARY_BACKEND env var (default: dummy)"
        ),
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show summary statistics and exit",
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

    # Determine backend and summary type
    backend = args.backend if args.backend else os.getenv("SUMMARY_BACKEND", "dummy")
    summary_type = args.summary_type

    logger.info("=" * 80)
    logger.info(f"Summary Generation Pipeline (Type: {summary_type}, Backend: {backend})")
    logger.info("=" * 80)

    try:
        with get_connection() as conn:
            repo = SummaryRepository(conn)

            # Show statistics if requested
            if args.stats:
                stats = repo.get_stats()
                logger.info("Summary Statistics:")
                logger.info(f"  Total paper versions: {stats['total_versions']}")
                logger.info(f"  Light summaries: {stats['light_summaries']}")
                logger.info(f"  Deep summaries: {stats['deep_summaries']}")
                logger.info(f"  Pending light: {stats['pending_light']}")
                logger.info(f"  Pending deep: {stats['pending_deep']}")
                sys.exit(0)

            # Get papers without summaries of the specified type
            logger.info(f"Fetching up to {args.limit} papers without '{summary_type}' summaries...")
            papers = repo.get_versions_without_summary(summary_type, limit=args.limit)

            if not papers:
                logger.info(f"No papers to process. All papers have '{summary_type}' summaries.")
                sys.exit(0)

            logger.info(f"Found {len(papers)} papers to process")
            logger.info("=" * 80)

            # Process each paper
            success_count = 0
            error_count = 0
            total_tokens = 0

            for i, paper in enumerate(papers, 1):
                arxiv_id = paper["arxiv_id"]
                version = paper["version"]
                version_id = paper["id"]

                try:
                    # Generate summary
                    logger.debug(f"Processing {arxiv_id} {version}...")

                    # Parse categories (stored as JSON array)
                    categories = paper["categories"]
                    if isinstance(categories, str):
                        categories = json.loads(categories)

                    summary, model_used, tokens_used = summarize_light(
                        title=paper["title"],
                        abstract=paper["abstract"],
                        categories=categories,
                        backend=backend,
                    )

                    # Validate summary
                    validate_summary(summary)

                    # Store in database
                    summary_id = repo.upsert_summary(
                        paper_version_id=version_id,
                        summary_type=summary_type,
                        summary_data=summary,
                        model_used=model_used,
                        tokens_used=tokens_used,
                    )

                    success_count += 1
                    if tokens_used:
                        total_tokens += tokens_used

                    # Log progress
                    if i % 10 == 0:
                        logger.info(
                            f"Progress: {i}/{len(papers)} papers processed "
                            f"({success_count} success, {error_count} errors)"
                        )

                    # Debug: show sample summary for first paper
                    if args.debug and i == 1:
                        logger.debug(f"Sample summary for {arxiv_id}:")
                        logger.debug(f"  Model: {model_used}")
                        logger.debug(f"  One-liner: {summary['one_liner']}")
                        logger.debug(f"  Keywords: {summary['keywords']}")
                        if tokens_used:
                            logger.debug(f"  Tokens: {tokens_used}")

                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to process {arxiv_id} {version}: {e}")
                    continue

            # Final statistics
            logger.info("=" * 80)
            logger.info(f"Summary Generation Complete ({summary_type.capitalize()})")
            logger.info("=" * 80)
            logger.info(f"Summary type: {summary_type}")
            logger.info(f"Backend: {backend}")
            logger.info(f"Total processed: {len(papers)}")
            logger.info(f"Successful: {success_count}")
            logger.info(f"Errors: {error_count}")
            if total_tokens > 0:
                logger.info(f"Total tokens: {total_tokens:,}")
                logger.info(f"Avg tokens/paper: {total_tokens // success_count if success_count > 0 else 0}")

            # Updated stats
            stats = repo.get_stats()
            logger.info(f"Database stats:")
            logger.info(f"  Light: {stats['light_summaries']} summaries, {stats['pending_light']} pending")
            logger.info(f"  Deep: {stats['deep_summaries']} summaries, {stats['pending_deep']} pending")
            logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        sys.exit(1)

    logger.info(f"✓ Summary pipeline completed successfully ({summary_type})")


if __name__ == "__main__":
    main()

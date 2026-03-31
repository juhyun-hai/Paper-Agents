#!/usr/bin/env python3
"""
Generate deep_pdf summaries by downloading PDFs and running the two-step
vLLM extraction + synthesis pipeline.

Selects paper_versions that have no 'deep_pdf' summary, downloads each PDF
(caching locally), extracts text and sections, then calls the vLLM API.

Usage:
    python scripts/run_deep_pdf_summary.py
    python scripts/run_deep_pdf_summary.py --limit 5
    python scripts/run_deep_pdf_summary.py --cache-dir /tmp/pdf_cache --limit 20
    python scripts/run_deep_pdf_summary.py --stats

Environment:
    DATABASE_URL=postgresql://user:password@localhost:5432/paper_agent
    VLLM_BASE_URL=http://localhost:8000/v1
    VLLM_MODEL=meta-llama/Llama-3.1-70B-Instruct
"""

import argparse
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from packages.core.parsing.pdf_text import (
    download_pdf,
    evidence_candidates,
    extract_sections,
    extract_text_pymupdf,
)
from packages.core.storage.db import get_connection
from packages.core.storage.summary_repo import SummaryRepository
from packages.core.summarizers.deep_pdf_vllm import summarize_deep_pdf
from packages.core.summarizers.light_vllm import get_token_count_estimate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SUMMARY_TYPE = "deep_pdf"
BACKEND = "vllm"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deep_pdf summaries for papers without them.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of papers to process (default: 10)",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="data/cache/pdfs",
        help="Directory for cached PDFs (default: data/cache/pdfs)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show summary statistics and exit",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=9000,
        help=(
            "Maximum total characters of PDF section text fed to the extraction "
            "prompt (default: 9000).  Reduce if hitting context-length errors."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Re-generate deep_pdf summaries even for paper versions that already "
            "have one (existing rows are overwritten)."
        ),
    )
    parser.add_argument(
        "--ids",
        type=str,
        default=None,
        help=(
            "Comma-separated paper_version IDs to process.  "
            "Overrides --limit and --force selection; upserts regardless of "
            "whether a deep_pdf summary already exists."
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def _validate_summary(summary_data: dict) -> None:
    """
    Verify that summary_data contains the required top-level keys.

    Raises:
        ValueError: If a required key is missing.
    """
    required = ("one_liner", "problem", "method", "keywords")
    missing = [k for k in required if k not in summary_data]
    if missing:
        raise ValueError(f"Summary missing required fields: {missing}")


def main() -> None:
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 80)
    logger.info("Deep PDF Summary Pipeline  (type=%s  backend=%s)", SUMMARY_TYPE, BACKEND)
    logger.info("=" * 80)

    try:
        with get_connection() as conn:
            repo = SummaryRepository(conn)

            # ── Statistics mode ───────────────────────────────────────────
            if args.stats:
                stats = repo.get_stats()
                logger.info("Summary statistics:")
                logger.info("  Total paper versions : %d", stats["total_versions"])
                logger.info("  light summaries      : %d", stats["light_summaries"])
                logger.info("  deep summaries       : %d", stats["deep_summaries"])
                logger.info("  deep_pdf summaries   : %d", stats["deep_pdf_summaries"])
                logger.info("  Pending deep_pdf     : %d", stats["pending_deep_pdf"])
                sys.exit(0)

            # ── Fetch candidates ──────────────────────────────────────────
            if args.ids:
                id_list = [
                    int(x.strip())
                    for x in args.ids.split(",")
                    if x.strip().isdigit()
                ]
                if not id_list:
                    logger.warning("--ids contained no valid integers; nothing to do.")
                    sys.exit(0)
                logger.info(
                    "IDS mode: processing %d specific paper_versions.", len(id_list)
                )
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT pv.id, pv.arxiv_id, pv.version, pv.title,
                               pv.abstract, pv.categories, pv.pdf_url
                        FROM paper_versions pv
                        WHERE pv.id = ANY(%s)
                        ORDER BY pv.version_published_date DESC
                        """,
                        (id_list,),
                    )
                    papers = cur.fetchall()
            elif args.force:
                logger.info(
                    "FORCE mode: fetching up to %d paper_versions (overwrite existing).",
                    args.limit,
                )
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT pv.id, pv.arxiv_id, pv.version, pv.title,
                               pv.abstract, pv.categories, pv.pdf_url
                        FROM paper_versions pv
                        ORDER BY pv.version_published_date DESC
                        LIMIT %s
                        """,
                        (args.limit,),
                    )
                    papers = cur.fetchall()
            else:
                logger.info(
                    "Fetching up to %d paper_versions without '%s' summaries...",
                    args.limit,
                    SUMMARY_TYPE,
                )
                papers = repo.get_versions_without_summary(SUMMARY_TYPE, limit=args.limit)

            if not papers:
                logger.info("No papers to process. All versions have deep_pdf summaries.")
                sys.exit(0)

            logger.info("Found %d papers to process", len(papers))
            logger.info("PDF cache dir     : %s", args.cache_dir)
            logger.info("Max section chars : %d", args.max_chars)
            logger.info("Force overwrite   : %s", args.force)
            logger.info("=" * 80)

            # ── Processing loop ───────────────────────────────────────────
            success_count = 0
            error_count = 0
            total_tokens = 0
            elapsed_times: list[float] = []

            for i, paper in enumerate(papers, 1):
                arxiv_id = paper["arxiv_id"]
                version = paper["version"]
                version_id = paper["id"]
                pdf_url = paper["pdf_url"]
                title = paper["title"]
                abstract = paper["abstract"] or ""

                categories = paper["categories"]
                if isinstance(categories, str):
                    categories = json.loads(categories)

                logger.info(
                    "[%d/%d] Processing %s %s — %s",
                    i,
                    len(papers),
                    arxiv_id,
                    version,
                    title[:60],
                )

                t_start = time.monotonic()

                try:
                    # 1. Download PDF
                    local_path = download_pdf(pdf_url, args.cache_dir)

                    # 2. Extract text
                    full_text = extract_text_pymupdf(local_path)
                    if not full_text.strip():
                        raise ValueError(
                            f"No extractable text in PDF (image-only?): {pdf_url}"
                        )

                    # 3. Split into sections
                    sections = extract_sections(full_text)
                    logger.debug("Sections found: %s", list(sections.keys()))

                    # 4. Build evidence candidates (metric lines first, then body)
                    cands = evidence_candidates(sections)
                    logger.debug(
                        "Evidence candidates: %d (metric-line priority)", len(cands)
                    )

                    # 5. Summarise
                    summary_data, evidence = summarize_deep_pdf(
                        title=title,
                        abstract=abstract,
                        categories=categories,
                        sections=sections,
                        max_chars=args.max_chars,
                        candidates=cands,
                        arxiv_id=arxiv_id,
                    )

                    # 6. Validate
                    _validate_summary(summary_data)

                    # 7. Estimate tokens (prompt + response heuristic)
                    tokens_used = get_token_count_estimate(
                        json.dumps(summary_data)
                    )

                    # 8. Upsert
                    model_used = os.getenv("VLLM_MODEL", "vllm-unknown")
                    summary_id = repo.upsert_summary(
                        paper_version_id=version_id,
                        summary_type=SUMMARY_TYPE,
                        summary_data=summary_data,
                        model_used=model_used,
                        tokens_used=tokens_used,
                    )

                    elapsed = time.monotonic() - t_start
                    elapsed_times.append(elapsed)
                    success_count += 1
                    total_tokens += tokens_used

                    logger.info(
                        "  ✓ summary_id=%d  evidence=%d snippets  %.1fs",
                        summary_id,
                        len(evidence),
                        elapsed,
                    )

                    if args.debug and i == 1:
                        logger.debug("Sample one_liner: %s", summary_data.get("one_liner"))
                        logger.debug("Sample keywords: %s", summary_data.get("keywords"))
                        logger.debug("Evidence[0]: %s", evidence[0] if evidence else "none")

                except Exception as exc:
                    error_count += 1
                    elapsed = time.monotonic() - t_start
                    logger.error(
                        "  ✗ Failed %s %s (%.1fs): %s",
                        arxiv_id,
                        version,
                        elapsed,
                        exc,
                    )
                    continue

                # Progress checkpoint every 5 papers
                if i % 5 == 0:
                    avg = sum(elapsed_times) / len(elapsed_times) if elapsed_times else 0
                    logger.info(
                        "Progress: %d/%d  (✓%d ✗%d)  avg %.1fs/paper",
                        i,
                        len(papers),
                        success_count,
                        error_count,
                        avg,
                    )

            # ── Final report ──────────────────────────────────────────────
            avg_time = sum(elapsed_times) / len(elapsed_times) if elapsed_times else 0
            logger.info("=" * 80)
            logger.info("Deep PDF Summary Pipeline — Done")
            logger.info("=" * 80)
            logger.info("Processed   : %d", len(papers))
            logger.info("Successful  : %d", success_count)
            logger.info("Errors      : %d", error_count)
            if total_tokens:
                logger.info(
                    "Total tokens: %d  (avg %d/paper)",
                    total_tokens,
                    total_tokens // success_count if success_count else 0,
                )
            logger.info("Avg time    : %.1fs/paper", avg_time)

            stats = repo.get_stats()
            logger.info(
                "DB totals   : deep_pdf=%d  pending=%d",
                stats["deep_pdf_summaries"],
                stats["pending_deep_pdf"],
            )
            logger.info("=" * 80)

    except Exception as exc:
        logger.error("Pipeline error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Daily pipeline orchestrator for paper-agent.

Runs all processing stages in sequence:

  1. Ingest       — fetch new papers from arXiv          (fatal on failure)
  2. Summarise    — generate light summaries via vLLM    (non-fatal)
  3. Keywords     — rebuild daily keyword stats           (non-fatal)
  4. Embeddings   — rebuild FAISS index if new papers exist (non-fatal)
  5. Deep PDF     — generate deep_pdf summaries           (optional, non-fatal)

Usage:
    python scripts/run_daily_pipeline.py
    python scripts/run_daily_pipeline.py --since 2d --deep-pdf-limit 20
    python scripts/run_daily_pipeline.py --skip-deep-pdf
    python scripts/run_daily_pipeline.py --dry-run
    python scripts/run_daily_pipeline.py --debug

Environment:
    DATABASE_URL=postgresql://user:password@localhost:5432/paper_agent
    VLLM_BASE_URL=http://localhost:8000/v1
    VLLM_MODEL=meta-llama/Llama-3.1-70B-Instruct
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PYTHON = sys.executable  # same interpreter / venv as the pipeline itself

_DEFAULT_DEEP_PDF_LIMIT = 10
_DEFAULT_INDEX_DIR = "data/index"


# ---------------------------------------------------------------------------
# Stage result tracking
# ---------------------------------------------------------------------------


@dataclass
class StageResult:
    name: str
    status: str = "pending"   # "ok" | "failed" | "skipped"
    elapsed: float = 0.0
    returncode: int = 0
    note: str = ""


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full daily paper-agent pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--since",
        type=str,
        default="1d",
        help="Time window passed to run_daily_ingest.py (default: 1d)",
    )
    parser.add_argument(
        "--deep-pdf-limit",
        type=int,
        default=_DEFAULT_DEEP_PDF_LIMIT,
        help=(
            f"Max papers to process in the deep_pdf stage "
            f"(default: {_DEFAULT_DEEP_PDF_LIMIT})"
        ),
    )
    parser.add_argument(
        "--skip-deep-pdf",
        action="store_true",
        help="Skip the deep_pdf summary stage entirely",
    )
    parser.add_argument(
        "--index-dir",
        type=str,
        default=_DEFAULT_INDEX_DIR,
        help=f"FAISS index directory for build_embeddings.py (default: {_DEFAULT_INDEX_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print each stage command without executing it",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Pass --debug to each stage script and enable verbose logging here",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Stage runner
# ---------------------------------------------------------------------------


def _script(name: str) -> str:
    """Return the absolute path to a script in the same directory."""
    return os.path.join(_SCRIPTS_DIR, name)


def _run_stage(
    result: StageResult,
    cmd: list[str],
    *,
    fatal: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Execute one pipeline stage, update *result* in-place.

    If ``fatal=True`` and the subprocess exits non-zero, the process exits
    immediately with the same return code.  Otherwise the failure is recorded
    and the pipeline continues.
    """
    logger.info("─" * 72)
    logger.info("STAGE  : %s", result.name)
    logger.info("COMMAND: %s", " ".join(cmd))

    if dry_run:
        result.status = "skipped"
        result.note = "dry-run"
        logger.info("DRY RUN — skipping execution")
        return

    t0 = time.monotonic()
    proc = subprocess.run(cmd)
    result.elapsed = time.monotonic() - t0
    result.returncode = proc.returncode

    if proc.returncode == 0:
        result.status = "ok"
        logger.info("✓ %s  (%.1fs)", result.name, result.elapsed)
    else:
        result.status = "failed"
        logger.error(
            "✗ %s  exit=%d  (%.1fs)",
            result.name,
            proc.returncode,
            result.elapsed,
        )
        if fatal:
            logger.error("Stage is fatal — aborting pipeline.")
            sys.exit(proc.returncode)


# ---------------------------------------------------------------------------
# Embedding-rebuild check
# ---------------------------------------------------------------------------


def _needs_embedding_rebuild(index_dir: str) -> bool:
    """
    Return True when there are paper_versions not yet in the FAISS index.

    Reads the companion id list from ``index_dir/papers_ids.json`` and
    compares its length against the total row count in paper_versions.
    Falls back to True (trigger rebuild) on any error so the pipeline
    stays safe by default.
    """
    ids_path = os.path.join(index_dir, "papers_ids.json")
    if not os.path.exists(ids_path):
        logger.info("No existing FAISS index found — rebuild needed.")
        return True

    try:
        with open(ids_path) as f:
            indexed_count = len(json.load(f))
    except Exception as exc:
        logger.warning("Could not read index id list (%s) — rebuilding.", exc)
        return True

    try:
        from packages.core.storage.db import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM paper_versions")
                total = cur.fetchone()["count"]

        if total > indexed_count:
            logger.info(
                "New papers detected: DB has %d versions, index has %d — rebuild needed.",
                total,
                indexed_count,
            )
            return True
        else:
            logger.info(
                "Index is up-to-date (%d/%d versions) — skipping rebuild.",
                indexed_count,
                total,
            )
            return False

    except Exception as exc:
        logger.warning("DB check failed (%s) — rebuilding index to be safe.", exc)
        return True


# ---------------------------------------------------------------------------
# Deep PDF candidate selection helper
# ---------------------------------------------------------------------------


def _select_deep_pdf_candidates(
    limit: int,
    index_dir: str,
    debug_flag: list[str],
    dry_run: bool,
) -> list[int] | None:
    """
    Run select_deep_pdf_candidates.py and return the selected version_ids.

    Captures stdout (JSON array) and logs stderr.  Returns:
      - list[int]  on success (may be empty if nothing to process)
      - None       if the script failed (caller should fall back to --limit)
    """
    cmd = [
        _PYTHON,
        _script("select_deep_pdf_candidates.py"),
        "--limit", str(limit),
        "--index-dir", index_dir,
    ] + debug_flag

    logger.info("COMMAND: %s", " ".join(cmd))

    if dry_run:
        logger.info("DRY RUN — skipping candidate selection")
        # In dry-run mode pretend we selected `limit` dummy ids so the
        # summarizer stage still prints its command.
        return list(range(1, limit + 1))

    proc = subprocess.run(cmd, capture_output=True, text=True)

    # Forward the script's log output (written to stderr) to our logger
    for line in proc.stderr.strip().splitlines():
        if line:
            logger.info("  [select] %s", line)

    if proc.returncode != 0:
        logger.warning(
            "select_deep_pdf_candidates.py exited %d — falling back to --limit",
            proc.returncode,
        )
        return None

    try:
        ids = json.loads(proc.stdout.strip())
        if not isinstance(ids, list):
            raise ValueError("expected JSON array")
        logger.info("Candidate selection → %d ids", len(ids))
        return [int(i) for i in ids]
    except Exception as exc:
        logger.warning("Could not parse selection output (%s) — falling back", exc)
        return None


# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------


def _print_summary(results: list[StageResult], pipeline_elapsed: float) -> None:
    """Print a compact pipeline summary table to the log."""
    logger.info("=" * 72)
    logger.info("Pipeline Summary — %s", date.today().isoformat())
    logger.info("=" * 72)

    col_w = 16
    header = f"  {'Stage':<{col_w}} {'Status':<10} {'Time':>8}"
    logger.info(header)
    logger.info("  " + "-" * (col_w + 20))

    for r in results:
        icon = {"ok": "✓", "failed": "✗", "skipped": "—"}.get(r.status, "?")
        time_str = f"{r.elapsed:.1f}s" if r.elapsed > 0 else "—"
        note = f"  ({r.note})" if r.note else ""
        logger.info(
            "  %-*s %-10s %8s%s",
            col_w,
            r.name,
            f"{icon} {r.status}",
            time_str,
            note,
        )

    logger.info("  " + "-" * (col_w + 20))
    logger.info("  Total pipeline time: %.1fs", pipeline_elapsed)
    logger.info("=" * 72)

    failures = [r for r in results if r.status == "failed"]
    if failures:
        names = ", ".join(r.name for r in failures)
        logger.warning("Stages with errors: %s", names)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 72)
    logger.info("paper-agent Daily Pipeline  (%s)", date.today().isoformat())
    logger.info("=" * 72)
    logger.info("since=%s  deep-pdf-limit=%d  skip-deep-pdf=%s  dry-run=%s",
                args.since, args.deep_pdf_limit, args.skip_deep_pdf, args.dry_run)
    logger.info("=" * 72)

    debug_flag = ["--debug"] if args.debug else []
    results: list[StageResult] = []
    pipeline_start = time.monotonic()

    # ── Stage 1: Ingest ───────────────────────────────────────────────────
    r1 = StageResult("Ingest")
    results.append(r1)
    _run_stage(
        r1,
        [_PYTHON, _script("run_daily_ingest.py"), "--since", args.since] + debug_flag,
        fatal=True,
        dry_run=args.dry_run,
    )

    # ── Stage 2: Light summaries ──────────────────────────────────────────
    r2 = StageResult("Summarise")
    results.append(r2)
    _run_stage(
        r2,
        [_PYTHON, _script("run_light_summary.py"), "--backend", "vllm"] + debug_flag,
        fatal=False,
        dry_run=args.dry_run,
    )

    # ── Stage 3: Keyword stats ────────────────────────────────────────────
    r3 = StageResult("Keywords")
    results.append(r3)
    _run_stage(
        r3,
        [_PYTHON, _script("build_keyword_stats.py"), "--day", date.today().isoformat()],
        fatal=False,
        dry_run=args.dry_run,
    )

    # ── Stage 4: Embeddings ───────────────────────────────────────────────
    r4 = StageResult("Embeddings")
    results.append(r4)

    if args.dry_run:
        _run_stage(r4, [_PYTHON, _script("build_embeddings.py"),
                        "--index-dir", args.index_dir] + debug_flag,
                   dry_run=True)
    else:
        if _needs_embedding_rebuild(args.index_dir):
            _run_stage(
                r4,
                [_PYTHON, _script("build_embeddings.py"),
                 "--index-dir", args.index_dir] + debug_flag,
                fatal=False,
                dry_run=False,
            )
        else:
            r4.status = "skipped"
            r4.note = "index up-to-date"
            logger.info("─" * 72)
            logger.info("STAGE  : Embeddings")
            logger.info("— skipped (index already covers all paper_versions)")

    # ── Stage 5: Deep PDF (optional) ──────────────────────────────────────
    r5 = StageResult("Deep PDF")
    results.append(r5)

    if args.skip_deep_pdf:
        r5.status = "skipped"
        r5.note = "--skip-deep-pdf"
        logger.info("─" * 72)
        logger.info("STAGE  : Deep PDF")
        logger.info("— skipped (--skip-deep-pdf)")
    else:
        # 5a: priority selection
        logger.info("─" * 72)
        logger.info("STAGE  : Deep PDF — candidate selection")
        selected_ids = _select_deep_pdf_candidates(
            args.deep_pdf_limit, args.index_dir, debug_flag, args.dry_run
        )

        # 5b: run summarizer on selected ids (or fall back to --limit)
        if selected_ids is None:
            # selection script failed — fall back to simple limit-based approach
            deep_pdf_cmd = [
                _PYTHON, _script("run_deep_pdf_summary.py"),
                "--limit", str(args.deep_pdf_limit),
            ] + debug_flag
            r5.note = "selection fallback"
        elif len(selected_ids) == 0:
            r5.status = "skipped"
            r5.note = "no candidates"
            logger.info("─" * 72)
            logger.info("STAGE  : Deep PDF — no candidates, skipping summarizer")
            deep_pdf_cmd = None
        else:
            ids_str = ",".join(str(i) for i in selected_ids)
            deep_pdf_cmd = [
                _PYTHON, _script("run_deep_pdf_summary.py"),
                "--ids", ids_str,
            ] + debug_flag

        if deep_pdf_cmd is not None:
            _run_stage(r5, deep_pdf_cmd, fatal=False, dry_run=args.dry_run)

    # ── Final summary ─────────────────────────────────────────────────────
    _print_summary(results, time.monotonic() - pipeline_start)


if __name__ == "__main__":
    main()

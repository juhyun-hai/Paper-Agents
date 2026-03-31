#!/usr/bin/env python3
"""
Recommend papers similar to a given idea or query text.

Loads the pre-built FAISS index, embeds the input idea, and prints the
top-k most similar papers with arxiv_id, title, cosine score, one-liner,
and a context snippet (evidence from deep_pdf, or fallback to summary
problem/method, or the abstract's first sentence).

With --group, calls vLLM once (temperature=0) to cluster the results into
3–5 thematic groups with short descriptive labels.

Usage:
    python scripts/recommend.py --idea "contrastive learning for vision"
    python scripts/recommend.py --idea "efficient transformers" --topk 5
    python scripts/recommend.py --idea "..." --group
    python scripts/recommend.py --idea "..." --group --topk 20

Environment:
    DATABASE_URL=postgresql://user:password@localhost:5432/paper_agent
    HF_HOME=data/cache/hf          # embedding model cache (default)
    VLLM_BASE_URL=http://localhost:8000/v1   # required for --group
    VLLM_MODEL=meta-llama/Llama-3.1-70B-Instruct
"""

import argparse
import json
import logging
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from packages.core.recommend.embeddings import embed_texts, get_embedder
from packages.core.recommend.index_faiss import load_index, query_index
from packages.core.recommend.priority import (
    compute_recency_score,
    compute_recommendation_score,
    compute_trending_boost,
    get_top_trending_keywords,
)
from packages.core.storage.db import get_connection

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_DEFAULT_INDEX_DIR = "data/index"
_DEFAULT_MODEL = "BAAI/bge-m3"
_DEFAULT_TOPK = 10
_GROUP_MAX_TOKENS = 400
_GROUP_TIMEOUT = (5, 60)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recommend arXiv papers similar to an input idea.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--idea",
        type=str,
        required=True,
        help="Free-text research idea or query to find similar papers for",
    )
    parser.add_argument(
        "--topk",
        type=int,
        default=_DEFAULT_TOPK,
        help=f"Number of results to return (default: {_DEFAULT_TOPK})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=_DEFAULT_MODEL,
        help=f"SentenceTransformer model for embedding the query (default: {_DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--index-dir",
        type=str,
        default=_DEFAULT_INDEX_DIR,
        help=f"Directory containing the FAISS index (default: {_DEFAULT_INDEX_DIR})",
    )
    parser.add_argument(
        "--group",
        action="store_true",
        help=(
            "Group results into 3–5 thematic clusters using vLLM "
            "(requires VLLM_BASE_URL and VLLM_MODEL)"
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _fetch_version_details(conn, version_ids: list[int]) -> dict[int, dict]:
    """
    Fetch paper_version metadata + summaries for a list of ids.

    Returns dict keyed by version_id.
    """
    if not version_ids:
        return {}

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, arxiv_id, version, title, abstract,
                   version_published_date
            FROM paper_versions
            WHERE id = ANY(%s)
            """,
            (version_ids,),
        )
        rows = cur.fetchall()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT paper_version_id, summary_type, summary_data
            FROM summaries
            WHERE paper_version_id = ANY(%s)
            """,
            (version_ids,),
        )
        summary_rows = cur.fetchall()

    summaries_by_id: dict[int, dict] = {}
    for s in summary_rows:
        vid = s["paper_version_id"]
        if vid not in summaries_by_id:
            summaries_by_id[vid] = {}
        data = s["summary_data"]
        if isinstance(data, str):
            data = json.loads(data)
        summaries_by_id[vid][s["summary_type"]] = data

    result = {}
    for row in rows:
        d = dict(row)
        d["summaries"] = summaries_by_id.get(row["id"], {})
        result[row["id"]] = d

    return result


# ---------------------------------------------------------------------------
# Context / evidence helpers
# ---------------------------------------------------------------------------


def _pick_evidence_snippet(summary: dict) -> str | None:
    """Return the first usable evidence snippet from a deep_pdf summary."""
    for item in summary.get("evidence", []):
        snippet = item.get("snippet", "")
        if snippet and len(snippet) >= 40:
            return snippet
    return None


def _pick_context(paper: dict) -> tuple[str, str] | None:
    """
    Return (label, text) for the best available context for a paper.

    Priority:
        1. deep_pdf evidence snippet  → label "Evidence"
        2. Best summary problem field → label "Context"
        3. Best summary method field  → label "Method"
        4. Abstract first sentence    → label "Abstract"

    Returns None if nothing usable is found.
    """
    summaries = paper.get("summaries", {})

    # 1. deep_pdf evidence snippet
    deep_pdf = summaries.get("deep_pdf")
    if deep_pdf:
        snippet = _pick_evidence_snippet(deep_pdf)
        if snippet:
            return ("Evidence", snippet)

    # 2 & 3. problem / method from best non-pdf summary
    best = summaries.get("deep") or summaries.get("light")
    if best:
        for field, label in (("problem", "Context"), ("method", "Method")):
            val = best.get(field, "")
            if val and val not in ("", "unknown"):
                return (label, val[:220])

    # 4. Abstract first sentence
    abstract = (paper.get("abstract") or "").strip()
    if abstract:
        dot = abstract.find(". ")
        sentence = abstract[: dot + 1] if dot != -1 else abstract
        sentence = sentence.strip()
        if len(sentence) >= 40:
            return ("Abstract", sentence[:220])

    return None


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _format_result(rank: int, score: float, paper: dict) -> str:
    """Format a single recommendation result for display."""
    summaries = paper.get("summaries", {})
    best = (
        summaries.get("deep_pdf")
        or summaries.get("deep")
        or summaries.get("light")
    )

    one_liner = ""
    if best:
        one_liner = best.get("one_liner", "")
        if one_liner == "unknown":
            one_liner = ""

    lines = [
        f"[{rank}] {paper['arxiv_id']} {paper['version']}  score={score:.4f}",
        f"  {paper['title']}",
    ]
    if one_liner:
        lines.append(f"  {one_liner}")

    ctx = _pick_context(paper)
    if ctx:
        label, text = ctx
        if label == "Evidence":
            lines.append(f'  Evidence: "{text}"')
        else:
            lines.append(f"  {label}: {text}")

    return "\n".join(lines)


def _rescore_and_sort(
    hits: list[tuple[int, float]],
    papers: dict[int, dict],
    trending_kws: set[str],
) -> list[tuple[int, float]]:
    """
    Re-rank FAISS hits using the hybrid recommendation score.

        final = 0.7 * embedding_sim + 0.2 * recency + 0.1 * trending

    Args:
        hits:         Raw (version_id, cosine_score) list from FAISS.
        papers:       Fetched paper detail dicts (must include version_published_date).
        trending_kws: Today's top trending keywords (lowercase).

    Returns:
        New (version_id, final_score) list sorted by final_score descending.
    """
    rescored: list[tuple[int, float]] = []
    for version_id, cosine_score in hits:
        paper = papers.get(version_id, {})

        pub_date = paper.get("version_published_date")
        recency = compute_recency_score(pub_date)

        summaries = paper.get("summaries", {})
        best = (
            summaries.get("deep_pdf")
            or summaries.get("deep")
            or summaries.get("light")
        )
        kws = (best or {}).get("keywords", [])
        if not isinstance(kws, list):
            kws = []
        trending = compute_trending_boost(paper.get("title", ""), kws, trending_kws)

        final = compute_recommendation_score(cosine_score, recency, trending)
        rescored.append((version_id, final))

    rescored.sort(key=lambda x: x[1], reverse=True)
    return rescored


def _print_linear(hits: list[tuple], papers: dict[int, dict]) -> None:
    """Print results as a flat ranked list."""
    for rank, (version_id, score) in enumerate(hits, 1):
        paper = papers.get(version_id)
        if not paper:
            print(f"[{rank}] version_id={version_id}  score={score:.4f}  (not in DB)")
        else:
            print(_format_result(rank, score, paper))
        print()


# ---------------------------------------------------------------------------
# Grouping via vLLM
# ---------------------------------------------------------------------------


def _vllm_chat(base_url: str, model: str, prompt: str, max_tokens: int) -> str:
    """Minimal vLLM chat completion call (temperature=0, deterministic)."""
    import requests

    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    resp = requests.post(
        endpoint,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=_GROUP_TIMEOUT,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"vLLM grouping call failed ({resp.status_code}): {resp.text[:300]}"
        )
    return resp.json()["choices"][0]["message"]["content"]


def _parse_json_loose(text: str) -> object:
    """Try direct JSON parse, then extract from first [ or { to last ] or }."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to extract array
    start = text.find("[")
    end = text.rfind("]") + 1
    if start != -1 and end > 0:
        return json.loads(text[start:end])
    # Try object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > 0:
        return json.loads(text[start:end])
    raise json.JSONDecodeError("No JSON found", text, 0)


def _group_papers_vllm(
    hits: list[tuple[int, float]],
    papers: dict[int, dict],
) -> list[dict] | None:
    """
    Call vLLM (temperature=0) to cluster the top-k papers into 3–5 groups.

    Returns a validated list of {"label": str, "indices": list[int]} dicts
    where indices are 1-based ranks, or None if grouping is unavailable/fails.
    Unassigned papers are collected into an "Other" group appended at the end.
    """
    # Import only what we need from the existing vLLM config helper
    try:
        from packages.core.summarizers.light_vllm import get_vllm_config
        base_url, model = get_vllm_config()
    except Exception as exc:
        logger.warning("vLLM not available for grouping: %s", exc)
        return None

    # Build compact paper list for the prompt
    paper_lines: list[str] = []
    for rank, (version_id, _score) in enumerate(hits, 1):
        paper = papers.get(version_id, {})
        title = paper.get("title", "Unknown")
        summaries = paper.get("summaries", {})
        best = (
            summaries.get("deep_pdf")
            or summaries.get("deep")
            or summaries.get("light")
        )
        one_liner = (best or {}).get("one_liner", "")
        if one_liner == "unknown":
            one_liner = ""
        if one_liner:
            paper_lines.append(f'[{rank}] "{title}" — {one_liner}')
        else:
            paper_lines.append(f'[{rank}] "{title}"')

    n = len(hits)
    papers_text = "\n".join(paper_lines)

    prompt = f"""You are a research paper organizer. Group the following {n} papers into 3 to 5 thematic clusters.

Rules:
- Each cluster needs a concise descriptive label (3–6 words, title case).
- Every paper index must appear in exactly one cluster.
- Do not invent new indices; only use 1 through {n}.

Papers:
{papers_text}

Return ONLY a valid JSON array with no extra text:
[
  {{"label": "Cluster Theme Here", "indices": [1, 3]}},
  {{"label": "Another Theme", "indices": [2, 4, 5]}}
]

JSON:"""

    try:
        response_text = _vllm_chat(base_url, model, prompt, max_tokens=_GROUP_MAX_TOKENS)
        raw_groups = _parse_json_loose(response_text)
    except Exception as exc:
        logger.warning("vLLM grouping failed: %s", exc)
        return None

    if not isinstance(raw_groups, list):
        logger.warning("Grouping response is not a list")
        return None

    # Validate: deduplicate indices, enforce bounds
    valid_groups: list[dict] = []
    seen: set[int] = set()
    for g in raw_groups:
        if not isinstance(g, dict):
            continue
        label = str(g.get("label", "Group")).strip()
        raw_indices = g.get("indices", [])
        if not isinstance(raw_indices, list):
            continue
        indices = [
            i for i in raw_indices
            if isinstance(i, int) and 1 <= i <= n and i not in seen
        ]
        if not indices:
            continue
        seen.update(indices)
        valid_groups.append({"label": label, "indices": sorted(indices)})

    # Collect any unassigned papers into an "Other" group
    unassigned = [i for i in range(1, n + 1) if i not in seen]
    if unassigned:
        valid_groups.append({"label": "Other", "indices": unassigned})

    return valid_groups or None


def _print_grouped(
    groups: list[dict],
    hits: list[tuple],
    papers: dict[int, dict],
) -> None:
    """Print results organised into thematic groups."""
    rank_map = {rank: (vid, score) for rank, (vid, score) in enumerate(hits, 1)}

    for g in groups:
        print(f"\n== {g['label']} ==")
        for rank in g["indices"]:
            if rank not in rank_map:
                continue
            version_id, score = rank_map[rank]
            paper = papers.get(version_id)
            if not paper:
                print(f"  [{rank}] version_id={version_id}  (not in DB)")
            else:
                # Indent each line of the formatted block by two spaces
                block = _format_result(rank, score, paper)
                print("  " + block.replace("\n", "\n  "))
            print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load FAISS index
    index, ids = load_index(index_dir=args.index_dir)

    # Embed query (cache_dir resolved automatically via HF_HOME env)
    model = get_embedder(args.model)
    query_vec = embed_texts(model, [args.idea])  # shape (1, dim)

    # Search
    hits = query_index(index, ids, query_vec, topk=args.topk)
    if not hits:
        print("No results found.")
        sys.exit(0)

    # Fetch paper details from DB + trending keywords, then re-score
    hit_ids = [h[0] for h in hits]
    with get_connection() as conn:
        papers = _fetch_version_details(conn, hit_ids)
        trending_kws = get_top_trending_keywords(conn, date.today())

    hits = _rescore_and_sort(hits, papers, trending_kws)

    # Display
    if args.group:
        groups = _group_papers_vllm(hits, papers)
        if groups:
            print(f'\nGrouped results for: "{args.idea}"\n' + "=" * 70)
            _print_grouped(groups, hits, papers)
        else:
            # Grouping unavailable or failed — fall back to linear list
            logger.warning("Grouping unavailable; showing linear list.")
            print(f'\nTop {len(hits)} papers for: "{args.idea}"\n' + "=" * 70)
            _print_linear(hits, papers)
    else:
        print(f'\nTop {len(hits)} papers for: "{args.idea}"\n' + "=" * 70)
        _print_linear(hits, papers)


if __name__ == "__main__":
    main()

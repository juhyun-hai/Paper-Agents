"""
Deep PDF summarization using vLLM via OpenAI-compatible API.

Two-step pipeline:
  Step 1 – Extraction:
      Receives a numbered list of evidence_candidates (key sentences from
      priority sections of the PDF).  The model extracts structured facts
      (datasets, model info, metrics, results, compute) and references
      each claim by a ``snippet_index`` — an integer index into the
      candidate list.  Free-form text snippets are forbidden.

  Step 2 – Synthesis:
      Merges the extraction output with title/abstract context to produce
      the full CLAUDE.md-schema summary_data.

Evidence quality guarantee:
  After extraction the snippet_index values are resolved to the actual
  candidate sentences (each 80–300 chars).  Any evidence item whose
  resolved snippet is shorter than 80 chars is considered invalid; the
  extraction call is retried once, and surviving invalid items are
  silently dropped.

Context-length safety:
  Before every /chat/completions call the prompt is tokenised via the
  vLLM /tokenize endpoint (falls back to char-count heuristic).
  max_tokens is computed as:

      ctx    = VLLM_MAX_LEN env var (default 4096)
      budget = ctx – prompt_tokens – 256
      max_tokens = clamp(budget, 300, 1200)

  If budget ≤ 0, the prompt is hard-truncated to ~¾ of the context
  window and recounted once before raising.

The evidence list is stored inside summary_data["evidence"] so it
travels with the summary in the DB.
"""

import json
import logging
import os
import urllib.parse
from typing import Any

import requests

from packages.core.parsing.pdf_text import evidence_candidates as _build_candidates
from packages.core.summarizers.light_vllm import get_vllm_config

logger = logging.getLogger(__name__)

# Timeout for large (70B) models: 5 s connect, 600 s read
_TIMEOUT = (5, 600)

# Context-length budget constants
_VLLM_MAX_LEN_DEFAULT = 4096
_SAFETY_TOKENS = 256
_MAX_RESPONSE_TOKENS = 1200
_MIN_RESPONSE_TOKENS = 300

# Default maximum total chars of section text (kept for signature compat)
_DEFAULT_MAX_SECTION_CHARS = 9000

# Maximum candidates shown in the extraction prompt (token-budget guard)
_MAX_PROMPT_CANDIDATES = 60

# Minimum snippet length for a valid evidence item
_MIN_SNIPPET_LEN = 80


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_prompt_tokens_vllm(prompt_text: str) -> int:
    """
    Return the token count for *prompt_text* by calling the vLLM /tokenize
    endpoint.

    The endpoint lives at the server root (not under /v1), so the /v1
    suffix is stripped from VLLM_BASE_URL before building the URL.

    Falls back to ``max(1, len(prompt_text) // 4)`` if the endpoint is
    unavailable or returns an unexpected format.

    Args:
        prompt_text: The prompt string to tokenise.

    Returns:
        Integer token count.
    """
    base_url, model = get_vllm_config()

    parsed = urllib.parse.urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    endpoint = f"{root}/tokenize"

    try:
        resp = requests.post(
            endpoint,
            json={"model": model, "prompt": prompt_text},
            timeout=(5, 30),
        )
        resp.raise_for_status()
        data = resp.json()
        if "count" in data:
            return int(data["count"])
        if "tokens" in data:
            return len(data["tokens"])
        logger.warning("Unexpected /tokenize response keys: %s", list(data.keys()))
    except Exception as exc:
        logger.warning(
            "Tokenize endpoint unavailable (%s); using char-count heuristic", exc
        )

    return max(1, len(prompt_text) // 4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def summarize_deep_pdf(
    title: str,
    abstract: str,
    categories: list[str],
    sections: dict[str, str],
    max_chars: int = _DEFAULT_MAX_SECTION_CHARS,
    candidates: list[str] | None = None,
    arxiv_id: str = "unknown",
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """
    Generate a deep PDF summary using a two-step vLLM pipeline.

    Step 1 – Extraction:
        Uses a pre-built or internally computed evidence_candidates list
        (key sentences from priority sections, up to 120).  Shows up to
        ``_MAX_PROMPT_CANDIDATES`` (60) in the prompt, numbered 1..N.
        The model must reference each claim by a 1-based ``snippet_index``.
        Indices are resolved to actual sentences after the call.  Items
        whose resolved snippet is < 80 chars are retried once, then dropped.

    Step 2 – Synthesis:
        Combines the extraction with title/abstract to produce the full
        CLAUDE.md-schema summary_data dict.

    Args:
        title:      Paper title.
        abstract:   Paper abstract.
        categories: List of arXiv category strings.
        sections:   Dict of section_name -> section_text from
                    pdf_text.extract_sections().
        max_chars:  Retained for call-site compatibility; currently unused
                    when candidates are provided.
        candidates: Pre-computed evidence candidate list.  If None, computed
                    internally via evidence_candidates(sections).  Pass
                    explicitly from the script to log and reuse the list.

    Returns:
        (summary_data, evidence)
        summary_data: Full summary dict matching CLAUDE.md schema, with an
                      added "evidence" key (list of {field, value, snippet,
                      snippet_index}).
        evidence:     The same flat evidence list for caller convenience.

    Raises:
        RuntimeError: If vLLM API calls or JSON parsing fail after retry.
    """
    base_url, model = get_vllm_config()

    # ── Build evidence candidate list ────────────────────────────────────
    if candidates is None:
        candidates = _build_candidates(sections)
    logger.debug("Evidence candidates: %d", len(candidates))

    # ── Step 1: extraction ───────────────────────────────────────────────
    extract_prompt = _build_extraction_prompt(title, abstract, candidates)
    extraction = _call_with_retry(base_url, model, extract_prompt, arxiv_id=arxiv_id)
    logger.debug("Extraction complete for: %.60s", title)

    evidence = _build_evidence_list(extraction, candidates)

    # ── Validate snippet length; retry once if any are too short ─────────
    if candidates and _has_invalid_snippets(evidence):
        n_invalid = sum(1 for e in evidence if len(e.get("snippet", "")) < _MIN_SNIPPET_LEN)
        logger.warning(
            "Short evidence snippets detected (%d/%d); retrying extraction",
            n_invalid,
            len(evidence),
        )
        extraction = _call_with_retry(base_url, model, extract_prompt, arxiv_id=arxiv_id)
        evidence = _build_evidence_list(extraction, candidates)
        # Filter out remaining invalids after retry
        evidence = [e for e in evidence if len(e.get("snippet", "")) >= _MIN_SNIPPET_LEN]

    # ── Step 2: synthesis ────────────────────────────────────────────────
    synth_prompt = _build_synthesis_prompt(title, abstract, categories, extraction)
    summary_data = _call_with_retry(base_url, model, synth_prompt, arxiv_id=arxiv_id)
    logger.debug("Synthesis complete for: %.60s", title)

    summary_data["evidence"] = evidence
    return summary_data, evidence


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def _build_extraction_prompt(
    title: str,
    abstract: str,
    candidates: list[str],
) -> str:
    """
    Build the extraction prompt using a numbered evidence_candidates list.

    The model is required to reference facts by ``snippet_index`` (an
    integer index into the candidate list) and is forbidden from writing
    free-form text snippets.  This guarantees that every evidence item
    can be resolved to a full sentence from the PDF.

    If *candidates* is empty the prompt falls back to requesting facts
    from title + abstract only, with no evidence indices.
    """
    if not candidates:
        return _build_extraction_prompt_abstract_only(title, abstract)

    prompt_cands = candidates[:_MAX_PROMPT_CANDIDATES]
    # 1-based numbering so the model sees natural numbers (1..N), not 0-based.
    cands_block = "\n".join(f"[{i + 1}] {s}" for i, s in enumerate(prompt_cands))
    n = len(prompt_cands)

    return f"""You are a scientific fact extractor. Extract structured information from the paper below.

CRITICAL RULES:
1. Only extract facts EXPLICITLY stated in the evidence candidates.
2. For every extracted item, set snippet_index to the candidate NUMBER (1–{n}) that supports it.
3. Use null for snippet_index if no candidate directly supports the claim.
4. Do NOT write any free-form text in snippet fields — only integer numbers or null.
5. If a field is not present in the candidates, use [] or "unknown".
6. Output ONLY valid JSON — no extra text before or after.

Paper Title: {title}
Abstract (first 400 chars): {abstract[:400]}

Evidence candidates (numbers 1–{n}):
{cands_block}

Output this exact JSON (snippet_index must be an integer 1–{n} or null):
{{
  "datasets": [
    {{"name": "dataset name", "task": "task type", "snippet_index": 5}}
  ],
  "model_info": {{
    "backbone": "architecture or unknown",
    "foundation_model": "base model or unknown",
    "parameters": "parameter count or unknown",
    "training_objective": "objective or unknown",
    "snippet_index": 3
  }},
  "metrics": [
    {{"name": "metric name", "snippet_index": 7}}
  ],
  "results": [
    {{"metric": "metric name", "value": "exact value", "setting": "eval setting", "snippet_index": 12}}
  ],
  "compute": {{
    "gpus": "gpu info or unknown",
    "steps": "training steps or unknown",
    "batch_size": "batch size or unknown",
    "training_time": "time or unknown",
    "snippet_index": null
  }},
  "limitations": "limitations text or unknown"
}}

Output ONLY the JSON object:"""


def _build_extraction_prompt_abstract_only(title: str, abstract: str) -> str:
    """
    Fallback extraction prompt used when no evidence candidates are available.

    Extracts facts from title and abstract only; no snippet_index fields.
    """
    return f"""You are a scientific fact extractor. Extract structured information from the title and abstract below.

CRITICAL RULES:
1. Only extract facts EXPLICITLY stated in the title or abstract.
2. If a field is not present, use [] or "unknown".
3. Output ONLY valid JSON — no extra text before or after.

Paper Title: {title}
Abstract: {abstract}

Output this exact JSON:
{{
  "datasets": [{{"name": "dataset name", "task": "task type"}}],
  "model_info": {{
    "backbone": "architecture or unknown",
    "foundation_model": "base model or unknown",
    "parameters": "parameter count or unknown",
    "training_objective": "objective or unknown"
  }},
  "metrics": [{{"name": "metric name"}}],
  "results": [{{"metric": "metric name", "value": "exact value", "setting": "eval setting"}}],
  "compute": {{
    "gpus": "unknown", "steps": "unknown",
    "batch_size": "unknown", "training_time": "unknown"
  }},
  "limitations": "unknown"
}}

Output ONLY the JSON object:"""


def _build_synthesis_prompt(
    title: str,
    abstract: str,
    categories: list[str],
    extraction: dict[str, Any],
) -> str:
    """
    Prompt that synthesises the full CLAUDE.md-schema summary_data.

    Uses title + abstract for one_liner / problem / method / limitations,
    and the extraction dict for datasets / model_info / metrics / results /
    compute.
    """
    categories_str = ", ".join(categories)
    extraction_str = json.dumps(extraction, indent=2)

    return f"""You are a scientific paper summarization system. Produce a complete structured summary.

CRITICAL RULES:
1. Output ONLY valid JSON matching the exact schema below. No extra text.
2. NEVER fabricate numbers, metrics, or results not present in the extraction or abstract.
3. Use "unknown" or empty arrays where information is absent.
4. Derive one_liner, problem, method from title and abstract.
5. Take datasets, model_info, metrics, results, compute directly from Extracted Facts.

Paper Title: {title}
Abstract: {abstract}
Categories: {categories_str}

Extracted Facts (from PDF):
{extraction_str}

Required JSON Schema:
{{
  "one_liner": "one-sentence summary of the paper",
  "problem": "problem addressed by this paper",
  "method": "proposed method or approach",
  "model_info": {{
    "backbone": "from extraction or unknown",
    "foundation_model": "from extraction or unknown",
    "parameters": "from extraction or unknown",
    "training_objective": "from extraction or unknown"
  }},
  "datasets": [{{"name": "...", "task": "..."}}],
  "metrics": ["metric1", "metric2"],
  "results": [{{"metric": "...", "value": "...", "setting": "..."}}],
  "compute": {{
    "gpus": "from extraction or unknown",
    "steps": "from extraction or unknown",
    "batch_size": "from extraction or unknown",
    "training_time": "from extraction or unknown"
  }},
  "limitations": "from extraction or abstract or unknown",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "relevance_tags": {json.dumps(categories)}
}}

Output ONLY the JSON object:"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_evidence_list(
    extraction: dict[str, Any],
    candidates: list[str],
) -> list[dict[str, Any]]:
    """
    Resolve 1-based ``snippet_index`` values from *extraction* into actual
    candidate sentences and return a flat evidence list.

    Each item in the returned list is::

        {
            "field":         str,  # "dataset" | "model_info" | "metric" | "result" | "compute"
            "value":         str,  # extracted value summary
            "snippet":       str,  # resolved candidate sentence (may be "" if index invalid)
            "snippet_index": int,  # 1-based number (omitted when None/invalid)
        }

    snippet_index uses the same 1-based numbering shown in the extraction
    prompt (candidate [1] is candidates[0], etc.).

    When *candidates* is empty (abstract-only fallback), all items will have
    ``snippet=""`` and no ``snippet_index`` key.
    """
    n = len(candidates)
    evidence: list[dict[str, Any]] = []

    def _resolve(idx: Any) -> tuple[str, int | None]:
        """Look up candidates by 1-based idx; return (sentence, idx) or ("", None)."""
        if not isinstance(idx, int) or idx < 1 or idx > n:
            return "", None
        return candidates[idx - 1], idx  # convert 1-based → 0-based for list access

    # Datasets
    for ds in extraction.get("datasets", []):
        if not isinstance(ds, dict):
            continue
        snippet, idx = _resolve(ds.get("snippet_index"))
        item: dict[str, Any] = {
            "field": "dataset",
            "value": ds.get("name", "unknown"),
            "snippet": snippet,
        }
        if idx is not None:
            item["snippet_index"] = idx
        if snippet:  # only include if we have any snippet
            evidence.append(item)

    # Model info (single object)
    model_info = extraction.get("model_info", {})
    if isinstance(model_info, dict):
        snippet, idx = _resolve(model_info.get("snippet_index"))
        item = {
            "field": "model_info",
            "value": model_info.get("backbone", "unknown"),
            "snippet": snippet,
        }
        if idx is not None:
            item["snippet_index"] = idx
        if snippet:
            evidence.append(item)

    # Metrics
    for m in extraction.get("metrics", []):
        if not isinstance(m, dict):
            continue
        snippet, idx = _resolve(m.get("snippet_index"))
        item = {
            "field": "metric",
            "value": m.get("name", "unknown"),
            "snippet": snippet,
        }
        if idx is not None:
            item["snippet_index"] = idx
        if snippet:
            evidence.append(item)

    # Results
    for r in extraction.get("results", []):
        if not isinstance(r, dict):
            continue
        snippet, idx = _resolve(r.get("snippet_index"))
        item = {
            "field": "result",
            "value": f"{r.get('metric', '')}={r.get('value', '')}",
            "snippet": snippet,
        }
        if idx is not None:
            item["snippet_index"] = idx
        if snippet:
            evidence.append(item)

    # Compute (single object)
    compute = extraction.get("compute", {})
    if isinstance(compute, dict):
        snippet, idx = _resolve(compute.get("snippet_index"))
        item = {
            "field": "compute",
            "value": compute.get("gpus", "unknown"),
            "snippet": snippet,
        }
        if idx is not None:
            item["snippet_index"] = idx
        if snippet:
            evidence.append(item)

    return evidence


def _has_invalid_snippets(evidence: list[dict[str, Any]]) -> bool:
    """Return True if any evidence item has a snippet shorter than _MIN_SNIPPET_LEN."""
    return any(len(e.get("snippet", "")) < _MIN_SNIPPET_LEN for e in evidence)


def _fit_prompt(base_url: str, model: str, prompt: str) -> tuple[str, int]:
    """
    Ensure *prompt* fits within the configured context window.

    1. Tokenise *prompt* via get_prompt_tokens_vllm().
    2. Compute budget = VLLM_MAX_LEN – prompt_tokens – _SAFETY_TOKENS.
    3. If budget ≤ 0, hard-truncate the prompt to ~¾ of the context
       window (in chars) and recount once.  Raises RuntimeError if the
       prompt is still too long after truncation.
    4. Return (prompt, max_tokens) where max_tokens is clamped to
       [_MIN_RESPONSE_TOKENS, _MAX_RESPONSE_TOKENS].
    """
    ctx = int(os.getenv("VLLM_MAX_LEN", str(_VLLM_MAX_LEN_DEFAULT)))

    prompt_tokens = get_prompt_tokens_vllm(prompt)
    budget = ctx - prompt_tokens - _SAFETY_TOKENS

    if budget <= 0:
        max_prompt_chars = ctx * 3
        prompt = prompt[:max_prompt_chars]
        prompt_tokens = get_prompt_tokens_vllm(prompt)
        budget = ctx - prompt_tokens - _SAFETY_TOKENS
        logger.warning(
            "Prompt truncated to %d chars (%d tokens, budget=%d)",
            len(prompt),
            prompt_tokens,
            budget,
        )
        if budget <= 0:
            raise RuntimeError(
                f"Prompt still too long after truncation "
                f"({prompt_tokens} tokens, ctx={ctx}, safety={_SAFETY_TOKENS})"
            )

    max_tokens = max(_MIN_RESPONSE_TOKENS, min(_MAX_RESPONSE_TOKENS, budget))
    logger.debug(
        "Prompt: %d tokens → max_tokens=%d (ctx=%d budget=%d)",
        prompt_tokens,
        max_tokens,
        ctx,
        budget,
    )
    return prompt, max_tokens


def _post_chat(base_url: str, model: str, prompt: str, max_tokens: int) -> str:
    """
    POST *prompt* to the vLLM /chat/completions endpoint.

    Logs the full response body before raising on HTTP 400 so that
    context-length errors are visible in the logs.
    """
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=_TIMEOUT,
        )
        if resp.status_code == 400:
            logger.error("vLLM API returned HTTP 400. Response body: %s", resp.text)
        resp.raise_for_status()

        data = resp.json()
        if "choices" not in data or not data["choices"]:
            raise RuntimeError(f"Unexpected response format (no choices): {data}")
        return data["choices"][0]["message"]["content"]

    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"vLLM API timeout (connect={_TIMEOUT[0]}s, read={_TIMEOUT[1]}s)"
        )
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"vLLM API HTTP error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"vLLM API request failed: {exc}") from exc


def _save_json_failure(raw: str, arxiv_id: str) -> None:
    """
    Persist *raw* LLM output to ``logs/json_failures/<arxiv_id>.txt``.

    The arxiv_id is sanitised (``/`` → ``_``) so it is safe as a filename.
    Errors during saving are logged but never propagated.
    """
    failure_dir = os.path.join("logs", "json_failures")
    try:
        os.makedirs(failure_dir, exist_ok=True)
        safe_id = arxiv_id.replace("/", "_").replace(" ", "_")
        path = os.path.join(failure_dir, f"{safe_id}.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(raw)
        logger.error("Raw LLM output saved to %s", path)
    except Exception as exc:
        logger.error("Could not write JSON failure log: %s", exc)


def _robust_parse_json(
    raw: str,
    base_url: str,
    model: str,
    arxiv_id: str = "unknown",
) -> dict[str, Any]:
    """
    Parse JSON from *raw* with three progressive attempts.

    1. ``json.loads(raw)`` — direct parse.
    2. Extract the substring from the first ``{`` to the last ``}`` and
       ``json.loads`` that.
    3. Ask the model to repair the broken content::

           "Fix the following text into a single valid JSON object.
            Output JSON only."

       The repair call uses ``temperature=0`` and ``max_tokens=_MAX_RESPONSE_TOKENS``.
       The result is then parsed with steps 1 and 2 again.

    If all three stages fail, the raw content is saved to
    ``logs/json_failures/<arxiv_id>.txt`` and ``RuntimeError`` is raised.

    Args:
        raw:       Raw text returned by the LLM.
        base_url:  vLLM base URL (for the repair call).
        model:     Model name (for the repair call).
        arxiv_id:  Used only as the failure-log filename stem.

    Returns:
        Parsed dict.

    Raises:
        RuntimeError: After all repair attempts fail.
    """
    # Stage 1 — direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Stage 2 — extract first { … last }
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > 0:
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass

    logger.warning(
        "JSON extraction failed for %s — calling model repair", arxiv_id
    )

    # Stage 3 — model repair (temperature=0, max_tokens=_MAX_RESPONSE_TOKENS)
    repair_prompt = (
        "Fix the following text into a single valid JSON object. "
        "Output JSON only.\n\n" + raw
    )
    try:
        repaired = _post_chat(base_url, model, repair_prompt, max_tokens=_MAX_RESPONSE_TOKENS)

        # Try stages 1+2 on the repaired output
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

        r_start = repaired.find("{")
        r_end = repaired.rfind("}") + 1
        if r_start != -1 and r_end > 0:
            return json.loads(repaired[r_start:r_end])

        raise json.JSONDecodeError("Repair produced no valid JSON object", repaired, 0)

    except (RuntimeError, json.JSONDecodeError) as exc:
        _save_json_failure(raw, arxiv_id)
        raise RuntimeError(
            f"JSON repair failed for {arxiv_id}: {exc}"
        ) from exc


def _call_with_retry(
    base_url: str,
    model: str,
    prompt: str,
    arxiv_id: str = "unknown",
) -> dict[str, Any]:
    """
    Fit the prompt to the context window, call the vLLM chat API, and
    parse the JSON response robustly.

    Delegates all parse/repair logic to ``_robust_parse_json``:
      1. Direct ``json.loads``.
      2. ``{…}`` substring extraction + ``json.loads``.
      3. Model-based repair call (temperature=0, max_tokens=_MAX_RESPONSE_TOKENS).
      4. Failure → save raw output to ``logs/json_failures/<arxiv_id>.txt``.

    Raises:
        RuntimeError: If the prompt cannot be fitted, the API call fails,
                      or all JSON repair attempts are exhausted.
    """
    prompt, max_tokens = _fit_prompt(base_url, model, prompt)
    raw = _post_chat(base_url, model, prompt, max_tokens)
    return _robust_parse_json(raw, base_url, model, arxiv_id=arxiv_id)

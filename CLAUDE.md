# Project: Paper Agent (arXiv-first)

## Objective
Build an arXiv-first daily ingestion and summarization system that:

1. Collects newly published papers daily
2. Stores metadata + abstract + pdf link
3. Generates structured summaries
4. Extracts datasets, models, metrics, and compute information
5. Supports keyword/date filtering
6. Detects trending research keywords automatically
7. (Next phase) Idea → relevant recent papers via embedding similarity

---

## Scope (MVP Phase 1)

- Source: arXiv only
- No heavy UI (CLI or minimal API is enough)
- Store everything, process selectively
- Light summary for all papers
- Deep summary only for selected/high-priority papers
- Enforce arXiv rate limiting (3 requests/sec)
- Deduplicate by arxiv_id + version

---

## Core Design Principles

- Never hallucinate experimental numbers
- Light summary must rely only on title + abstract
- Deep summary may use PDF/tex text
- Always return strict JSON structures
- Prefer deterministic extraction + LLM refinement
- All summaries must pass Pydantic validation before DB insert

---

## Structured Summary Schema (Required JSON Output)

Each paper must return:

{
  "one_liner": "",
  "problem": "",
  "method": "",
  "model_info": {
    "backbone": "",
    "foundation_model": "",
    "parameters": "",
    "training_objective": ""
  },
  "datasets": [
    {"name": "", "task": ""}
  ],
  "metrics": [],
  "results": [
    {"metric": "", "value": "", "setting": ""}
  ],
  "compute": {
    "gpus": "",
    "steps": "",
    "batch_size": "",
    "training_time": ""
  },
  "limitations": "",
  "keywords": [],
  "relevance_tags": []
}

If information is not explicitly present, return "unknown".
Never fabricate values.

---

## Trending Keyword Detection

After sufficient data accumulation:

1. Extract keywords from:
   - Title
   - Abstract
   - LLM-generated keywords field

2. Compute frequency:
   - Recent 7 days
   - Previous 30 days baseline

3. Trending score:
   score = (recent_freq + 1) / (baseline_freq + 1)
   (If baseline_freq == 0, optionally mark as "new")

4. Rank and store top trending keywords weekly.

---

## Storage Requirements

We must support:

- papers
- paper_versions (track arXiv updates)
  - Unique key: (arxiv_id, version)
  - Latest version determined by max(version)
  - Re-summarize when new version detected
- summaries (light/deep)
- embeddings (Phase 2)
- keyword_stats (for trending)

---

## Coding Standards

- Python 3.11+
- Modular structure
- Small pure functions
- Pydantic models for validation
- Clear separation of:
  - ingestion
  - parsing
  - summarization
  - ranking
  - API

---

## Error Handling (MVP)

- arXiv API: enforce 3 req/sec and retry up to 3 times
- LLM API: retry once if invalid JSON; otherwise skip summary
- Validation failure: do not insert invalid summaries
- Pipeline must continue even if individual papers fail

---

## Minimal API (Phase 1)

- GET /papers?keyword=&from=&to=&category=
- GET /papers/{arxiv_id}
- GET /papers/{arxiv_id}/summary

---

## Commands

Daily ingest:
python scripts/run_daily_ingest.py --since 1d

Backfill:
python scripts/backfill.py --from YYYY-MM-DD --to YYYY-MM-DD

Run API:
uvicorn apps.api.main:app --reload

---

## Phase Roadmap

Phase 1:
- arXiv connector
- Rate limiting (3 req/sec)
- DB schema
- Deduplication (arxiv_id + version)
- Light summary
- Pydantic validation
- Filtering API

Phase 2:
- Deep summary (PDF parsing)
- Embeddings
- Idea → paper recommendation

Phase 3:
- Trending keyword engine
- Priority ranking systems
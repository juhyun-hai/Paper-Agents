# Paper Agent - arXiv Paper Ingestion & Summarization

An arXiv-first daily ingestion and summarization system that collects papers, generates structured summaries, and detects trending research keywords.

## Quick Start

### 1. Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL
```

### 2. Initialize Database

```bash
# Create PostgreSQL database
createdb paper_agent

# Run schema initialization
python scripts/init_db.py
```

### 3. Run Daily Ingestion

```bash
# Fetch papers from last 1 day (default categories: cs.LG, cs.CV, cs.CL, stat.ML)
python scripts/run_daily_ingest.py --since 1d

# Fetch from last 7 days with custom categories
python scripts/run_daily_ingest.py --since 7d --categories cs.AI,cs.CL

# Filter by keywords
python scripts/run_daily_ingest.py --since 3d --keywords "large language model,transformer"

# Test database connection
python scripts/run_daily_ingest.py --test-db
```

### 4. Generate Summaries

```bash
# Generate light summaries (default: dummy backend)
python scripts/run_light_summary.py --limit 50

# Generate deep summaries using vLLM with 70B model
python scripts/run_light_summary.py --summary-type deep --backend vllm --limit 10

# Generate light summaries with vLLM (8B model)
python scripts/run_light_summary.py --summary-type light --backend vllm --limit 100

# Show summary statistics
python scripts/run_light_summary.py --stats

# Debug mode
python scripts/run_light_summary.py --limit 10 --debug
```

## Phase 1 Features (Current)

✅ **Implemented:**
- arXiv API connector with rate limiting (3 req/sec)
- Paper metadata ingestion with deduplication
- PostgreSQL storage (arxiv_id + version)
- Automatic version tracking (latest_version_id)
- Light summarization (dummy/heuristic-based)
- Summary validation and storage
- CLI tools for ingestion and summarization
- Retry logic with exponential backoff

🚧 **Not Yet Implemented:**
- LLM-based summarization (currently using dummy)
- Deep summarization
- Filtering API endpoints
- Embedding generation
- Trending keyword detection

## Project Structure

```
paper-agent/
├── packages/core/
│   ├── connectors/
│   │   └── arxiv.py              # arXiv API client
│   ├── summarizers/
│   │   └── light.py              # Light summarizer (dummy)
│   └── storage/
│       ├── db.py                 # Database connection
│       ├── ingest_repo.py        # Ingestion repository
│       └── summary_repo.py       # Summary repository
├── scripts/
│   ├── run_daily_ingest.py       # Main ingestion script
│   ├── run_light_summary.py      # Light summary generation
│   └── init_db.py                # Database initialization
├── schema.sql                    # PostgreSQL schema
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
└── CLAUDE.md                     # Project instructions
```

## Database Schema

**papers** - Canonical paper entities (1 row per arXiv ID)
- Tracks latest version via `latest_version_id`

**paper_versions** - Version-specific data (1 row per version)
- Unique constraint on `(arxiv_id, version)`
- Stores title, authors, abstract, categories

**summaries** - Structured JSON summaries (Phase 1+)
- light/deep summary types
- Validates required fields

**embeddings** - Vector embeddings (Phase 2)
- For similarity search and recommendations

**keyword_stats** - Trending keywords (Phase 3)
- Daily keyword frequency tracking

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:password@localhost:5432/paper_agent

# Optional
ARXIV_EMAIL=your.email@example.com  # Recommended for arXiv API

# Summarization backend
SUMMARY_BACKEND=dummy  # Options: "dummy" or "vllm"

# vLLM configuration (required if SUMMARY_BACKEND=vllm)
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
```

## CLI Examples

### Ingestion
```bash
# Standard daily run (last 24 hours)
python scripts/run_daily_ingest.py --since 1d

# Weekly backfill
python scripts/run_daily_ingest.py --since 7d --max-results 5000

# Specific research area
python scripts/run_daily_ingest.py --since 3d --categories cs.AI,cs.RO

# Debug mode
python scripts/run_daily_ingest.py --since 1d --debug
```

### Summarization
```bash
# Generate light summaries (dummy backend)
python scripts/run_light_summary.py --summary-type light

# Generate deep summaries with vLLM (70B model)
python scripts/run_light_summary.py --summary-type deep --backend vllm

# Use vLLM for both light and deep (different models)
# 1. Start vLLM with 8B model for light summaries
VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct python scripts/run_light_summary.py \
  --summary-type light --backend vllm --limit 100

# 2. Restart vLLM with 70B model for deep summaries
VLLM_MODEL=meta-llama/Llama-3.1-70B-Instruct python scripts/run_light_summary.py \
  --summary-type deep --backend vllm --limit 10

# View statistics
python scripts/run_light_summary.py --stats
```

## arXiv API Details

- **Base URL**: http://export.arxiv.org/api/query
- **Rate Limit**: Max 3 requests/second (enforced)
- **Retry Logic**: Up to 3 attempts with exponential backoff
- **Response Format**: Atom XML (parsed via xml.etree)

## Summary Backends

### Dummy Backend (Default)
- Simple heuristic-based extraction
- No LLM required
- Fast and free
- Good for testing and prototyping

### vLLM Backend
- LLM-based summarization via OpenAI-compatible API
- Requires running vLLM server
- Generates structured JSON summaries
- Temperature=0 for deterministic output
- Max 700 tokens per summary
- Retry logic for malformed JSON

**Start vLLM server:**
```bash
# Example: Run Llama-3.1-8B-Instruct
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --port 8000 \
  --max-model-len 4096

# Or with quantization
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --port 8000 \
  --quantization awq
```

## Summary Schema

Each light summary includes:
- **one_liner**: Brief one-sentence summary
- **problem**: Problem statement
- **method**: Method description
- **keywords**: Key terms and topics
- **relevance_tags**: arXiv categories
- **model_info**, **datasets**, **metrics**, **results**, **compute**: Extracted if present, else "unknown"

**Critical rule:** Never fabricate experimental numbers. If not explicitly in abstract, return "unknown" or empty arrays.

### Light vs Deep Summaries

- **Light summaries**: Based on title + abstract only
  - Fast generation (~1-2 seconds with 8B model)
  - Suitable for all papers
  - Recommended model: Llama-3.1-8B-Instruct

- **Deep summaries**: Can include PDF/full-text analysis (future)
  - Slower generation (~5-10 seconds with 70B model)
  - More detailed analysis
  - Recommended model: Llama-3.1-70B-Instruct
  - Use for high-priority papers only

Both types use the same JSON schema and can coexist in the database without conflicts.

## Next Steps

1. Replace dummy summarizer with LLM (Claude API)
2. Build filtering API (FastAPI)
3. Add unit tests
4. Implement deep summarization (PDF parsing)

## Development

```bash
# Format code
black packages/ scripts/

# Lint
ruff check packages/ scripts/

# Run tests (when implemented)
pytest tests/
```

## License

MIT

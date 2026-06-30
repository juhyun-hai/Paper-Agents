# HotPaper.ai · AI 논문 큐레이션 + 한국어 deep summary

> **No ads · No sponsored ranking** — 학술 도구는 학술적으로.

매일 03시 자동 수집 (HuggingFace + arXiv + Conference) → Featured Top 25 + ar5iv 본문 기반 한국어 deep summary + 동적 tag 추출 → 사이트/RSS/MCP/Saved-search 제공.

## 🌐 사이트
- **운영**: https://hotpaper.ai
- **RSS**: https://hotpaper.ai/api/feed/rss (Feedly/Inoreader)
- **MCP**: [mcp_server/README.md](mcp_server/README.md) — Claude Desktop/Cursor에서 직접 검색
- **데모**: `docker compose -f docker-compose.demo.yml up` → localhost:5174

## 🧠 핵심 기능

| 영역 | 무엇 | 어디 |
|---|---|---|
| **수집** | HF Daily + arXiv RSS + Crossref + S2 conf venue 통합, multi-source bonus | `scripts/daily_cron.py` (03시 KST) |
| **점수** | featured_score v4 (popularity × cross × venue × HAI), Top 25 선정 | 동상 |
| **요약** | Ollama qwen3:32b + ar5iv 본문 활용 (PDF 0 다운로드) → 한국어 7섹션 deep summary | `scripts/auto_daily_summaries.py` (04시 KST) |
| **환각 차단** | P6 Verifier — 요약 수치를 본문에 grep, 미매칭 비율 30% 초과 시 `+unverified` 태그 | 동상 |
| **동적 카테고리** | LLM 자동 tag 추출 (paper당 5-10), `concepts` + `paper_concepts` | `scripts/extract_tags.py` |
| **의미 검색** | Conf seed centroid → 최근 arXiv top-K cosine (BGE-m3) | `scripts/arxiv_semantic_bridge.py` |
| **사이트 layer** | Tag chip + Popular Tags cloud + Bookmarks (localStorage) + Alerts (saved search) + RSS feed | `frontend/src/` |
| **알람** | Healthchecks.io heartbeat, 0편이면 fail ping → 자동 메일 알람 | `scripts/auto_daily_summaries.py` |
| **운영** | cron + venv python, logrotate (일 회전, 14일 보관), HAI plugin isolation (`ENABLE_HAI_PLUGIN=false`) | `scripts/run_daily.sh`, `scripts/logrotate.conf` |

## 📚 문서

- [`docs/PLUGIN_HAI.md`](docs/PLUGIN_HAI.md) — fork할 때 HAI Lab 코드 끄는 방법
- [`docs/TALK_OUTLINE.md`](docs/TALK_OUTLINE.md) — 강연 outline skeleton
- [`templates/CUSTOMIZE.md`](templates/CUSTOMIZE.md) — 자기 분야로 customize
- [`mcp_server/README.md`](mcp_server/README.md) — Claude Desktop/Cursor 등록

## ⚙️ Cron 등록 권장

```cron
# 매일 03시 KST: 수집 + Featured + tag + semantic bridge + figure backfill + embedding
0 3 * * * /home/.../backend/scripts/run_daily.sh >> /home/.../backend/logs/hotpaper_daily.log 2>&1

# 매일 04시 KST: 한국어 deep summary (Ollama qwen3:32b + ar5iv)
0 4 * * * cd /home/.../backend && /home/.../venv/bin/python3 -u scripts/auto_daily_summaries.py >> /home/.../backend/logs/auto_summaries.log 2>&1

# 매일 09시 KST: saved-search 이메일 digest (SMTP env 있을 때)
0 9 * * * cd /home/.../backend && /home/.../venv/bin/python3 -u scripts/send_alert_digest.py >> /home/.../backend/logs/alert_digest.log 2>&1

# 매일 00:05: log rotation
5 0 * * * /usr/sbin/logrotate -s /home/.../backend/logs/.logrotate.state /home/.../backend/scripts/logrotate.conf
```

## 🚀 1편 직접 처리

```bash
# 수집 + 점수 (시간 짧으면)
venv/bin/python backend/scripts/daily_cron.py

# 1편 deep summary (Ollama 32B + ar5iv 자동 시도)
SUMMARY_LOOKBACK_DAYS=1 venv/bin/python backend/scripts/auto_daily_summaries.py
```

---

## 옛 Quick Start (Phase 1 MVP)


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

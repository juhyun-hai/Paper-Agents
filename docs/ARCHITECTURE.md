# Research Intelligence Platform -- Technical Architecture

## Current State Analysis

### What Exists Today

```
Backend (Python/FastAPI):
  - app.py                          # Main FastAPI server (SQLite + PG dual mode)
  - src/api/main.py                 # Second FastAPI app (Vite React frontend)
  - src/api/search.py               # FTS5 + semantic hybrid search
  - src/database/db_manager.py      # SQLite PaperDBManager
  - src/database/models.py          # SQLite CREATE TABLE statements
  - src/recommender/content_recommender.py  # Cosine similarity recommender
  - src/recommender/trend_recommender.py    # Trending papers by velocity
  - src/collector/arxiv_collector.py        # arXiv API connector
  - src/collector/semantic_scholar.py       # Citation enrichment
  - packages/core/recommend/embeddings.py   # BAAI/bge-m3 embedding pipeline
  - packages/core/recommend/index_faiss.py  # FAISS index for fast ANN
  - packages/core/storage/sqlite_db.py      # Alternate SQLite layer
  - packages/core/summarizers/light.py      # Light summary (title+abstract)
  - packages/core/summarizers/deep_pdf_vllm.py  # Deep PDF summary via vLLM

Frontend (React + Vite + Tailwind):
  - frontend/src/App.jsx            # Router: Home, Search, Paper, Graph, Dashboard, Feedback
  - frontend/src/components/        # Navbar, SearchBar, PaperCard, KnowledgeGraph, MiniGraph, etc.
  - frontend/src/pages/             # Home, Search, Paper, Graph, Dashboard, Trending, etc.

Data:
  - data/paper_db.sqlite            # ~1,262 papers
  - data/embeddings/*.npy           # Per-paper embedding files (all-MiniLM-L6-v2)
  - config/settings.yaml            # Runtime config

Schema (PostgreSQL, planned):
  - schema.sql                      # papers, paper_versions, summaries, embeddings, keyword_stats
```

### Key Gaps to Address

1. **No explanation generation** -- recommendations lack reasoning
2. **No research question generation** -- no gap/contradiction detection
3. **No knowledge graph data model** -- graph is built on-the-fly from embeddings only
4. **No comparison engine** -- no side-by-side paper analysis
5. **No Obsidian export** -- config exists but no implementation
6. **Dual database** -- SQLite in production, PostgreSQL schema exists but unused
7. **No Redis caching** -- every request hits DB/embeddings directly
8. **No pgvector** -- embeddings stored as .npy files on disk
9. **Frontend is basic React/Vite** -- needs migration to Next.js with App Router

---

## Target Architecture

### System Overview

```
                    +------------------+
                    |   Next.js App    |
                    |   (App Router)   |
                    +--------+---------+
                             |
                    +--------+---------+
                    |   API Gateway    |
                    |   (FastAPI)      |
                    +--------+---------+
                             |
          +------------------+------------------+
          |                  |                  |
   +------+------+   +------+------+   +------+------+
   | Search &    |   | AI Layer    |   | Graph       |
   | Discovery   |   | (Reasoning) |   | Engine      |
   +------+------+   +------+------+   +------+------+
          |                  |                  |
   +------+------------------+------------------+------+
   |                    Data Layer                     |
   |  PostgreSQL + pgvector  |  Redis  |  Object Store |
   +---------------------------------------------------+
```

### Directory Structure (Target)

```
paper-agent/
|
|-- backend/
|   |-- alembic/                        # Database migrations
|   |   |-- versions/
|   |   |-- env.py
|   |   +-- alembic.ini
|   |
|   |-- app/
|   |   |-- __init__.py
|   |   |-- main.py                     # FastAPI application factory
|   |   |-- config.py                   # Settings via pydantic-settings
|   |   |-- dependencies.py             # FastAPI dependency injection
|   |   |
|   |   |-- models/                     # SQLAlchemy ORM models
|   |   |   |-- __init__.py
|   |   |   |-- base.py                 # DeclarativeBase, common mixins
|   |   |   |-- paper.py                # Paper, PaperVersion
|   |   |   |-- summary.py             # Summary
|   |   |   |-- embedding.py           # Embedding (pgvector)
|   |   |   |-- graph.py               # GraphNode, GraphEdge
|   |   |   |-- collection.py          # Collection, CollectionItem
|   |   |   |-- research_question.py   # ResearchQuestion
|   |   |   |-- user.py                # UserNote, UserBookmark
|   |   |   +-- keyword_stat.py        # KeywordStat
|   |   |
|   |   |-- schemas/                    # Pydantic request/response schemas
|   |   |   |-- __init__.py
|   |   |   |-- paper.py
|   |   |   |-- summary.py
|   |   |   |-- graph.py
|   |   |   |-- research.py            # ResearchAnalyzeRequest/Response
|   |   |   |-- comparison.py          # ComparisonRequest/Response
|   |   |   |-- export.py              # ObsidianExportRequest/Response
|   |   |   +-- common.py              # Pagination, filters, etc.
|   |   |
|   |   |-- api/                        # Route modules
|   |   |   |-- __init__.py
|   |   |   |-- router.py              # Central router aggregation
|   |   |   |-- papers.py              # GET /papers, /papers/{id}, /papers/{id}/summary
|   |   |   |-- search.py              # GET /search (hybrid FTS + semantic)
|   |   |   |-- research.py            # POST /research/analyze, GET /research/questions
|   |   |   |-- compare.py             # POST /papers/compare
|   |   |   |-- graph.py               # GET /graph, GET /graph/{paper_id}
|   |   |   |-- collections.py         # CRUD /collections
|   |   |   |-- export.py              # POST /export/obsidian
|   |   |   |-- trending.py            # GET /trending
|   |   |   |-- ingest.py              # POST /admin/ingest
|   |   |   +-- health.py              # GET /health
|   |   |
|   |   |-- services/                   # Business logic layer
|   |   |   |-- __init__.py
|   |   |   |-- paper_service.py
|   |   |   |-- search_service.py       # Hybrid search (FTS + pgvector)
|   |   |   |-- research_service.py     # Idea -> papers with reasoning
|   |   |   |-- comparison_service.py   # Side-by-side analysis
|   |   |   |-- graph_service.py        # Knowledge graph construction
|   |   |   |-- question_service.py     # Research question generation
|   |   |   |-- export_service.py       # Obsidian markdown export
|   |   |   |-- embedding_service.py    # Embedding pipeline (BAAI/bge-m3)
|   |   |   |-- summary_service.py      # Light/deep summarization
|   |   |   |-- trending_service.py     # Keyword trending
|   |   |   +-- collection_service.py
|   |   |
|   |   |-- ai/                         # AI/LLM integration layer
|   |   |   |-- __init__.py
|   |   |   |-- client.py              # Unified LLM client (OpenAI/Claude/vLLM)
|   |   |   |-- prompts.py             # All prompt templates
|   |   |   |-- explanation.py         # WHY-explanation generator
|   |   |   |-- question_gen.py        # Research question generator
|   |   |   |-- comparison_gen.py      # Comparison reasoning generator
|   |   |   +-- validators.py          # JSON output validation
|   |   |
|   |   |-- connectors/                # External data sources
|   |   |   |-- __init__.py
|   |   |   |-- arxiv.py               # arXiv API (rate-limited)
|   |   |   |-- semantic_scholar.py    # Citation data
|   |   |   +-- pdf_parser.py          # PDF text extraction
|   |   |
|   |   +-- core/                       # Shared utilities
|   |       |-- __init__.py
|   |       |-- cache.py               # Redis cache wrapper
|   |       |-- rate_limiter.py        # Rate limiting
|   |       |-- logging.py            # Structured logging
|   |       +-- exceptions.py          # Custom exceptions
|   |
|   |-- scripts/
|   |   |-- migrate_sqlite_to_pg.py    # One-time migration script
|   |   |-- run_daily_ingest.py
|   |   |-- build_embeddings.py
|   |   |-- build_graph.py
|   |   +-- backfill.py
|   |
|   |-- tests/
|   |   |-- conftest.py                # Fixtures (test DB, test client)
|   |   |-- test_search_service.py
|   |   |-- test_research_service.py
|   |   |-- test_comparison_service.py
|   |   |-- test_graph_service.py
|   |   |-- test_export_service.py
|   |   +-- test_api/
|   |       |-- test_papers.py
|   |       |-- test_research.py
|   |       +-- test_graph.py
|   |
|   |-- pyproject.toml
|   |-- requirements.txt
|   +-- Dockerfile
|
|-- frontend/
|   |-- app/                            # Next.js App Router
|   |   |-- layout.tsx                  # Root layout (4-panel structure)
|   |   |-- page.tsx                    # Home / landing
|   |   |-- globals.css
|   |   |-- (workspace)/                # Route group for main workspace
|   |   |   |-- layout.tsx             # 4-panel workspace layout
|   |   |   |-- page.tsx               # Default workspace view
|   |   |   |-- research/
|   |   |   |   +-- page.tsx           # Research analyze flow
|   |   |   |-- papers/
|   |   |   |   |-- page.tsx           # Paper list / search
|   |   |   |   +-- [id]/
|   |   |   |       +-- page.tsx       # Paper detail
|   |   |   |-- graph/
|   |   |   |   +-- page.tsx           # Full graph explorer
|   |   |   |-- compare/
|   |   |   |   +-- page.tsx           # Comparison table
|   |   |   |-- collections/
|   |   |   |   |-- page.tsx
|   |   |   |   +-- [id]/
|   |   |   |       +-- page.tsx
|   |   |   +-- export/
|   |   |       +-- page.tsx           # Obsidian export config
|   |   +-- api/                        # Next.js API routes (BFF proxy)
|   |       +-- [...proxy]/
|   |           +-- route.ts           # Proxy to FastAPI backend
|   |
|   |-- components/
|   |   |-- ui/                         # shadcn/ui primitives
|   |   |   |-- button.tsx
|   |   |   |-- card.tsx
|   |   |   |-- input.tsx
|   |   |   |-- badge.tsx
|   |   |   |-- tabs.tsx
|   |   |   |-- dialog.tsx
|   |   |   |-- dropdown-menu.tsx
|   |   |   |-- command.tsx            # Command palette (cmdk)
|   |   |   +-- ...
|   |   |
|   |   |-- panels/                     # 4-panel layout components
|   |   |   |-- LeftPanel.tsx          # Idea input, filters, goal selector
|   |   |   |-- CenterPanel.tsx        # Paper list, explanations, quick actions
|   |   |   |-- RightPanel.tsx         # Graph visualization
|   |   |   +-- BottomPanel.tsx        # Comparison table, research questions
|   |   |
|   |   |-- research/
|   |   |   |-- IdeaInput.tsx          # Textarea + goal selector
|   |   |   |-- FilterBar.tsx          # Category, date range, venue filters
|   |   |   |-- GoalSelector.tsx       # "Explore" / "Deep dive" / "Compare" / "Export"
|   |   |   +-- ResearchProgress.tsx   # Streaming progress indicator
|   |   |
|   |   |-- papers/
|   |   |   |-- PaperCard.tsx          # Paper with explanation snippet
|   |   |   |-- PaperDetail.tsx        # Full paper view with summary
|   |   |   |-- PaperList.tsx          # Scrollable paper results
|   |   |   +-- ExplanationBadge.tsx   # "Why recommended" expandable
|   |   |
|   |   |-- graph/
|   |   |   |-- ForceGraph.tsx         # react-force-graph-2d wrapper
|   |   |   |-- GraphControls.tsx      # Zoom, filter, layout controls
|   |   |   |-- GraphLegend.tsx        # Node type legend
|   |   |   +-- NodeTooltip.tsx        # Hover tooltip for graph nodes
|   |   |
|   |   |-- compare/
|   |   |   |-- ComparisonTable.tsx    # Side-by-side paper comparison
|   |   |   |-- DimensionSelector.tsx  # Select comparison axes
|   |   |   +-- ComparisonReasoning.tsx # AI-generated comparison text
|   |   |
|   |   |-- questions/
|   |   |   |-- QuestionList.tsx       # Generated research questions
|   |   |   +-- QuestionCard.tsx       # Individual question with rationale
|   |   |
|   |   |-- export/
|   |   |   |-- ObsidianPreview.tsx    # Preview markdown output
|   |   |   +-- ExportConfig.tsx       # Configure export structure
|   |   |
|   |   +-- shared/
|   |       |-- CommandPalette.tsx      # Ctrl+K command palette
|   |       |-- ThemeToggle.tsx
|   |       |-- LoadingStates.tsx
|   |       +-- ErrorBoundary.tsx
|   |
|   |-- lib/
|   |   |-- api.ts                     # Typed API client (fetch wrapper)
|   |   |-- hooks/
|   |   |   |-- useResearch.ts         # Research analyze hook
|   |   |   |-- useGraph.ts            # Graph data hook
|   |   |   |-- useComparison.ts       # Comparison hook
|   |   |   +-- usePapers.ts           # Paper search/list hook
|   |   |-- stores/
|   |   |   |-- workspace-store.ts     # Zustand store for workspace state
|   |   |   +-- graph-store.ts         # Graph interaction state
|   |   +-- utils.ts                   # cn(), formatDate(), etc.
|   |
|   |-- public/
|   |-- next.config.ts
|   |-- tailwind.config.ts
|   |-- tsconfig.json
|   |-- package.json
|   +-- Dockerfile
|
|-- docker-compose.yml                  # PostgreSQL, Redis, backend, frontend
|-- .env.example
+-- Makefile                            # Common operations
```

---

## Data Architecture

### PostgreSQL Schema (Extended from existing schema.sql)

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- Trigram fuzzy matching

-- ============================================================
-- CORE TABLES (migrated from existing schema.sql)
-- ============================================================

-- papers, paper_versions, summaries, keyword_stats
-- (keep existing schema.sql definitions unchanged)

-- ============================================================
-- EMBEDDING TABLE (upgraded to pgvector)
-- ============================================================

-- Replace BYTEA with native vector type
CREATE TABLE embeddings (
  id BIGSERIAL PRIMARY KEY,
  paper_version_id BIGINT NOT NULL REFERENCES paper_versions(id) ON DELETE CASCADE,
  embedding_type VARCHAR(20) NOT NULL
    CHECK (embedding_type IN ('title_abstract', 'abstract', 'full_text', 'summary')),
  model_name VARCHAR(100) NOT NULL,
  embedding vector(1024),              -- bge-m3 output dimension
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT embeddings_unique UNIQUE (paper_version_id, embedding_type, model_name)
);

-- HNSW index for fast ANN search
CREATE INDEX idx_embeddings_hnsw ON embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 200);

-- ============================================================
-- KNOWLEDGE GRAPH TABLES
-- ============================================================

-- Canonical concept/entity nodes
CREATE TABLE graph_nodes (
  id BIGSERIAL PRIMARY KEY,
  node_type VARCHAR(30) NOT NULL
    CHECK (node_type IN (
      'paper', 'concept', 'author', 'venue',
      'user_note', 'research_question', 'collection'
    )),
  external_id VARCHAR(100),            -- arxiv_id, author ORCID, venue slug, etc.
  label TEXT NOT NULL,                 -- Display name
  properties JSONB NOT NULL DEFAULT '{}',
  embedding vector(1024),             -- Optional node embedding for graph ML
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_graph_nodes_type ON graph_nodes(node_type);
CREATE INDEX idx_graph_nodes_external_id ON graph_nodes(external_id);
CREATE INDEX idx_graph_nodes_label_trgm ON graph_nodes USING GIN (label gin_trgm_ops);

-- Edges between nodes
CREATE TABLE graph_edges (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
  target_id BIGINT NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
  edge_type VARCHAR(30) NOT NULL
    CHECK (edge_type IN (
      'cites', 'cited_by', 'similar_to',
      'authored_by', 'published_at',
      'has_concept', 'concept_related',
      'user_link', 'part_of_collection',
      'answers_question'
    )),
  weight FLOAT DEFAULT 1.0,
  properties JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT graph_edges_no_self_loop CHECK (source_id != target_id),
  CONSTRAINT graph_edges_unique UNIQUE (source_id, target_id, edge_type)
);

CREATE INDEX idx_graph_edges_source ON graph_edges(source_id);
CREATE INDEX idx_graph_edges_target ON graph_edges(target_id);
CREATE INDEX idx_graph_edges_type ON graph_edges(edge_type);

-- ============================================================
-- RESEARCH INTELLIGENCE TABLES
-- ============================================================

-- Collections (user-created groupings)
CREATE TABLE collections (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  description TEXT,
  goal_type VARCHAR(30) DEFAULT 'explore'
    CHECK (goal_type IN ('explore', 'deep_dive', 'compare', 'survey')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE collection_items (
  id BIGSERIAL PRIMARY KEY,
  collection_id BIGINT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
  paper_id BIGINT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  added_reason TEXT,                   -- AI-generated reason for inclusion
  position INTEGER DEFAULT 0,         -- Ordering within collection
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT collection_items_unique UNIQUE (collection_id, paper_id)
);

-- Research questions generated from paper analysis
CREATE TABLE research_questions (
  id BIGSERIAL PRIMARY KEY,
  question TEXT NOT NULL,
  question_type VARCHAR(30) NOT NULL
    CHECK (question_type IN (
      'gap', 'contradiction', 'extension',
      'application', 'methodology', 'open_problem'
    )),
  rationale TEXT NOT NULL,             -- Why this question matters
  source_paper_ids BIGINT[] NOT NULL,  -- Papers that prompted this question
  confidence FLOAT DEFAULT 0.5,
  properties JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_research_questions_type ON research_questions(question_type);

-- Comparison records (cached analysis results)
CREATE TABLE comparisons (
  id BIGSERIAL PRIMARY KEY,
  paper_ids BIGINT[] NOT NULL,         -- Papers being compared
  dimensions JSONB NOT NULL,           -- {dimension: {paper_id: value}}
  reasoning TEXT NOT NULL,             -- AI-generated comparison narrative
  model_used VARCHAR(100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User notes (annotations on papers/concepts)
CREATE TABLE user_notes (
  id BIGSERIAL PRIMARY KEY,
  target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('paper', 'concept', 'collection')),
  target_id BIGINT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Explanation cache (why a paper was recommended)
CREATE TABLE explanations (
  id BIGSERIAL PRIMARY KEY,
  query_text TEXT NOT NULL,            -- The user's input idea/query
  paper_id BIGINT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  explanation TEXT NOT NULL,           -- AI-generated explanation
  relevance_score FLOAT NOT NULL,
  reasoning_chain JSONB,              -- Step-by-step reasoning
  model_used VARCHAR(100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_explanations_paper ON explanations(paper_id);
```

### Redis Cache Strategy

```
Key patterns:
  search:{hash(query+filters)}          -> JSON search results     TTL: 1h
  embedding:{paper_version_id}:{type}   -> float32 bytes           TTL: 24h
  graph:subgraph:{center_id}:{depth}    -> JSON subgraph           TTL: 30m
  comparison:{hash(sorted_paper_ids)}   -> JSON comparison         TTL: 6h
  questions:{hash(paper_ids)}           -> JSON questions           TTL: 6h
  explanation:{hash(query)}:{paper_id}  -> JSON explanation         TTL: 3h
  trending:keywords:{period}            -> JSON keyword list        TTL: 15m
  stats:global                          -> JSON system stats        TTL: 5m
```

---

## API Design

### Core Endpoints

```
# Paper Discovery
GET    /api/v2/papers                    # Search/browse with filters
GET    /api/v2/papers/{arxiv_id}         # Paper detail + summary
GET    /api/v2/papers/{arxiv_id}/similar # Similar papers with explanations
GET    /api/v2/search                    # Hybrid search (FTS + semantic)
GET    /api/v2/autocomplete              # Search suggestions

# Research Intelligence (NEW)
POST   /api/v2/research/analyze          # Idea -> papers + reasoning + graph
POST   /api/v2/papers/compare            # Multi-paper comparison table
GET    /api/v2/research/questions         # Generated research questions
POST   /api/v2/research/questions/generate # Generate questions from paper set

# Knowledge Graph (NEW)
GET    /api/v2/graph                     # Full graph data (paginated)
GET    /api/v2/graph/subgraph/{node_id}  # Ego-centric subgraph
GET    /api/v2/graph/path/{from}/{to}    # Shortest path between nodes
POST   /api/v2/graph/expand              # Expand graph from selected nodes
GET    /api/v2/graph/concepts            # List extracted concepts

# Collections (NEW)
GET    /api/v2/collections
POST   /api/v2/collections
GET    /api/v2/collections/{id}
PUT    /api/v2/collections/{id}
DELETE /api/v2/collections/{id}
POST   /api/v2/collections/{id}/papers   # Add paper with AI reason

# Export (NEW)
POST   /api/v2/export/obsidian           # Generate Obsidian vault ZIP
POST   /api/v2/export/bibtex             # BibTeX export
POST   /api/v2/export/markdown           # Single markdown summary

# Existing (migrated)
GET    /api/v2/trending                  # Trending keywords
GET    /api/v2/stats                     # System statistics
GET    /api/v2/categories                # Category list
GET    /api/v2/hot-topics                # Hot topics
POST   /api/v2/admin/ingest              # Trigger ingestion
GET    /api/v2/health                    # Health check
```

### Key Request/Response Schemas

#### POST /api/v2/research/analyze

```json
// Request
{
  "idea": "How can we use diffusion models for molecular generation?",
  "goal": "explore",                    // explore | deep_dive | compare | survey
  "filters": {
    "categories": ["cs.LG", "q-bio.BM"],
    "date_from": "2024-01-01",
    "date_to": null,
    "min_citations": 0
  },
  "limit": 20,
  "explain": true                       // Generate per-paper explanations
}

// Response
{
  "query_analysis": {
    "interpreted_as": "Application of denoising diffusion probabilistic models to molecular graph generation and drug discovery",
    "key_concepts": ["diffusion models", "molecular generation", "drug discovery", "graph neural networks"],
    "suggested_categories": ["cs.LG", "q-bio.BM", "cs.AI"]
  },
  "papers": [
    {
      "arxiv_id": "2209.02738",
      "title": "Equivariant Diffusion for Molecule Generation in 3D",
      "authors": ["Hoogeboom, E.", "..."],
      "abstract": "...",
      "date": "2022-09-06",
      "categories": ["cs.LG"],
      "similarity_score": 0.912,
      "explanation": {
        "relevance": "Directly addresses 3D molecular generation using equivariant diffusion, establishing the foundation for your research direction.",
        "connection_to_idea": "This paper solves the key challenge of applying diffusion to 3D molecular structures by preserving rotational equivariance.",
        "key_contribution": "E(3)-equivariant diffusion process for atom coordinates and features."
      },
      "quick_actions": ["add_to_collection", "compare", "view_graph", "export"]
    }
  ],
  "graph_snapshot": {
    "nodes": [...],
    "edges": [...]
  },
  "research_questions": [
    {
      "question": "Can equivariant diffusion models generalize to larger molecules (>100 atoms) without significant quality degradation?",
      "type": "extension",
      "rationale": "Current models are validated on small molecules. Scaling behavior remains unexplored.",
      "source_papers": ["2209.02738", "2203.17003"]
    }
  ],
  "meta": {
    "total_candidates_scanned": 1262,
    "processing_time_ms": 2340,
    "models_used": {
      "embedding": "BAAI/bge-m3",
      "reasoning": "claude-3-5-sonnet"
    }
  }
}
```

#### POST /api/v2/papers/compare

```json
// Request
{
  "paper_ids": ["2209.02738", "2203.17003", "2302.04313"],
  "dimensions": ["method", "datasets", "metrics", "compute", "limitations"]
}

// Response
{
  "comparison": {
    "papers": [
      {"arxiv_id": "2209.02738", "title": "Equivariant Diffusion..."},
      {"arxiv_id": "2203.17003", "title": "GeoDiff..."},
      {"arxiv_id": "2302.04313", "title": "DiffDock..."}
    ],
    "table": {
      "method": {
        "2209.02738": "E(3)-equivariant DDPM on atom coordinates + features",
        "2203.17003": "SE(3)-equivariant geometric diffusion",
        "2302.04313": "Diffusion over ligand poses in SE(3)"
      },
      "datasets": {
        "2209.02738": ["QM9", "GEOM-Drugs"],
        "2203.17003": ["QM9", "GEOM-Drugs"],
        "2302.04313": ["PDBBind", "ESMFold structures"]
      },
      "metrics": {
        "2209.02738": ["Atom stability", "Molecule stability", "Validity"],
        "2203.17003": ["COV-R", "MAT-R"],
        "2302.04313": ["Top-1 RMSD", "% below 2A"]
      },
      "compute": {
        "2209.02738": "8x A100, ~24h",
        "2203.17003": "4x V100, ~12h",
        "2302.04313": "4x A100, ~8h"
      },
      "limitations": {
        "2209.02738": "Limited to small molecules (<30 atoms in practice)",
        "2203.17003": "Slower sampling due to SE(3) computations",
        "2302.04313": "Requires known protein structure"
      }
    },
    "reasoning": "These three papers represent a progression in applying diffusion models to molecular tasks...",
    "model_used": "claude-3-5-sonnet"
  }
}
```

#### POST /api/v2/export/obsidian

```json
// Request
{
  "paper_ids": ["2209.02738", "2203.17003"],
  "collection_id": 5,
  "include": {
    "paper_notes": true,
    "summaries": true,
    "comparison": true,
    "research_questions": true,
    "graph_moc": true                  // Map of Content index
  },
  "template": "academic"               // academic | compact | detailed
}

// Response: application/zip stream
// Contains:
//   Papers/
//     2209.02738 - Equivariant Diffusion.md
//     2203.17003 - GeoDiff.md
//   Concepts/
//     Diffusion Models.md
//     Molecular Generation.md
//   Comparisons/
//     Diffusion for Molecules Comparison.md
//   Questions/
//     Open Questions - Molecular Diffusion.md
//   MOC - Research Collection.md        // Map of Content (index)
```

---

## Service Layer Design

### SearchService (Hybrid Search)

```
Query -> normalize (synonyms, typo fix)
      -> parallel: [FTS via pg_trgm] + [pgvector ANN]
      -> merge with weighted scoring (0.6 FTS + 0.4 semantic)
      -> filter (category, date, venue)
      -> sort (relevance, citations, date, compound)
      -> paginate
      -> cache result
```

Migration from current: replace SQLite FTS5 with PostgreSQL `pg_trgm` + `tsvector`. Replace .npy file loading with `pgvector` `<=>` operator.

### ResearchService (Core Intelligence)

```
POST /research/analyze:

1. Parse idea -> extract key concepts (LLM call or keyword extraction)
2. Embed idea text using BAAI/bge-m3
3. pgvector ANN search: top 100 candidates by cosine similarity
4. Re-rank with LLM scoring (batch):
   - For each candidate, score relevance to idea (0-1)
   - Generate 1-sentence explanation
5. Take top N papers
6. If explain=true, generate full explanations (parallel LLM calls)
7. Build local knowledge graph snapshot:
   - Paper nodes + concept nodes extracted from results
   - Citation edges from Semantic Scholar
   - Similarity edges from embedding distance
   - Concept edges from shared keywords
8. Generate research questions (single LLM call on the paper set)
9. Return combined response
```

### GraphService (Knowledge Graph)

```
Graph construction pipeline (offline, triggered after ingestion):

1. For each new paper:
   a. Create paper node in graph_nodes
   b. Create author nodes + authored_by edges
   c. Extract concepts from title/abstract/summary keywords
   d. Create concept nodes (deduplicated) + has_concept edges
   e. Fetch citations from Semantic Scholar -> cites/cited_by edges
   f. Compute embedding similarity to existing papers -> similar_to edges (threshold > 0.7)

2. Concept clustering:
   a. Group concepts by embedding similarity
   b. Create concept_related edges between closely related concepts

Query patterns:
  - Subgraph: BFS from center node, depth 1-3
  - Path: Dijkstra between two nodes
  - Expand: Add neighbors of selected nodes
  - Filter: By node_type, edge_type, date range
```

### ExportService (Obsidian)

```
Markdown template per node type:

Paper note template:
  ---
  arxiv_id: {id}
  title: {title}
  authors: [{authors}]
  date: {date}
  categories: [{categories}]
  tags: [{keywords}]
  ---
  # {title}
  ## One-Liner
  {one_liner}
  ## Problem
  {problem}
  ## Method
  {method}
  ## Key Results
  {results table}
  ## Limitations
  {limitations}
  ## Related Papers
  {wikilinks to similar papers}
  ## Notes
  {user_notes if any}

MOC template:
  # {collection_name}
  ## Papers
  {list of wikilinks grouped by relevance}
  ## Concept Map
  {list of concept wikilinks}
  ## Research Questions
  {numbered list with links to source papers}
  ## Comparison
  {embedded comparison table}
```

---

## Embedding Pipeline

### Current -> Target Migration

```
Current:
  Model: all-MiniLM-L6-v2 (384 dims, stored as .npy files)
  Index: FAISS IndexFlatIP (separate process)
  Search: Load all .npy files, compute cosine similarity in loop

Target:
  Model: BAAI/bge-m3 (1024 dims, stored in pgvector column)
  Index: pgvector HNSW (in-database, automatic)
  Search: SQL query with vector_cosine_ops
```

### Embedding Computation Service

```python
# Pseudocode for embedding pipeline

class EmbeddingService:
    def __init__(self, model_name="BAAI/bge-m3"):
        self.model = SentenceTransformer(model_name)
        self.dim = 1024

    async def embed_paper(self, paper_version_id: int) -> None:
        """Compute and store embedding for a paper version."""
        pv = await get_paper_version(paper_version_id)
        summaries = await get_summaries(paper_version_id)
        text = build_index_text(pv, summaries)  # reuse existing function
        vector = self.model.encode(text, normalize_embeddings=True)

        await upsert_embedding(
            paper_version_id=paper_version_id,
            embedding_type="title_abstract",
            model_name="BAAI/bge-m3",
            embedding=vector
        )

    async def search_similar(self, query_text: str, limit: int = 20):
        """Semantic search using pgvector."""
        query_vec = self.model.encode(query_text, normalize_embeddings=True)
        # pgvector cosine distance: 1 - cosine_similarity
        results = await db.execute("""
            SELECT e.paper_version_id, 1 - (e.embedding <=> $1::vector) as similarity
            FROM embeddings e
            WHERE e.embedding_type = 'title_abstract'
            ORDER BY e.embedding <=> $1::vector
            LIMIT $2
        """, [query_vec.tolist(), limit])
        return results
```

---

## AI Layer Design

### LLM Client Abstraction

```python
# Unified interface for explanation/question/comparison generation

class AIClient:
    """Supports OpenAI, Anthropic Claude, and local vLLM backends."""

    async def generate_explanation(
        self, idea: str, paper: PaperData
    ) -> Explanation:
        prompt = EXPLANATION_PROMPT.format(idea=idea, title=paper.title, abstract=paper.abstract)
        response = await self._call(prompt, response_model=Explanation)
        return response

    async def generate_comparison(
        self, papers: list[PaperData], dimensions: list[str]
    ) -> Comparison:
        prompt = COMPARISON_PROMPT.format(...)
        response = await self._call(prompt, response_model=Comparison)
        return response

    async def generate_questions(
        self, papers: list[PaperData]
    ) -> list[ResearchQuestion]:
        prompt = QUESTION_PROMPT.format(...)
        response = await self._call(prompt, response_model=QuestionList)
        return response.questions
```

### Prompt Templates (Key Examples)

```
EXPLANATION_PROMPT:
  Given the research idea: "{idea}"

  Analyze this paper:
  Title: {title}
  Abstract: {abstract}

  Provide a structured explanation of why this paper is relevant:
  1. relevance: One sentence on why this paper matters for the idea
  2. connection_to_idea: How the paper's contribution connects to the idea
  3. key_contribution: The paper's main technical contribution

  Return valid JSON matching the schema.

COMPARISON_PROMPT:
  Compare the following papers across these dimensions: {dimensions}

  Papers:
  {for each paper: title, abstract, summary_data}

  For each dimension, provide a concise comparison value for each paper.
  Then write a 2-3 sentence reasoning paragraph explaining the key differences.

  Return valid JSON matching the schema.

QUESTION_PROMPT:
  Based on these papers:
  {for each paper: title, one_liner, method, limitations}

  Generate research questions in these categories:
  - gap: What is missing from the collective body of work?
  - contradiction: Where do papers disagree or present conflicting results?
  - extension: What natural next steps does this work suggest?
  - open_problem: What fundamental challenges remain unsolved?

  For each question, provide the question text, type, rationale, and source paper IDs.
```

---

## Frontend Architecture

### Layout System

```
+------------------------------------------------------------------+
|  Navbar: Logo | Search (Ctrl+K) | Collections | Export | Theme   |
+------------------------------------------------------------------+
|          |                           |                           |
|  LEFT    |        CENTER             |        RIGHT              |
|  PANEL   |        PANEL              |        PANEL              |
|  (320px) |        (flex-1)           |        (400px)            |
|          |                           |                           |
|  Idea    |  Paper Results            |  Knowledge Graph          |
|  Input   |  - PaperCard              |  - ForceGraph             |
|          |  - Explanation            |  - Controls               |
|  Filters |  - Quick Actions          |  - Legend                 |
|  - Cat   |                           |  - Node detail            |
|  - Date  |                           |                           |
|  - Venue |                           |                           |
|          |                           |                           |
|  Goal    |                           |                           |
|  Selector|                           |                           |
|          |                           |                           |
+----------+---------------------------+---------------------------+
|                       BOTTOM PANEL (300px)                       |
|  Tabs: [Comparison] [Research Questions] [Export Preview]        |
|                                                                  |
|  ComparisonTable | QuestionList | ObsidianPreview                |
+------------------------------------------------------------------+
```

### State Management (Zustand)

```typescript
interface WorkspaceState {
  // Research flow
  idea: string;
  goal: 'explore' | 'deep_dive' | 'compare' | 'survey';
  filters: FilterState;
  results: PaperResult[];
  explanations: Map<string, Explanation>;
  isAnalyzing: boolean;

  // Selection
  selectedPapers: Set<string>;          // arxiv_ids selected for comparison/export
  focusedPaper: string | null;          // Currently detailed paper

  // Graph
  graphData: GraphData | null;
  graphCenter: string | null;

  // Bottom panel
  comparison: ComparisonData | null;
  questions: ResearchQuestion[];
  activeBottomTab: 'comparison' | 'questions' | 'export';

  // Actions
  analyze: (idea: string) => Promise<void>;
  selectPaper: (id: string) => void;
  comparePapers: () => Promise<void>;
  generateQuestions: () => Promise<void>;
  exportObsidian: () => Promise<Blob>;
}
```

### Graph Visualization

Use `react-force-graph-2d` for the primary graph view:

```typescript
// Node styling by type
const nodeStyles = {
  paper:             { color: '#3b82f6', shape: 'circle' },
  concept:           { color: '#8b5cf6', shape: 'diamond' },
  author:            { color: '#10b981', shape: 'square' },
  venue:             { color: '#f59e0b', shape: 'triangle' },
  research_question: { color: '#ef4444', shape: 'star' },
  collection:        { color: '#6366f1', shape: 'hexagon' },
};

// Edge styling by type
const edgeStyles = {
  cites:             { color: '#94a3b8', dash: false },
  similar_to:        { color: '#60a5fa', dash: true },
  has_concept:       { color: '#a78bfa', dash: false },
  concept_related:   { color: '#c084fc', dash: true },
  user_link:         { color: '#34d399', dash: false },
};
```

---

## Migration Strategy

### Phase 0: Preparation (1 week)

```
Tasks:
  1. Set up PostgreSQL + pgvector in Docker
  2. Set up Redis in Docker
  3. Write alembic migration from schema.sql
  4. Write migrate_sqlite_to_pg.py script:
     - Read all papers from SQLite
     - Insert into PostgreSQL papers + paper_versions tables
     - Migrate embeddings from .npy files to pgvector column
  5. Verify data integrity after migration
  6. Set up docker-compose.yml for local development
```

### Phase 1: Backend Core (2 weeks)

```
Week 1:
  - backend/app/ scaffold with FastAPI factory pattern
  - SQLAlchemy ORM models for all tables
  - Config via pydantic-settings
  - Dependency injection (DB session, Redis, AI client)
  - Paper CRUD endpoints (GET /papers, /papers/{id})
  - Hybrid search endpoint (pgvector + pg_trgm)
  - Redis caching layer

Week 2:
  - Embedding service (BAAI/bge-m3 + pgvector storage)
  - POST /research/analyze (idea -> papers with explanations)
  - POST /papers/compare (comparison table generation)
  - GET /research/questions (question generation)
  - Knowledge graph construction pipeline
  - GET /graph endpoints
```

### Phase 2: Frontend (2 weeks)

```
Week 3:
  - Next.js App Router scaffold
  - shadcn/ui setup
  - 4-panel layout system
  - Left panel: IdeaInput, FilterBar, GoalSelector
  - Center panel: PaperList, PaperCard with ExplanationBadge
  - API client (typed fetch wrapper)
  - Zustand workspace store

Week 4:
  - Right panel: ForceGraph with controls
  - Bottom panel: ComparisonTable, QuestionList
  - Obsidian export preview + download
  - Command palette (Ctrl+K)
  - Dark mode
  - Loading states + error boundaries
```

### Phase 3: Polish + Intelligence (1 week)

```
  - Collection CRUD (create, add papers, export)
  - Graph path-finding (shortest path between papers)
  - Streaming responses for long AI operations
  - Performance: batch embedding, query optimization
  - Tests for all services
  - Production Docker setup
```

---

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://paper_agent:secret@localhost:5432/paper_agent
REDIS_URL=redis://localhost:6379/0

# AI
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
AI_PROVIDER=anthropic                  # openai | anthropic | vllm
AI_MODEL=claude-3-5-sonnet-20241022
VLLM_BASE_URL=http://localhost:8000/v1 # If using local vLLM

# Embedding
EMBEDDING_MODEL=BAAI/bge-m3
HF_HOME=data/cache/hf

# arXiv
ARXIV_EMAIL=your@email.com
ARXIV_RATE_LIMIT=3

# App
APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

### Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: paper_agent
      POSTGRES_USER: paper_agent
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://paper_agent:secret@postgres:5432/paper_agent
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8080:8080"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8080
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  pgdata:
```

---

## Performance Targets

| Operation                          | Target Latency | Strategy                          |
|------------------------------------|---------------|-----------------------------------|
| Paper search (hybrid)              | < 200ms       | pgvector HNSW + pg_trgm + Redis  |
| Research analyze (no explain)      | < 2s          | pgvector ANN + re-rank batch     |
| Research analyze (with explain)    | < 8s          | Parallel LLM calls + streaming   |
| Paper comparison (3 papers)        | < 5s          | Single LLM call + cache          |
| Question generation                | < 4s          | Single LLM call + cache          |
| Graph subgraph (depth 2)           | < 300ms       | Pre-computed edges + Redis cache  |
| Obsidian export (20 papers)        | < 3s          | Template rendering + ZIP stream   |
| Full graph load (500 nodes)        | < 1s          | Paginated query + client-side GPU |

---

## Key Technical Decisions

1. **pgvector over FAISS**: Eliminates the separate index management, simplifies deployment, enables SQL-based filtering combined with vector search. HNSW index provides sub-linear search time.

2. **BAAI/bge-m3 over all-MiniLM-L6-v2**: 1024-dim multilingual embeddings with superior performance on academic text. Supports the Korean synonym/search use case visible in the current codebase.

3. **Next.js App Router over current React/Vite**: Server components for initial data loading, streaming for long AI operations, built-in API routes for BFF pattern, better SEO for public-facing pages.

4. **Zustand over Redux**: Lightweight state management sufficient for the workspace pattern. No boilerplate for the selected-papers / comparison / graph interaction states.

5. **react-force-graph-2d over full d3**: Handles the WebGL rendering needed for 500+ node graphs while providing React integration. Falls back to canvas for larger graphs.

6. **Pydantic-settings for config**: Type-safe configuration with `.env` file support, validation at startup, consistent with existing Pydantic usage in the codebase.

7. **Alembic for migrations**: Standard SQLAlchemy migration tool, supports the progressive schema changes needed as new features land.

8. **Streaming responses for AI operations**: Use Server-Sent Events (SSE) for the research/analyze endpoint so the frontend can show progressive results (papers first, then explanations, then questions).

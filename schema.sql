-- Paper Agent PostgreSQL Schema (Phase 1) - Minimal & Clean
-- PostgreSQL 14+ recommended

-- =========================
-- TABLES
-- =========================

-- Canonical paper entity (1 row per arXiv id)
CREATE TABLE papers (
  id BIGSERIAL PRIMARY KEY,
  arxiv_id VARCHAR(20) NOT NULL UNIQUE,
  title TEXT NOT NULL,
  primary_category TEXT,
  published_date TIMESTAMPTZ NOT NULL,
  updated_date TIMESTAMPTZ,
  latest_version_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT papers_arxiv_id_check CHECK (arxiv_id ~ '^[0-9]{4}\.[0-9]{4,5}$|^[a-z\\-]+/[0-9]{7}$')
);

-- Version rows (v1/v2/v3...) - dedup here
CREATE TABLE paper_versions (
  id BIGSERIAL PRIMARY KEY,
  paper_id BIGINT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  arxiv_id VARCHAR(20) NOT NULL,
  version VARCHAR(10) NOT NULL, -- v1, v2, ...
  title TEXT NOT NULL,
  authors JSONB NOT NULL,
  abstract TEXT NOT NULL,
  categories JSONB NOT NULL,
  pdf_url TEXT NOT NULL,
  html_url TEXT,
  version_published_date TIMESTAMPTZ NOT NULL,
  updated_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT paper_versions_unique UNIQUE (arxiv_id, version),
  CONSTRAINT paper_versions_version_check CHECK (version ~ '^v[0-9]+$'),
  CONSTRAINT paper_versions_categories_check CHECK (jsonb_array_length(categories) > 0)
);

-- Link latest_version_id to actual version row
ALTER TABLE papers
  ADD CONSTRAINT papers_latest_version_fk
  FOREIGN KEY (latest_version_id) REFERENCES paper_versions(id);

-- Migration for existing databases (run once if upgrading from initial schema):
--   ALTER TABLE summaries DROP CONSTRAINT IF EXISTS summaries_summary_type_check;
--   ALTER TABLE summaries ADD CONSTRAINT summaries_summary_type_check
--     CHECK (summary_type IN ('light', 'deep', 'deep_pdf'));

-- Structured summaries (light/deep/deep_pdf) stored as JSONB
CREATE TABLE summaries (
  id BIGSERIAL PRIMARY KEY,
  paper_version_id BIGINT NOT NULL REFERENCES paper_versions(id) ON DELETE CASCADE,
  summary_type VARCHAR(10) NOT NULL CHECK (summary_type IN ('light', 'deep', 'deep_pdf')),
  summary_data JSONB NOT NULL,
  model_used VARCHAR(100),
  tokens_used INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT summaries_unique UNIQUE (paper_version_id, summary_type),
  CONSTRAINT summaries_required_fields CHECK (
    summary_data ? 'one_liner' AND
    summary_data ? 'problem' AND
    summary_data ? 'method' AND
    summary_data ? 'keywords'
  )
);

-- Future embedding support (Phase 2) - store bytes for now (no pgvector required)
CREATE TABLE embeddings (
  id BIGSERIAL PRIMARY KEY,
  paper_version_id BIGINT NOT NULL REFERENCES paper_versions(id) ON DELETE CASCADE,
  embedding_type VARCHAR(20) NOT NULL CHECK (embedding_type IN ('title_abstract', 'abstract', 'full_text', 'summary')),
  model_name VARCHAR(100) NOT NULL,
  embedding_bytes BYTEA NOT NULL,
  dims INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT embeddings_unique UNIQUE (paper_version_id, embedding_type, model_name)
);

-- Daily keyword counts for trending (Phase 3)
CREATE TABLE keyword_stats (
  id BIGSERIAL PRIMARY KEY,
  day DATE NOT NULL,
  keyword VARCHAR(100) NOT NULL,
  source VARCHAR(20) NOT NULL CHECK (source IN ('title','abstract','llm')),
  count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT keyword_stats_unique UNIQUE (day, keyword, source),
  CONSTRAINT keyword_stats_count_check CHECK (count >= 0)
);

-- =========================
-- INDEXES (Phase 1 essentials)
-- =========================
CREATE INDEX idx_papers_published_date ON papers(published_date DESC);
CREATE INDEX idx_papers_updated_date ON papers(updated_date DESC);

CREATE INDEX idx_versions_arxiv_id ON paper_versions(arxiv_id);
CREATE INDEX idx_versions_paper_id ON paper_versions(paper_id);
CREATE INDEX idx_versions_published_date ON paper_versions(version_published_date DESC);
CREATE INDEX idx_versions_categories ON paper_versions USING GIN (categories);

CREATE INDEX idx_summaries_version_id ON summaries(paper_version_id);
CREATE INDEX idx_summaries_type ON summaries(summary_type);

CREATE INDEX idx_keyword_stats_day ON keyword_stats(day);
CREATE INDEX idx_keyword_stats_keyword ON keyword_stats(keyword);
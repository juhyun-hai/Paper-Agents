-- Research Intelligence Platform Database Schema
-- PostgreSQL 16 + pgvector extension

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- =========================
-- CORE ENTITIES
-- =========================

-- Papers table (core paper metadata)
CREATE TABLE papers (
    id BIGSERIAL PRIMARY KEY,
    arxiv_id VARCHAR(20) NOT NULL UNIQUE,
    title TEXT NOT NULL,
    abstract TEXT,
    authors JSONB NOT NULL DEFAULT '[]',
    categories JSONB NOT NULL DEFAULT '[]',
    venue TEXT,
    year INTEGER,
    citation_count INTEGER DEFAULT 0,
    pdf_url TEXT,
    html_url TEXT,
    published_date TIMESTAMPTZ,
    updated_date TIMESTAMPTZ,
    -- Embeddings for semantic search
    title_embedding VECTOR(1024),
    abstract_embedding VECTOR(1024),
    full_embedding VECTOR(1024),
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT papers_arxiv_id_check CHECK (arxiv_id ~ '^[0-9]{4}\.[0-9]{4,5}$|^[a-z\\-]+/[0-9]{7}$')
);

-- Concepts table (extracted concepts: methods, tasks, datasets, etc)
CREATE TABLE concepts (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('method', 'task', 'dataset', 'metric', 'domain', 'keyword')),
    description TEXT,
    aliases JSONB DEFAULT '[]',
    embedding VECTOR(1024),
    paper_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(name, type)
);

-- Many-to-many relationship between papers and concepts
CREATE TABLE paper_concepts (
    id BIGSERIAL PRIMARY KEY,
    paper_id BIGINT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    concept_id BIGINT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    weight FLOAT DEFAULT 1.0,
    confidence FLOAT DEFAULT 1.0,
    extraction_method VARCHAR(50) DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(paper_id, concept_id)
);

-- Authors table (for better author tracking)
CREATE TABLE authors (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    affiliations JSONB DEFAULT '[]',
    h_index INTEGER,
    total_citations INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(normalized_name)
);

-- Paper-Author relationship
CREATE TABLE paper_authors (
    paper_id BIGINT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    author_id BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    author_order INTEGER NOT NULL,
    is_corresponding BOOLEAN DEFAULT FALSE,

    PRIMARY KEY(paper_id, author_id)
);

-- =========================
-- KNOWLEDGE GRAPH
-- =========================

-- Graph nodes (unified node representation)
CREATE TABLE graph_nodes (
    id BIGSERIAL PRIMARY KEY,
    node_type VARCHAR(20) NOT NULL CHECK (node_type IN ('paper', 'concept', 'author', 'venue', 'user_note', 'collection')),
    entity_id BIGINT NOT NULL,
    label TEXT NOT NULL,
    properties JSONB DEFAULT '{}',
    embedding VECTOR(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(node_type, entity_id)
);

-- Graph edges (relationships between nodes)
CREATE TABLE graph_edges (
    id BIGSERIAL PRIMARY KEY,
    source_node_id BIGINT NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id BIGINT NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(30) NOT NULL CHECK (edge_type IN (
        'citation', 'similarity', 'uses_method', 'uses_dataset',
        'same_author', 'same_venue', 'user_link', 'contains'
    )),
    weight FLOAT DEFAULT 1.0,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(source_node_id, target_node_id, edge_type)
);

-- =========================
-- USER WORKSPACE
-- =========================

-- User notes and annotations
CREATE TABLE user_notes (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    note_type VARCHAR(20) DEFAULT 'general',
    linked_papers JSONB DEFAULT '[]',
    linked_concepts JSONB DEFAULT '[]',
    tags JSONB DEFAULT '[]',
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Research questions generated from analysis
CREATE TABLE research_questions (
    id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    question_type VARCHAR(30) NOT NULL CHECK (question_type IN ('gap', 'contradiction', 'extension', 'application', 'methodology')),
    related_papers JSONB NOT NULL DEFAULT '[]',
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    novelty_score FLOAT CHECK (novelty_score >= 0 AND novelty_score <= 1),
    evidence TEXT,
    generated_by VARCHAR(50) DEFAULT 'system',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Paper collections (curated sets)
CREATE TABLE collections (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    paper_ids JSONB NOT NULL DEFAULT '[]',
    tags JSONB DEFAULT '[]',
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- AI INTELLIGENCE LAYER
-- =========================

-- Paper comparisons (side-by-side analysis)
CREATE TABLE comparisons (
    id BIGSERIAL PRIMARY KEY,
    paper_ids JSONB NOT NULL,
    comparison_data JSONB NOT NULL,
    focus_aspects JSONB DEFAULT '["method", "task", "dataset", "results"]',
    generated_by VARCHAR(50) DEFAULT 'system',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Explanations for recommendations
CREATE TABLE explanations (
    id BIGSERIAL PRIMARY KEY,
    paper_id BIGINT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    query_idea TEXT NOT NULL,
    explanation_type VARCHAR(30) NOT NULL CHECK (explanation_type IN ('relevance', 'method_similarity', 'task_similarity', 'gap_analysis', 'trend_analysis')),
    explanation TEXT NOT NULL,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    generated_by VARCHAR(50) DEFAULT 'system',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- SEARCH & PERFORMANCE INDEXES
-- =========================

-- Full-text search indexes
CREATE INDEX papers_title_fts_idx ON papers USING gin (to_tsvector('english', title));
CREATE INDEX papers_abstract_fts_idx ON papers USING gin (to_tsvector('english', abstract));
CREATE INDEX papers_authors_fts_idx ON papers USING gin (to_tsvector('english', authors::text));

-- Vector similarity indexes (HNSW for fast ANN search)
CREATE INDEX papers_title_embedding_hnsw_idx ON papers USING hnsw (title_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX papers_abstract_embedding_hnsw_idx ON papers USING hnsw (abstract_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX papers_full_embedding_hnsw_idx ON papers USING hnsw (full_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX concepts_embedding_hnsw_idx ON concepts USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Regular indexes for common queries
CREATE INDEX papers_year_idx ON papers (year DESC);
CREATE INDEX papers_citation_count_idx ON papers (citation_count DESC);
CREATE INDEX papers_published_date_idx ON papers (published_date DESC);
CREATE INDEX papers_categories_gin_idx ON papers USING gin (categories);

CREATE INDEX concepts_type_idx ON concepts (type);
CREATE INDEX concepts_paper_count_idx ON concepts (paper_count DESC);

CREATE INDEX paper_concepts_paper_id_idx ON paper_concepts (paper_id);
CREATE INDEX paper_concepts_concept_id_idx ON paper_concepts (concept_id);
CREATE INDEX paper_concepts_weight_idx ON paper_concepts (weight DESC);

CREATE INDEX graph_edges_source_idx ON graph_edges (source_node_id);
CREATE INDEX graph_edges_target_idx ON graph_edges (target_node_id);
CREATE INDEX graph_edges_type_idx ON graph_edges (edge_type);
CREATE INDEX graph_edges_weight_idx ON graph_edges (weight DESC);

CREATE INDEX user_notes_created_at_idx ON user_notes (created_at DESC);
CREATE INDEX research_questions_type_idx ON research_questions (question_type);
CREATE INDEX research_questions_confidence_idx ON research_questions (confidence_score DESC);

-- =========================
-- PERFORMANCE OPTIMIZATION
-- =========================

-- Update timestamps trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
CREATE TRIGGER update_papers_updated_at BEFORE UPDATE ON papers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_concepts_updated_at BEFORE UPDATE ON concepts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_notes_updated_at BEFORE UPDATE ON user_notes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_collections_updated_at BEFORE UPDATE ON collections FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================
-- VIEWS FOR COMMON QUERIES
-- =========================

-- Papers with full metadata
CREATE VIEW papers_full AS
SELECT
    p.id,
    p.arxiv_id,
    p.title,
    p.abstract,
    p.authors,
    p.categories,
    p.venue,
    p.year,
    p.citation_count,
    p.published_date,
    COALESCE(array_agg(DISTINCT c.name) FILTER (WHERE c.id IS NOT NULL), '{}') as concept_names,
    COALESCE(array_agg(DISTINCT c.type) FILTER (WHERE c.id IS NOT NULL), '{}') as concept_types
FROM papers p
LEFT JOIN paper_concepts pc ON p.id = pc.paper_id
LEFT JOIN concepts c ON pc.concept_id = c.id
GROUP BY p.id;

-- Top concepts by paper count
CREATE VIEW top_concepts AS
SELECT
    c.id,
    c.name,
    c.type,
    c.paper_count,
    COUNT(pc.paper_id) as actual_paper_count
FROM concepts c
LEFT JOIN paper_concepts pc ON c.id = pc.concept_id
GROUP BY c.id, c.name, c.type, c.paper_count
ORDER BY actual_paper_count DESC;
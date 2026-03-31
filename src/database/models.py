CREATE_PAPERS_TABLE = """
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arxiv_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    authors TEXT NOT NULL,
    abstract TEXT,
    categories TEXT,
    date TEXT,
    pdf_url TEXT,
    rating INTEGER DEFAULT NULL,
    status TEXT DEFAULT 'unread',
    embedding_path TEXT DEFAULT NULL,
    citation_count INTEGER DEFAULT 0,
    venue TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
)
"""

CREATE_FEEDBACK_TABLE = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    message TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
)
"""

MIGRATE_ADD_COLUMNS = [
    "ALTER TABLE papers ADD COLUMN citation_count INTEGER DEFAULT 0",
    "ALTER TABLE papers ADD COLUMN venue TEXT DEFAULT ''",
    "ALTER TABLE hot_topics ADD COLUMN upvotes INTEGER DEFAULT 0",
]

CREATE_TAGS_TABLE = """
CREATE TABLE IF NOT EXISTS paper_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arxiv_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (arxiv_id) REFERENCES papers(arxiv_id),
    UNIQUE(arxiv_id, tag)
)
"""

CREATE_HOT_TOPICS_TABLE = """
CREATE TABLE IF NOT EXISTS hot_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    title TEXT NOT NULL,
    tech_name TEXT NOT NULL,
    summary TEXT,
    key_results TEXT,
    github_url TEXT DEFAULT '',
    paper_url TEXT DEFAULT '',
    hf_url TEXT DEFAULT '',
    source TEXT DEFAULT '',
    upvotes INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(date, tech_name)
)
"""

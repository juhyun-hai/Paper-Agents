#!/usr/bin/env python3
"""운영 DB → demo seed.sql 생성."""
from __future__ import annotations
import argparse
import asyncio
import json
import os

import asyncpg

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'


def esc(v) -> str:
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return 'TRUE' if v else 'FALSE'
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (list, dict)):
        return "'" + json.dumps(v).replace("'", "''") + "'::jsonb"
    s = str(v).replace("'", "''")
    return f"'{s}'"


SCHEMA = """-- HotPaper demo seed (auto-generated)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS papers (
  id SERIAL PRIMARY KEY,
  arxiv_id VARCHAR(64) UNIQUE NOT NULL,
  title TEXT, abstract TEXT, authors JSONB, categories JSONB,
  venue VARCHAR(128), year INT,
  pdf_url TEXT, html_url TEXT, published_date DATE,
  citation_count INT DEFAULT 0,
  is_hai BOOLEAN DEFAULT FALSE, hai_score FLOAT DEFAULT 0, hai_topic TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS paper_summaries (
  id SERIAL PRIMARY KEY,
  arxiv_id VARCHAR(64) UNIQUE,
  summary_text TEXT, summary_type VARCHAR(32),
  generation_model VARCHAR(128), word_count INT,
  figures JSONB, figure_count INT,
  generated_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS trending_papers (
  id SERIAL PRIMARY KEY,
  arxiv_id VARCHAR(64), title TEXT, sources JSONB,
  trending_score FLOAT, final_score FLOAT, rank INT,
  multi_source_bonus FLOAT, date DATE,
  featured_score FLOAT, is_featured BOOLEAN DEFAULT FALSE, upvotes INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (arxiv_id, date)
);
CREATE TABLE IF NOT EXISTS concepts (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL, type VARCHAR(20), paper_count INT DEFAULT 0
);
CREATE TABLE IF NOT EXISTS paper_concepts (
  id SERIAL PRIMARY KEY,
  paper_id INT REFERENCES papers(id) ON DELETE CASCADE,
  concept_id INT REFERENCES concepts(id) ON DELETE CASCADE,
  weight FLOAT DEFAULT 1.0, confidence FLOAT DEFAULT 1.0,
  extraction_method VARCHAR(50),
  UNIQUE (paper_id, concept_id)
);
"""


async def main():
    p = argparse.ArgumentParser()
    p.add_argument('--days', type=int, default=7)
    p.add_argument('--out', default='demo/seed.sql')
    args = p.parse_args()

    conn = await asyncpg.connect(DB_URL)
    parts = [SCHEMA]

    rows = await conn.fetch(f"""
        SELECT DISTINCT p.* FROM papers p
        JOIN trending_papers tp ON tp.arxiv_id = p.arxiv_id
        WHERE tp.date >= CURRENT_DATE - {args.days} AND tp.is_featured
        ORDER BY p.id DESC LIMIT 60
    """)
    print(f"papers: {len(rows)}")
    keep_arxiv = {r['arxiv_id'] for r in rows}
    for r in rows:
        d = dict(r)
        # abstract cap 1500자
        if d.get('abstract'): d['abstract'] = d['abstract'][:1500]
        cols = ['arxiv_id','title','abstract','authors','categories','venue','year',
                'pdf_url','html_url','published_date','citation_count',
                'is_hai','hai_score','hai_topic']
        vals = [esc(d.get(c)) for c in cols]
        parts.append(f"INSERT INTO papers ({','.join(cols)}) VALUES ({','.join(vals)}) ON CONFLICT (arxiv_id) DO NOTHING;")

    rows = await conn.fetch(f"""
        SELECT s.* FROM paper_summaries s
        WHERE s.arxiv_id = ANY($1::text[])
    """, list(keep_arxiv))
    print(f"summaries: {len(rows)}")
    for r in rows:
        d = dict(r)
        # figures의 base64 image data가 가장 큰 부피 — 5장에서 1장으로 cap, base64 truncate
        figs = d.get('figures')
        if figs and isinstance(figs, list):
            figs = figs[:1]
            for f in figs:
                if isinstance(f, dict) and f.get('image_base64'):
                    f['image_base64'] = ''  # demo에서 그림 표시 X (용량 압축)
            d['figures'] = figs
            d['figure_count'] = len(figs)
        cols = ['arxiv_id','summary_text','summary_type','generation_model',
                'word_count','figures','figure_count']
        vals = [esc(d.get(c)) for c in cols]
        parts.append(f"INSERT INTO paper_summaries ({','.join(cols)}) VALUES ({','.join(vals)}) ON CONFLICT (arxiv_id) DO NOTHING;")

    rows = await conn.fetch(f"""
        SELECT * FROM trending_papers
        WHERE date >= CURRENT_DATE - 2
          AND arxiv_id = ANY($1::text[])
        ORDER BY date DESC, rank ASC
    """, list(keep_arxiv))
    print(f"trending: {len(rows)}")
    for r in rows:
        d = dict(r)
        cols = ['arxiv_id','title','sources','trending_score','final_score','rank',
                'multi_source_bonus','date','featured_score','is_featured','upvotes']
        vals = [esc(d.get(c)) for c in cols]
        parts.append(f"INSERT INTO trending_papers ({','.join(cols)}) VALUES ({','.join(vals)}) ON CONFLICT (arxiv_id, date) DO NOTHING;")

    rows = await conn.fetch("""
        SELECT * FROM concepts WHERE type='keyword' AND paper_count > 0
        ORDER BY paper_count DESC LIMIT 100
    """)
    print(f"concepts: {len(rows)}")
    for r in rows:
        d = dict(r)
        parts.append(f"INSERT INTO concepts (id, name, type, paper_count) VALUES ({d['id']}, {esc(d['name'])}, 'keyword', {d['paper_count']}) ON CONFLICT (name) DO NOTHING;")

    rows = await conn.fetch("""
        SELECT pc.* FROM paper_concepts pc
        JOIN papers p ON p.id = pc.paper_id
        JOIN trending_papers tp ON tp.arxiv_id = p.arxiv_id
        WHERE tp.date >= CURRENT_DATE - 7 AND tp.is_featured
    """)
    print(f"paper_concepts: {len(rows)}")
    for r in rows:
        d = dict(r)
        parts.append(f"INSERT INTO paper_concepts (paper_id, concept_id, weight, confidence, extraction_method) "
                     f"VALUES ({d['paper_id']}, {d['concept_id']}, {d['weight']}, {d['confidence']}, {esc(d['extraction_method'])}) ON CONFLICT (paper_id, concept_id) DO NOTHING;")

    text = '\n'.join(parts) + '\n'
    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(text)
    print(f"\n✅ Seed: {out_path} ({len(text)//1024} KB)")
    await conn.close()


if __name__ == '__main__':
    asyncio.run(main())

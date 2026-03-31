#!/usr/bin/env python3
"""
Merge papers from both databases and ensure no duplicates
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import json
from src.database.db_manager import PaperDBManager
from src.utils.config import load_config

def merge_databases():
    """Merge papers.db into paper_db.sqlite"""
    print("🔀 데이터베이스 병합 시작...")

    # 두 데이터베이스 연결
    old_db = sqlite3.connect('data/paper_db.sqlite')
    new_db = sqlite3.connect('data/papers.db')

    old_db.row_factory = sqlite3.Row
    new_db.row_factory = sqlite3.Row

    # 기존 논문 ID들 수집
    existing_ids = set()
    for row in old_db.execute("SELECT arxiv_id FROM papers"):
        existing_ids.add(row['arxiv_id'])

    print(f"📊 기존 데이터베이스: {len(existing_ids)}개 논문")

    # 새 데이터베이스에서 중요 논문들 가져오기
    new_papers = []
    for row in new_db.execute("SELECT * FROM papers"):
        if row['arxiv_id'] not in existing_ids:
            new_papers.append(dict(row))

    print(f"📊 새로 추가할 논문: {len(new_papers)}개")

    # 중요 논문들을 기존 DB에 추가
    added_count = 0
    for paper in new_papers:
        try:
            old_db.execute("""
                INSERT INTO papers
                (arxiv_id, title, authors, abstract, categories, date, pdf_url,
                 citation_count, venue, importance_score, research_area, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper['arxiv_id'], paper['title'], paper['authors'],
                paper['abstract'], paper['categories'], paper['date'],
                paper['pdf_url'], paper.get('citation_count', 0),
                paper.get('venue', ''), paper.get('importance_score', 0),
                paper.get('research_area', ''), paper.get('status', 'unread')
            ))
            added_count += 1
            print(f"  ✅ {paper['title'][:50]}...")
        except Exception as e:
            print(f"  ❌ 실패: {paper['arxiv_id']} - {e}")

    # 학습 로드맵 테이블들도 복사
    print("\n🗺️ 학습 로드맵 복사 중...")

    # 테이블 생성 (존재하지 않을 경우)
    old_db.execute("""
        CREATE TABLE IF NOT EXISTS learning_roadmaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_name TEXT NOT NULL,
            track_title TEXT NOT NULL,
            description TEXT,
            difficulty TEXT DEFAULT 'beginner',
            estimated_time TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(track_name)
        )
    """)

    old_db.execute("""
        CREATE TABLE IF NOT EXISTS roadmap_papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_name TEXT NOT NULL,
            arxiv_id TEXT NOT NULL,
            step_order INTEGER NOT NULL,
            why_important TEXT,
            estimated_read_time TEXT DEFAULT '30 min',
            prerequisites TEXT DEFAULT '',
            UNIQUE(track_name, step_order)
        )
    """)

    old_db.execute("""
        CREATE TABLE IF NOT EXISTS paper_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_arxiv_id TEXT NOT NULL,
            to_arxiv_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            strength REAL DEFAULT 1.0,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(from_arxiv_id, to_arxiv_id, relationship_type)
        )
    """)

    # 로드맵 데이터 복사
    roadmap_count = 0
    for table in ['learning_roadmaps', 'roadmap_papers', 'paper_relationships']:
        try:
            for row in new_db.execute(f"SELECT * FROM {table}"):
                columns = list(row.keys())
                placeholders = ','.join(['?' for _ in columns])
                columns_str = ','.join(columns)

                old_db.execute(f"""
                    INSERT OR REPLACE INTO {table} ({columns_str})
                    VALUES ({placeholders})
                """, [row[col] for col in columns])
                roadmap_count += 1
        except Exception as e:
            print(f"  ❌ {table} 복사 실패: {e}")

    old_db.commit()
    old_db.close()
    new_db.close()

    print(f"\n🎉 병합 완료!")
    print(f"📊 새로 추가된 논문: {added_count}개")
    print(f"🗺️ 로드맵 데이터: {roadmap_count}개 항목")

    # 최종 확인
    final_db = sqlite3.connect('data/paper_db.sqlite')
    total_papers = final_db.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    total_roadmaps = final_db.execute("SELECT COUNT(*) FROM learning_roadmaps").fetchone()[0]
    final_db.close()

    print(f"📚 최종 논문 수: {total_papers}개")
    print(f"🗺️ 최종 로드맵 수: {total_roadmaps}개")

if __name__ == "__main__":
    merge_databases()
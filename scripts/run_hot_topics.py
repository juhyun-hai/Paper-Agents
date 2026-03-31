#!/usr/bin/env python3
"""
Run hot topics collector and save to database
"""

import sys
import os
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collector.hot_topics_collector import HotTopicsCollector
from src.utils.config import load_config

def save_hot_topics_to_db(hot_topics, db_path):
    """Save hot topics to database"""
    conn = sqlite3.connect(db_path)
    today = datetime.now().strftime("%Y-%m-%d")

    added_count = 0
    for topic in hot_topics:
        try:
            conn.execute("""
                INSERT OR REPLACE INTO hot_topics
                (date, title, tech_name, summary, key_results, github_url, paper_url, hf_url, source, upvotes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                today,
                topic.get('title', ''),
                topic.get('tech_name', ''),
                topic.get('summary', ''),
                topic.get('key_results', ''),
                topic.get('github_url', ''),
                topic.get('paper_url', ''),
                topic.get('hf_url', ''),
                topic.get('source', ''),
                topic.get('upvotes', 0)
            ))
            added_count += 1
        except Exception as e:
            print(f"❌ 저장 실패: {topic.get('title', 'Unknown')} - {e}")

    conn.commit()
    conn.close()
    return added_count

def run_hot_topics_collection():
    """Run the hot topics collection process"""
    print("🔥 Hot Topics 수집 시작...")

    config = load_config()
    db_path = config["database"]["path"]

    # Initialize collector
    collector = HotTopicsCollector(db_path)

    # Fetch hot topics from all sources
    try:
        hot_topics = collector.fetch_all()
        print(f"📊 수집된 Hot Topics: {len(hot_topics)}개")

        if hot_topics:
            # Process each topic to add summary and key results
            processed_topics = []
            for topic in hot_topics:
                processed = collector.summarize_topic(topic)
                processed_topics.append(processed)
                print(f"  ✅ {processed.get('title', 'Unknown')[:50]}...")

            # Save to database
            saved_count = save_hot_topics_to_db(processed_topics, db_path)

            print(f"\n🎉 Hot Topics 수집 완료!")
            print(f"📊 저장된 항목: {saved_count}개")

            # Show sample
            for i, topic in enumerate(processed_topics[:3]):
                print(f"\n{i+1}. {topic['title']}")
                print(f"   🏷️ {topic['tech_name']} | 📍 {topic['source']}")
                if topic.get('upvotes'):
                    print(f"   ⬆️ {topic['upvotes']} upvotes")

        else:
            print("⚠️ 수집된 Hot Topics가 없습니다.")

    except Exception as e:
        print(f"❌ Hot Topics 수집 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_hot_topics_collection()
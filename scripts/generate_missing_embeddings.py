#!/usr/bin/env python3
"""
Generate embeddings for papers missing them
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import PaperDBManager
from src.utils.config import load_config
import numpy as np
from sentence_transformers import SentenceTransformer

def generate_missing_embeddings():
    """Generate embeddings for papers that don't have them"""
    print("🧮 누락된 논문 embeddings 생성 시작...")

    config = load_config()
    db = PaperDBManager(config["database"]["path"])

    # Load embedding model
    print("📥 Embedding 모델 로딩...")
    model = SentenceTransformer(config["embedding"]["model"])

    # Get all papers
    all_papers = db.get_all_papers()
    embed_dir = config["embedding"]["save_path"]

    missing_count = 0
    generated_count = 0

    for paper in all_papers:
        arxiv_id = paper["arxiv_id"]
        safe_id = arxiv_id.replace("/", "_").replace(".", "_")
        embed_path = os.path.join(embed_dir, f"{safe_id}.npy")

        if not os.path.exists(embed_path):
            missing_count += 1

            # Generate embedding from title + abstract
            text = f"{paper['title']} {paper.get('abstract', '')}"

            try:
                embedding = model.encode(text)

                # Save embedding
                os.makedirs(embed_dir, exist_ok=True)
                np.save(embed_path, embedding)

                generated_count += 1
                if generated_count % 10 == 0:
                    print(f"  ✅ 진행상황: {generated_count}개 생성...")

            except Exception as e:
                print(f"  ❌ 실패: {arxiv_id} - {e}")

    print(f"\n🎉 Embeddings 생성 완료!")
    print(f"📊 누락: {missing_count}개, 생성: {generated_count}개")

if __name__ == "__main__":
    generate_missing_embeddings()
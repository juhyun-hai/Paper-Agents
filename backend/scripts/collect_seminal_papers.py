#!/usr/bin/env python3
"""
Collect seminal/foundational papers that are essential for any research platform.
"""

import asyncio
import sys
import os
from typing import List, Dict, Any
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from app.models import Paper
from sqlalchemy import select

try:
    import arxiv
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False
    print("❌ arxiv-py not installed. Run: pip install arxiv")

class SeminalPaperCollector:
    """Collect foundational papers that every research platform should have."""

    def __init__(self):
        if not ARXIV_AVAILABLE:
            raise ImportError("arxiv-py not available")

        self.client = arxiv.Client()

        # Foundational papers by category
        self.seminal_papers = {
            "transformers_and_attention": [
                "1706.03762",  # Attention Is All You Need
                "1810.04805",  # BERT
                "1801.10198",  # Universal Transformers
                "2005.14165",  # GPT-3
                "1909.11942",  # DistilBERT
                "1910.13461",  # ELECTRA
                "2010.11929",  # Vision Transformer
                "2103.00020",  # Swin Transformer
            ],

            "computer_vision": [
                "1512.03385",  # ResNet
                "1409.1556",   # VGG
                "1311.2901",   # ZFNet
                "1409.4842",   # GoogLeNet/Inception
                "1505.04597",  # U-Net
                "1506.02640",  # YOLO
                "1703.06870",  # Mask R-CNN
                "1406.2661",   # GAN
                "1511.06434",  # DCGAN
                "1710.10196",  # Progressive GAN
            ],

            "nlp_foundations": [
                "1301.3781",   # Word2Vec
                "1409.3215",   # Seq2Seq
                "1409.0473",   # Neural Machine Translation
                "1508.04025",  # FastText
                "1506.05869",  # LSTM for NMT
                "1705.03122",  # FaceNet
                "1607.01759",  # Layer Normalization
            ],

            "optimization_and_training": [
                "1412.6980",   # Adam
                "1502.03167",  # Batch Normalization
                "1506.02142",  # Dropout
                "1608.06993",  # DenseNet
                "1512.00567",  # Deep Residual Learning
                "1602.07261",  # Layer Normalization
            ],

            "reinforcement_learning": [
                "1312.5602",   # DQN
                "1509.02971",  # A3C
                "1707.06347",  # PPO
                "1802.01561",  # Rainbow
                "1706.02275",  # Parameter Space Noise
            ],

            "generative_models": [
                "1312.6114",   # VAE
                "1406.2661",   # GAN
                "1511.06434",  # DCGAN
                "1701.07875",  # Wasserstein GAN
                "1710.10196",  # Progressive GAN
                "1809.11096",  # StyleGAN
                "2006.11239",  # Denoising Diffusion
            ],

            "multimodal": [
                "1412.2306",   # Show and Tell
                "1502.03044",  # Show, Attend and Tell
                "1707.07998",  # Transformer for Image Captioning
                "2103.00020",  # ViT
                "2102.12092",  # CLIP
            ],

            "graph_networks": [
                "1609.02907",  # Graph Convolutional Networks
                "1710.10903",  # GraphSAGE
                "1710.09829",  # Graph Attention Networks
                "1905.02265",  # Graph Neural Networks
            ]
        }

    async def collect_seminal_papers(self):
        """Collect all seminal papers."""
        print("📚 Collecting Seminal Papers for Research Intelligence Platform")
        print("=" * 70)

        total_collected = 0
        total_existing = 0

        async with AsyncSessionLocal() as session:
            for category, arxiv_ids in self.seminal_papers.items():
                print(f"\n🎯 Category: {category.replace('_', ' ').title()}")
                print("-" * 50)

                category_collected = 0
                category_existing = 0

                for arxiv_id in arxiv_ids:
                    try:
                        # Check if paper already exists
                        result = await session.execute(
                            select(Paper).where(Paper.arxiv_id == arxiv_id)
                        )
                        existing_paper = result.scalar_one_or_none()

                        if existing_paper:
                            print(f"  ✓ {arxiv_id}: Already exists - {existing_paper.title[:60]}...")
                            category_existing += 1
                            continue

                        # Fetch from arXiv
                        try:
                            search = arxiv.Search(id_list=[arxiv_id])
                            paper = next(self.client.results(search))

                            # Create Paper object
                            new_paper = Paper(
                                arxiv_id=arxiv_id,
                                title=paper.title,
                                abstract=paper.summary,
                                authors=[str(author) for author in paper.authors],
                                categories=[cat for cat in paper.categories],
                                published_date=paper.published.date() if paper.published else None,
                                updated_date=paper.updated.date() if paper.updated else None,
                                pdf_url=paper.pdf_url,
                                html_url=paper.entry_id,
                                year=paper.published.year if paper.published else None
                            )

                            session.add(new_paper)
                            await session.commit()

                            print(f"  ✅ {arxiv_id}: Added - {paper.title[:60]}...")
                            category_collected += 1

                        except StopIteration:
                            print(f"  ❌ {arxiv_id}: Not found on arXiv")
                        except Exception as e:
                            print(f"  ❌ {arxiv_id}: Error - {str(e)[:50]}...")

                        # Rate limiting
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        print(f"  💥 {arxiv_id}: Database error - {e}")

                print(f"  📊 {category}: {category_collected} new, {category_existing} existing")
                total_collected += category_collected
                total_existing += category_existing

        print("\n" + "=" * 70)
        print(f"🎯 Collection Summary:")
        print(f"   📄 New papers collected: {total_collected}")
        print(f"   ✓ Papers already present: {total_existing}")
        print(f"   📚 Total seminal papers: {total_collected + total_existing}")

        # Generate embeddings for new papers
        if total_collected > 0:
            print(f"\n🧠 Generating embeddings for {total_collected} new papers...")
            try:
                from ..services.embedding_service import get_embedding_service
                embedding_service = get_embedding_service()

                async with AsyncSessionLocal() as session:
                    # Get papers without embeddings
                    result = await session.execute(
                        select(Paper).where(Paper.full_embedding.is_(None))
                    )
                    papers_to_embed = result.scalars().all()

                    for paper in papers_to_embed:
                        try:
                            await embedding_service.generate_and_store_embeddings(session, paper)
                            print(f"  🧠 Generated embedding for: {paper.title[:50]}...")
                            await asyncio.sleep(0.1)  # Avoid overwhelming the model
                        except Exception as e:
                            print(f"  ❌ Embedding failed for {paper.arxiv_id}: {e}")

                    await session.commit()
                    print("✅ Embedding generation completed!")

            except Exception as e:
                print(f"⚠️  Embedding generation skipped: {e}")

async def main():
    """Run seminal paper collection."""
    print("🏛️  Research Intelligence Platform - Seminal Papers Collection")
    print("Collecting foundational papers that define modern AI/ML research")
    print("=" * 80)

    try:
        collector = SeminalPaperCollector()
        await collector.collect_seminal_papers()

        print("\n🎉 Seminal paper collection completed!")
        print("\nYour research platform now includes:")
        print("• Transformer foundations (Attention, BERT, GPT)")
        print("• Computer vision classics (ResNet, VGG, YOLO, GAN)")
        print("• NLP fundamentals (Word2Vec, Seq2Seq)")
        print("• Training innovations (Adam, BatchNorm, Dropout)")
        print("• Modern architectures (Vision Transformer, CLIP)")

    except Exception as e:
        print(f"\n💥 Collection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
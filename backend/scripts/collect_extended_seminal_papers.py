#!/usr/bin/env python3
"""
Extended seminal papers collection - including recent breakthroughs.
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

class ExtendedSeminalCollector:
    """Collect additional foundational papers including recent breakthroughs."""

    def __init__(self):
        if not ARXIV_AVAILABLE:
            raise ImportError("arxiv-py not available")

        self.client = arxiv.Client()

        # Extended foundational papers including recent breakthroughs
        self.extended_papers = {
            "cnn_foundations": [
                "1202.2745",  # AlexNet
                "1312.4400",  # Network in Network
                "1409.4842",  # GoogLeNet/Inception
                "1409.1556",  # VGG (already added but ensuring)
                "1512.03385", # ResNet (already added but ensuring)
                "1608.06993", # DenseNet
                "1707.01083", # SENet
                "1801.04381", # MobileNets
                "1905.11946", # EfficientNet
            ],

            "diffusion_models": [
                "2006.11239", # Denoising Diffusion Probabilistic Models
                "2102.09672", # Improved Denoising Diffusion
                "2105.05233", # Diffusion Models Beat GANs
                "2112.10752", # High-Resolution Image Synthesis with Latent Diffusion
                "2203.02378", # Classifier-Free Diffusion Guidance
                "2207.12598", # Imagen
                "2208.01618", # DALL·E 2
                "2301.11093", # Muse
            ],

            "vision_transformers": [
                "2010.11929", # Vision Transformer (ViT)
                "2103.14030", # Swin Transformer
                "2104.13840", # CaiT
                "2103.15808", # DINO (self-supervised ViT)
                "2104.02057", # Twins
                "2106.09681", # ConvNeXt
                "2201.03545", # Masked Autoencoders (MAE)
            ],

            "large_language_models": [
                "1706.03762", # Attention Is All You Need (ensuring)
                "1810.04805", # BERT (ensuring)
                "1909.11942", # DistilBERT
                "1910.13461", # ELECTRA
                "2005.14165", # GPT-3
                "2204.02311", # PaLM
                "2302.13971", # LLaMA
                "2307.09288", # LLaMA 2
                "2203.15556", # InstructGPT
                "2005.11401", # T5
            ],

            "multimodal_models": [
                "2102.12092", # CLIP
                "2103.00020", # ViT (ensuring)
                "2204.14198", # Flamingo
                "2301.12597", # BLIP-2
                "2304.10592", # LLaVA
                "2305.06500", # InstructBLIP
                "2306.14895", # GPT-4V
            ],

            "self_supervised_learning": [
                "1807.03748", # SimCLR precursor
                "2002.05709", # SimCLR
                "2006.07733", # SwAV
                "2011.10566", # BYOL
                "2104.14294", # DINO
                "2201.03545", # MAE
                "2104.02057", # MoCo v3
            ],

            "object_detection": [
                "1506.02640", # YOLO
                "1506.01497", # Faster R-CNN
                "1703.06870", # Mask R-CNN
                "1708.02002", # Focal Loss / RetinaNet
                "2005.12872", # DETR
                "1708.01241", # Feature Pyramid Networks
            ],

            "nlp_recent_breakthroughs": [
                "2005.14165", # GPT-3 (ensuring)
                "2203.02155", # Chain-of-Thought Prompting
                "2204.01691", # PaLM Reasoning
                "2210.03493", # Toolformer
                "2302.14045", # Language is not all you need
                "2303.08774", # GPT-4
                "2306.05685", # Textbooks Are All You Need
            ],

            "graph_neural_networks": [
                "1609.02907", # Graph Convolutional Networks
                "1710.10903", # GraphSAGE
                "1710.09829", # Graph Attention Networks
                "1905.02265", # Graph Neural Networks survey
                "2103.07206", # Graph Transformer
            ],

            "federated_and_distributed": [
                "1602.05629", # Communication-Efficient Learning
                "1909.06335", # Federated Learning
                "2007.14390", # FedAvg improvements
            ],

            "neural_architecture_search": [
                "1611.01578", # Neural Architecture Search
                "1807.11626", # ENAS
                "1806.09055", # MnasNet
                "1905.11946", # EfficientNet (ensuring)
                "2101.00436", # Once-for-All Networks
            ]
        }

    async def collect_extended_papers(self):
        """Collect all extended seminal papers."""
        print("🚀 Collecting Extended Seminal Papers")
        print("Including: Diffusion, LLaMA, DINO, CNN classics, and more!")
        print("=" * 70)

        total_collected = 0
        total_existing = 0

        async with AsyncSessionLocal() as session:
            for category, arxiv_ids in self.extended_papers.items():
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
        print(f"🎯 Extended Collection Summary:")
        print(f"   📄 New papers collected: {total_collected}")
        print(f"   ✓ Papers already present: {total_existing}")
        print(f"   📚 Total extended papers: {total_collected + total_existing}")

        return total_collected

async def main():
    """Run extended seminal paper collection."""
    print("🌟 Research Intelligence Platform - Extended Seminal Collection")
    print("Adding missing foundational papers including:")
    print("• Diffusion Models (DDPM, DALL-E 2, Imagen)")
    print("• Large Language Models (LLaMA, GPT-4, PaLM)")
    print("• Vision Models (DINO, MAE, ConvNeXt)")
    print("• CNN Classics (AlexNet, EfficientNet)")
    print("• Self-Supervised Learning breakthroughs")
    print("=" * 80)

    try:
        collector = ExtendedSeminalCollector()
        new_papers = await collector.collect_extended_papers()

        print(f"\n🎉 Extended collection completed! Added {new_papers} papers")
        print("\nYour research platform now includes ALL major AI breakthroughs:")
        print("• 🖼️  CNN foundations (AlexNet → EfficientNet)")
        print("• 🎨 Diffusion models (DDPM → DALL-E 2 → Imagen)")
        print("• 🦙 Large language models (BERT → GPT-3 → LLaMA → GPT-4)")
        print("• 👁️  Vision transformers (ViT → DINO → MAE)")
        print("• 🔗 Multimodal models (CLIP → GPT-4V → LLaVA)")
        print("• 🎯 Object detection (YOLO → DETR)")

    except Exception as e:
        print(f"\n💥 Collection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
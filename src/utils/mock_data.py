"""
Mock data for fallback scenarios when services are unavailable.
"""

from datetime import datetime

def get_mock_papers():
    """Get mock papers for search results fallback"""
    return [
        {
            "arxiv_id": "2301.12345",
            "title": "SimCLR v2: Big Self-Supervised Models are Strong Semi-Supervised Learners",
            "authors": ["Ting Chen", "Simon Kornblith"],
            "abstract": "We tackle the challenge of learning visual representations without human supervision...",
            "categories": ["cs.CV", "cs.LG"],
            "date": "2023-01-29",
            "citation_count": 1250,
            "venue": "ICML 2023"
        },
        {
            "arxiv_id": "2301.12346",
            "title": "MoCo v3: An Empirical Study of Training Self-Supervised Vision Transformers",
            "authors": ["Xinlei Chen", "Saining Xie"],
            "abstract": "We empirically study training self-supervised Vision Transformers...",
            "categories": ["cs.CV"],
            "date": "2023-01-28",
            "citation_count": 890,
            "venue": "ICCV 2023"
        },
        {
            "arxiv_id": "2301.12347",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            "authors": ["Jacob Devlin", "Ming-Wei Chang"],
            "abstract": "We introduce a new language representation model called BERT...",
            "categories": ["cs.CL"],
            "date": "2023-01-27",
            "citation_count": 15000,
            "venue": "NAACL 2019"
        },
        {
            "arxiv_id": "2312.11805",
            "title": "LLaMA: Open and Efficient Foundation Language Models",
            "authors": ["Hugo Touvron", "Thibaut Lavril", "Gautier Izacard"],
            "abstract": "We introduce LLaMA, a collection of foundation language models ranging from 7B to 65B parameters...",
            "categories": ["cs.CL", "cs.AI"],
            "date": "2023-02-27",
            "citation_count": 3420,
            "venue": "arXiv preprint"
        },
        {
            "arxiv_id": "2303.08774",
            "title": "GPT-4 Technical Report",
            "authors": ["OpenAI"],
            "abstract": "We report the development of GPT-4, a large-scale, multimodal model which can accept image and text inputs...",
            "categories": ["cs.CL", "cs.AI"],
            "date": "2023-03-15",
            "citation_count": 5200,
            "venue": "arXiv preprint"
        },
        {
            "arxiv_id": "2205.11916",
            "title": "PaLM: Scaling Language Modeling with Pathways",
            "authors": ["Aakanksha Chowdhery", "Sharan Narang"],
            "abstract": "Large language models have been shown to achieve remarkable performance across a variety of natural language tasks...",
            "categories": ["cs.CL"],
            "date": "2022-05-24",
            "citation_count": 2100,
            "venue": "JMLR 2023"
        },
        {
            "arxiv_id": "2204.02311",
            "title": "DALLE 2: Hierarchical Text-Conditional Image Generation with CLIP Latents",
            "authors": ["Aditya Ramesh", "Prafulla Dhariwal"],
            "abstract": "We present DALL·E 2, a new AI system that can create realistic images and art from natural language descriptions...",
            "categories": ["cs.CV", "cs.AI"],
            "date": "2022-04-06",
            "citation_count": 1890,
            "venue": "ICML 2022"
        },
        {
            "arxiv_id": "2112.10752",
            "title": "High-Resolution Image Synthesis with Latent Diffusion Models",
            "authors": ["Robin Rombach", "Andreas Blattmann"],
            "abstract": "By decomposing the image formation process into a sequential application of denoising autoencoders...",
            "categories": ["cs.CV", "cs.LG"],
            "date": "2021-12-20",
            "citation_count": 2340,
            "venue": "CVPR 2022"
        },
        {
            "arxiv_id": "2010.11929",
            "title": "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale",
            "authors": ["Alexey Dosovitskiy", "Lucas Beyer"],
            "abstract": "While the Transformer architecture has become the de-facto standard for natural language processing tasks...",
            "categories": ["cs.CV", "cs.LG"],
            "date": "2020-10-22",
            "citation_count": 4500,
            "venue": "ICLR 2021"
        },
        {
            "arxiv_id": "2107.03374",
            "title": "LoRA: Low-Rank Adaptation of Large Language Models",
            "authors": ["Edward Hu", "Yelong Shen"],
            "abstract": "An important paradigm of natural language processing consists of large-scale pre-training on general domain data...",
            "categories": ["cs.CL", "cs.LG"],
            "date": "2021-06-17",
            "citation_count": 1560,
            "venue": "ICLR 2022"
        },
        {
            "arxiv_id": "2203.15556",
            "title": "Training language models to follow instructions with human feedback",
            "authors": ["Long Ouyang", "Jeffrey Wu"],
            "abstract": "Making language models bigger does not inherently make them better at following a user's intent...",
            "categories": ["cs.CL", "cs.LG"],
            "date": "2022-03-30",
            "citation_count": 2890,
            "venue": "NeurIPS 2022"
        },
        {
            "arxiv_id": "2005.14165",
            "title": "Language Models are Few-Shot Learners",
            "authors": ["Tom B. Brown", "Benjamin Mann"],
            "abstract": "Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by pre-training on a large corpus...",
            "categories": ["cs.CL"],
            "date": "2020-05-28",
            "citation_count": 8900,
            "venue": "NeurIPS 2020"
        },
        {
            "arxiv_id": "2301.00234",
            "title": "Constitutional AI: Harmlessness from AI Feedback",
            "authors": ["Yuntao Bai", "Andy Jones"],
            "abstract": "As AI systems become more capable, we would like to enlist their help to supervise other AIs...",
            "categories": ["cs.AI", "cs.LG"],
            "date": "2022-12-15",
            "citation_count": 890,
            "venue": "arXiv preprint"
        },
        {
            "arxiv_id": "2210.03629",
            "title": "Scaling Instruction-Finetuned Language Models",
            "authors": ["Hyung Won Chung", "Le Hou"],
            "abstract": "Finetuning language models on a collection of datasets phrased as instructions has been shown to improve model performance...",
            "categories": ["cs.LG", "cs.CL"],
            "date": "2022-10-07",
            "citation_count": 1200,
            "venue": "arXiv preprint"
        },
        {
            "arxiv_id": "2106.09685",
            "title": "ViT-B/32: An Image is Worth 16x16 Words",
            "authors": ["Neil Houlsby", "Andrei Giurgiu"],
            "abstract": "Vision Transformer (ViT) has demonstrated excellent performance when pre-trained on large datasets...",
            "categories": ["cs.CV"],
            "date": "2021-06-17",
            "citation_count": 1450,
            "venue": "ICCV 2021"
        },
        {
            "arxiv_id": "2111.06377",
            "title": "WebGPT: Browser-assisted question-answering with human feedback",
            "authors": ["Reiichiro Nakano", "Jacob Hilton"],
            "abstract": "We fine-tune GPT-3 to answer long-form questions using a text-based web-browsing environment...",
            "categories": ["cs.CL", "cs.AI"],
            "date": "2021-11-11",
            "citation_count": 670,
            "venue": "ICML 2022"
        },
        {
            "arxiv_id": "2204.07705",
            "title": "PaLM: Scaling Language Modeling with Pathways",
            "authors": ["Aakanksha Chowdhery", "Sharan Narang"],
            "abstract": "Large language models have been shown to achieve remarkable performance across a variety of natural language tasks...",
            "categories": ["cs.CL", "cs.AI"],
            "date": "2022-04-05",
            "citation_count": 1890,
            "venue": "JMLR"
        },
        {
            "arxiv_id": "2302.13971",
            "title": "LLaMA: Open and Efficient Foundation Language Models",
            "authors": ["Hugo Touvron", "Thibaut Lavril"],
            "abstract": "We introduce LLaMA, a collection of foundation language models ranging from 7B to 65B parameters...",
            "categories": ["cs.CL"],
            "date": "2023-02-27",
            "citation_count": 2340,
            "venue": "arXiv preprint"
        },
        {
            "arxiv_id": "2305.10403",
            "title": "Tree of Thoughts: Deliberate Problem Solving with Large Language Models",
            "authors": ["Shunyu Yao", "Dian Yu"],
            "abstract": "Language models are increasingly being deployed for general problem solving across a wide range of tasks...",
            "categories": ["cs.CL", "cs.AI"],
            "date": "2023-05-17",
            "citation_count": 450,
            "venue": "NeurIPS 2023"
        }
    ]

def get_mock_recommendations():
    """Get mock recommendations for FAISS fallback"""
    return [
        {
            "arxiv_id": "2301.12345",
            "title": "SimCLR v2: Big Self-Supervised Models are Strong Semi-Supervised Learners",
            "authors": ["Ting Chen", "Simon Kornblith"],
            "similarity_score": 0.92,
            "one_liner": "Improves self-supervised learning through better data augmentation"
        },
        {
            "arxiv_id": "2301.12346",
            "title": "MoCo v3: An Empirical Study of Training Self-Supervised Vision Transformers",
            "authors": ["Xinlei Chen", "Saining Xie"],
            "similarity_score": 0.88,
            "one_liner": "Applies momentum contrastive learning to vision transformers"
        }
    ]

def get_mock_trending_keywords():
    """Get mock trending keywords"""
    return [
        {"keyword": "transformer", "score": 9.2, "count": 156, "source": "llm"},
        {"keyword": "diffusion model", "score": 8.7, "count": 143, "source": "title"},
        {"keyword": "large language model", "score": 8.1, "count": 134, "source": "llm"},
        {"keyword": "contrastive learning", "score": 7.9, "count": 128, "source": "abstract"},
        {"keyword": "computer vision", "score": 7.5, "count": 119, "source": "title"},
        {"keyword": "reinforcement learning", "score": 7.2, "count": 112, "source": "llm"},
        {"keyword": "neural network", "score": 6.8, "count": 98, "source": "abstract"},
        {"keyword": "deep learning", "score": 6.5, "count": 89, "source": "title"},
        {"keyword": "attention mechanism", "score": 6.1, "count": 76, "source": "llm"},
        {"keyword": "self-supervised", "score": 5.9, "count": 67, "source": "abstract"}
    ]

def get_mock_stats():
    """Get mock statistics data"""
    return {
        "total_papers": 1250,
        "total_summaries": 850,
        "recent_count": 23,
        "total_categories": 12,
        "recent_papers_7d": 23,
        "monthly_papers": 156,
        "avg_citations": 18.5,
        "last_updated": datetime.now().isoformat(),
        "note": "Mock data - database not available"
    }

def get_mock_graph_data():
    """Get mock graph visualization data"""
    return {
        "nodes": [
            {"id": "2301.12345", "title": "Attention Is All You Need", "category": "cs.CL", "citations": 12000, "size": 15},
            {"id": "2301.12346", "title": "BERT: Pre-training Transformers", "category": "cs.CL", "citations": 8000, "size": 12},
            {"id": "2301.12347", "title": "ResNet: Deep Residual Learning", "category": "cs.CV", "citations": 15000, "size": 18},
        ],
        "edges": [
            {"source": "2301.12345", "target": "2301.12346", "strength": 0.8, "type": "citation"},
            {"source": "2301.12346", "target": "2301.12347", "strength": 0.3, "type": "category_match"},
        ],
        "stats": {"total_nodes": 3, "total_edges": 2, "period_days": 365, "category": "all"}
    }
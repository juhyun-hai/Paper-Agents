import os
import re
from typing import Dict, Any, List

from src.utils.logger import get_logger
from src.utils.config import load_config

logger = get_logger(__name__)

CATEGORY_TAGS = {
    "cs.CL": ["llm", "nlp"],
    "cs.AI": ["ai", "foundation"],
    "cs.CV": ["cv"],
    "cs.LG": ["ml"],
    "stat.ML": ["ml", "timeseries"],
}

KEYWORD_TAGS = {
    "reinforcement learning": ["rl"],
    "diffusion": ["generative"],
    "gan": ["generative"],
    "vae": ["generative"],
    "time series": ["timeseries"],
    "forecasting": ["timeseries"],
    "anomaly detection": ["timeseries"],
    "foundation model": ["foundation"],
    "multimodal": ["foundation"],
}


class NoteGenerator:
    def __init__(self, config: dict = None):
        self.config = config or load_config()
        self.vault_path = self.config["obsidian"]["vault_path"]
        self.papers_path = self.config["obsidian"]["papers_path"]
        os.makedirs(self.papers_path, exist_ok=True)

    def _auto_tags(self, paper: Dict[str, Any]) -> List[str]:
        tags = set()
        for cat in paper.get("categories", []):
            for t in CATEGORY_TAGS.get(cat, []):
                tags.add(t)
        text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
        for kw, kw_tags in KEYWORD_TAGS.items():
            if kw in text:
                for t in kw_tags:
                    tags.add(t)
        return sorted(tags) if tags else ["ai"]

    def _korean_summary(self, paper: Dict[str, Any]) -> str:
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        cats = paper.get("categories", [])
        cat_str = ", ".join(cats[:3])
        summary = (
            f"이 논문은 {cat_str} 분야의 연구로, {title}에 관한 내용을 다룹니다. "
            f"연구팀은 새로운 방법론을 제안하여 기존 접근 방식의 한계를 극복하고자 했습니다. "
        )
        if len(abstract) > 100:
            first_sentence = abstract.split(".")[0] if "." in abstract else abstract[:150]
            summary += f"핵심 내용은 다음과 같습니다: {first_sentence[:200]}."
        return summary

    def generate_note(self, paper: Dict[str, Any]) -> str:
        tags = self._auto_tags(paper)
        authors = paper.get("authors", [])
        authors_yaml = "[" + ", ".join(f'"{a}"' for a in authors[:5]) + "]"
        cats = paper.get("categories", [])
        cats_yaml = "[" + ", ".join(f'"{c}"' for c in cats) + "]"
        tags_yaml = "[" + ", ".join(f'"{t}"' for t in tags) + "]"
        tags_hash = " ".join(f"#{t}" for t in tags)
        arxiv_id = paper.get("arxiv_id", "")
        title = paper.get("title", "")
        date = paper.get("date", "")
        abstract = paper.get("abstract", "")
        pdf_url = paper.get("pdf_url", f"https://arxiv.org/pdf/{arxiv_id}")
        korean_summary = self._korean_summary(paper)
        authors_display = ", ".join(authors[:3])
        if len(authors) > 3:
            authors_display += f" et al. (+{len(authors) - 3})"
        note = f"""---
title: "{title}"
arxiv_id: "{arxiv_id}"
authors: {authors_yaml}
date: {date}
categories: {cats_yaml}
tags: {tags_yaml}
status: "unread"
rating: null
---

# {title}

## 📋 Metadata
- **Authors**: {authors_display}
- **Published**: {date}
- **arXiv**: [Link](https://arxiv.org/abs/{arxiv_id})
- **PDF**: [Download]({pdf_url})
- **Categories**: {", ".join(cats)}
- **Tags**: {tags_hash}

## 📝 Abstract (Original)
{abstract}

## 🇰🇷 한국어 요약
{korean_summary}
- **핵심 기여**: 새로운 접근법 또는 방법론 제안
- **방법론**: 실험 및 분석을 통한 검증
- **주요 결과**: 기존 방법 대비 성능 향상

## 🔗 Related Papers
(관련 논문 링크를 여기에 추가)

## 💡 My Notes
(수동 메모 공간)
"""
        return note

    def save_note(self, paper: Dict[str, Any]) -> str:
        arxiv_id = paper.get("arxiv_id", "unknown")
        safe_id = re.sub(r"[^\w\-.]", "_", arxiv_id)
        note_content = self.generate_note(paper)
        file_path = os.path.join(self.papers_path, f"{safe_id}.md")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(note_content)
            logger.info(f"Note saved: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save note for {arxiv_id}: {e}")
            return ""

    def save_notes_batch(self, papers: list) -> List[str]:
        saved_paths = []
        for paper in papers:
            path = self.save_note(paper)
            if path:
                saved_paths.append(path)
        return saved_paths

"""Hot Topics Collector: scrapes GitHub Trending, HuggingFace daily papers, Papers With Code."""
import re
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from src.utils.logger import get_logger

logger = get_logger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


class HotTopicsCollector:
    def __init__(self, db_path: str = "data/paper_db.sqlite"):
        self.db_path = db_path

    def _get_recent_tech_names(self, days: int = 7) -> set:
        """Return set of tech_names featured in last N days (to avoid repeats)."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            rows = conn.execute(
                "SELECT tech_name FROM hot_topics WHERE date >= ?", (cutoff,)
            ).fetchall()
            conn.close()
            return {r["tech_name"].lower() for r in rows}
        except Exception:
            return set()

    def fetch_huggingface_papers(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch HuggingFace daily papers via JSON API, sorted by upvotes.

        Uses the official HF papers API which returns paper.upvotes — the number
        of community upvotes, a reliable signal of actual community attention.
        """
        results = []
        try:
            url = "https://huggingface.co/api/daily_papers"
            if date:
                url += f"?date={date}"
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            items = r.json()

            # Sort by upvotes descending — this is the actual "주목받는" signal
            items.sort(key=lambda x: x.get("paper", {}).get("upvotes", 0), reverse=True)

            for item in items[:10]:
                paper = item.get("paper", {})
                title = paper.get("title", "")
                if not title or len(title) < 10:
                    continue

                arxiv_id = paper.get("id", "")
                upvotes = paper.get("upvotes", 0)
                description = paper.get("summary") or item.get("summary", "")
                paper_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""
                hf_url = f"https://huggingface.co/papers/{arxiv_id}" if arxiv_id else ""

                results.append({
                    "title": title,
                    "description": description[:500],
                    "paper_url": paper_url,
                    "github_url": "",
                    "hf_url": hf_url,
                    "source": "HuggingFace Papers",
                    "tech_name": self._extract_tech_name(title),
                    "upvotes": upvotes,
                })

            logger.info(f"HuggingFace papers (sorted by upvotes): {len(results)} found")
        except Exception as e:
            logger.warning(f"HuggingFace API error: {e}")
        return results

    def fetch_github_trending(self) -> List[Dict[str, Any]]:
        """Scrape GitHub trending AI/ML repositories."""
        results = []
        try:
            url = "https://github.com/trending?since=daily&spoken_language_code=en"
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            repos = soup.select("article.Box-row")
            # Specific AI/ML terms — multi-word phrases prevent false positives,
            # single words checked as whole words only (e.g. " ai " not "again")
            ai_phrases = {
                "transformer", "llm", "diffusion", "neural network", "deep learning",
                "machine learning", "gpt", "bert", "rag", "embedding", "multimodal",
                "fine-tun", "lora", "reinforcement learning", "pytorch", "tensorflow",
                "huggingface", "large language", "stable diffusion", "generative ai",
                "llama", "mistral", "openai", "anthropic", "langchain", "llamaindex",
                "agentic", "agent framework", "vector database", "language model",
                # Known AI/ML frameworks & tools
                "monai", "vllm", "ollama", "mlflow", "wandb", "triton-inference",
                "ai toolkit", "ai framework", "ml framework", "inference engine",
                "model serving", "model training", "computer vision", "nlp toolkit",
            }
            # Short abbreviations — only valid when surrounded by spaces (true standalone words)
            # Exclude " ai " — too generic (matches "all-in-one", "available in", etc.)
            ai_words = {" llm ", " nlp ", " rag ", " vllm ", " llms "}

            def _is_ai_repo(name: str, description: str) -> bool:
                combined = f" {(name + ' ' + description).lower()} "
                return (any(ph in combined for ph in ai_phrases) or
                        any(w in combined for w in ai_words))

            for repo in repos[:20]:
                name_el = repo.select_one("h2 a")
                desc_el = repo.select_one("p")
                stars_el = repo.select_one("[aria-label*='star'],.octicon-star + span")

                if not name_el:
                    continue

                name = name_el.get_text(strip=True).replace("\n", "").strip().replace(" ", "")
                description = desc_el.get_text(strip=True) if desc_el else ""

                if not _is_ai_repo(name, description):
                    continue

                href = name_el.get("href", "")
                github_url = f"https://github.com{href}" if href.startswith("/") else href

                results.append({
                    "title": name.split("/")[-1].replace("-", " ").replace("_", " ").title(),
                    "description": description,
                    "paper_url": "",
                    "github_url": github_url,
                    "hf_url": "",
                    "source": "GitHub Trending",
                    "tech_name": self._extract_tech_name(name.split("/")[-1]),
                })
            logger.info(f"GitHub trending AI repos: {len(results)} found")
        except Exception as e:
            logger.warning(f"GitHub trending scrape error: {e}")
        return results

    def fetch_hf_papers_yesterday(self) -> List[Dict[str, Any]]:
        """Fetch yesterday's HuggingFace papers sorted by upvotes.

        Papers With Code was acquired by HuggingFace. Yesterday's papers have had
        ~24h to accumulate upvotes, giving a more stable signal than today's.
        """
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        results = self.fetch_huggingface_papers(date=yesterday)
        for r in results:
            r["source"] = "HuggingFace Papers (Yesterday)"
        logger.info(f"HuggingFace yesterday papers: {len(results)} found")
        return results

    def _extract_tech_name(self, title: str) -> str:
        """Extract a clean tech name from title."""
        # If starts with an acronym/model name followed by colon, use that
        m = re.match(r"^([A-Za-z][A-Za-z0-9-]{1,20})[\s:]", title)
        if m:
            candidate = m.group(1)
            # If it looks like a model name (has uppercase, digits, or hyphen), use it
            if re.search(r"[A-Z]|\d|-", candidate):
                return candidate
        # If contains parenthetical acronym like "Attention Is All You Need (Transformer)"
        m = re.search(r"\(([A-Z][A-Za-z0-9-]+)\)", title)
        if m:
            return m.group(1)
        # Use first 3 words max
        words = re.sub(r"[^\w\s-]", "", title).split()[:3]
        return " ".join(words)

    def _get_arxiv_abstract(self, paper_url: str) -> str:
        """Fetch abstract from arXiv if URL is arXiv."""
        if "arxiv.org" not in paper_url:
            return ""
        try:
            arxiv_id = re.search(r"(\d{4}\.\d{4,5})", paper_url)
            if not arxiv_id:
                return ""
            aid = arxiv_id.group(1)
            r = requests.get(f"https://arxiv.org/abs/{aid}", headers=HEADERS, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            abstract_el = soup.select_one(".abstract")
            if abstract_el:
                return abstract_el.get_text(strip=True).replace("Abstract:", "").strip()
        except Exception:
            pass
        return ""

    def summarize_topic(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured summary from scraped data (no hallucination - uses actual text)."""
        title = item.get("title", "")
        description = item.get("description", "")
        paper_url = item.get("paper_url", "")

        # Try to get full abstract if paper_url is arXiv
        if paper_url and "arxiv.org" in paper_url and not description:
            description = self._get_arxiv_abstract(paper_url)
            time.sleep(0.5)

        if not description:
            description = f"{title} - see source for details."

        # Build summary from actual text (first 2-3 sentences)
        sentences = re.split(r"(?<=[.!?])\s+", description.strip())
        summary_sentences = [s for s in sentences if len(s) > 20][:3]
        summary = " ".join(summary_sentences) if summary_sentences else description[:300]

        # Extract key results: look for numbers/metrics in the text
        key_results_lines = []
        # Find sentences with metrics
        metric_pattern = re.compile(r"[^\n.!?]*(\d+\.?\d*\s*%|SOTA|state.of.the.art|\d+x\s+faster|benchmark)[^\n.!?]*[.!?]?", re.IGNORECASE)
        for m in metric_pattern.finditer(description):
            line = m.group().strip()
            if len(line) > 15 and len(key_results_lines) < 4:
                key_results_lines.append(f"• {line}")

        if not key_results_lines:
            # Fallback: use remaining sentences as bullet points
            for s in summary_sentences[1:3]:
                if len(s) > 20:
                    key_results_lines.append(f"• {s}")

        key_results = "\n".join(key_results_lines) if key_results_lines else f"• {description[:150]}"

        return {
            **item,
            "summary": summary[:600],
            "key_results": key_results[:800],
        }

    def fetch_all(self) -> List[Dict[str, Any]]:
        """Fetch from all sources, deduplicate, interleave, return top items.

        Sources are interleaved so each source gets fair representation:
        HF today (upvote), GitHub trending (stars), HF yesterday (upvote).
        """
        recent = self._get_recent_tech_names(days=7)

        def _dedupe(items: list) -> list:
            seen_local = set()
            out = []
            for item in items:
                tech = item.get("tech_name", "").lower()
                if not tech or tech in seen_local or tech in recent:
                    continue
                seen_local.add(tech)
                out.append(item)
            return out

        hf_today = _dedupe(self.fetch_huggingface_papers())
        time.sleep(1)
        github   = _dedupe(self.fetch_github_trending())
        time.sleep(1)
        hf_yest  = _dedupe(self.fetch_hf_papers_yesterday())

        # Allocate slots: HF-today 3, GitHub up to 2 (fallback to HF if 0), HF-yesterday rest
        hf_slots  = hf_today[:3]
        gh_slots  = github[:2]
        # If GitHub has no AI repos today, fill with HF yesterday instead
        fill_slots = gh_slots if gh_slots else hf_yest[:2]
        extra     = hf_yest[:2] if gh_slots else hf_yest[2:4]

        seen = set()
        interleaved = []
        for bucket in [hf_slots, fill_slots, extra]:
            for item in bucket:
                tech = item.get("tech_name", "").lower()
                if tech and tech not in seen:
                    seen.add(tech)
                    interleaved.append(item)

        logger.info(f"Hot topics: {len(hf_slots)} HF-today, {len(gh_slots)} GitHub, fill={len(fill_slots)} → {len(interleaved)} total")
        return interleaved[:5]

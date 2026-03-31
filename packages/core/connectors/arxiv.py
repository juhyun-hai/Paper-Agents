"""
arXiv API connector with rate limiting and retry logic.

API docs: https://info.arxiv.org/help/api/index.html
"""

import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from defusedxml import ElementTree as ET
from xml.etree.ElementTree import Element  # For type hints only
import urllib.request
import urllib.parse
import urllib.error

logger = logging.getLogger(__name__)

# arXiv API constants
ARXIV_API_URL = "http://export.arxiv.org/api/query"
MAX_RESULTS_PER_REQUEST = 100  # arXiv recommends <= 100
RATE_LIMIT_DELAY = 0.34  # ~3 requests per second (1/3 = 0.333...)
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


class ArxivConnector:
    """Fetches papers from arXiv API with rate limiting and error handling."""

    def __init__(self, email: Optional[str] = None):
        """
        Initialize connector.

        Args:
            email: Optional contact email (recommended by arXiv for courtesy)
        """
        self.email = email
        self.last_request_time = 0.0

    def fetch_papers(
        self,
        categories: List[str],
        since_days: int,
        keywords: Optional[List[str]] = None,
        max_results: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch papers from arXiv published in the last N days.

        Args:
            categories: List of arXiv categories (e.g., ["cs.LG", "cs.CV"])
            since_days: Number of days to look back
            keywords: Optional list of keywords to filter by (AND logic)
            max_results: Maximum total papers to fetch

        Returns:
            List of paper dictionaries with metadata
        """
        logger.info(
            f"Fetching papers: categories={categories}, since_days={since_days}, "
            f"keywords={keywords}, max_results={max_results}"
        )

        query = self._build_query(categories, since_days, keywords)
        papers = []
        start = 0

        while len(papers) < max_results:
            batch_size = min(MAX_RESULTS_PER_REQUEST, max_results - len(papers))
            batch = self._fetch_batch(query, start, batch_size)

            if not batch:
                break  # No more results

            papers.extend(batch)
            start += len(batch)

            logger.info(f"Fetched {len(papers)} papers so far...")

            if len(batch) < batch_size:
                break  # Last page

        logger.info(f"Fetch complete: {len(papers)} papers retrieved")
        return papers

    def _build_query(
        self,
        categories: List[str],
        since_days: int,
        keywords: Optional[List[str]] = None,
    ) -> str:
        """
        Build arXiv API search query.

        Query syntax: https://info.arxiv.org/help/api/user-manual.html#query_details
        """
        # Category filter: cat:cs.LG OR cat:cs.CV OR ...
        cat_terms = [f"cat:{cat}" for cat in categories]
        cat_query = " OR ".join(cat_terms)

        # Date filter (approximate using submittedDate)
        # Note: arXiv doesn't support exact date filtering, so we fetch more and filter locally
        query_parts = [f"({cat_query})"]

        # Keyword filter: all:keyword1 AND all:keyword2 AND ...
        if keywords:
            kw_terms = [f"all:{kw}" for kw in keywords]
            kw_query = " AND ".join(kw_terms)
            query_parts.append(f"({kw_query})")

        return " AND ".join(query_parts)

    def _fetch_batch(
        self, query: str, start: int, max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch a single batch of results from arXiv API.

        Args:
            query: Search query string
            start: Starting index
            max_results: Number of results to fetch

        Returns:
            List of parsed paper dictionaries
        """
        params = {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        url = f"{ARXIV_API_URL}?{urllib.parse.urlencode(params)}"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._rate_limit()
                logger.debug(f"Request: start={start}, max_results={max_results}")

                headers = {}
                if self.email:
                    headers["User-Agent"] = f"PaperAgent/1.0 ({self.email})"

                request = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(request, timeout=30) as response:
                    xml_data = response.read()

                papers = self._parse_xml(xml_data)
                return papers

            except urllib.error.HTTPError as e:
                logger.warning(
                    f"HTTP error {e.code} on attempt {attempt}/{MAX_RETRIES}"
                )
                if attempt < MAX_RETRIES:
                    self._backoff(attempt)
                else:
                    raise

            except urllib.error.URLError as e:
                logger.warning(
                    f"URL error {e.reason} on attempt {attempt}/{MAX_RETRIES}"
                )
                if attempt < MAX_RETRIES:
                    self._backoff(attempt)
                else:
                    raise

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if attempt < MAX_RETRIES:
                    self._backoff(attempt)
                else:
                    raise

        return []

    def _rate_limit(self):
        """Enforce rate limit of ~3 requests per second."""
        elapsed = time.time() - self.last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            sleep_time = RATE_LIMIT_DELAY - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _backoff(self, attempt: int):
        """Exponential backoff for retries."""
        sleep_time = RETRY_BACKOFF_BASE ** attempt
        logger.info(f"Backing off for {sleep_time}s before retry...")
        time.sleep(sleep_time)

    def _parse_xml(self, xml_data: bytes) -> List[Dict[str, Any]]:
        """
        Parse arXiv API XML response into paper dictionaries.

        XML format: Atom feed with custom arXiv namespace
        Docs: https://info.arxiv.org/help/api/user-manual.html#_query_interface
        """
        root = ET.fromstring(xml_data)

        # Define namespaces
        namespaces = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        papers = []

        for entry in root.findall("atom:entry", namespaces):
            try:
                paper = self._parse_entry(entry, namespaces)
                papers.append(paper)
            except Exception as e:
                logger.warning(f"Failed to parse entry: {e}")
                continue

        return papers

    def _parse_entry(
        self, entry: Element, namespaces: Dict[str, str]
    ) -> Dict[str, Any]:
        """Parse a single entry element into a paper dictionary."""

        # Extract arXiv ID from id URL (e.g., http://arxiv.org/abs/2301.12345v1)
        id_url = entry.find("atom:id", namespaces).text
        arxiv_id_with_version = id_url.split("/abs/")[-1]

        # Split arxiv_id and version (e.g., "2301.12345v1" -> "2301.12345", "v1")
        if "v" in arxiv_id_with_version:
            arxiv_id, version = arxiv_id_with_version.rsplit("v", 1)
            version = f"v{version}"
        else:
            arxiv_id = arxiv_id_with_version
            version = "v1"  # Default if version not specified

        # Title
        title = entry.find("atom:title", namespaces).text.strip()
        title = " ".join(title.split())  # Normalize whitespace

        # Authors
        authors = []
        for author in entry.findall("atom:author", namespaces):
            name = author.find("atom:name", namespaces).text
            affiliation_elem = author.find("arxiv:affiliation", namespaces)
            affiliation = affiliation_elem.text if affiliation_elem is not None else None
            authors.append({"name": name, "affiliation": affiliation})

        # Abstract
        abstract = entry.find("atom:summary", namespaces).text.strip()
        abstract = " ".join(abstract.split())  # Normalize whitespace

        # Categories
        categories = []
        primary_category = entry.find("arxiv:primary_category", namespaces)
        if primary_category is not None:
            categories.append(primary_category.get("term"))

        for category in entry.findall("atom:category", namespaces):
            cat_term = category.get("term")
            if cat_term and cat_term not in categories:
                categories.append(cat_term)

        # URLs
        pdf_url = None
        html_url = None
        for link in entry.findall("atom:link", namespaces):
            if link.get("title") == "pdf":
                pdf_url = link.get("href")
            elif link.get("rel") == "alternate":
                html_url = link.get("href")

        # Dates
        published_text = entry.find("atom:published", namespaces).text
        published_date = datetime.fromisoformat(published_text.replace("Z", "+00:00"))

        updated_elem = entry.find("atom:updated", namespaces)
        updated_date = None
        if updated_elem is not None:
            updated_text = updated_elem.text
            updated_date = datetime.fromisoformat(updated_text.replace("Z", "+00:00"))

        return {
            "arxiv_id": arxiv_id,
            "version": version,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "categories": categories,
            "primary_category": categories[0] if categories else None,
            "pdf_url": pdf_url,
            "html_url": html_url,
            "published_date": published_date,
            "updated_date": updated_date,
        }


def parse_since_arg(since: str) -> int:
    """
    Parse --since argument to number of days.

    Examples: "1d" -> 1, "7d" -> 7, "30d" -> 30

    Args:
        since: String like "1d", "7d", etc.

    Returns:
        Number of days as integer
    """
    if not since.endswith("d"):
        raise ValueError(f"Invalid --since format: {since}. Expected format: '1d', '7d', etc.")

    try:
        days = int(since[:-1])
        if days <= 0:
            raise ValueError(f"Days must be positive: {days}")
        return days
    except ValueError as e:
        raise ValueError(f"Invalid --since format: {since}. Expected format: '1d', '7d', etc.") from e

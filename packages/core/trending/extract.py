"""
Keyword extraction for trending analysis.

No external NLP libraries required.
"""

import re
from typing import Optional


# Standard English stopwords (function words + low-signal academic boilerplate)
STOPWORDS = frozenset({
    # Articles / determiners
    "a", "an", "the",
    # Conjunctions / prepositions
    "and", "or", "but", "nor", "so", "yet", "for",
    "in", "on", "at", "to", "by", "up", "as", "if", "of", "off", "out",
    "with", "from", "into", "onto", "about", "above", "after", "along",
    "among", "around", "before", "behind", "below", "beneath", "beside",
    "between", "beyond", "down", "during", "except", "inside", "near",
    "outside", "over", "past", "since", "through", "throughout", "under",
    "until", "upon", "within", "without", "toward", "towards", "against",
    "across",
    # Pronouns
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    # Auxiliary verbs
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having",
    "do", "does", "did", "doing",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "need", "dare", "ought",
    # Quantifiers / determiners / generic connectives
    "all", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "not", "only", "same", "than", "too", "very", "just", "also",
    "then", "however", "therefore", "thus", "hence", "where",
    "either", "neither", "whether", "while", "although", "because",
    # Academic paper boilerplate
    "paper", "work", "propose", "proposed", "presents", "present",
    "show", "shows", "shown", "demonstrate", "demonstrates", "demonstrated",
    "introduce", "introduces", "introduced", "study", "studies",
    "proposes", "achieve", "achieves", "existing",
    # Common low-signal words
    "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "first", "second", "third", "last", "one", "new", "novel",
    "high", "low", "real", "prior",
    "can", "using", "used", "use", "based", "via", "well", "often", "many",
    "much", "highly", "significantly",
    "approach", "approaches", "method", "task",
    # Generic verbs (too broad as unigrams in paper context)
    "remain", "provide", "improve",
    # Generic adjectives / nouns
    "standard", "aware", "dynamic", "critical", "human",
    "system", "accuracy", "baseline", "space",
    # Phrase-component artifacts (captured as phrases; useless as unigrams)
    "art", "test",
    # Generic ML/academic terms that are too broad as unigrams
    "model", "models", "method", "methods", "data", "result", "results",
    "performance", "language", "languages", "large", "time", "tasks",
    "neural", "learning", "training", "generation", "state",
    "framework", "benchmark", "dataset", "policy", "information",
    "efficiency", "distribution", "representation",
    "challenge",
    # URL / protocol tokens that appear after normalization strips punctuation
    "http", "https", "www",
    # Generic structural / design words
    "strong", "address", "offer", "experiment", "domain",
    "design", "structure", "text", "pattern",
    # Stemmed artifacts (e.g. "across" -> "acros" via naive plural stripping)
    "acros",
})

# Known multi-word phrases to extract (normalized: lowercase, spaces only).
# Checked as substrings in the normalized token stream before unigram extraction.
# Priority phrases are listed first; longer/more-specific phrases precede shorter ones
# to allow both to match independently (substring logic keeps all matches).
KNOWN_PHRASES = (
    # Priority phrases (detected before unigram tokenization)
    "flow matching",
    "foundation model",
    "chain of thought",
    "test time",
    "diffusion model",
    "vision language",
    "retrieval augmented",
    "state of the art",
    # Large language model family (longer first to catch the full phrase)
    "large language model",
    "language model",
    # Learning paradigms
    "in context learning",
    "few shot learning",
    "zero shot learning",
    "few shot",
    "zero shot",
    "fine tuning",
    "instruction tuning",
    "prompt tuning",
    "parameter efficient",
    "pre training",
    "self supervised",
    "contrastive learning",
    "transfer learning",
    "reinforcement learning",
    "machine learning",
    "deep learning",
    # Architecture / mechanisms
    "attention mechanism",
    "mixture of experts",
    "neural network",
    "knowledge distillation",
    # Generative models
    "generative model",
    # Multimodal / retrieval
    "multimodal learning",
)

# Map detected phrases to their canonical keyword form.
# Applied after phrase detection so multiple surface forms collapse to one entry.
_PHRASE_CANON: dict[str, str] = {
    "large language model": "llm",
    "large language models": "llm",
    "language model": "llm",
    "language models": "llm",
}

_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_SPACE_RE = re.compile(r"\s+")
_HAS_LETTER_RE = re.compile(r"[a-z]")

# Common inflectional suffixes that produce low-signal unigrams.
# Phrases (multi-word) bypass this filter and are never suffix-stripped.
_SUFFIX_FILTERS = ("ed", "ing", "ive", "able", "ful")

# Words ending in 's' that must NOT have the trailing 's' removed.
_PLURAL_EXCEPTIONS = frozenset({
    "analysis", "basis", "bias", "class", "corpus", "focus",
    "hypothesis", "loss", "process", "series", "status", "success",
    "synthesis", "thesis", "progress", "address",
})


def _stem_plural(token: str) -> str:
    """Remove trailing 's' if len > 4 and not a known exception.

    Words ending in '-ness' or '-less' are not plurals and are never stemmed.
    """
    if not token.endswith("s") or len(token) <= 4:
        return token
    if token in _PLURAL_EXCEPTIONS:
        return token
    if token.endswith(("ness", "less")):
        return token
    return token[:-1]


def _normalize_text(text: str) -> str:
    """Lowercase, replace hyphens with spaces, remove punctuation, collapse spaces."""
    text = text.lower()
    text = text.replace("-", " ")
    text = _PUNCT_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text


def _is_valid_token(token: str) -> bool:
    """Return True if token is a meaningful keyword candidate.

    Filters applied (all deterministic, no external NLP):
      1. Length < 4
      2. No alphabetic characters at all (e.g. pure digits)
      3. In STOPWORDS
      4. Ends with a low-signal inflectional suffix (ed/ing/ive/able/ful)
      5. Non-alpha ratio > 0.3 (more than 30% of chars are digits)
    """
    if len(token) < 4:
        return False
    if not _HAS_LETTER_RE.search(token):
        return False
    if token in STOPWORDS:
        return False
    if token.endswith(_SUFFIX_FILTERS):
        return False
    non_alpha = sum(1 for c in token if not c.isalpha())
    if non_alpha / len(token) > 0.3:
        return False
    return True


# Connector tokens that may sit in the middle of a meaningful trigram.
# These are typically stopwords but are allowed as glue in X-of-Y constructions.
_CONNECTORS = frozenset({"of", "for", "to", "in", "with"})


def _extract_ngrams(normalized: str) -> list[str]:
    """
    Dynamically extract bigrams and trigrams from a normalized token sequence.

    Bigrams:  both adjacent tokens must be valid (non-stopword, has letter, len>=3)
              after stemming.  Uses the stemmed forms so "transformers" and
              "transformer" produce the same bigram partner.

    Trigrams: valid_stem + connector + valid_stem.  The connector (of/for/to/in/with)
              is kept verbatim; outer positions use stemmed forms.

    Canonicalization (_PHRASE_CANON) is applied before returning so that any
    dynamically generated "language model" phrase maps to "llm".
    """
    raw = normalized.split()
    n = len(raw)

    # Pre-compute the valid stemmed form for each position.
    # None means the token should not participate in ngrams as an outer token.
    stems: list[str | None] = []
    for t in raw:
        if t in STOPWORDS:
            stems.append(None)
        else:
            s = _stem_plural(t)
            stems.append(s if _is_valid_token(s) else None)

    seen: set[str] = set()
    ngrams: list[str] = []

    def _add(phrase: str) -> None:
        canonical = _PHRASE_CANON.get(phrase, phrase)
        if canonical not in seen:
            seen.add(canonical)
            ngrams.append(canonical)

    # Bigrams: adjacent valid stems
    for i in range(n - 1):
        if stems[i] and stems[i + 1]:
            _add(f"{stems[i]} {stems[i + 1]}")

    # Trigrams: valid + connector + valid
    for i in range(n - 2):
        mid = raw[i + 1]
        if mid in _CONNECTORS and stems[i] and stems[i + 2]:
            _add(f"{stems[i]} {mid} {stems[i + 2]}")

    return ngrams


def _extract_from_text(text: str) -> list[str]:
    """
    Extract keyword candidates from a single text string.

    Detects known multi-word phrases first, then filters individual tokens.
    Deduplicates while preserving order (phrases before unigrams).
    """
    if not text or not text.strip():
        return []

    normalized = _normalize_text(text)

    # 1. Known phrases (fixed list) with canonicalization
    known = [_PHRASE_CANON.get(p, p) for p in KNOWN_PHRASES if p in normalized]

    # 2. Dynamic bigrams / trigrams from adjacent valid tokens
    dynamic = _extract_ngrams(normalized)

    # 3. Valid unigrams; check original token first (catches -es forms),
    #    then stem and re-check the canonical form.
    unigrams = []
    for token in normalized.split():
        if token in STOPWORDS:
            continue
        stemmed = _stem_plural(token)
        if _is_valid_token(stemmed):
            unigrams.append(stemmed)

    # Combine: known phrases → dynamic ngrams → unigrams; deduplicate in order
    seen: set[str] = set()
    result: list[str] = []
    for kw in known + dynamic + unigrams:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result


def _normalize_llm_keywords(keywords: list) -> list[str]:
    """
    Normalize LLM-generated keywords: lowercase, clean punctuation, deduplicate.

    Multi-word LLM keywords are kept as-is (they are already meaningful phrases).
    Single-word LLM keywords are subject to the same token validity filter.
    """
    seen: set[str] = set()
    result: list[str] = []
    for kw in keywords:
        if not isinstance(kw, str):
            continue
        normalized = _normalize_text(kw)
        if not normalized or len(normalized) < 3:
            continue
        words = normalized.split()
        # Single-word LLM keywords must pass the same token filter
        if len(words) == 1 and not _is_valid_token(words[0]):
            continue
        canonical = _PHRASE_CANON.get(normalized, normalized)
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result


def extract_keywords(
    title: str,
    abstract: str,
    llm_keywords: Optional[list] = None,
) -> dict[str, list[str]]:
    """
    Extract keywords from title, abstract, and optional LLM keyword list.

    Args:
        title:        Paper title string.
        abstract:     Paper abstract string.
        llm_keywords: Optional list of keyword strings from a deep summary.

    Returns:
        Dict with keys 'title', 'abstract', 'llm'. Each value is a deduplicated
        list of normalized keyword strings.
    """
    return {
        "title": _extract_from_text(title),
        "abstract": _extract_from_text(abstract),
        "llm": _normalize_llm_keywords(llm_keywords or []),
    }

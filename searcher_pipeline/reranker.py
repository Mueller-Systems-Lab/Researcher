"""Result Reranker — scores and reorders search results.

Initial implementation: lexical + domain diversity scoring.
Cross-Encoder optional for future enhancement (DR-04+).
"""

from __future__ import annotations

import re


def calculate_score(
    text: str,
    query: str,
    *,
    domain: str = "",
    existing_domains: set[str] | None = None,
    freshness_days: float = 30.0,
) -> float:
    """Calculate a relevance score for a text segment against a query.

    Components:
    - Lexical overlap (term frequency)
    - Title/query keyword overlap
    - Domain diversity bonus
    - Freshness penalty (older → lower)
    """
    score = 0.0

    # 1. Lexical overlap (max 0.5)
    query_terms = set(query.lower().split())
    text_terms = set(text.lower().split())
    if query_terms:
        overlap = len(query_terms & text_terms) / len(query_terms)
        score += overlap * 0.5

    # 2. Keyword density (max 0.3)
    query_keywords = _extract_keywords(query)
    text_lower = text.lower()
    keyword_hits = sum(1 for kw in query_keywords if kw in text_lower)
    if query_keywords:
        score += (keyword_hits / len(query_keywords)) * 0.3

    # 3. Domain diversity bonus (0.1)
    if existing_domains and domain and domain not in existing_domains:
        score += 0.1

    # 4. Length penalty for very short/long texts
    text_len = len(text)
    if text_len < 50:
        score *= 0.5
    elif text_len > 5000:
        score *= 0.8

    return min(score, 1.0)


def rerank(
    items: list[dict],
    query: str,
    *,
    max_results: int = 10,
) -> list[dict]:
    """Rerank search result items by relevance to query.

    Each item is a dict with at least 'text' and 'domain' keys.
    """
    seen_domains: set[str] = set()

    for item in items:
        text = item.get("text", "")
        domain = item.get("domain", "")
        base_score = item.get("score", 0.5)

        relevance = calculate_score(
            text=text,
            query=query,
            domain=domain,
            existing_domains=seen_domains,
        )

        # Combine base and relevance scores
        item["score"] = (base_score + relevance) / 2
        seen_domains.add(domain)

    # Sort by score descending
    items.sort(key=lambda x: x.get("score", 0), reverse=True)

    return items[:max_results]


def _extract_keywords(query: str) -> list[str]:
    """Extract meaningful keywords from a query."""
    # Remove stop words, short words
    stopwords = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "der",
        "die",
        "das",
        "ist",
        "sind",
        "war",
        "und",
        "oder",
        "mit",
        "von",
        "für",
        "auf",
        "in",
        "zu",
        "wie",
        "was",
        "what",
        "how",
        "when",
        "where",
        "why",
        "which",
        "who",
        "and",
        "or",
        "not",
        "but",
        "for",
        "with",
        "from",
    }
    words = re.findall(r"\b\w+\b", query.lower())
    return [w for w in words if w not in stopwords and len(w) > 2]

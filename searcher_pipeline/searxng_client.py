"""SearXNG Client — queries a local SearXNG instance for search results.

Returns structured JSON results suitable for the Searcher Pipeline.
"""

from __future__ import annotations

import json
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

DEFAULT_SEARXNG_URL = "http://127.0.0.1:8080"


def search(
    query: str,
    *,
    base_url: str = DEFAULT_SEARXNG_URL,
    categories: str = "general",
    language: str = "en",
    max_results: int = 20,
    timeout: float = 10.0,
) -> list[dict]:
    """Execute a search query against a local SearXNG instance.

    Args:
        query: The search query string.
        base_url: Base URL of the SearXNG instance.
        categories: Comma-separated search categories.
        language: Language code for results.
        max_results: Maximum results to return.
        timeout: HTTP request timeout in seconds.

    Returns:
        List of result dicts with keys: title, url, content, engine, score.
        Returns empty list on any error (never raises).
    """
    try:
        import urllib.request

        params = {
            "q": query,
            "format": "json",
            "categories": categories,
            "language": language,
        }
        url = f"{base_url.rstrip('/')}/search?{urlencode(params)}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Researcher/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("SearXNG search failed for query '%s': %s", query[:80], exc)
        return []

    results: list[dict] = []
    for r in data.get("results", [])[:max_results]:
        results.append(
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "engine": ",".join(r.get("engines", [])),
                "score": r.get("score", 0.0),
            }
        )

    return results


def healthcheck(base_url: str = DEFAULT_SEARXNG_URL, timeout: float = 5.0) -> bool:
    """Check if the SearXNG instance is reachable."""
    try:
        import urllib.request

        url = f"{base_url.rstrip('/')}/search?q=test&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Researcher/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

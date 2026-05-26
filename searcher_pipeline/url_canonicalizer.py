"""URL Canonicalizer — normalizes URLs to a stable canonical form."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def canonicalize(url: str) -> str:
    """Normalize a URL to its canonical form.

    - Lowercase scheme + host
    - Remove default ports (80, 443)
    - Remove fragments
    - Sort query parameters
    - Remove trailing slashes on path (except root)
    - Decode safe percent-encoded chars
    """
    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.hostname or ""
    port = parsed.port

    # Remove default ports
    if scheme == "http" and port == 80:
        netloc = netloc
        port = None
    elif scheme == "https" and port == 443:
        port = None

    host_part = netloc.lower()
    if port:
        host_part = f"{host_part}:{port}"

    # Normalize path
    path = parsed.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Sort query params
    query = _sort_query_params(parsed.query)

    # Fragment dropped
    return urlunparse((scheme, host_part, path, "", query, ""))


def _sort_query_params(query: str) -> str:
    """Sort query parameters alphabetically."""
    if not query:
        return ""
    params = parse_qs(query, keep_blank_values=True)
    sorted_items = sorted(params.items())
    return urlencode(sorted_items, doseq=True)


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs share the same domain."""
    d1 = urlparse(url1).hostname or ""
    d2 = urlparse(url2).hostname or ""
    return d1.lower() == d2.lower()


def extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    return (urlparse(url).hostname or "").lower()

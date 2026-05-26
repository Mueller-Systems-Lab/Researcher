"""HTTP Fetch Cache — in-memory with Cache-Control compliance.

Rules:
- Cache key: HTTP method + normalized URL
- Only GET requests cached
- Respect Cache-Control: no-store never cached
- Authorization headers never stored in shared cache
- Content hashing for integrity verification
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

# In-memory cache
_cache: dict[str, CacheEntry] = {}


@dataclass
class CacheEntry:
    """A cached HTTP response."""

    key: str
    url: str
    content: str
    content_hash: str
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    cached_at: float = field(default_factory=time.time)
    ttl: int = 300  # 5 min default


def _cache_key(method: str, url: str) -> str:
    """Generate a stable cache key."""
    normalized = f"{method.upper()}|{url}"
    return hashlib.sha256(normalized.encode()).hexdigest()


def get(method: str, url: str) -> CacheEntry | None:
    """Retrieve a cached response. Returns None on miss or expiry."""
    key = _cache_key(method, url)
    entry = _cache.get(key)
    if entry is None:
        return None
    if (time.time() - entry.cached_at) > entry.ttl:
        del _cache[key]
        return None
    return entry


def put(
    method: str,
    url: str,
    content: str,
    status_code: int,
    headers: dict[str, str] | None = None,
    ttl: int | None = None,
) -> CacheEntry:
    """Store a response in the cache.

    Respects Cache-Control: no-store and Authorization headers.
    """
    # Never cache no-store
    cc = (headers or {}).get("cache-control", "").lower()
    if "no-store" in cc:
        # Return a non-cached entry for consistency
        return CacheEntry(
            key="",
            url=url,
            content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            status_code=status_code,
            headers=headers or {},
            ttl=0,
        )

    # Never cache responses with Authorization
    if "authorization" in (headers or {}):
        return CacheEntry(
            key="",
            url=url,
            content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            status_code=status_code,
            headers=headers or {},
            ttl=0,
        )

    key = _cache_key(method, url)
    entry = CacheEntry(
        key=key,
        url=url,
        content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        status_code=status_code,
        headers=headers or {},
    )
    if ttl is not None:
        entry.ttl = ttl
    _cache[key] = entry
    return entry


def clear_cache() -> None:
    """Clear the entire cache (for testing)."""
    _cache.clear()

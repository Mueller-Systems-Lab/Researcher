"""Robots Policy — checks robots.txt for crawl permissions.

Rules:
- /robots.txt per domain check
- Cache result (TTL from max-age or default 3600s)
- 5xx/unreachable → fail closed (disallow)
- 4xx/unavailable → documented decision
- robots content treated as untrusted
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

# In-memory robots cache: domain → RobotsPolicy
_robots_cache: dict[str, RobotsPolicy] = {}


@dataclass
class RobotsPolicy:
    """Cached robots.txt policy for a domain."""

    domain: str
    allowed: bool = True
    fetched_at: float = field(default_factory=time.time)
    ttl: int = 3600
    disallowed_paths: list[str] = field(default_factory=list)
    error: str | None = None

    def is_expired(self) -> bool:
        return (time.time() - self.fetched_at) > self.ttl


def _fetch_robots(domain: str, timeout: float = 5.0) -> RobotsPolicy | None:
    """Fetch and parse /robots.txt for a domain.

    Returns None on fetch failure → fail closed.
    """
    try:
        import urllib.request

        robots_url = f"https://{domain}/robots.txt"
        req = urllib.request.Request(
            robots_url, headers={"User-Agent": "Researcher/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            if 500 <= status < 600:
                # 5xx → fail closed
                return None
            if 400 <= status < 500:
                # 4xx → documented decision: allow but log
                policy = RobotsPolicy(
                    domain=domain, allowed=True, error=f"HTTP {status}"
                )
                return policy
            content = resp.read().decode("utf-8", errors="replace")
    except Exception:
        # Unreachable → fail closed
        return None

    return _parse_robots_content(domain, content)


def _parse_robots_content(domain: str, content: str) -> RobotsPolicy:
    """Parse robots.txt content (untrusted — treat carefully)."""
    policy = RobotsPolicy(domain=domain)
    disallowed: list[str] = []
    current_agent = ""

    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Limit line length to prevent abuse
        if len(line) > 1024:
            continue

        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()

            if key == "user-agent":
                current_agent = value.lower()
            elif key == "disallow" and (
                "*" in current_agent or "researcher" in current_agent
            ):
                if value:
                    disallowed.append(value)
            elif key == "crawl-delay":
                try:
                    policy.ttl = max(policy.ttl, int(float(value)))
                except ValueError:
                    pass

    policy.disallowed_paths = disallowed
    return policy


def is_allowed(url: str, user_agent: str = "Researcher/1.0") -> bool:
    """Check if a URL is allowed by robots.txt.

    Returns True if allowed, False if disallowed.
    Fail-closed: if robots.txt can't be fetched, assume disallowed.
    """
    parsed = urlparse(url)
    domain = parsed.hostname or ""

    if not domain:
        return False

    # Check cache
    cached = _robots_cache.get(domain)
    if cached and not cached.is_expired():
        if cached.error:
            return cached.allowed
        return _check_path(parsed.path, cached.disallowed_paths)

    # Fetch
    policy = _fetch_robots(domain)
    if policy is None:
        # Fail closed
        policy = RobotsPolicy(domain=domain, allowed=False, error="fetch_failed")
        _robots_cache[domain] = policy
        return False

    _robots_cache[domain] = policy
    return _check_path(parsed.path, policy.disallowed_paths)


def _check_path(path: str, disallowed: list[str]) -> bool:
    """Check if a path matches any disallowed pattern."""
    for pattern in disallowed:
        if pattern == "/":
            return False
        if path.startswith(pattern):
            return False
    return True


def clear_cache() -> None:
    """Clear the robots cache (for testing)."""
    _robots_cache.clear()

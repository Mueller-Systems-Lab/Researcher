"""Domain Rate Limiter — per-domain leaky bucket.

Ensures fair, respectful crawling with configurable delay.
"""

from __future__ import annotations

import time
from collections import defaultdict

# Domain → (last_request_time, delay_seconds)
_domain_timers: dict[str, tuple[float, float]] = defaultdict(lambda: (0.0, 0.0))
DEFAULT_DELAY = 2.0  # 2 seconds between requests to same domain


def set_domain_delay(domain: str, delay: float) -> None:
    """Set the minimum delay between requests for a domain."""
    last, _ = _domain_timers[domain]
    _domain_timers[domain] = (last, delay)


def check_rate(domain: str) -> bool:
    """Check if a request to domain is allowed now.

    Returns True if allowed, False if rate-limited.
    """
    last, delay = _domain_timers[domain]
    if delay == 0:
        delay = DEFAULT_DELAY
    elapsed = time.time() - last
    return elapsed >= delay


def wait_if_needed(domain: str) -> None:
    """Block until the rate limit for domain allows a request."""
    last, delay = _domain_timers[domain]
    if delay == 0:
        delay = DEFAULT_DELAY
    elapsed = time.time() - last
    if elapsed < delay:
        time.sleep(delay - elapsed)


def record_request(domain: str) -> None:
    """Record that a request was made to domain (updates last-request time)."""
    _, delay = _domain_timers[domain]
    if delay == 0:
        delay = DEFAULT_DELAY
    _domain_timers[domain] = (time.time(), delay)


def reset() -> None:
    """Reset all domain timers (for testing)."""
    _domain_timers.clear()

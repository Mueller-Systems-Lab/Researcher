# =============================================================================
# Scrapers — Zentrales HTTP-Session-Management für alle Scraper
# =============================================================================
# Bietet:
#   - http_session.create_session() — requests.Session mit Retry-Adapter
#   - http_session.detect_js_only() — JavaScript-Seiten-Erkennung
#   - http_session.USER_AGENT — Zentraler User-Agent
# =============================================================================

from scrapers.http_session import (
    DEFAULT_TIMEOUT,
    RETRY_CONFIG,
    USER_AGENT,
    USER_AGENT_FALLBACK,
    create_session,
    detect_js_only,
)

__all__ = [
    "USER_AGENT",
    "USER_AGENT_FALLBACK",
    "DEFAULT_TIMEOUT",
    "RETRY_CONFIG",
    "create_session",
    "detect_js_only",
]

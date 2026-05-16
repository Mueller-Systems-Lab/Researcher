# =============================================================================
# Darknet-Crawler — Konfiguration
# =============================================================================
# Alle konfigurierbaren Parameter werden aus Umgebungsvariablen gelesen,
# mit sinnvollen Defaults. Siehe .env.example für Details.
# =============================================================================

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CrawlerConfig:
    """Zentrale Konfiguration für den Darknet-Crawler."""

    # Tor SOCKS5-Proxy
    tor_host: str = field(default_factory=lambda: os.getenv("TOR_HOST", "127.0.0.1"))
    tor_port: int = field(default_factory=lambda: int(os.getenv("TOR_PORT", "9050")))

    # Forum
    forum_base_url: str = field(default_factory=lambda: os.getenv("FORUM_BASE_URL", ""))
    login_url: str = field(default_factory=lambda: os.getenv("LOGIN_URL", ""))
    username: str = field(default_factory=lambda: os.getenv("FORUM_USERNAME", ""))
    password: str = field(default_factory=lambda: os.getenv("FORUM_PASSWORD", ""))

    # Crawl-Verhalten
    max_pages: int = field(
        default_factory=lambda: int(os.getenv("CRAWL_MAX_PAGES", "5"))
    )
    crawl_delay: float = field(
        default_factory=lambda: float(os.getenv("CRAWL_DELAY", "5.0"))
    )
    max_posts_per_page: int = field(
        default_factory=lambda: int(os.getenv("CRAWL_MAX_POSTS", "50"))
    )

    # Index
    index_path: str = field(
        default_factory=lambda: os.getenv("DARKNET_INDEX_PATH", "./darknet_index")
    )

    @property
    def proxy_url(self) -> str:
        return f"socks5h://{self.tor_host}:{self.tor_port}"

    @property
    def is_configured(self) -> bool:
        """Prüft, ob die minimale Konfiguration vorhanden ist."""
        return bool(self.forum_base_url and self.login_url)


# Globale Instanz
config = CrawlerConfig()

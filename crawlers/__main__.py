# =============================================================================
# Darknet-Crawler — CLI-Entrypoint
# =============================================================================
# Ermöglicht den Aufruf von: python -m crawlers
# Nutzung:  python -m crawlers [--max-pages N] [--delay N]
# =============================================================================

import argparse
import logging
import sys

from crawlers.config import config
from crawlers.darknet_crawler import DarknetCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Darknet-Forum-Crawler (Tor SOCKS5)")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=config.max_pages,
        help=f"Maximale Seitenzahl (default: {config.max_pages})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=config.crawl_delay,
        help=f"Sekunden zwischen Requests (default: {config.crawl_delay})",
    )
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Nur Konfiguration anzeigen, nicht crawlen",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Ausführliche Logs aktivieren"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Konfiguration anzeigen
    print("=" * 60)
    print("  Darknet-Crawler Konfiguration")
    print("=" * 60)
    print(f"  Proxy:      {config.proxy_url}")
    print(f"  Forum-URL:  {config.forum_base_url or '(nicht gesetzt)'}")
    print(f"  Login-URL:  {config.login_url or '(nicht gesetzt)'}")
    print(f"  Eingeloggt: {bool(config.username)}")
    print(f"  Max Seiten: {args.max_pages}")
    print(f"  Delay:      {args.delay}s")
    print(f"  Index-Pfad: {config.index_path}")
    print("=" * 60)

    if args.config_only:
        return

    if not config.is_configured:
        print("\n  ❌ Crawler nicht konfiguriert.")
        print("  Setze FORUM_BASE_URL und LOGIN_URL in .env")
        print("  Siehe .env.example für alle Optionen.")
        sys.exit(1)

    # Crawler starten
    print(f"\n  Starte Crawling ({args.max_pages} Seiten)...\n")
    crawler = DarknetCrawler(
        {
            "max_pages": args.max_pages,
            "crawl_delay": args.delay,
        }
    )

    posts = crawler.crawl(max_pages=args.max_pages)
    print(f"\n  ✅ {len(posts)} Posts extrahiert")

    if posts:
        print("\n  Erstes Posting:")
        print(f"    Autor:     {posts[0].author}")
        print(f"    Content:   {posts[0].content[:100]}...")
        print(f"    Timestamp: {posts[0].timestamp}")


if __name__ == "__main__":
    main()

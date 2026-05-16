# =============================================================================
# Onion Discovery — CLI-Entrypoint
# =============================================================================
# python -m onion_discovery [--run] [--add-seed URL] [--stats] [--review]
# =============================================================================

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Onion Discovery Engine (ADR-007)")
    parser.add_argument(
        "--run", action="store_true", help="Einmaligen Discovery-Durchlauf starten"
    )
    parser.add_argument(
        "--add-seed", type=str, metavar="URL", help="Seed manuell hinzufügen"
    )
    parser.add_argument(
        "--add-seeds",
        type=str,
        metavar="FILE",
        help="Seeds aus Datei hinzufügen (eine URL pro Zeile)",
    )
    parser.add_argument("--stats", action="store_true", help="Statistiken anzeigen")
    parser.add_argument(
        "--review", action="store_true", help="Nächste Review-Items anzeigen"
    )
    parser.add_argument(
        "--approve", type=str, metavar="ID", help="Review-Item genehmigen"
    )
    parser.add_argument(
        "--reject",
        type=str,
        nargs=2,
        metavar=("ID", "REASON"),
        help="Review-Item ablehnen",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Ausführliche Logs"
    )
    parser.add_argument(
        "--config-only", action="store_true", help="Nur Konfiguration anzeigen"
    )
    parser.add_argument(
        "--tor-check", action="store_true", help="Tor-Verbindung prüfen"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    from onion_discovery.seed_queue import SeedQueue
    from onion_discovery.policy_gateway import PolicyGateway
    from onion_discovery.human_review import ReviewQueue
    from onion_discovery.engine import DiscoveryPipeline

    if args.config_only:
        print("=" * 60)
        print("  Onion Discovery — Konfiguration")
        print("=" * 60)
        print(
            f"  ONION_DISCOVERY_ENABLED: "
            f"{os.getenv('ONION_DISCOVERY_ENABLED', 'false')}"
        )
        print(f"  Tor-Proxy: socks5h://127.0.0.1:9050")
        print(f"  Pipeline aktiv: {DiscoveryPipeline().enabled()}")
        print("=" * 60)
        return

    if args.tor_check:
        import requests

        try:
            r = requests.get(
                "http://check.torproject.org/api/ip",
                proxies={
                    "http": "socks5h://127.0.0.1:9050",
                    "https": "socks5h://127.0.0.1:9050",
                },
                timeout=10,
            )
            print(f"  Tor-Verbindung OK: {r.json()}")
        except Exception as e:
            print(f"  ❌ Tor nicht erreichbar: {e}")
        return

    if args.add_seed:
        pipeline = DiscoveryPipeline()
        if pipeline.add_seed(args.add_seed):
            print(f"  ✅ Seed hinzugefügt: {args.add_seed}")
        else:
            print(f"  ℹ️  Seed existiert bereits: {args.add_seed}")

    if args.add_seeds:
        try:
            with open(args.add_seeds) as f:
                urls = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
            pipeline = DiscoveryPipeline()
            count = pipeline.add_seeds(urls)
            print(f"  ✅ {count} Seeds aus {args.add_seeds} hinzugefügt")
        except FileNotFoundError:
            print(f"  ❌ Datei nicht gefunden: {args.add_seeds}")
            sys.exit(1)

    if args.stats:
        sq = SeedQueue()
        rq = ReviewQueue()
        pg = PolicyGateway()
        print("=" * 60)
        print("  Onion Discovery — Statistiken")
        print("=" * 60)
        print(f"  Seeds: {sq.get_stats()}")
        print(f"  Review-Queue: {rq.get_stats()}")
        print(f"  Policy: {pg.stats}")
        print("=" * 60)

    if args.review:
        rq = ReviewQueue()
        items = [item for item in rq._items.values() if item.status == "pending"]
        if not items:
            print("  Keine pending Review-Items.")
            return
        print("=" * 60)
        print("  Review-Queue (Pending)")
        print("=" * 60)
        for item in sorted(
            items,
            key=lambda x: x.discovered_at,
        )[:10]:
            print(f"  ID:     {item.id}")
            print(f"  URL:    {item.url}")
            print(f"  Thema:  {item.topic}")
            print(f"  Risiko: {item.risk_level}")
            print(f"  Status: {item.status}")
            print("  ---")

    if args.approve:
        rq = ReviewQueue()
        if rq.approve(args.approve, reviewer="cli"):
            print(f"  ✅ Item {args.approve} genehmigt")
        else:
            print(f"  ❌ Item {args.approve} nicht gefunden")

    if args.reject:
        item_id, reason = args.reject
        rq = ReviewQueue()
        if rq.reject(item_id, reviewer="cli", reason=reason):
            print(f"  ✅ Item {item_id} abgelehnt: {reason}")
        else:
            print(f"  ❌ Item {item_id} nicht gefunden")

    if args.run:
        pipeline = DiscoveryPipeline()
        print("  Starte Discovery-Durchlauf...")
        stats = pipeline.run_once()
        print(f"  ✅ Durchlauf abgeschlossen: {stats}")

    if not any(vars(args).values()):
        parser.print_help()


if __name__ == "__main__":
    main()

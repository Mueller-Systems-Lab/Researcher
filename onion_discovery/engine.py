# =============================================================================
# Onion Discovery — Pipeline Engine
# =============================================================================
# Haupt-Pipeline: Seed → Fetch → Parse → Extract → Classify → Review → Index
#
# Orchestriert die Discovery-Komponenten:
#   - SeedQueue: Seeds verwalten
#   - PolicyGateway: Sicherheitsprüfungen
#   - LinkExtractor: Onion-Links finden
#   - Classifier: Seiten klassifizieren
#   - ReviewQueue: Human Approval
#   - WhooshIndex: Persistente Speicherung
#
# ADR-006: Onion Zone disabled by default.
# ADR-007: Discovery ≠ Crawling.
#
# Nutzung:
#   from onion_discovery.engine import DiscoveryPipeline
#   pipeline = DiscoveryPipeline()
#   pipeline.run_once()  # Einmaliger Discovery-Durchlauf
# =============================================================================

import hashlib
import logging
import os
import time
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from onion_discovery.seed_queue import SeedQueue
from onion_discovery.policy_gateway import PolicyGateway
from onion_discovery.link_extractor import LinkExtractor
from onion_discovery.classifier import Classifier, RISK_CRITICAL, RISK_HIGH
from onion_discovery.human_review import ReviewQueue

logger = logging.getLogger(__name__)


class DiscoveryPipeline:
    """Orchestriert die Onion-Discovery-Pipeline.

    Führt einen vollständigen Durchlauf aus:
    Seed → Policy Check → Fetch → Parse → Link Extract → Classify → Review → Index
    """

    def __init__(
        self,
        seed_queue: Optional[SeedQueue] = None,
        policy_gateway: Optional[PolicyGateway] = None,
        link_extractor: Optional[LinkExtractor] = None,
        classifier: Optional[Classifier] = None,
        review_queue: Optional[ReviewQueue] = None,
        max_pages_per_run: int = 3,
        tor_proxy: str = "socks5h://127.0.0.1:9050",
    ):
        self.seed_queue = seed_queue or SeedQueue()
        self.policy = policy_gateway or PolicyGateway()
        self.link_extractor = link_extractor or LinkExtractor()
        self.classifier = classifier or Classifier()
        self.review_queue = review_queue or ReviewQueue()
        self.max_pages_per_run = max_pages_per_run
        self.tor_proxy = tor_proxy
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Erstellt eine requests.Session mit Tor-Proxy."""
        session = requests.Session()
        session.proxies = {
            "http": self.tor_proxy,
            "https": self.tor_proxy,
        }
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
                    "Gecko/20100101 Firefox/128.0"
                ),
                "Accept": "text/html,application/xhtml+xml",
            }
        )
        session.timeout = 30
        return session

    def enabled(self) -> bool:
        """Prüft, ob Onion Discovery aktiviert ist (ADR-006)."""
        return os.getenv("ONION_DISCOVERY_ENABLED", "false").lower() in (
            "true",
            "1",
            "yes",
        )

    def run_once(self) -> dict:
        """Führt einen einzelnen Discovery-Durchlauf aus.

        Returns:
            Dict mit Statistiken des Durchlaufs.
        """
        if not self.enabled():
            logger.info("Onion Discovery deaktiviert (ONION_DISCOVERY_ENABLED=false)")
            return {"status": "disabled"}

        stats = {
            "seeds_processed": 0,
            "pages_fetched": 0,
            "links_found": 0,
            "new_seeds_added": 0,
            "classified": 0,
            "sent_to_review": 0,
            "sent_to_index": 0,
            "errors": 0,
        }

        for _ in range(self.max_pages_per_run):
            seed = self.seed_queue.get_next()
            if seed is None:
                logger.info("Keine pending Seeds — Durchlauf beendet")
                break

            stats["seeds_processed"] += 1
            logger.info(f"Verarbeite Seed: {seed.url}")

            # 1. Policy Check
            decision = self.policy.is_allowed(seed.url)
            if not decision.allowed:
                logger.warning(f"Seed {seed.url} abgewiesen: {decision.reason}")
                self.seed_queue.mark_error(seed.url, decision.reason)
                stats["errors"] += 1
                continue

            # 2. Fetch
            try:
                response = self._session.get(seed.url, timeout=30)
                response.raise_for_status()
                html = response.text
                stats["pages_fetched"] += 1
            except requests.RequestException as e:
                logger.warning(f"Fetch-Fehler für {seed.url}: {e}")
                self.seed_queue.mark_error(seed.url, str(e))
                stats["errors"] += 1
                continue

            # 3. Parse & Extract Links
            links = self.link_extractor.extract(seed.url, html)
            stats["links_found"] += len(links)

            # Neue Seeds hinzufügen
            for link in links:
                if self.seed_queue.add_seed(
                    link["url"],
                    source="crawl",
                    priority=3,
                ):
                    stats["new_seeds_added"] += 1

            # 4. Extract Title & Text
            title = ""
            content = ""
            try:
                soup = BeautifulSoup(html, "lxml")
                title = soup.title.get_text(strip=True) if soup.title else ""
                # Text aus relevanten Tags extrahieren
                for tag in soup.find_all(["p", "h1", "h2", "h3", "li", "article"]):
                    text = tag.get_text(strip=True)
                    if text:
                        content += text + "\n"
                content = content[:5000]  # Begrenzen
            except Exception as e:
                logger.warning(f"Parse-Fehler: {e}")

            # 5. Classify
            classification = self.classifier.classify(
                url=seed.url,
                title=title,
                content=content,
            )
            stats["classified"] += 1

            # 6. Human Review (wenn nötig)
            item_id = hashlib.md5(seed.url.encode()).hexdigest()[:16]

            if classification.requires_human_review:
                self.review_queue.add(
                    item_id=item_id,
                    url=seed.url,
                    title=title,
                    content=content[:500],
                    topic=classification.topic,
                    risk_level=classification.risk_level,
                    confidence=classification.confidence,
                    source_seed=seed.url,
                )
                stats["sent_to_review"] += 1
                logger.info(
                    f"Zur Review-Queue: {seed.url[:60]} "
                    f"({classification.topic}, "
                    f"Risiko: {classification.risk_level})"
                )

            # 7. Direkt indexieren (wenn kein Review nötig)
            if classification.indexable and not classification.requires_human_review:
                try:
                    from darknet_search.index import WhooshIndex

                    idx = WhooshIndex()
                    idx.add_post(
                        {
                            "url": seed.url,
                            "author": "onion_discovery",
                            "title": title or "Onion Page",
                            "timestamp": datetime.now(),
                            "content": content[:2000],
                            "forum_id": "onion_discovery",
                        }
                    )
                    stats["sent_to_index"] += 1
                except Exception as e:
                    logger.warning(f"Index-Fehler: {e}")

            # Seed als verarbeitet markieren
            self.seed_queue.mark_completed(
                seed.url,
                status="reviewed"
                if classification.requires_human_review
                else "approved",
            )

        logger.info(f"Discovery-Durchlauf abgeschlossen: {stats}")
        return stats

    def add_seed(self, url: str) -> bool:
        """Fügt manuell einen Seed hinzu."""
        return self.seed_queue.add_seed(url, source="manual", priority=10)

    def add_seeds(self, urls: list[str]) -> int:
        """Fügt mehrere Seeds hinzu."""
        return self.seed_queue.add_seeds(urls, source="manual", priority=10)

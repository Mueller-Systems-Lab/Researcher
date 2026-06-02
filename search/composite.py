# =============================================================================
# CompositeRetriever — Parallele Suche SearXNG + Darknet
# =============================================================================
# Implementiert das GPT-Researcher-Retriever-Interface.
# Führt parallele Abfragen in SearXNG (Websuche) und DarknetRetriever
# (Whoosh-Index) aus, merged und dedupliziert die Ergebnisse.
#
# Nutzung:
#   retriever = CompositeRetriever("suchbegriff")
#   results = retriever.search(max_results=15)
#
# GPT Researcher Integration:
#   RETRIEVER=custom
#   RETRIEVER_ENDPOINT=http://localhost:9876/search
#   (oder als Code-Retriever registrieren)
# =============================================================================

import logging
import os
from typing import Any
from urllib.parse import urljoin

import requests

from darknet_search.retriever import DarknetRetriever
from scrapers.http_session import create_session

logger = logging.getLogger(__name__)


class CompositeRetriever:
    """GPT-Researcher-kompatibler Composite-Retriever.

    Fragt parallel SearXNG (Web) und DarknetRetriever (Forum) ab,
    merged Ergebnisse anhand der URL und dedupliziert.

    Fehlerzustände sind über `last_errors` abrufbar — leere Ergebnisse
    bedeuten entweder "keine Ergebnisse" ODER "Backend nicht erreichbar".
    """

    def __init__(
        self,
        query: str,
        query_domains: list | None = None,
        searx_url: str | None = None,
        darknet_index_dir: str | None = None,
    ):
        self.query = query
        self.query_domains = query_domains or []
        self.searx_url = searx_url or os.getenv("SEARX_URL", "http://localhost:8080")
        self.darknet_index_dir = darknet_index_dir or os.getenv(
            "DARKNET_INDEX_PATH", "./darknet_index"
        )
        self.darknet_enabled = os.getenv("DARKNET_ENABLED", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        self.last_errors: dict[str, str | None] = {
            "searxng": None,
            "darknet": None,
        }

    def _search_searxng(self, max_results: int) -> list[dict]:
        """Sucht in SearXNG.

        Returns:
            Liste von Ergebnissen im GPT-Researcher-Format, oder leere Liste.
        """
        try:
            search_url = urljoin(self.searx_url or "http://localhost:8080", "search")
            params: dict[str, Any] = {
                "q": self.query,
                "format": "json",
                "language": "de-DE",
                "categories": "general",
                "pageno": 1,
            }
            response = create_session().get(search_url, params=params, timeout=15)
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError:
                self.last_errors["searxng"] = "SearXNG lieferte ungültiges JSON"
                logger.warning(self.last_errors["searxng"])
                return []

            results = []
            for r in data.get("results", [])[:max_results]:
                url = r.get("url", "")
                if not url:
                    continue
                results.append(
                    {
                        "url": url,
                        "title": r.get("title", ""),
                        "body": r.get("content", ""),
                        "source": "SearXNG",
                        "engine": r.get("engine", ""),
                        "score": r.get("score", 0),
                        "raw_content": r.get("content", ""),
                    }
                )
            logger.info(f'SearXNG: {len(results)} Ergebnisse für "{self.query}"')
            return results

        except requests.exceptions.ConnectionError:
            self.last_errors["searxng"] = (
                f"SearXNG nicht erreichbar unter {self.searx_url}"
            )
            logger.warning(self.last_errors["searxng"])
            return []
        except requests.RequestException as e:
            self.last_errors["searxng"] = f"SearXNG-Fehler: {e}"
            logger.warning(self.last_errors["searxng"])
            return []

    def _search_darknet(self, max_results: int) -> list[dict]:
        """Sucht im Darknet-Index.

        Returns:
            Liste von Ergebnissen im GPT-Researcher-Format, oder leere Liste.
        """
        if not self.darknet_enabled:
            logger.info("Darknet-Suche deaktiviert (DARKNET_ENABLED=false)")
            return []

        try:
            retriever = DarknetRetriever(
                self.query,
                index_dir=self.darknet_index_dir,
            )
            results = retriever.search(max_results=max_results)
            logger.info(f'Darknet: {len(results)} Ergebnisse für "{self.query}"')
            return results
        except Exception as e:
            self.last_errors["darknet"] = f"Darknet-Suche fehlgeschlagen: {e}"
            logger.error(
                f"Darknet-Suche fehlgeschlagen: {e}. "
                f"Index: {getattr(self, 'darknet_index_dir', '?')}",
                exc_info=True,
            )
            return []

    @staticmethod
    def _deduplicate(results: list[dict]) -> list[dict]:
        """Dedupliziert Ergebnisse anhand der URL.

        Behält die erste Instanz einer URL. Ignoriert leere URLs.
        """
        seen = set()
        deduped = []
        for r in results:
            url = r.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append(r)
        return deduped

    def search(self, max_results: int = 15) -> list[dict]:
        """GPT-Researcher-Interface: Parallele Suche in beiden Backends.

        Args:
            max_results: Maximale Gesamtergebnisse.

        Returns:
            Gemergte, deduplizierte Ergebnisliste.
        """
        # Parallele Abfrage beider Backends
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="composite"
        ) as executor:
            searx_future = executor.submit(self._search_searxng, max_results)
            darknet_future = executor.submit(self._search_darknet, max_results)

            # as_completed: Darknet-Ergebnisse sofort verfügbar,
            # auch wenn SearXNG noch läuft (oder timeoutet)
            future_map = {
                searx_future: "searxng",
                darknet_future: "darknet",
            }
            searx_results: list[dict] = []
            darknet_results: list[dict] = []
            for future in concurrent.futures.as_completed(future_map):
                key = future_map[future]
                try:
                    if key == "searxng":
                        searx_results = future.result()
                    else:
                        darknet_results = future.result()
                except concurrent.futures.TimeoutError:
                    logger.warning(
                        f"CompositeRetriever {key}: Timeout, verwende partial results"
                    )
                except (
                    Exception
                ) as e:  # pragma: no cover — _search_* catch-all prevents this
                    logger.warning(f"CompositeRetriever {key}: {e}")

        # Mischen & deduplizieren
        merged = searx_results + darknet_results
        deduped = self._deduplicate(merged)

        # Nach Score sortieren (falls vorhanden), begrenzen
        deduped.sort(key=lambda x: x.get("score", 0) or 0, reverse=True)
        final = deduped[:max_results]

        logger.info(
            f"CompositeRetriever: "
            f"SearXNG={len(searx_results)}, Darknet={len(darknet_results)}, "
            f"merged={len(merged)}, deduped={len(deduped)}, "
            f"final={len(final)}"
        )
        return final

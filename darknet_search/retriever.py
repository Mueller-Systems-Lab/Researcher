# =============================================================================
# DarknetRetriever — GPT-Researcher-kompatibler Retriever
# =============================================================================
# Implementiert das GPT Researcher Retriever-Interface für die Suche im
# Whoosh-Index. Kann mit RETRIEVER=darknet in GPT Researcher registriert
# werden.
#
# Interface:
#   __init__(self, query: str, query_domains=None)
#   search(self, max_results: int = 10) -> List[Dict[str, str]]
#
# Nutzung:
#   retriever = DarknetRetriever("suchbegriff")
#   results = retriever.search(max_results=10)
# =============================================================================

import logging
import os
from typing import Optional

from darknet_search.index import WhooshIndex

logger = logging.getLogger(__name__)


def make_darknet_uri(forum_id: str, post_url: str) -> str:
    """Erzeugt eine synthetische darknet://-URI für Zitate.

    Format: darknet://<forum-id>/post/<post-hash>
    """
    import hashlib

    post_hash = hashlib.md5(post_url.encode()).hexdigest()[:12]
    return f"darknet://{forum_id}/post/{post_hash}"


class DarknetRetriever:
    """GPT-Researcher-kompatibler Retriever für den Whoosh-Index.

    Durchsucht den Darknet-Forum-Volltextindex und gibt Ergebnisse
    im GPT-Researcher-Format zurück.
    """

    def __init__(
        self,
        query: str,
        query_domains: Optional[list] = None,
        index_dir: Optional[str] = None,
    ):
        """
        Args:
            query: Suchbegriff.
            query_domains: Wird ignoriert (Darknet hat keine Domains).
            index_dir: Pfad zum Whoosh-Index (default: DARKNET_INDEX_PATH env).
        """
        self.query = query
        self.query_domains = query_domains or []

        # Index-Pfad aus Umgebungsvariable oder Default
        index_path = index_dir or os.getenv("DARKNET_INDEX_PATH", "./darknet_index")
        self.index = WhooshIndex(index_path)

    def search(self, max_results: int = 10) -> list[dict]:
        """Führt die Suche im Whoosh-Index aus.

        Args:
            max_results: Maximale Anzahl Suchergebnisse.

        Returns:
            Liste von Ergebnis-Dicts im GPT-Researcher-Format:
            [{ "url": "...", "title": "...", "body": "...", ... }]
        """
        results = self.index.search(self.query, limit=max_results)

        # In GPT-Researcher-Format konvertieren
        gpt_results = []
        seen_urls = set()

        for r in results:
            uri = make_darknet_uri(r.get("forum_id", "unknown"), r["url"])
            if uri in seen_urls:
                continue
            seen_urls.add(uri)

            gpt_results.append(
                {
                    "url": uri,
                    "title": r.get("title", "Darknet Post"),
                    "body": r.get("content", ""),
                    "source": r.get("source", "Darknet Forum"),
                    "author": r.get("author", ""),
                    "timestamp": r.get("timestamp", ""),
                    "raw_content": r.get("content", ""),
                }
            )

        logger.info(
            f'DarknetRetriever: {len(gpt_results)} Ergebnisse für "{self.query}"'
        )
        return gpt_results

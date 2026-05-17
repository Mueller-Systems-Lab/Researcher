# =============================================================================
# Darknet Search — Whoosh-Volltextindex
# =============================================================================
# Verwaltet den Whoosh-Index für Darknet-Forum-Posts.
# Wird vom Crawler (T-005) befüllt und vom DarknetRetriever (T-007) gelesen.
#
# Nutzung:
#   from darknet_search.index import WhooshIndex
#   idx = WhooshIndex("./darknet_index")
#   idx.add_post(post)
#   results = idx.search("suchbegriff", limit=10)
# =============================================================================

import hashlib
import logging
import os
from datetime import datetime
from typing import Optional

from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, DATETIME
from whoosh.qparser import MultifieldParser
from whoosh.writing import AsyncWriter

logger = logging.getLogger(__name__)


# Whoosh-Schema für Forum-Posts
POST_SCHEMA = Schema(
    post_id=ID(stored=True, unique=True),
    url=ID(stored=True),
    author=TEXT(stored=True),
    title=TEXT(stored=True),
    timestamp=DATETIME(stored=True),
    content=TEXT(stored=True),
    forum_id=ID(stored=True),
)


class WhooshIndex:
    """Whoosh-Volltextindex für Darknet-Forum-Posts."""

    def __init__(self, index_dir: str = "./darknet_index"):
        self.index_dir = index_dir
        self._ix = None

    @property
    def ix(self):
        """Lazy-Initialisierung des Index."""
        if self._ix is None:
            self._open_or_create()
        return self._ix

    def _open_or_create(self):
        """Öffnet existierenden Index oder erstellt neuen."""
        os.makedirs(self.index_dir, exist_ok=True)
        if exists_in(self.index_dir):
            logger.info(f"Öffne existierenden Whoosh-Index: {self.index_dir}")
            self._ix = open_dir(self.index_dir, schema=POST_SCHEMA)
        else:
            logger.info(f"Erstelle neuen Whoosh-Index: {self.index_dir}")
            self._ix = create_in(self.index_dir, POST_SCHEMA)

    def add_post(self, post: dict) -> bool:
        """Fügt einen Post zum Index hinzu.

        Args:
            post: Dict mit Keys: url, author, title, timestamp, content, forum_id
                  timestamp kann str (ISO-8601) oder datetime sein.

        Returns:
            True bei Erfolg, False bei Fehler.
        """
        try:
            writer = AsyncWriter(self.ix)
            post_id = (
                post.get("url") or hashlib.sha256(str(post).encode()).hexdigest()[:32]
            )

            # Timestamp normalisieren
            ts = post.get("timestamp")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except ValueError:
                    ts = datetime.now()

            writer.update_document(
                post_id=post_id,
                url=post.get("url", ""),
                author=post.get("author", ""),
                title=post.get("title", ""),
                timestamp=ts or datetime.now(),
                content=post.get("content", ""),
                forum_id=post.get("forum_id", "unknown"),
            )
            writer.commit()
            return True

        except Exception as e:
            logger.exception(f"Fehler beim Indexieren von Post: {e}")
            return False

    def add_posts(self, posts: list[dict]) -> int:
        """Fügt mehrere Posts zum Index hinzu.

        Args:
            posts: Liste von Post-Dicts.

        Returns:
            Anzahl erfolgreich indexierter Posts.
        """
        count = 0
        for post in posts:
            if self.add_post(post):
                count += 1
        logger.info(f"{count}/{len(posts)} Posts indexiert")
        return count

    def search(
        self,
        query_str: str,
        limit: int = 10,
    ) -> list[dict]:
        """Volltextsuche im Index.

        Args:
            query_str: Suchbegriff.
            limit: Maximale Anzahl Ergebnisse.

        Returns:
            Liste von Ergebnis-Dicts mit Keys: url, author, title,
            timestamp, content, source, score.
        """
        if not query_str.strip():
            return []

        try:
            with self.ix.searcher() as searcher:
                parser = MultifieldParser(
                    ["content", "author", "title", "forum_id"],
                    schema=self.ix.schema,
                )
                query = parser.parse(query_str)
                results = searcher.search(query, limit=limit)

                output = []
                for hit in results:
                    output.append(
                        {
                            "url": hit["url"],
                            "author": hit["author"],
                            "title": hit["title"] or "Darknet Post",
                            "timestamp": str(hit["timestamp"])
                            if hit["timestamp"]
                            else "",
                            "content": hit["content"][:500] + "..."
                            if len(hit["content"]) > 500
                            else hit["content"],
                            "source": "Darknet Forum",
                            "score": hit.score,
                            "forum_id": hit["forum_id"],
                        }
                    )
                return output

        except Exception as e:
            logger.exception(f"Suchfehler: {e}")
            return []

    def optimize(self):
        """Optimiert den Index (Komprimierung)."""
        try:
            from whoosh import writing

            writer = AsyncWriter(self.ix)
            writer.commit(optimize=True)
            logger.info("Index optimiert")
        except Exception as e:
            logger.exception(f"Fehler bei Index-Optimierung: {e}")

    @property
    def doc_count(self) -> int:
        """Anzahl der Dokumente im Index."""
        try:
            with self.ix.searcher() as searcher:
                return searcher.doc_count()
        except Exception:
            logger.exception("Fehler bei doc_count")
            return 0

    def clear(self):
        """Leert den Index vollständig."""
        try:
            from whoosh import index

            self._ix = create_in(self.index_dir, POST_SCHEMA)
            logger.info("Index geleert")
        except Exception as e:
            logger.exception(f"Fehler beim Leeren des Index: {e}")

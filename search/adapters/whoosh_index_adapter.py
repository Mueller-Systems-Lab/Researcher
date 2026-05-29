"""WhooshIndexAdapter — Whoosh-based search index adapter (Legacy)."""

import hashlib
import logging
import os
from datetime import datetime

from whoosh.fields import DATETIME, ID, TEXT, Schema
from whoosh.index import create_in, exists_in, open_dir
from whoosh.qparser import MultifieldParser
from whoosh.writing import AsyncWriter

from search.ports.search_index_repository import SearchIndexRepository

logger = logging.getLogger(__name__)
_SEARCH_FIELDS = ["author", "title", "content", "forum_id"]


class WhooshIndexAdapter(SearchIndexRepository):
    def __init__(self, index_dir: str = "./darknet_index"):
        self.index_dir = index_dir
        self._schema = Schema(
            post_id=ID(stored=True, unique=True),
            url=ID(stored=True),
            author=TEXT(stored=True),
            title=TEXT(stored=True),
            timestamp=DATETIME(stored=True),
            content=TEXT(stored=True),
            forum_id=ID(stored=True),
        )
        self._ix = self._open_or_create_index()

    def _open_or_create_index(self):
        os.makedirs(self.index_dir, exist_ok=True)
        if exists_in(self.index_dir):
            return open_dir(self.index_dir)
        return create_in(self.index_dir, self._schema)

    def index(self, doc: dict) -> bool:
        try:
            writer = AsyncWriter(self._ix)
            post_id = (
                doc.get("url") or hashlib.sha256(str(doc).encode()).hexdigest()[:32]
            )
            writer.update_document(
                post_id=post_id,
                url=doc.get("url", ""),
                author=doc.get("author", ""),
                title=doc.get("title", ""),
                timestamp=doc.get("timestamp", datetime.min),
                content=doc.get("content", ""),
                forum_id=doc.get("forum_id", "unknown"),
            )
            writer.commit()
            return True
        except Exception as e:
            logger.exception(f"Whoosh-Indexfehler: {e}")
            return False

    def search(self, query: str, limit: int = 10) -> list[dict]:
        if not query.strip():
            return []
        try:
            parser = MultifieldParser(_SEARCH_FIELDS, schema=self._ix.schema)
            with self._ix.searcher() as searcher:
                results = searcher.search(parser.parse(query), limit=limit)
                output = []
                for hit in results:
                    ts = hit.get("timestamp")
                    if isinstance(ts, datetime):
                        ts = ts.isoformat()
                    elif ts is None:
                        ts = ""
                    content = hit.get("content") or ""
                    output.append(
                        {
                            "url": hit.get("url"),
                            "author": hit.get("author"),
                            "title": hit.get("title") or "Darknet Post",
                            "timestamp": ts,
                            "content": content[:500] + "..."
                            if len(content) > 500
                            else content,
                            "source": "Darknet Forum (Whoosh)",
                            "score": hit.score,
                            "forum_id": hit.get("forum_id"),
                        }
                    )
                return output
        except Exception as e:
            logger.exception(f"Whoosh-Suchfehler: {e}")
            return []

    def delete(self, doc_id: str) -> bool:
        try:
            writer = AsyncWriter(self._ix)
            writer.delete_by_term("post_id", doc_id)
            writer.commit()
            return True
        except Exception as e:
            logger.exception(f"Whoosh-Löschfehler: {e}")
            return False

    def clear(self) -> None:
        import shutil

        try:
            self._ix.close()
            shutil.rmtree(self.index_dir, ignore_errors=True)
            self._ix = self._open_or_create_index()
            logger.info("Whoosh-Index geleert")
        except Exception as e:
            logger.exception(f"Whoosh-Fehler beim Leeren: {e}")

    @property
    def doc_count(self) -> int:
        try:
            with self._ix.searcher() as searcher:
                return searcher.doc_count()
        except Exception:
            logger.exception("Fehler bei doc_count (Whoosh)")
            return 0

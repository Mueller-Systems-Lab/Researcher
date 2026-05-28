# =============================================================================
# Vector DB — ChromaDB Wrapper
# =============================================================================
# Kapselt ChromaDB-Zugriff für persistente Vektorspeicherung.
# Embeddings werden über den EmbeddingService (Ollama) erzeugt.
#
# Nutzung:
#   from vectordb.store import VectorStore
#   store = VectorStore()
#   store.add("text1", {"source": "web"}, embedding_vector)
#   results = store.query(embedding_vector, n_results=5)
# =============================================================================

import logging
import os
import sqlite3
import threading
import time

logger = logging.getLogger(__name__)

# Retry-Parameter für "database is locked"-Fehler (ADR-016 Resilience-Pattern)
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 0.1  # 0.1s → 0.2s → 0.4s


class VectorStore:
    """ChromaDB-Wrapper für persistente Vektorspeicherung.

    Speichert Embeddings auf Disk (kein RAM-Problem).
    Bietet explizite Fehlererkennung: Prüfe `available`-Property
    vor Operationen. Letzter Fehler in `last_error` abrufbar.
    """

    def __init__(
        self,
        persist_directory: str | None = None,
        collection_name: str | None = None,
    ):
        self.persist_directory = persist_directory or os.getenv(
            "CHROMA_PERSIST_DIRECTORY", "./chroma_db"
        )
        self.collection_name = collection_name or os.getenv(
            "CHROMA_COLLECTION", "gpt_researcher"
        )
        self._collection = None
        self._client = None
        self._lock = threading.RLock()
        self.last_error: str | None = None

    @property
    def available(self) -> bool:
        """Prüft, ob ChromaDB verfügbar und die Collection bereit ist."""
        return self._get_collection() is not None

    def _get_client(self):
        """Lazy-Initialisierung des ChromaDB-Clients (thread-safe)."""
        if self._client is None:
            with self._lock:
                if self._client is not None:
                    return self._client
                try:
                    import chromadb

                    self._client = chromadb.PersistentClient(
                        path=self.persist_directory
                    )
                    logger.info(f"ChromaDB verbunden: {self.persist_directory}")
                except ImportError:
                    self.last_error = "chromadb nicht installiert"
                    logger.warning(
                        "chromadb nicht installiert. Installiere: pip install chromadb"
                    )
                    return None
                except Exception as e:
                    self.last_error = f"ChromaDB nicht verfügbar: {e}"
                    logger.warning(
                        f"ChromaDB nicht verfügbar: {e}. "
                        "Betrieb ohne Vektorspeicherung."
                    )
                    return None
        return self._client

    def _get_collection(self):
        """Lazy-Initialisierung der ChromaDB-Collection (thread-safe)."""
        if self._collection is None:
            with self._lock:
                if self._collection is not None:
                    return self._collection
                client = self._get_client()
                if client is None:
                    return None
                try:
                    self._collection = client.get_or_create_collection(
                        name=self.collection_name
                    )
                    logger.info(f"Collection '{self.collection_name}' bereit")
                except Exception as e:
                    self.last_error = f"Collection-Fehler: {e}"
                    logger.warning(f"Collection-Fehler: {e}")
                    return None
        return self._collection

    def _execute_with_retry(self, operation: str, fn, *args, **kwargs):
        """Führt fn(*args, **kwargs) mit Retry bei 'database is locked' aus.

        Exponentielles Backoff: 0.1s → 0.2s → 0.4s.
        Gibt das fn-Ergebnis zurück oder raised den letzten Fehler.
        """
        last_error = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return fn(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "database is locked" not in str(e):
                    raise
                last_error = e
                if attempt < _MAX_RETRIES:
                    backoff = _BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        "ChromaDB %s: database locked (attempt %d/%d), backoff %.2fs",
                        operation,
                        attempt,
                        _MAX_RETRIES,
                        backoff,
                    )
                    time.sleep(backoff)
        if last_error:
            raise last_error

    def add(
        self,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> bool:
        """Fügt Dokumente mit Embeddings hinzu (thread-safe mit Retry).

        Args:
            documents: Liste von Textdokumenten.
            embeddings: Liste von Embedding-Vektoren.
            metadatas: Optionale Metadaten pro Dokument.
            ids: Optionale IDs (werden automatisch generiert).

        Returns:
            True bei Erfolg, False bei Fehler (graceful degradation).
        """
        collection = self._get_collection()
        if collection is None:
            logger.warning("ChromaDB nicht verfügbar — Dokument nicht gespeichert")
            return False

        import uuid

        doc_ids = ids or [str(uuid.uuid4()) for _ in documents]
        meta = metadatas or [{}] * len(documents)

        try:
            with self._lock:
                self._execute_with_retry(
                    "add",
                    collection.add,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=meta,
                    ids=doc_ids,
                )
            logger.debug(f"{len(documents)} Dokumente zu ChromaDB hinzugefügt")
            return True
        except sqlite3.OperationalError as e:
            logger.warning(
                f"ChromaDB-Add nach {_MAX_RETRIES} Retries fehlgeschlagen: {e}"
            )
            return False
        except Exception as e:
            logger.warning(f"Fehler beim ChromaDB-Add: {e}")
            return False

    def add_one(
        self,
        document: str,
        embedding: list[float],
        metadata: dict | None = None,
        doc_id: str | None = None,
    ) -> bool:
        """Fügt ein einzelnes Dokument hinzu."""
        import uuid

        return self.add(
            documents=[document],
            embeddings=[embedding],
            metadatas=[metadata if metadata is not None else {"_source": "unknown"}],
            ids=[doc_id or str(uuid.uuid4())],
        )

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where_filter: dict | None = None,
    ) -> list[dict]:
        """Sucht ähnliche Dokumente per Embedding (ein einzelner Vektor).

        Args:
            query_embedding: Ein einzelner Embedding-Vektor für die Suche.
                Keine Batch-Queries — für mehrere Vektoren mehrfach aufrufen.
            n_results: Anzahl gewünschter Ergebnisse.
            where_filter: Optionaler ChromaDB-Metadaten-Filter (z.B.
                {"topic": "technology"}).

        Returns:
            Liste von Ergebnis-Dicts mit keys: document, metadata, distance, id.
            Leere Liste wenn ChromaDB nicht verfügbar ist (prüfe `available`-
            Property oder `last_error` für Fehlerdetails).
        """
        collection = self._get_collection()
        if collection is None:
            logger.warning(
                f"ChromaDB-Query fehlgeschlagen — nicht verfügbar: "
                f"{self.last_error or 'unbekannter Fehler'}"
            )
            return []

        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
        }
        if where_filter:
            kwargs["where"] = where_filter

        try:
            with self._lock:
                results = self._execute_with_retry("query", collection.query, **kwargs)
            output = []
            if results.get("documents"):
                for i in range(len(results["documents"][0])):
                    output.append(
                        {
                            "document": results["documents"][0][i],
                            "metadata": (
                                results["metadatas"][0][i]
                                if results.get("metadatas")
                                else {}
                            ),
                            "distance": (
                                results["distances"][0][i]
                                if results.get("distances")
                                else None
                            ),
                            "id": (results["ids"][0][i] if results.get("ids") else ""),
                        }
                    )
            return output
        except sqlite3.OperationalError as e:
            self.last_error = f"ChromaDB-Query nach Retries fehlgeschlagen: {e}"
            logger.error(f"ChromaDB-Query: database locked nach {_MAX_RETRIES} Retries")
            return []
        except Exception as e:
            self.last_error = f"ChromaDB-Query-Fehler: {e}"
            logger.error(f"Fehler bei ChromaDB-Query: {e}", exc_info=True)
            return []

    @property
    def count(self) -> int:
        """Anzahl der Dokumente in der Collection (thread-safe).

        Returns:
            Anzahl der Dokumente, oder 0 wenn ChromaDB nicht verfügbar.
        """
        collection = self._get_collection()
        if collection is None:
            return 0
        try:
            with self._lock:
                return collection.count()
        except Exception as e:
            self.last_error = f"ChromaDB-Count-Fehler: {e}"
            logger.error(f"Fehler bei ChromaDB-Count: {e}", exc_info=True)
            return 0

    def delete_collection(self):
        """Löscht die gesamte Collection (thread-safe)."""
        client = self._get_client()
        if client is None:
            return
        try:
            with self._lock:
                client.delete_collection(self.collection_name)
            self._collection = None
            logger.info(f"Collection '{self.collection_name}' gelöscht")
        except Exception as e:
            logger.warning(f"Fehler beim Löschen: {e}")

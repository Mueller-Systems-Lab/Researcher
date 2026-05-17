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
from typing import Optional

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB-Wrapper für persistente Vektorspeicherung.

    Speichert Embeddings auf Disk (kein RAM-Problem).
    Graceful Degradation: Wenn ChromaDB nicht verfügbar ist,
    werden Operationen übersprungen statt abzubrechen.
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        self.persist_directory = persist_directory or os.getenv(
            "CHROMA_PERSIST_DIRECTORY", "./chroma_db"
        )
        self.collection_name = collection_name or os.getenv(
            "CHROMA_COLLECTION", "gpt_researcher"
        )
        self._collection = None
        self._client = None

    def _get_client(self):
        """Lazy-Initialisierung des ChromaDB-Clients."""
        if self._client is None:
            try:
                import chromadb

                self._client = chromadb.PersistentClient(path=self.persist_directory)
                logger.info(f"ChromaDB verbunden: {self.persist_directory}")
            except ImportError:
                logger.warning(
                    "chromadb nicht installiert. Installiere: pip install chromadb"
                )
                return None
            except Exception as e:
                logger.warning(
                    f"ChromaDB nicht verfügbar: {e}. Betrieb ohne Vektorspeicherung."
                )
                return None
        return self._client

    def _get_collection(self):
        """Lazy-Initialisierung der ChromaDB-Collection."""
        if self._collection is None:
            client = self._get_client()
            if client is None:
                return None
            try:
                self._collection = client.get_or_create_collection(
                    name=self.collection_name
                )
                logger.info(f"Collection '{self.collection_name}' bereit")
            except Exception as e:
                logger.warning(f"Collection-Fehler: {e}")
                return None
        return self._collection

    def add(
        self,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ) -> bool:
        """Fügt Dokumente mit Embeddings hinzu.

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

        try:
            import uuid

            doc_ids = ids or [str(uuid.uuid4()) for _ in documents]
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas or [{}] * len(documents),
                ids=doc_ids,
            )
            logger.debug(f"{len(documents)} Dokumente zu ChromaDB hinzugefügt")
            return True
        except Exception as e:
            logger.warning(f"Fehler beim ChromaDB-Add: {e}")
            return False

    def add_one(
        self,
        document: str,
        embedding: list[float],
        metadata: Optional[dict] = None,
        doc_id: Optional[str] = None,
    ) -> bool:
        """Fügt ein einzelnes Dokument hinzu."""
        import uuid

        return self.add(
            documents=[document],
            embeddings=[embedding],
            metadatas=[metadata or {}],
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
            Leere Liste bei Fehler oder wenn ChromaDB nicht verfügbar.
        """
        collection = self._get_collection()
        if collection is None:
            return []

        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
        }
        if where_filter:
            kwargs["where"] = where_filter

        try:
            results = collection.query(**kwargs)
            output = []
            if results.get("documents"):
                # ChromaDB gibt pro Query-Embedding eine Ergebnisliste zurück.
                # Da wir nur EIN Embedding senden, greifen wir auf Index [0] zu.
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
        except Exception as e:
            logger.warning(f"Fehler bei ChromaDB-Query: {e}", exc_info=True)
            return []

    @property
    def count(self) -> int:
        """Anzahl der Dokumente in der Collection."""
        collection = self._get_collection()
        if collection is None:
            return 0
        try:
            return collection.count()
        except Exception:
            logger.debug("Fehler bei ChromaDB-Count", exc_info=True)
            return 0

    def delete_collection(self):
        """Löscht die gesamte Collection."""
        client = self._get_client()
        if client is None:
            return
        try:
            client.delete_collection(self.collection_name)
            self._collection = None
            logger.info(f"Collection '{self.collection_name}' gelöscht")
        except Exception as e:
            logger.warning(f"Fehler beim Löschen: {e}")

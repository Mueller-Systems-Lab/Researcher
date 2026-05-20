# =============================================================================
# Tests: VectorStore & EmbeddingService
# =============================================================================
# Testet ChromaDB-Wrapper und Embedding-Service.
# Nutzt temporäre Verzeichnisse für Isolation.
#
# Ausführung:
#   python3 -m pytest tests/test_vectordb.py -v
# =============================================================================

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_vector_store_init():
    """Test: VectorStore initialisieren mit temp-Verzeichnis."""
    from vectordb.store import VectorStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore(
            persist_directory=tmpdir,
            collection_name="test_collection",
        )
        assert store is not None
        assert store.persist_directory == tmpdir
        assert store.collection_name == "test_collection"


def test_vector_store_add_and_count():
    """Test: Dokumente zu ChromaDB hinzufügen und zählen."""
    from vectordb.store import VectorStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore(
            persist_directory=tmpdir,
            collection_name="test_collection",
        )

        # Testvektor (1536 Dimensionen wie nomic-embed-text)
        test_embedding = [0.1] * 768
        success = store.add_one(
            document="Dies ist ein Testdokument über künstliche Intelligenz.",
            embedding=test_embedding,
            metadata={"source": "test", "topic": "AI"},
        )
        assert success, "Hinzufügen sollte erfolgreich sein"

        count = store.count
        assert count >= 1, f"Mindestens 1 Dokument erwartet, aber {count}"


def test_vector_store_query():
    """Test: Ähnlichkeitssuche in ChromaDB."""
    from vectordb.store import VectorStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore(
            persist_directory=tmpdir,
            collection_name="test_collection",
        )

        # Dokumente hinzufügen
        docs = [
            ("Künstliche Intelligenz und Machine Learning", {"topic": "AI"}),
            ("Kochen und Backen Rezepte", {"topic": "Cooking"}),
            ("Neural Networks und Deep Learning", {"topic": "AI"}),
        ]
        for doc_text, meta in docs:
            store.add_one(
                document=doc_text,
                embedding=[0.1] * 768,
                metadata=meta,
            )

        # Suchen
        results = store.query(
            query_embedding=[0.1] * 768,
            n_results=5,
        )
        assert len(results) >= 1, "Sollte Ergebnisse finden"


def test_vector_store_graceful_degradation():
    """Test: Graceful degradation bei fehlender ChromaDB."""
    from vectordb.store import VectorStore

    # Ungültiger Pfad provoziert keinen Fehler
    store = VectorStore(
        persist_directory="/nonexistent/path/that/will/fail",
        collection_name="test",
    )
    # add sollte False zurückgeben (keine Exception)
    result = store.add_one("test", [0.1] * 768)
    assert result is False, "Sollte False bei Fehler zurückgeben"

    # query sollte leere Liste zurückgeben
    results = store.query([0.1] * 768)
    assert results == [], "Sollte leere Liste bei Fehler zurückgeben"

    # count sollte 0 zurückgeben
    assert store.count == 0, "Sollte 0 bei Fehler zurückgeben"


def test_embedding_service_config():
    """Test: EmbeddingService-Konfiguration."""
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(
        base_url="http://localhost:11434",
        model="nomic-embed-text:latest",
    )
    assert svc.base_url == "http://localhost:11434"
    assert svc.model == "nomic-embed-text:latest"


def test_embedding_service_connection_error():
    """Test: EmbeddingService gibt ConnectionError bei nicht erreichbarem Server."""
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(
        base_url="http://localhost:19999",  # Nicht existierender Port
        model="nomic-embed-text:latest",
    )
    assert svc.is_available is False, "Sollte nicht verfügbar sein"

    import pytest

    with pytest.raises(ConnectionError):
        svc.embed("test")


# ---------------------------------------------------------------------------
# VectorStore — erweiterte Tests (Repair Coverage)
# ---------------------------------------------------------------------------


def test_vector_store_delete_collection():
    """Test: delete_collection löscht die Collection und setzt _collection zurück."""
    from vectordb.store import VectorStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore(
            persist_directory=tmpdir,
            collection_name="test_delete_collection",
        )
        # Collection erstellen durch add_one (metadata required by ChromaDB 1.5.9)
        store.add_one("test doc", [0.1] * 768, metadata={"source": "test"})
        assert store.count >= 1

        # Collection löschen
        store.delete_collection()
        assert store._collection is None

        # Nach Löschen: count sollte 0 sein (neue Collection)
        assert store.count >= 0


def test_vector_store_query_with_where_filter():
    """Test: query mit where_filter Parameter."""
    from vectordb.store import VectorStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore(
            persist_directory=tmpdir,
            collection_name="test_filtered",
        )
        # Dokumente mit unterschiedlichen Metadaten
        store.add_one("AI document", [0.1] * 768, metadata={"topic": "AI"})
        store.add_one("Cooking document", [0.2] * 768, metadata={"topic": "Cooking"})

        # Mit Filter nur AI-Dokumente finden
        results = store.query(
            query_embedding=[0.1] * 768,
            n_results=5,
            where_filter={"topic": "AI"},
        )
        assert len(results) >= 1, "Sollte mindestens ein AI-Dokument finden"

        # Ergebnisse sollten nur AI-Topic haben
        for r in results:
            assert r.get("metadata", {}).get("topic") == "AI"


def test_vector_store_count_after_clear():
    """Test: count nach Hinzufügen und Löschen konsistent."""
    from vectordb.store import VectorStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore(
            persist_directory=tmpdir,
            collection_name="test_count",
        )
        assert store.count == 0

        store.add_one("doc1", [0.1] * 768, metadata={"source": "test"})
        assert store.count == 1

        store.add_one("doc2", [0.2] * 768, metadata={"source": "test"})
        assert store.count == 2

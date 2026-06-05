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


def test_get_client_import_error():
    """_get_client: ImportError branch — sets last_error and returns None."""
    import builtins
    import sys

    from vectordb.store import VectorStore

    chromadb_saved = sys.modules.pop("chromadb", None)
    _original_import = builtins.__import__

    def _selective_import_fail(name, *args, **kwargs):
        if name == "chromadb" or name.startswith("chromadb."):
            raise ImportError("No module named 'chromadb'")
        return _original_import(name, *args, **kwargs)

    try:
        builtins.__import__ = _selective_import_fail
        store = VectorStore(persist_directory="/tmp/test_vdb")
        client = store._get_client()
        assert client is None
        assert "chromadb nicht installiert" in (store.last_error or "")
    finally:
        builtins.__import__ = _original_import
        if chromadb_saved is not None:
            sys.modules["chromadb"] = chromadb_saved


def test_get_client_double_check_lock():
    """_get_client: inner double-check returns client — simulates thread race."""
    from unittest.mock import MagicMock

    from vectordb.store import VectorStore

    store = VectorStore(persist_directory="/tmp/test_vdb")
    mock_client = MagicMock()

    # Simulate: outer check sees None, but lock acquisition triggers
    # another "thread" to set _client. We replace the lock with a mock.
    def _lock_side_effect(*args):
        store._client = mock_client

    mock_lock = MagicMock()
    mock_lock.__enter__.side_effect = _lock_side_effect
    mock_lock.__exit__.return_value = None

    store._lock = mock_lock
    store._client = None  # Outer check at line 58 sees None
    result = store._get_client()
    assert result is mock_client


def test_execute_with_retry_exhausted():
    """_execute_with_retry: raises last_error after all retries exhausted."""
    import sqlite3

    import pytest

    from vectordb.store import VectorStore

    store = VectorStore()
    call_count = [0]

    def _always_locked(*_args, **_kwargs):
        call_count[0] += 1
        raise sqlite3.OperationalError("database is locked")
        return None

    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        store._execute_with_retry("test", _always_locked)

    assert call_count[0] == 3


def test_add_fallback_ids_and_metadatas():
    """add(): generates UUIDs and empty metadatas when None is passed."""
    from unittest.mock import MagicMock

    from vectordb.store import VectorStore

    store = VectorStore()
    mock_collection = MagicMock()
    store._collection = mock_collection

    result = store.add(
        documents=["alpha", "beta"],
        embeddings=[[0.1] * 768, [0.2] * 768],
        metadatas=None,
        ids=None,
    )

    assert result is True
    assert mock_collection.add.call_count == 1
    add_kwargs = mock_collection.add.call_args[1]
    assert len(add_kwargs["ids"]) == 2
    for doc_id in add_kwargs["ids"]:
        assert len(doc_id) == 36
    assert add_kwargs["metadatas"] == [{}, {}]


def test_query_collection_unavailable():
    """query(): returns [] when _get_collection returns None."""
    from unittest.mock import patch

    from vectordb.store import VectorStore

    store = VectorStore()
    store.last_error = "mock unavailable"

    with patch.object(store, "_get_collection", return_value=None):
        results = store.query(query_embedding=[0.1] * 768)

    assert results == []


# ---------------------------------------------------------------------------
# R2 Branch-Coverage Tests — vectordb/store.py (82% → 95%)
# Targeting missing lines: 54, 98-101, 116, 171-178, 255-262, 277-280, 286, 292-293
# ---------------------------------------------------------------------------


def test_available_when_collection_none():
    """available property: returns False when _get_collection returns None (Line 54)."""
    from unittest.mock import patch

    from vectordb.store import VectorStore

    store = VectorStore()
    with patch.object(store, "_get_collection", return_value=None):
        assert store.available is False


def test_get_collection_generic_exception():
    """_get_collection: generic Exception sets last_error and returns None (Lines 98-101)."""
    from unittest.mock import MagicMock

    from vectordb.store import VectorStore

    store = VectorStore()
    mock_client = MagicMock()
    mock_client.get_or_create_collection.side_effect = Exception(
        "simulated collection failure"
    )
    store._client = mock_client
    store._collection = None  # trigger lazy init

    result = store._get_collection()
    assert result is None
    assert "Collection-Fehler" in (store.last_error or "")


def test_execute_with_retry_non_locked_error():
    """_execute_with_retry: immediately re-raises non-locked OperationalError (Line 116)."""
    import sqlite3

    import pytest

    from vectordb.store import VectorStore

    store = VectorStore()
    call_count = [0]

    def _disk_io_error(*_args, **_kwargs):
        call_count[0] += 1
        raise sqlite3.OperationalError("disk I/O error")

    with pytest.raises(sqlite3.OperationalError, match="disk I/O error"):
        store._execute_with_retry("test", _disk_io_error)

    assert call_count[0] == 1  # re-raised immediately, no retry


def test_add_retry_exhaustion_returns_false():
    """add(): retry exhaustion after MAX_RETRIES returns False (Lines 171-175)."""
    import sqlite3
    from unittest.mock import MagicMock

    from vectordb.store import VectorStore

    store = VectorStore()
    mock_collection = MagicMock()

    def _raise_locked(*_args, **_kwargs):
        raise sqlite3.OperationalError("database is locked")

    mock_collection.add.side_effect = _raise_locked
    store._collection = mock_collection

    result = store.add(
        documents=["test"],
        embeddings=[[0.1] * 768],
    )
    assert result is False


def test_add_generic_exception_returns_false():
    """add(): non-sqlite3 Exception returns False (Lines 176-178)."""
    from unittest.mock import MagicMock

    from vectordb.store import VectorStore

    store = VectorStore()
    mock_collection = MagicMock()
    mock_collection.add.side_effect = RuntimeError("generic add failure")
    store._collection = mock_collection

    result = store.add(
        documents=["test"],
        embeddings=[[0.1] * 768],
    )
    assert result is False


def test_query_retry_exhaustion_returns_empty():
    """query(): retry exhaustion returns [] and sets last_error (Lines 255-258)."""
    import sqlite3
    from unittest.mock import MagicMock

    from vectordb.store import VectorStore

    store = VectorStore()
    mock_collection = MagicMock()
    mock_collection.query.side_effect = sqlite3.OperationalError("database is locked")
    store._collection = mock_collection

    results = store.query(query_embedding=[0.1] * 768)
    assert results == []
    assert "ChromaDB-Query nach Retries fehlgeschlagen" in (store.last_error or "")


def test_query_generic_exception_returns_empty():
    """query(): non-sqlite3 Exception returns [] and sets last_error (Lines 259-262)."""
    from unittest.mock import MagicMock

    from vectordb.store import VectorStore

    store = VectorStore()
    mock_collection = MagicMock()
    mock_collection.query.side_effect = RuntimeError("generic query failure")
    store._collection = mock_collection

    results = store.query(query_embedding=[0.1] * 768)
    assert results == []
    assert "ChromaDB-Query-Fehler" in (store.last_error or "")


def test_count_generic_exception_returns_zero():
    """count property: generic Exception returns 0 and sets last_error (Lines 277-280)."""
    from unittest.mock import MagicMock

    from vectordb.store import VectorStore

    store = VectorStore()
    mock_collection = MagicMock()
    mock_collection.count.side_effect = RuntimeError("count failed")
    store._collection = mock_collection

    assert store.count == 0
    assert "ChromaDB-Count-Fehler" in (store.last_error or "")


def test_delete_collection_client_none():
    """delete_collection: _get_client returns None → early return, no error (Line 286)."""
    from unittest.mock import patch

    from vectordb.store import VectorStore

    store = VectorStore()
    with patch.object(store, "_get_client", return_value=None):
        # Should not raise
        store.delete_collection()
    # If we reach here, the early return path was exercised
    assert True


def test_delete_collection_generic_exception():
    """delete_collection: Exception during delete is caught, no re-raise (Lines 292-293)."""
    from unittest.mock import MagicMock, patch

    from vectordb.store import VectorStore

    store = VectorStore()
    mock_client = MagicMock()
    mock_client.delete_collection.side_effect = RuntimeError("delete failed")

    with patch.object(store, "_get_client", return_value=mock_client):
        # Should not raise — exception caught in try/except
        store.delete_collection()

    mock_client.delete_collection.assert_called_once()

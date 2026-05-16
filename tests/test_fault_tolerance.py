# =============================================================================
# Tests: Fehlertoleranz
# =============================================================================
# Testet das Verhalten bei Ausfall einzelner Komponenten.
# Alle Komponenten müssen graceful degradation unterstützen.
#
# Ausführung:
#   python3 -m pytest tests/test_fault_tolerance.py -v
# =============================================================================

import sys
import os
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@patch("search.composite.requests.get")
def test_fault_searxng_down_darknet_ok(mock_get):
    """Fehlertoleranz: SearXNG down, Darknet OK → nur Darknet."""
    from search.composite import CompositeRetriever
    from darknet_search.index import WhooshIndex

    from requests.exceptions import ConnectionError

    mock_get.side_effect = ConnectionError("SearXNG not reachable")

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        idx.add_post(
            {
                "url": "http://forum.onion/post/1",
                "author": "user",
                "title": "Darknet Post",
                "timestamp": datetime.now(),
                "content": "Research findings about security topics.",
                "forum_id": "f1",
            }
        )

        old_val = os.environ.get("DARKNET_ENABLED")
        os.environ["DARKNET_ENABLED"] = "true"
        try:
            r = CompositeRetriever(
                "security",
                searx_url="http://localhost:8080",
                darknet_index_dir=tmpdir,
            )
            results = r.search(max_results=10)

            # Darknet sollte noch Ergebnisse liefern
            assert len(results) >= 1, "Darknet sollte noch Ergebnisse liefern"
            assert results[0]["source"] == "Darknet Forum"
        finally:
            if old_val is not None:
                os.environ["DARKNET_ENABLED"] = old_val
            else:
                del os.environ["DARKNET_ENABLED"]


@patch("search.composite.requests.get")
def test_fault_both_backends_down(mock_get):
    """Fehlertoleranz: Beide Backends down → leere Liste (kein Fehler)."""
    from search.composite import CompositeRetriever

    from requests.exceptions import ConnectionError

    mock_get.side_effect = ConnectionError("SearXNG not reachable")

    r = CompositeRetriever(
        "test",
        searx_url="http://localhost:8080",
        darknet_index_dir="/nonexistent",
    )
    r.darknet_enabled = True
    results = r.search(max_results=10)
    assert results == [], "Sollte leere Liste liefern"


def test_fault_vectorstore_chromadb_down():
    """Fehlertoleranz: ChromaDB nicht verfügbar."""
    from vectordb.store import VectorStore

    store = VectorStore(
        persist_directory="/nonexistent/path",
        collection_name="test",
    )
    # Keine Exception, nur graceful degradation
    assert store.add_one("test", [0.1] * 768) is False
    assert store.query([0.1] * 768) == []
    assert store.count == 0


def test_fault_embedding_ollama_down():
    """Fehlertoleranz: Ollama nicht verfügbar (Embedding)."""
    from vectordb.embedding import EmbeddingService
    import pytest

    svc = EmbeddingService(
        base_url="http://localhost:19999",
        model="nomic-embed-text:latest",
    )
    assert svc.is_available is False

    # Embedding sollte ConnectionError werfen
    with pytest.raises(ConnectionError):
        svc.embed("test")


@patch("search.composite.requests.get")
def test_fault_searxng_timeout(mock_get):
    """Fehlertoleranz: SearXNG timeout."""
    from search.composite import CompositeRetriever

    from requests.exceptions import Timeout

    mock_get.side_effect = Timeout("SearXNG timed out")

    r = CompositeRetriever(
        "test",
        searx_url="http://localhost:8080",
    )
    r.darknet_enabled = False
    results = r.search(max_results=10)
    assert isinstance(results, list)

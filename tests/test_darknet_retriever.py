# =============================================================================
# Tests: DarknetRetriever & WhooshIndex
# =============================================================================
# Testet die Index- und Such-Funktionalität des Darknet-Search-Moduls.
#
# Ausführung:
#   python -m pytest tests/test_darknet_retriever.py -v
# =============================================================================

import os
import sys
import tempfile
from datetime import datetime

# Projekt-Root zum Import-Pfad hinzufügen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_whoosh_index_create_and_search():
    """Test: Index erstellen, Post hinzufügen, suchen."""
    from darknet_search.index import WhooshIndex

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)

        # Post hinzufügen
        post = {
            "url": "http://darkforum.onion/thread/123",
            "author": "testuser",
            "title": "Test Thread",
            "timestamp": datetime.now(),
            "content": "Dies ist ein Test-Post über geheime Forschung.",
            "forum_id": "forum1",
        }
        success = idx.add_post(post)
        assert success, "Post konnte nicht indexiert werden"

        # Suchen
        results = idx.search("Test", limit=10)
        assert len(results) >= 1, "Sollte mindestens 1 Ergebnis finden"
        assert "geheime Forschung" in results[0]["content"]

        # Nach nicht-existierendem Begriff suchen
        no_results = idx.search("nichtvorhandenXYZ", limit=10)
        assert len(no_results) == 0, "Sollte keine Ergebnisse finden"


def test_whoosh_index_multiple_posts():
    """Test: Mehrere Posts indexieren und suchen."""
    from darknet_search.index import WhooshIndex

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)

        posts = [
            {
                "url": f"http://forum.onion/post/{i}",
                "author": f"user{i}",
                "title": f"Title{i}",
                "timestamp": datetime.now(),
                "content": f"Content about topic {i}",
                "forum_id": "forum1",
            }
            for i in range(10)
        ]
        count = idx.add_posts(posts)
        assert count == 10, f"Sollte 10 Posts indexieren, aber {count}"

        # Alle finden
        results = idx.search("topic", limit=20)
        assert len(results) == 10, f"Sollte 10 Treffer finden, aber {len(results)}"


def test_whoosh_index_empty_search():
    """Test: Leere Suchanfrage."""
    from darknet_search.index import WhooshIndex

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        results = idx.search("", limit=10)
        assert results == [], "Leere Suche sollte leere Liste zurückgeben"


def test_whoosh_index_stats():
    """Test: Index-Dokumentenzählung."""
    from darknet_search.index import WhooshIndex

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        assert idx.doc_count == 0, "Neuer Index sollte 0 Dokumente haben"

        post = {
            "url": "http://forum.onion/test",
            "author": "test",
            "title": "Test",
            "timestamp": datetime.now(),
            "content": "Test content",
            "forum_id": "f1",
        }
        idx.add_post(post)
        assert idx.doc_count == 1, "Nach Hinzufügen sollte 1 Dokument sein"


def test_darknet_retriever_basic():
    """Test: DarknetRetriever grundlegend."""
    from darknet_search.index import WhooshIndex
    from darknet_search.retriever import DarknetRetriever

    with tempfile.TemporaryDirectory() as tmpdir:
        # Index vorbereiten
        idx = WhooshIndex(tmpdir)
        post = {
            "url": "http://forum.onion/thread/999",
            "author": "researcher",
            "title": "Wichtige Forschung",
            "timestamp": datetime.now(),
            "content": "Hier wird über wichtige Forschungsthemen diskutiert.",
            "forum_id": "darkforum",
        }
        idx.add_post(post)

        # Retriever testen
        retriever = DarknetRetriever("Forschung", index_dir=tmpdir)
        results = retriever.search(max_results=5)

        assert len(results) >= 1, "Sollte Ergebnisse finden"
        result = results[0]
        assert "url" in result, "Ergebnis sollte URL haben"
        assert result["url"].startswith("darknet://"), (
            f"URL sollte darknet://-Präfix haben: {result['url']}"
        )


def test_darknet_uri_format():
    """Test: Synthetische darknet://-URI."""
    from darknet_search.retriever import make_darknet_uri

    uri = make_darknet_uri("forum1", "http://forum.onion/post/abc123")
    assert uri.startswith("darknet://"), "Sollte mit darknet:// beginnen"
    assert "forum1" in uri, "Sollte forum_id enthalten"
    assert len(uri) > len("darknet://forum1/post/"), "Sollte Hash enthalten"

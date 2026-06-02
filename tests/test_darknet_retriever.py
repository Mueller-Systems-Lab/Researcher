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


def test_darknet_retriever_duplicate_deduplication():
    """Duplicate URIs are silently skipped."""
    from unittest.mock import patch
    from darknet_search.retriever import DarknetRetriever

    retriever = DarknetRetriever("test", index_dir="/tmp/fake")
    fake_results = [
        {"forum_id": "f1", "url": "http://f.onion/p/1", "title": "T1", "content": "C1"},
        {"forum_id": "f1", "url": "http://f.onion/p/1", "title": "T2", "content": "C2"},
    ]
    with patch.object(retriever.index, "search", return_value=fake_results):
        results = retriever.search(max_results=5)
    assert len(results) == 1


# ── DarknetIndex coverage gap tests ─────────────────────────────────────


def test_add_post_invalid_timestamp_fallback():
    """Ungültiger Timestamp-String → Fallback auf datetime.now()."""
    from darknet_search.index import WhooshIndex
    from datetime import datetime

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        post = {
            "url": "http://forum.onion/invalid-ts",
            "author": "testuser",
            "title": "Invalid Timestamp Post",
            "timestamp": "dies-ist-kein-iso-8601-datum",
            "content": "Test content with bad timestamp.",
            "forum_id": "f1",
        }
        success = idx.add_post(post)
        assert success

        results = idx.search("bad timestamp", limit=10)
        assert len(results) == 1


def test_clear_index_happy_path():
    """Index leeren (clear) — Happy Path."""
    from darknet_search.index import WhooshIndex
    from datetime import datetime

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        posts = [
            {
                "url": f"http://forum.onion/clear-test-{i}",
                "author": "testuser",
                "title": f"Clear Test {i}",
                "timestamp": datetime.now(),
                "content": f"Content #{i}.",
                "forum_id": "f1",
            }
            for i in range(5)
        ]
        count = idx.add_posts(posts)
        assert count == 5
        assert idx.doc_count == 5

        idx.clear()
        assert idx.doc_count == 0

        results = idx.search("cleared", limit=10)
        assert results == []

        # Can re-add after clear
        idx.add_post(
            {
                "url": "http://forum.onion/after-clear",
                "author": "newuser",
                "title": "After Clear",
                "timestamp": datetime.now(),
                "content": "New post after clearing the index.",
                "forum_id": "f2",
            }
        )
        assert idx.doc_count == 1


# ---------------------------------------------------------------------------
# R2 Branch-Coverage Tests — darknet_search/index.py (84% → 95%)
# Missing lines: 104-109, 174-176, 180-188, 196-198, 206-209
# ---------------------------------------------------------------------------


def test_add_post_lock_error():
    """add_post: Whoosh LockError caught, returns False (Lines 104-106)."""
    from unittest.mock import MagicMock, patch
    from darknet_search.index import WhooshIndex
    from whoosh.index import LockError

    idx = WhooshIndex("/tmp/fake_idx")
    mock_ix = MagicMock()
    idx._ix = mock_ix

    with patch("darknet_search.index.AsyncWriter") as mock_writer:
        mock_writer.side_effect = LockError("index locked")
        result = idx.add_post({"url": "http://x.onion/test", "content": "test"})
        assert result is False


def test_add_post_generic_exception():
    """add_post: generic Exception caught, returns False (Lines 107-109)."""
    from unittest.mock import MagicMock, patch
    from darknet_search.index import WhooshIndex

    idx = WhooshIndex("/tmp/fake_idx")
    mock_ix = MagicMock()
    idx._ix = mock_ix

    with patch("darknet_search.index.AsyncWriter") as mock_writer:
        mock_writer.side_effect = RuntimeError("unexpected writer failure")
        result = idx.add_post({"url": "http://x.onion/test", "content": "test"})
        assert result is False


def test_search_generic_exception():
    """search(): generic Exception caught, returns [] (Lines 174-176)."""
    from unittest.mock import MagicMock, patch
    from darknet_search.index import WhooshIndex

    idx = WhooshIndex("/tmp/fake_idx")
    mock_ix = MagicMock()
    mock_searcher = MagicMock()
    mock_searcher.search.side_effect = RuntimeError("search crash")
    mock_ix.searcher.return_value.__enter__.return_value = mock_searcher
    idx._ix = mock_ix

    results = idx.search("test query")
    assert results == []


def test_optimize_happy_path():
    """optimize(): happy path — calls AsyncWriter.commit(optimize=True) (Lines 180-184)."""
    from unittest.mock import MagicMock, patch
    from darknet_search.index import WhooshIndex

    idx = WhooshIndex("/tmp/fake_idx")
    mock_ix = MagicMock()
    idx._ix = mock_ix

    mock_writer = MagicMock()
    with patch("darknet_search.index.AsyncWriter", return_value=mock_writer):
        idx.optimize()

    mock_writer.commit.assert_called_once_with(optimize=True)


def test_optimize_lock_error():
    """optimize(): Whoosh LockError caught, no re-raise (Lines 185-186)."""
    from unittest.mock import MagicMock, patch
    from darknet_search.index import WhooshIndex
    from whoosh.index import LockError

    idx = WhooshIndex("/tmp/fake_idx")
    mock_ix = MagicMock()
    idx._ix = mock_ix

    with patch("darknet_search.index.AsyncWriter") as mock_writer:
        mock_writer.side_effect = LockError("optimize locked")
        # Should not raise
        idx.optimize()


def test_optimize_generic_exception():
    """optimize(): generic Exception caught, no re-raise (Lines 187-188)."""
    from unittest.mock import MagicMock, patch
    from darknet_search.index import WhooshIndex

    idx = WhooshIndex("/tmp/fake_idx")
    mock_ix = MagicMock()
    idx._ix = mock_ix

    with patch("darknet_search.index.AsyncWriter") as mock_writer:
        mock_writer.side_effect = RuntimeError("optimize crash")
        # Should not raise
        idx.optimize()


def test_doc_count_generic_exception():
    """doc_count: generic Exception caught, returns 0 (Lines 196-198)."""
    from unittest.mock import MagicMock, patch
    from darknet_search.index import WhooshIndex

    idx = WhooshIndex("/tmp/fake_idx")
    mock_ix = MagicMock()
    mock_searcher = MagicMock()
    mock_searcher.doc_count.side_effect = RuntimeError("doc_count crash")
    mock_ix.searcher.return_value.__enter__.return_value = mock_searcher
    idx._ix = mock_ix

    assert idx.doc_count == 0


def test_clear_lock_error():
    """clear(): Whoosh LockError caught, no re-raise (Lines 206-207)."""
    from unittest.mock import MagicMock, patch
    from darknet_search.index import WhooshIndex
    from whoosh.index import LockError

    idx = WhooshIndex("/tmp/fake_idx")
    mock_ix = MagicMock()
    idx._ix = mock_ix

    with patch("darknet_search.index.create_in") as mock_create:
        mock_create.side_effect = LockError("clear locked")
        # Should not raise
        idx.clear()


def test_clear_generic_exception():
    """clear(): generic Exception caught, no re-raise (Lines 208-209)."""
    from unittest.mock import MagicMock, patch
    from darknet_search.index import WhooshIndex

    idx = WhooshIndex("/tmp/fake_idx")
    mock_ix = MagicMock()
    idx._ix = mock_ix

    with patch("darknet_search.index.create_in") as mock_create:
        mock_create.side_effect = RuntimeError("clear crash")
        # Should not raise
        idx.clear()

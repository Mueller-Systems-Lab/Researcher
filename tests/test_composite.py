# =============================================================================
# Tests: CompositeRetriever
# =============================================================================
# Testet parallele Suche, Deduplizierung und Fehlertoleranz.
# Mockt externe HTTP-Anfragen (SearXNG) und DarknetRetriever.
#
# Ausführung:
#   python3 -m pytest tests/test_composite.py -v
# =============================================================================

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_composite_retriever_init():
    """Test: CompositeRetriever initialisieren."""
    from search.composite import CompositeRetriever

    r = CompositeRetriever("test query")
    assert r.query == "test query"
    assert r.searx_url == "http://localhost:8080"


@patch("search.composite.create_session")
def test_composite_searxng_success(mock_create):
    """Test: SearXNG liefert Ergebnisse."""
    from search.composite import CompositeRetriever

    # Mock SearXNG response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "url": "http://example.com/1",
                "title": "Result 1",
                "content": "Content 1",
                "engine": "duckduckgo",
                "score": 0.95,
            },
            {
                "url": "http://example.com/2",
                "title": "Result 2",
                "content": "Content 2",
                "engine": "wikipedia",
                "score": 0.85,
            },
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_create.return_value = mock_session

    r = CompositeRetriever("test", searx_url="http://localhost:8080")
    results = r.search(max_results=10)

    assert len(results) >= 2, "Sollte 2+ Ergebnisse haben"
    assert results[0]["source"] == "SearXNG"
    assert results[0]["url"] == "http://example.com/1"


@patch("search.composite.create_session")
def test_composite_searxng_down(mock_create):
    """Test: SearXNG down — Fallback ohne Fehler."""
    # SearXNG nicht erreichbar
    from requests.exceptions import ConnectionError

    from search.composite import CompositeRetriever

    mock_session = MagicMock()
    mock_session.get.side_effect = ConnectionError()
    mock_create.return_value = mock_session

    r = CompositeRetriever(
        "test",
        searx_url="http://localhost:8080",
    )
    results = r.search(max_results=10)

    # Sollte trotzdem funktionieren (leere Liste von SearXNG)
    assert isinstance(results, list)


def test_composite_deduplication():
    """Test: Deduplizierung anhand URL."""
    from search.composite import CompositeRetriever

    results = [
        {"url": "http://example.com/1", "title": "A", "source": "SearXNG"},
        {"url": "http://example.com/2", "title": "B", "source": "SearXNG"},
        {"url": "http://example.com/1", "title": "A (duplicate)", "source": "Darknet"},
        {"url": "http://example.com/3", "title": "C", "source": "Darknet"},
        {"url": "", "title": "Empty URL", "source": "SearXNG"},
    ]

    deduped = CompositeRetriever._deduplicate(results)
    assert len(deduped) == 3, f"Sollte 3 eindeutige URLs haben, aber {len(deduped)}"
    # Leere URL wurde entfernt
    assert all(r["url"] for r in deduped), "Keine leeren URLs erlaubt"


def test_composite_deduplication_empty():
    """Test: Deduplizierung mit leerer Liste."""
    from search.composite import CompositeRetriever

    assert CompositeRetriever._deduplicate([]) == []


def test_composite_deduplication_no_duplicates():
    """Test: Deduplizierung ohne Duplikate ändert nichts."""
    from search.composite import CompositeRetriever

    results = [
        {"url": "http://a.com", "title": "A"},
        {"url": "http://b.com", "title": "B"},
        {"url": "http://c.com", "title": "C"},
    ]
    deduped = CompositeRetriever._deduplicate(results)
    assert len(deduped) == 3


@patch("search.composite.create_session")
def test_composite_darknet_disabled(mock_create):
    """Test: Darknet deaktiviert (DARKNET_ENABLED=false) — nur SearXNG."""
    from search.composite import CompositeRetriever

    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_create.return_value = mock_session

    r = CompositeRetriever(
        "test",
        searx_url="http://localhost:8080",
    )
    r.darknet_enabled = False
    results = r.search(max_results=10)

    # Nur SearXNG sollte befragt worden sein
    assert isinstance(results, list)


@patch("search.composite.create_session")
def test_composite_with_darknet_results(mock_create):
    """Test: Composite mit beiden Backends."""
    from datetime import datetime

    from darknet_search.index import WhooshIndex
    from search.composite import CompositeRetriever

    # SearXNG mock (keine Ergebnisse)
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_create.return_value = mock_session

    # Darknet-Index mit Testdaten befüllen
    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        idx.add_post(
            {
                "url": "http://forum.onion/thread/1",
                "author": "test",
                "title": "Darknet Research",
                "timestamp": datetime.now(),
                "content": "Important research findings from darknet forum.",
                "forum_id": "f1",
            }
        )
        idx.add_post(
            {
                "url": "http://forum.onion/thread/2",
                "author": "user2",
                "title": "Another Thread",
                "timestamp": datetime.now(),
                "content": "More findings about security topics.",
                "forum_id": "f1",
            }
        )

        # DARKNET_ENABLED für diesen Test aktivieren
        import os

        old_val = os.environ.get("DARKNET_ENABLED")
        os.environ["DARKNET_ENABLED"] = "true"

        try:
            r = CompositeRetriever(
                "findings",  # Suchbegriff, der beide Posts matched
                searx_url="http://localhost:8080",
                darknet_index_dir=tmpdir,
            )
            results = r.search(max_results=10)
            assert len(results) >= 2, (
                f"Sollte Darknet-Ergebnisse enthalten: {len(results)}"
            )
            # Ergebnisse sollten darknet://-URIs enthalten
            darknet_results = [
                res for res in results if res["source"] == "Darknet Forum"
            ]
            assert len(darknet_results) >= 2, (
                "Sollte mindestens 2 Darknet-Ergebnisse haben"
            )
            assert all(r["url"].startswith("darknet://") for r in darknet_results), (
                "Darknet-URIs sollten darknet://-Präfix haben"
            )
        finally:
            if old_val is not None:
                os.environ["DARKNET_ENABLED"] = old_val
            else:
                del os.environ["DARKNET_ENABLED"]


@patch("search.composite.create_session")
def test_composite_total_limit(mock_create):
    """Test: max_results wird eingehalten."""
    from search.composite import CompositeRetriever

    # SearXNG liefert viele Ergebnisse
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "url": f"http://example.com/{i}",
                "title": f"Result {i}",
                "content": f"Content {i}",
                "engine": "duckduckgo",
                "score": 0.5,
            }
            for i in range(20)
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_create.return_value = mock_session

    r = CompositeRetriever("test", searx_url="http://localhost:8080")
    r.darknet_enabled = False
    results = r.search(max_results=5)

    assert len(results) <= 5, f"Max 5 Ergebnisse erlaubt, aber {len(results)}"


# ── Missing-Line Coverage (lines 92, 136-143, 198-199) ───────────────────


@patch("search.composite.create_session")
def test_composite_searxng_result_without_url(mock_create):
    """SearXNG result without URL is skipped (line 92 continue)."""
    from search.composite import CompositeRetriever

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "url": "",
                "title": "No URL",
                "content": "body",
                "engine": "g",
                "score": 0.8,
            },
            {
                "url": "http://example.com/valid",
                "title": "OK",
                "content": "body",
                "engine": "g",
                "score": 0.9,
            },
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_create.return_value = mock_session

    r = CompositeRetriever("test", searx_url="http://localhost:8080")
    r.darknet_enabled = False
    results = r.search(max_results=10)

    # Only the valid URL should be returned
    assert len(results) == 1
    assert results[0]["url"] == "http://example.com/valid"


@patch("search.composite.DarknetRetriever")
@patch("search.composite.create_session")
def test_composite_darknet_search_exception(mock_create, mock_darknet_cls):
    """Darknet search raises exception → caught gracefully (lines 136-143)."""
    from search.composite import CompositeRetriever

    # SearXNG returns empty
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_create.return_value = mock_session

    # DarknetRetriever raises exception
    mock_darknet = MagicMock()
    mock_darknet.search.side_effect = RuntimeError("Index corrupted")
    mock_darknet_cls.return_value = mock_darknet

    r = CompositeRetriever(
        "test",
        searx_url="http://localhost:8080",
    )
    r.darknet_enabled = True
    results = r.search(max_results=10)

    # Should not crash; darknet results are empty
    assert isinstance(results, list)
    assert r.last_errors.get("darknet") is not None


@patch("search.composite.DarknetRetriever")
@patch("search.composite.create_session")
def test_composite_future_exception(mock_create, mock_darknet_cls):
    """Concurrent future raises non-TimeoutError → caught (lines 198-199)."""
    from search.composite import CompositeRetriever

    # SearXNG raises ConnectionError during execution (caught by _search_searxng)
    mock_session = MagicMock()
    from requests.exceptions import ConnectionError

    mock_session.get.side_effect = ConnectionError("Down")
    mock_create.return_value = mock_session

    # Darknet also raises exception to trigger the except block
    mock_darknet = MagicMock()
    mock_darknet.search.side_effect = RuntimeError("Index unavailable")
    mock_darknet_cls.return_value = mock_darknet

    r = CompositeRetriever(
        "test",
        searx_url="http://localhost:8080",
    )
    r.darknet_enabled = True
    results = r.search(max_results=10)

    # Should not crash
    assert isinstance(results, list)

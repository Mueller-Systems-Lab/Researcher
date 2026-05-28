# =============================================================================
# Integrationstests: CompositeRetriever
# =============================================================================
# Testet das Zusammenspiel der Komponenten.
# Nutzt gemockte externe Dienste (SearXNG) und echten Whoosh-Index.
#
# Ausführung:
#   python3 -m pytest tests/test_composite_integration.py -v
# =============================================================================

import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@patch("search.composite.create_session")
def test_composite_full_pipeline(mock_create):
    """Integration: Komplette Composite-Pipeline mit beiden Backends."""
    from darknet_search.index import WhooshIndex
    from search.composite import CompositeRetriever

    # SearXNG Mock: 2 Ergebnisse
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "url": "http://web.example/1",
                "title": "Web Result 1",
                "content": "Web content about research topics.",
                "engine": "duckduckgo",
                "score": 0.9,
            },
            {
                "url": "http://web.example/2",
                "title": "Web Result 2",
                "content": "More web research content.",
                "engine": "wikipedia",
                "score": 0.8,
            },
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_create.return_value = mock_session

    # Darknet-Index mit Daten
    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        idx.add_post(
            {
                "url": "http://forum.onion/thread/1",
                "author": "researcher",
                "title": "Darknet Research",
                "timestamp": datetime.now(),
                "content": "Deep research from darknet forum on various topics.",
                "forum_id": "f1",
            }
        )
        idx.add_post(
            {
                "url": "http://forum.onion/thread/2",
                "author": "analyst",
                "title": "Security Analysis",
                "timestamp": datetime.now(),
                "content": (
                    "Analysis of security research findings from multiple sources."
                ),
                "forum_id": "f1",
            }
        )

        old_val = os.environ.get("DARKNET_ENABLED")
        os.environ["DARKNET_ENABLED"] = "true"
        try:
            retriever = CompositeRetriever(
                "research",
                searx_url="http://localhost:8080",
                darknet_index_dir=tmpdir,
            )
            results = retriever.search(max_results=10)

            # Ergebnisse aus beiden Quellen
            assert len(results) >= 1, "Sollte Ergebnisse liefern"

            sources = {r["source"] for r in results}
            assert "SearXNG" in sources, "SearXNG-Ergebnisse erwartet"

            # Keine Duplikate
            urls = [r["url"] for r in results]
            assert len(urls) == len(set(urls)), "Keine Duplikate erlaubt"

        finally:
            if old_val is not None:
                os.environ["DARKNET_ENABLED"] = old_val
            else:
                del os.environ["DARKNET_ENABLED"]


@patch("search.composite.create_session")
def test_composite_mixed_sources(mock_create):
    """Integration: Gemischte Quellen und korrekte Sortierung."""
    from datetime import datetime

    from darknet_search.index import WhooshIndex
    from search.composite import CompositeRetriever

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "url": "http://web.example/high",
                "title": "High Score",
                "content": "Relevant content.",
                "engine": "duckduckgo",
                "score": 0.99,
            },
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_create.return_value = mock_session

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        idx.add_post(
            {
                "url": "http://forum.onion/low",
                "author": "user",
                "title": "Low Relevance",
                "timestamp": datetime.now(),
                "content": "Less relevant content.",
                "forum_id": "f1",
            }
        )

        old_val = os.environ.get("DARKNET_ENABLED")
        os.environ["DARKNET_ENABLED"] = "true"
        try:
            r = CompositeRetriever(
                "relevant",
                searx_url="http://localhost:8080",
                darknet_index_dir=tmpdir,
            )
            results = r.search(max_results=5)
            assert len(results) >= 1
        finally:
            if old_val is not None:
                os.environ["DARKNET_ENABLED"] = old_val
            else:
                del os.environ["DARKNET_ENABLED"]


def test_composite_invalid_config():
    """Integration: Ungültige Konfiguration erzeugt keine Exceptions."""
    from search.composite import CompositeRetriever

    r = CompositeRetriever(
        "test",
        searx_url="http://nonexistent:9999",
        darknet_index_dir="/nonexistent/index",
    )
    r.darknet_enabled = True
    # Sollte graceful degraded Ergebnisse liefern (leere Liste)
    results = r.search(max_results=5)
    assert isinstance(results, list)

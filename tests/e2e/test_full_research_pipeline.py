# =============================================================================
# E2E Test: Full Research Pipeline
# =============================================================================
# Szenario: SearXNG-Mock → Scraper → Retriever → Claim Validator → Index → Query
#
# Nutzt pytest-Fixtures, kein Hardcoding.
# Kann mit pytest -m e2e ausgeführt werden.
# =============================================================================

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_searxng_response():
    """Mock: 3 SearXNG-Suchergebnisse."""
    return {
        "results": [
            {
                "url": "https://example.com/article1",
                "title": "Climate Change Evidence 2025",
                "content": (
                    "New research confirms accelerating climate "
                    "change trends with 95% confidence."
                ),
                "engine": "google",
                "score": 0.95,
            },
            {
                "url": "https://example.org/study2",
                "title": "Renewable Energy Growth Report",
                "content": (
                    "Solar and wind energy capacity doubled in the last five years."
                ),
                "engine": "duckduckgo",
                "score": 0.88,
            },
            {
                "url": "https://example.net/analysis3",
                "title": "Carbon Emissions Analysis",
                "content": (
                    "Global carbon emissions peaked in 2024 according to new data."
                ),
                "engine": "brave",
                "score": 0.82,
            },
        ]
    }


@pytest.fixture
def temp_index_dir():
    """Temporäres Verzeichnis für den Suchindex."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = os.environ.get("DARKNET_INDEX_PATH")
        os.environ["DARKNET_INDEX_PATH"] = tmpdir
        os.environ["SEARCH_INDEX_BACKEND"] = "sqlite_fts5"
        yield tmpdir
        if old_path:
            os.environ["DARKNET_INDEX_PATH"] = old_path
        else:
            os.environ.pop("DARKNET_INDEX_PATH", None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_full_pipeline_searxng_mock(mock_searxng_response, temp_index_dir):
    """E2E: Mock SearXNG → Retriever → Claim Validator → Index → Query."""
    # 1. Mock SearXNG (Scope deckt Retriever + Claim Validator + Index ab)
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_searxng_response
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_get.return_value = mock_response

        # 2. Retriever (CompositeRetriever)
        from search.composite import CompositeRetriever

        retriever = CompositeRetriever("climate change")
        results = retriever.search(max_results=3)

        assert len(results) > 0, "Retriever sollte Ergebnisse liefern"
        assert any("climate" in r.get("title", "").lower() for r in results), (
            "Ergebnisse sollten zum Suchbegriff passen"
        )

        # 3. Claim Validator
        from mcp_tools.claim_validator import ClaimValidator

        validator = ClaimValidator()
        result = validator.run(
            {
                "claim": "Climate change is accelerating",
                "max_sources": 5,
                "search_mode": "all",
            }
        )

        assert result["success"] is True, (
            f"Claim-Validierung sollte erfolgreich sein: {result}"
        )
        assert "confidence" in result["data"], "Ergebnis sollte confidence enthalten"
        assert "sources" in result["data"], "Ergebnis sollte sources enthalten"
        assert result["data"]["source_count"] > 0, (
            "Sollte mindestens eine Quelle finden"
        )

        # 4. Index: Ergebnisse in SQLiteFTS5Adapter schreiben
        from mcp_tools.claim_index_writer import write_results_to_index

        count = write_results_to_index(result["data"]["sources"])
        assert count > 0, f"Sollte Ergebnisse indexieren: {count}"

        # 5. Index-Query: Ergebnisse wieder auslesen
        import os as _os

        from gpt_researcher.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        db_path = _os.path.join(temp_index_dir, "darknet_index.sqlite3")
        adapter = SQLiteFTS5Adapter(db_path)

        search_results = adapter.search("climate", limit=10)
        assert len(search_results) > 0, "Index sollte Ergebnisse enthalten"


@pytest.mark.e2e
def test_full_pipeline_scoring():
    """E2E: Claim Scoring mit synthetischen Daten."""
    from mcp_tools.claim_scorer import calculate_confidence

    # Simulierte Ergebnisse
    results = [
        {
            "url": "https://example.com/1",
            "title": "Test Article 1",
            "snippet": "climate change evidence confirms acceleration trends",
            "source": "web",
            "score": 0.9,
        },
        {
            "url": "https://example.com/2",
            "title": "Test Article 2",
            "snippet": "recent data supports climate change models",
            "source": "web",
            "score": 0.7,
        },
        {
            "url": "https://example.com/3",
            "title": "Test Article 3",
            "snippet": "carbon emissions decreasing",
            "source": "web",
            "score": 0.5,
        },
    ]

    confidence = calculate_confidence(results, "climate change is accelerating")
    assert confidence > 0.0, "Confidence sollte > 0 sein"
    assert confidence <= 1.0, "Confidence sollte <= 1 sein"

    # Mit mehr relevanten Quellen sollte Confidence höher sein
    more_results = results + [
        {
            "url": "https://example.com/4",
            "title": "More Evidence",
            "snippet": "climate change acceleration proven by multiple studies",
            "source": "web",
            "score": 0.85,
        },
    ]
    higher_confidence = calculate_confidence(
        more_results, "climate change is accelerating"
    )
    assert higher_confidence >= confidence, (
        "Mehr Quellen sollten höhere Confidence ergeben"
    )


@pytest.mark.e2e
def test_full_pipeline_index_roundtrip(temp_index_dir):
    """E2E: Index schreiben und lesen (Roundtrip)."""
    import os as _os

    from gpt_researcher.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

    db_path = _os.path.join(temp_index_dir, "darknet_index.sqlite3")
    adapter = SQLiteFTS5Adapter(db_path)

    # Dokumente indexieren
    docs = [
        {
            "url": "https://darknet.example/doc1",
            "author": "researcher1",
            "title": "Bitcoin Mixer Analysis",
            "content": (
                "This document analyzes Bitcoin mixing "
                "services and their effectiveness."
            ),
            "forum_id": "crypto",
        },
        {
            "url": "https://darknet.example/doc2",
            "author": "researcher2",
            "title": "Monero Privacy Features",
            "content": (
                "Monero provides stronger privacy guarantees than Bitcoin mixers."
            ),
            "forum_id": "crypto",
        },
    ]

    for doc in docs:
        assert adapter.index(doc), f"Sollte {doc['title']} indexieren"

    assert adapter.doc_count == 2, "Sollte 2 Dokumente enthalten"

    # Suchen
    results = adapter.search("Bitcoin", limit=10)
    assert len(results) > 0, "Sollte Bitcoin-Ergebnisse finden"

    # Löschen
    assert adapter.delete("https://darknet.example/doc1"), "Sollte doc1 löschen"
    assert adapter.doc_count == 1, "Sollte 1 Dokument übrig sein"

    # Clearen
    adapter.clear()
    assert adapter.doc_count == 0, "Sollte leer sein nach clear()"

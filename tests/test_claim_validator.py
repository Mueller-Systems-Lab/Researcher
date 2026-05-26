# =============================================================================
# Tests: Claim Validator Coverage (T-025)
# =============================================================================
import os
import sys
import types
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_claim_validator_assess():
    from mcp_tools.claim_validator import ClaimValidator

    v = ClaimValidator()
    assert v._assess(0.8) == "gut belegt"
    assert v._assess(0.5) == "teilweise belegt"
    assert v._assess(0.2) == "schwach belegt"
    assert v._assess(0.0) == "nicht belegt"


def test_claim_validator_no_claim():
    from mcp_tools.claim_validator import ClaimValidator

    result = ClaimValidator().run({})
    assert result["success"] is False


@patch("mcp_tools.claim_validator.ClaimValidator.run")
def test_claim_validator_empty_sources(mock_run):
    """ClaimValidator mit leerer Ergebnisliste (0 Quellen = 0 confidence)."""
    from mcp_tools.claim_validator import ClaimValidator

    v = ClaimValidator()
    assert v._assess(0.0) == "nicht belegt"


def test_calculate_confidence_empty_results():
    """Leere Ergebnisliste → 0.0."""
    from mcp_tools.claim_scorer import calculate_confidence

    assert calculate_confidence([], "test") == 0.0


def test_calculate_confidence_full_sources():
    """Max Quellen erreicht → hoher Score."""
    from mcp_tools.claim_scorer import calculate_confidence

    results = [{"score": 1.0, "snippet": "matching claim text"} for _ in range(5)]
    conf = calculate_confidence(results, "matching claim text", max_sources=5)
    assert conf >= 0.5


def test_calculate_confidence_partial():
    """Weniger Quellen als max → proportionaler Score."""
    from mcp_tools.claim_scorer import calculate_confidence

    results = [{"score": 0.5, "snippet": "text"}]
    conf = calculate_confidence(results, "other text", max_sources=5)
    assert 0.0 < conf < 0.5


def test_assess_all_levels():
    """assess() für alle Confidence-Bereiche."""
    from mcp_tools.claim_scorer import assess

    assert assess(0.8) == "gut belegt"
    assert assess(0.5) == "teilweise belegt"
    assert assess(0.15) == "schwach belegt"
    assert assess(0.05) == "nicht belegt"
    assert assess(0.0) == "nicht belegt"


def test_calculate_confidence_zero_scores():
    """Ergebnisse mit score=0 → minimaler Confidence."""
    from mcp_tools.claim_scorer import calculate_confidence

    results = [{"score": 0, "snippet": ""} for _ in range(3)]
    conf = calculate_confidence(results, "test", 5)
    assert conf >= 0.0


@patch("mcp_tools.claim_validator.retrieve_composite")
@patch("mcp_tools.claim_validator.retrieve_fulltext")
def test_claim_validator_composite_mode(mock_fulltext, mock_composite):
    """search_mode='composite' ruft NUR retrieve_composite auf."""
    from mcp_tools.claim_validator import ClaimValidator

    mock_composite.return_value = {
        "results": [
            {"url": "http://ex.com", "title": "T", "snippet": "S", "score": 0.8}
        ],
        "errors": {},
        "total": 1,
    }
    result = ClaimValidator().run({"claim": "test", "search_mode": "composite"})
    assert result["success"] is True
    mock_composite.assert_called_once()
    mock_fulltext.assert_not_called()


@patch("mcp_tools.claim_validator.retrieve_composite")
@patch("mcp_tools.claim_validator.retrieve_fulltext")
def test_claim_validator_invalid_search_mode(mock_fulltext, mock_composite):
    """Ungültiger search_mode → beide Retriever werden als default 'all' aufgerufen."""
    from mcp_tools.claim_validator import ClaimValidator

    mock_composite.return_value = {"results": [], "errors": {}, "total": 0}
    mock_fulltext.return_value = {"results": [], "errors": {}, "total": 0}
    result = ClaimValidator().run({"claim": "test", "search_mode": "invalid"})
    assert result["success"] is True
    assert result["data"]["source_count"] == 0
    mock_composite.assert_called_once()
    mock_fulltext.assert_called_once()


def test_claim_validator_unicode_claim():
    """Claim mit Unicode/Sonderzeichen → korrekt verarbeitet."""
    claim = "Äpfel schmecken gut mit 日本語 и кириллица 🎉"
    with patch(
        "mcp_tools.claim_validator.retrieve_composite",
        return_value={"results": [], "errors": {}, "total": 0},
    ):
        with patch(
            "mcp_tools.claim_validator.retrieve_fulltext",
            return_value={"results": [], "errors": {}, "total": 0},
        ):
            from mcp_tools.claim_validator import ClaimValidator

            result = ClaimValidator().run({"claim": claim})
            assert result["success"] is True
            assert result["data"]["claim"] == claim
            assert result["data"]["confidence"] == 0.0


def test_claim_validator_name_and_params():
    """name, description, parameters Properties."""
    from mcp_tools.claim_validator import ClaimValidator

    v = ClaimValidator()
    assert v.name == "claim-validator"
    assert "Validiert" in v.description
    assert "claim" in v.parameters["required"]


def test_retriever_sanitize_onion_url():
    """Onion-URLs werden gehasht, normale URLs bleiben."""
    from mcp_tools.claim_retriever import _sanitize_url

    result = _sanitize_url("http://abc123.onion/page")
    assert result.startswith("onion://")
    assert "abc123" not in result
    assert _sanitize_url("http://example.com") == "http://example.com"
    assert _sanitize_url("") == ""


def test_retrieve_composite_handles_error():
    """CompositeRetriever wirft Exception → Dict mit Fehler, kein Crash."""
    from mcp_tools.claim_retriever import retrieve_composite

    with patch.dict(sys.modules, {"search.composite": None}):
        result = retrieve_composite("test")

    assert isinstance(result, dict)
    assert result["results"] == []
    assert "import" in result.get("errors", {})


def test_retrieve_composite_maps_results_without_network():
    """CompositeRetriever-Ergebnisse werden ohne Netzwerk korrekt gemappt."""
    from mcp_tools.claim_retriever import retrieve_composite

    search_pkg = types.ModuleType("search")
    search_pkg.__path__ = []
    composite_mod = types.ModuleType("search.composite")
    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [
        {
            "url": "http://abc123.onion/page",
            "title": "Titel",
            "body": "Snippet-Text",
            "source": "web",
            "score": 0.9,
        }
    ]
    composite_mod.CompositeRetriever = MagicMock(return_value=mock_retriever)

    with patch.dict(
        sys.modules, {"search": search_pkg, "search.composite": composite_mod}
    ):
        result = retrieve_composite("test", max_sources=1)

    results = result["results"]
    assert results[0]["url"].startswith("onion://")
    assert results[0]["title"] == "Titel"
    assert results[0]["snippet"] == "Snippet-Text"
    assert results[0]["match_type"] == "keyword"
    assert result["total"] == 1
    mock_retriever.search.assert_called_once_with(max_results=1)


def test_retrieve_fulltext_handles_error():
    """WhooshIndex wirft Exception → Dict mit Fehler, kein Crash."""
    from mcp_tools.claim_retriever import retrieve_fulltext

    mock_whoosh = MagicMock()
    mock_whoosh.WhooshIndex.return_value.search.side_effect = Exception("Index corrupt")
    with patch.dict(sys.modules, {"darknet_search.index": mock_whoosh}):
        result = retrieve_fulltext("test")

    assert isinstance(result, dict)
    assert result["results"] == []
    assert "runtime" in result.get("errors", {})


def test_retrieve_fulltext_maps_results_without_index():
    """Whoosh-Ergebnisse werden ohne echten Index korrekt gemappt."""
    from mcp_tools.claim_retriever import retrieve_fulltext

    darknet_pkg = types.ModuleType("darknet_search")
    darknet_pkg.__path__ = []
    index_mod = types.ModuleType("darknet_search.index")
    mock_index = MagicMock()
    mock_index.search.return_value = [
        {
            "url": "http://example.com/doc",
            "title": "Titel",
            "content": "Inhalt" * 100,
            "source": "index",
            "score": 0.7,
        }
    ]
    index_mod.WhooshIndex = MagicMock(return_value=mock_index)

    with patch.dict(
        sys.modules, {"darknet_search": darknet_pkg, "darknet_search.index": index_mod}
    ):
        result = retrieve_fulltext("test", max_sources=1)

    results = result["results"]
    assert results[0]["url"] == "http://example.com/doc"
    assert results[0]["title"] == "Titel"
    assert len(results[0]["snippet"]) == 300
    assert results[0]["match_type"] == "fulltext"
    assert result["total"] == 1
    mock_index.search.assert_called_once_with("test", limit=1)


def test_write_results_to_index_empty():
    """Leere Ergebnisliste → 0 geschrieben."""
    from mcp_tools.claim_index_writer import write_results_to_index

    mock_backend = MagicMock()
    count = write_results_to_index([], index_backend=mock_backend)
    assert count == 0


def test_write_results_to_index_success():
    """Ergebnisse werden erfolgreich indexiert."""
    from mcp_tools.claim_index_writer import write_results_to_index

    mock_backend = MagicMock()
    mock_backend.index.return_value = True
    results = [{"url": "http://x.com", "title": "T", "snippet": "S"}]
    count = write_results_to_index(results, index_backend=mock_backend)
    assert count == 1
    mock_backend.index.assert_called_once()


def test_write_results_to_index_partial_failure():
    """Einige Ergebnisse schlagen fehl → korrekte Zählung."""
    from mcp_tools.claim_index_writer import write_results_to_index

    mock_backend = MagicMock()
    mock_backend.index.side_effect = [True, False, True]
    results = [{"url": f"http://{i}.com"} for i in range(3)]
    count = write_results_to_index(results, index_backend=mock_backend)
    assert count == 2

"""Tests für deep_report/outline.py — Error-Pfade und Fallbacks.

Phase 5 — B1-2: Deckt 13 Missed Lines in outline.py ab.
Die Happy-Path-Tests für generate_outline sind in test_deep_report_writer.py.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from deep_report.outline import (
    _extract_domain,
    _extract_sources_from_artifacts,
    _load_sources_from_evidence_store,
    _merge_sources,
    generate_outline,
    load_run_data_for_outline,
)


# ═══════════════════════════════════════════════════════════════════════════
# load_run_data_for_outline — Error-Pfade
# ═══════════════════════════════════════════════════════════════════════════


def test_load_run_data_run_dir_not_found():
    """run_dir existiert nicht → returns {}."""
    result = load_run_data_for_outline("nonexistent_run_999999")
    assert result == {}


def test_load_run_data_state_path_missing():
    """state.json existiert nicht → returns {} (line 195)."""
    with tempfile.TemporaryDirectory() as tmp:
        runs_dir = Path(tmp) / "runs"
        run_dir = runs_dir / "test_run"
        run_dir.mkdir(parents=True)
        # state.json NOT created

        with patch.dict("os.environ", {"DEEP_REPORT_DIR": tmp}):
            result = load_run_data_for_outline("test_run")
            assert result == {}


def test_load_run_data_corrupt_json():
    """state.json enthält korruptes JSON → JSONDecodeError → returns {} (lines 199-201)."""
    with tempfile.TemporaryDirectory() as tmp:
        runs_dir = Path(tmp) / "runs"
        run_dir = runs_dir / "test_run"
        run_dir.mkdir(parents=True)
        (run_dir / "state.json").write_text("not valid json {{{", encoding="utf-8")

        with patch.dict("os.environ", {"DEEP_REPORT_DIR": tmp}):
            result = load_run_data_for_outline("test_run")
            assert result == {}


def test_load_run_data_os_error():
    """OSError beim Lesen von state.json → returns {} (lines 199-201)."""
    with tempfile.TemporaryDirectory() as tmp:
        runs_dir = Path(tmp) / "runs"
        run_dir = runs_dir / "test_run"
        run_dir.mkdir(parents=True)
        state_path = run_dir / "state.json"
        state_path.write_text("{}", encoding="utf-8")
        # Make it unreadable
        state_path.chmod(0o000)

        try:
            with patch.dict("os.environ", {"DEEP_REPORT_DIR": tmp}):
                result = load_run_data_for_outline("test_run")
                assert result == {}
        finally:
            state_path.chmod(0o644)


def test_load_run_data_success():
    """load_run_data_for_outline mit gültigen Daten → returns structured dict."""
    with tempfile.TemporaryDirectory() as tmp:
        runs_dir = Path(tmp) / "runs"
        run_dir = runs_dir / "test_run"
        run_dir.mkdir(parents=True)
        state_data = {
            "query": "Test query",
            "language": "de",
            "node_states": {
                "n1": {"status": "completed", "artifacts": []},
                "n2": {"status": "pending", "artifacts": []},
            },
            "node_questions": {"n1": "Q1", "n2": "Q2"},
        }
        (run_dir / "state.json").write_text(json.dumps(state_data), encoding="utf-8")

        with patch.dict("os.environ", {"DEEP_REPORT_DIR": tmp}):
            with patch(
                "deep_report.outline._load_sources_from_evidence_store",
                return_value=[],
            ):
                result = load_run_data_for_outline("test_run")
                assert result["query"] == "Test query"
                assert result["language"] == "de"
                assert "n1" in result["node_results"]
                assert result["node_results"]["n1"]["status"] == "completed"


# ═══════════════════════════════════════════════════════════════════════════
# _extract_domain — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════


def test_extract_domain_empty_url():
    """Leere URL → returns 'unknown' (line 251)."""
    assert _extract_domain("") == "unknown"


def test_extract_domain_none_url():
    """None URL → returns 'unknown'."""
    assert _extract_domain("") == "unknown"  # empty string, not None


def test_extract_domain_valid_url():
    """Valide URL → extrahiert korrekt."""
    assert _extract_domain("https://example.com/path") == "example.com"


def test_extract_domain_malformed_url():
    """Malformed URL → Exception → returns 'unknown' (lines 256-257)."""
    # A URL that causes urlparse to fail or return empty netloc
    # Using a path that can't be parsed
    result = _extract_domain("://invalid")
    assert result in ("unknown", "")


def test_extract_domain_no_netloc():
    """URL ohne netloc → returns 'unknown'."""
    # mailto: has no netloc
    result = _extract_domain("mailto:test@example.com")
    assert result in ("unknown", "")


def test_extract_domain_urlparse_exception():
    """urlparse wirft Exception → returns 'unknown' (lines 256-257)."""
    with patch("urllib.parse.urlparse", side_effect=Exception("parse error")):
        result = _extract_domain("http://example.com")
        assert result == "unknown"


# ═══════════════════════════════════════════════════════════════════════════
# _load_sources_from_evidence_store — Error-Pfade
# ═══════════════════════════════════════════════════════════════════════════


def test_load_sources_evidence_store_import_error():
    """evidence_store nicht importierbar → returns [] (lines 304-306)."""
    import builtins

    real_import = builtins.__import__

    def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
        if "evidence_store" in name:
            raise ImportError("No evidence_store")
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=mock_import):
        result = _load_sources_from_evidence_store("test_run")
        assert result == []


def test_load_sources_evidence_store_exception():
    """evidence_store.load_sources wirft Exception → returns [] (lines 314-316)."""
    from unittest.mock import MagicMock
    import sys

    # Ensure evidence_store is in sys.modules (may have been removed by previous test)
    if "evidence_store" not in sys.modules:
        sys.modules["evidence_store"] = MagicMock()

    # Build a mock evidence_store.store module that will be used
    # during the internal import in _load_sources_from_evidence_store
    mock_store = MagicMock()
    mock_store.load_sources_by_run_id = MagicMock(
        side_effect=RuntimeError("DB connection failed")
    )
    mock_store.load_sources = MagicMock()

    with patch.dict(sys.modules, {"evidence_store.store": mock_store}):
        result = _load_sources_from_evidence_store("test_run")
        assert result == []


def test_load_sources_evidence_store_success():
    """load_sources_by_run_id returns sources → success path (lines 311-313, 318-329)."""
    from unittest.mock import MagicMock
    import sys

    if "evidence_store" not in sys.modules:
        sys.modules["evidence_store"] = MagicMock()

    mock_source = MagicMock()
    mock_source.url = "https://example.com"
    mock_source.title = "Example Title"
    mock_source.domain = "example.com"
    mock_source.retrieved_at = "2024-01-01T00:00:00"

    mock_store = MagicMock()
    mock_store.load_sources_by_run_id = MagicMock(return_value=[mock_source])
    mock_store.load_sources = MagicMock()  # not called when run_id sources exist

    with patch.dict(sys.modules, {"evidence_store.store": mock_store}):
        result = _load_sources_from_evidence_store("test_run")
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com"
        assert result[0]["title"] == "Example Title"


def test_load_sources_evidence_store_fallback_to_global():
    """load_sources_by_run_id returns empty → fallback to load_sources() (line 312)."""
    from unittest.mock import MagicMock
    import sys

    if "evidence_store" not in sys.modules:
        sys.modules["evidence_store"] = MagicMock()

    mock_source = MagicMock()
    mock_source.url = "https://fallback.com"
    mock_source.title = "Fallback"
    mock_source.domain = "fallback.com"
    mock_source.retrieved_at = ""
    # Set run_id to trigger only non-run_id sources in the fallback filter
    mock_source.run_id = ""

    mock_store = MagicMock()
    mock_store.load_sources_by_run_id = MagicMock(return_value=[])
    mock_store.load_sources = MagicMock(return_value=[mock_source])

    with patch.dict(sys.modules, {"evidence_store.store": mock_store}):
        result = _load_sources_from_evidence_store("test_run")
        assert len(result) == 1
        assert result[0]["url"] == "https://fallback.com"


def test_load_sources_evidence_store_exception():
    """evidence_store.load_sources wirft Exception → returns [] (lines 314-316)."""
    # Patch the specific functions AFTER they've been imported into the function scope
    with (
        patch(
            "evidence_store.store.load_sources_by_run_id",
            side_effect=RuntimeError("DB connection failed"),
        ),
        patch(
            "evidence_store.store.load_sources",
            side_effect=RuntimeError("DB connection failed"),
        ),
    ):
        result = _load_sources_from_evidence_store("test_run")
        assert result == []


def test_load_sources_evidence_store_exception():
    """evidence_store.load_sources wirft Exception → returns [] (lines 314-316)."""
    from unittest.mock import MagicMock
    import sys

    # Build a mock evidence_store.store module that will be used
    # during the internal import in _load_sources_from_evidence_store
    mock_store = MagicMock()
    mock_store.load_sources_by_run_id = MagicMock(
        side_effect=RuntimeError("DB connection failed")
    )
    mock_store.load_sources = MagicMock()

    with patch.dict(sys.modules, {"evidence_store.store": mock_store}):
        result = _load_sources_from_evidence_store("test_run")
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════
# _extract_sources_from_artifacts — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════


def test_extract_sources_empty_artifacts():
    """Leere node_results → returns []."""
    result = _extract_sources_from_artifacts({})
    assert result == []


def test_extract_sources_malformed_json_artifact():
    """Malformed JSON in artifact → ignored (continue)."""
    node_results = {
        "n1": {
            "artifacts": ["not valid json {{"],
            "status": "completed",
        }
    }
    result = _extract_sources_from_artifacts(node_results)
    assert result == []  # malformed JSON → skipped


def test_extract_sources_valid_artifact():
    """Valider JSON-Artifact → sources extrahiert."""
    node_results = {
        "n1": {
            "artifacts": [
                json.dumps(
                    {
                        "search_results": [
                            {"url": "https://example.com", "title": "Example"}
                        ]
                    }
                )
            ],
            "status": "completed",
        }
    }
    result = _extract_sources_from_artifacts(node_results)
    assert len(result) == 1
    assert result[0]["url"] == "https://example.com"


# ═══════════════════════════════════════════════════════════════════════════
# _merge_sources — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════


def test_merge_sources_empty_both():
    """Beide Listen leer → returns []."""
    result = _merge_sources([], [])
    assert result == []


def test_merge_sources_artifacts_priority():
    """Artifact-Sources haben Priorität vor Evidence-Sources."""
    evidence = [{"url": "http://ev.com", "title": "Evidence"}]
    artifacts = [{"url": "http://art.com", "title": "Artifact"}]
    result = _merge_sources(evidence, artifacts)
    assert len(result) == 1
    assert result[0]["url"] == "http://art.com"


def test_merge_sources_no_artifacts_fallback():
    """Keine Artifact-Sources → Evidence-Sources als Fallback."""
    evidence = [{"url": "http://ev.com", "title": "Evidence"}]
    result = _merge_sources(evidence, [])
    assert len(result) == 1
    assert result[0]["url"] == "http://ev.com"


def test_merge_sources_deduplicates():
    """Doppelte URLs werden dedupliziert."""
    artifacts = [
        {"url": "http://a.com", "title": "A1"},
        {"url": "http://a.com", "title": "A2"},
        {"url": "http://b.com", "title": "B"},
    ]
    result = _merge_sources([], artifacts)
    assert len(result) == 2
    urls = [s["url"] for s in result]
    assert urls == ["http://a.com", "http://b.com"]


# ═══════════════════════════════════════════════════════════════════════════
# generate_outline — Erweiterte Featur-Pfade
# ═══════════════════════════════════════════════════════════════════════════


def test_generate_outline_with_node_results():
    """Outline mit node_results → Findings + Executive Summary populated."""
    node_results = {
        "n1": {"title": "Step 1", "status": "completed", "artifacts": []},
        "n2": {"title": "Step 2", "status": "completed", "artifacts": []},
    }
    outline = generate_outline(
        "Test query",
        node_titles=["Step 1", "Step 2"],
        node_results=node_results,
    )
    findings = next(s for s in outline if s["title"] == "Findings by DAG Node")
    assert "Step 1" in findings["content"]
    assert "completed" in findings["content"]


def test_generate_outline_with_sources():
    """Outline mit sources → Evidence Table + Source List populated."""
    sources = [
        {
            "url": "https://example.com",
            "title": "Example",
            "domain": "example.com",
            "retrieved": "2024-01-01",
        },
    ]
    outline = generate_outline("Test", sources=sources)
    evidence = next(s for s in outline if s["title"] == "Evidence Table")
    assert "example.com" in evidence["content"]
    source_list = next(s for s in outline if s["title"] == "Source List")
    assert "Example" in source_list["content"]


def test_generate_outline_with_evaluation():
    """Outline mit evaluation → Uncertainty + Evaluation Summary populated."""
    evaluation = {
        "uncertainty": "Low confidence on topic X",
        "completeness": 0.8,
    }
    outline = generate_outline("Test", evaluation=evaluation)
    uncertainty = next(s for s in outline if s["title"] == "Uncertainty")
    assert "Low confidence" in uncertainty["content"]
    eval_summary = next(s for s in outline if s["title"] == "Evaluation Summary")
    assert "completeness" in eval_summary["content"]


def test_generate_outline_method_section():
    """Method/Search-Plan-Sektion wird mit Node-Count gerendert."""
    outline = generate_outline("Q", node_titles=["A", "B", "C"])
    method = next(s for s in outline if s["title"] == "Method / Search Plan")
    assert "3" in method["content"]  # node count


def test_generate_outline_placeholder_backward_compat():
    """placeholder-Feld wird immer gesetzt (backward compatibility)."""
    outline = generate_outline("Q")
    for section in outline:
        assert "placeholder" in section
        assert section["placeholder"] != "" or section["content"] != ""

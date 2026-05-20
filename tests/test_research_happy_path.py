"""Tests für Research-Happy-Path (gemockt, keine echten Dienste)."""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── check_cloud_blocker ───────────────────────────────────────────────────────


def test_cloud_blocker_clean():
    from scripts.research_happy_path import check_cloud_blocker

    with patch.dict(os.environ, {}, clear=True):
        assert check_cloud_blocker() is True


def test_cloud_blocker_allow_cloud_active():
    from scripts.research_happy_path import check_cloud_blocker

    with patch.dict(os.environ, {"ALLOW_CLOUD": "true"}):
        assert check_cloud_blocker() is False


def test_cloud_blocker_openai_active():
    from scripts.research_happy_path import check_cloud_blocker

    with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True):
        assert check_cloud_blocker() is False


# ── is_safe_query ─────────────────────────────────────────────────────────────


def test_safe_query_ok():
    from scripts.research_happy_path import is_safe_query

    assert is_safe_query("What is a search engine?") is True
    assert is_safe_query("How does local search work?") is True


def test_safe_query_blocked():
    from scripts.research_happy_path import is_safe_query

    assert is_safe_query("exploit database search") is False
    assert is_safe_query("Find CVE-2024 vulnerabilities") is False
    assert is_safe_query("malware analysis tools") is False
    assert is_safe_query("target.com credentials") is False


# ── search_searxng ────────────────────────────────────────────────────────────


def test_search_searxng_success():
    from scripts.research_happy_path import search_searxng

    with patch("scripts.research_happy_path.requests.get") as mock_get:
        mock_r = MagicMock()
        mock_r.json.return_value = {
            "results": [
                {"title": "Result 1", "url": "http://ex.com/1", "content": "abc"},
                {"title": "Result 2", "url": "http://ex.com/2", "content": "def"},
            ]
        }
        mock_r.status_code = 200
        mock_get.return_value = mock_r

        results = search_searxng("test")
        assert len(results) == 2
        assert results[0]["title"] == "Result 1"


def test_search_searxng_connection_error():
    import requests

    from scripts.research_happy_path import search_searxng

    with patch("scripts.research_happy_path.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError()
        assert search_searxng("test") == []


# ── summarize_with_ollama ─────────────────────────────────────────────────────


def test_summarize_success():
    from scripts.research_happy_path import summarize_with_ollama

    with patch("scripts.research_happy_path.requests.post") as mock_post:
        mock_r = MagicMock()
        mock_r.json.return_value = {"response": "This is a summary."}
        mock_r.status_code = 200
        mock_post.return_value = mock_r

        result = summarize_with_ollama(
            "test", [{"title": "S", "content": "C"}], "test-model"
        )
        assert "This is a summary" in result


def test_summarize_no_sources():
    from scripts.research_happy_path import summarize_with_ollama

    result = summarize_with_ollama("test", [], "")
    assert "Keine Quellen" in result


def test_summarize_connection_error():
    import requests

    from scripts.research_happy_path import summarize_with_ollama

    with patch("scripts.research_happy_path.requests.post") as mock_post:
        mock_post.side_effect = requests.ConnectionError()
        result = summarize_with_ollama(
            "test", [{"title": "S", "content": "C"}], "test-model"
        )
        assert "not available" in result


# ── write_report ──────────────────────────────────────────────────────────────


def test_write_report_creates_file():
    from scripts.research_happy_path import write_report

    sources = [
        {"title": "Test Source", "url": "http://example.com", "content": "content"}
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        filename = write_report("test query", sources, "A summary.", tmpdir)
        assert os.path.exists(filename)
        with open(filename) as f:
            content = f.read()
            assert "test query" in content
            assert "A summary" in content
            assert "Test Source" in content

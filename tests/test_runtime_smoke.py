"""Unit-Tests für Runtime-Smoke-Test (gemockt, keine echten Dienste)."""

import os
import sys
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── check_ollama ──────────────────────────────────────────────────────────────


def test_ollama_available():
    from config.ollama_models import load_ollama_model_config
    from scripts.runtime_smoke import check_ollama

    chat_model = load_ollama_model_config().chat_model

    with patch("scripts.runtime_smoke.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "nomic-embed-text:latest"},
                {"name": chat_model},
            ]
        }
        mock_get.return_value = mock_response

        assert check_ollama() is True


def test_ollama_unreachable():
    from scripts.runtime_smoke import check_ollama

    with patch("scripts.runtime_smoke.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError()

        assert check_ollama() is False


def test_ollama_missing_model():
    from scripts.runtime_smoke import check_ollama

    with patch("scripts.runtime_smoke.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "other-model"}]}
        mock_get.return_value = mock_response

        assert check_ollama() is False


# ── check_searxng ─────────────────────────────────────────────────────────────


def test_searxng_available():
    from scripts.runtime_smoke import check_searxng

    with patch("scripts.runtime_smoke.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"title": "test"}]}
        mock_get.return_value = mock_response

        assert check_searxng() is True


def test_searxng_unreachable():
    from scripts.runtime_smoke import check_searxng

    with patch("scripts.runtime_smoke.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError()

        assert check_searxng() is False


def test_searxng_no_results():
    from scripts.runtime_smoke import check_searxng

    with patch("scripts.runtime_smoke.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        assert check_searxng() is False


def test_searxng_bad_json():
    """SearXNG returns 200 but invalid JSON."""
    from scripts.runtime_smoke import check_searxng

    with patch("scripts.runtime_smoke.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("bad json")
        mock_get.return_value = mock_response

        assert check_searxng() is False


def test_searxng_bad_status():
    """SearXNG returns HTTP 500."""
    from scripts.runtime_smoke import check_searxng

    with patch("scripts.runtime_smoke.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        assert check_searxng() is False


def test_searxng_timeout():
    """SearXNG timeout simulation."""
    from scripts.runtime_smoke import check_searxng

    with patch("scripts.runtime_smoke.requests.get") as mock_get:
        mock_get.side_effect = requests.Timeout()

        assert check_searxng() is False


# ── check_tor ─────────────────────────────────────────────────────────────────


def test_tor_available():
    from scripts.runtime_smoke import check_tor

    with patch("scripts.runtime_smoke.socket.socket") as mock_socket:
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock

        assert check_tor() is True


def test_tor_unreachable():
    from scripts.runtime_smoke import check_tor

    with patch("scripts.runtime_smoke.socket.socket") as mock_socket:
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 1
        mock_socket.return_value = mock_sock

        assert check_tor() is False


# ── check_cloud_blocker ───────────────────────────────────────────────────────


def test_cloud_blocker_clean():
    from scripts.runtime_smoke import check_cloud_blocker

    with patch.dict(os.environ, {}, clear=True):
        assert check_cloud_blocker() is True


def test_cloud_blocker_allowed():
    from scripts.runtime_smoke import check_cloud_blocker

    with patch.dict(os.environ, {"ALLOW_CLOUD": "true", "LLM_PROVIDER": "openai"}):
        assert check_cloud_blocker() is True


def test_cloud_blocker_violation():
    from scripts.runtime_smoke import check_cloud_blocker

    with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True):
        assert check_cloud_blocker() is False


# ── _is_strict ────────────────────────────────────────────────────────────────


def test_is_strict_false_default():
    from scripts.runtime_smoke import _is_strict

    with patch.dict(os.environ, {}, clear=True):
        assert _is_strict("ollama") is False


def test_is_strict_true():
    from scripts.runtime_smoke import _is_strict

    with patch.dict(os.environ, {"REQUIRE_OLLAMA": "true"}):
        assert _is_strict("ollama") is True


def test_is_strict_true_yes():
    from scripts.runtime_smoke import _is_strict

    with patch.dict(os.environ, {"REQUIRE_SEARXNG": "yes"}):
        assert _is_strict("searxng") is True

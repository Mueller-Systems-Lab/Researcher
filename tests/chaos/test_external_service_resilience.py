"""Resilience-Tests für externe Dienst-Abhängigkeiten — Ollama, SearXNG, Tor, ChromaDB."""

import json
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


@pytest.mark.resilience
class TestOllamaResilience:
    """Ollama-Ausfall-Szenarien."""

    @pytest.mark.parametrize(
        "error,expected_exception",
        [
            (requests.exceptions.ConnectionError("refused"), ConnectionError),
            (requests.exceptions.Timeout("timeout"), ValueError),
        ],
    )
    @patch("vectordb.embedding.requests.post")
    def test_ollama_connection_errors_handled(
        self, mock_post, error, expected_exception
    ):
        """ConnectionRefused und Timeout werden als kontrollierte Exceptions behandelt."""
        from vectordb.embedding import EmbeddingService

        mock_post.side_effect = error
        svc = EmbeddingService(base_url="http://ollama.invalid")

        with pytest.raises(expected_exception):
            svc.embed("test")

    @patch("vectordb.embedding.requests.post")
    def test_ollama_invalid_json_response(self, mock_post):
        """Ollama liefert malformed JSON → kontrollierter ValueError statt Crash."""
        from vectordb.embedding import EmbeddingService

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.side_effect = json.JSONDecodeError("bad json", "<html>", 0)
        mock_post.return_value = response

        svc = EmbeddingService(base_url="http://ollama.invalid")

        with pytest.raises(ValueError, match="Embedding-Fehler"):
            svc.embed("test")

    @patch("vectordb.embedding.requests.post")
    def test_ollama_503_service_unavailable(self, mock_post):
        """Ollama 503 → kontrollierte Degradation als ValueError."""
        from vectordb.embedding import EmbeddingService

        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError(
            "503 Service Unavailable"
        )
        mock_post.return_value = response

        svc = EmbeddingService(base_url="http://ollama.invalid")

        with pytest.raises(ValueError, match="Embedding-Fehler"):
            svc.embed("test")


@pytest.mark.resilience
class TestSearXNGResilience:
    """SearXNG-Degradations-Szenarien."""

    @patch("search.composite.create_session")
    def test_searxng_rate_limited_429(self, mock_create):
        """SearXNG liefert 429 → leere Ergebnisse, kein Fehler."""
        from search.composite import CompositeRetriever

        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError(
            "429 Too Many Requests"
        )
        mock_session = MagicMock()
        mock_session.get.return_value = response
        mock_create.return_value = mock_session

        r = CompositeRetriever("test")
        r.darknet_enabled = False

        assert r.search(max_results=10) == []

    @pytest.mark.xfail(
        reason="ValueError aus response.json() wird derzeit nicht abgefangen."
    )
    @patch("search.composite.create_session")
    def test_searxng_malformed_html_response(self, mock_create):
        """SearXNG liefert HTML statt JSON → parst leere Ergebnisse."""
        from search.composite import CompositeRetriever

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("HTML statt JSON")
        mock_session = MagicMock()
        mock_session.get.return_value = response
        mock_create.return_value = mock_session

        r = CompositeRetriever("test")
        r.darknet_enabled = False

        assert r.search(max_results=10) == []

    @patch("search.composite.create_session")
    def test_searxng_empty_results_field(self, mock_create):
        """SearXNG JSON ohne 'results'-Key → kein KeyError."""
        from search.composite import CompositeRetriever

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"query": "test"}
        mock_session = MagicMock()
        mock_session.get.return_value = response
        mock_create.return_value = mock_session

        r = CompositeRetriever("test")
        r.darknet_enabled = False

        assert r.search(max_results=10) == []


@pytest.mark.resilience
class TestTorProxyResilience:
    """Tor-Proxy-Ausfall-Szenarien."""

    @patch("onion_discovery.engine.DiscoveryPipeline.enabled", return_value=True)
    def test_tor_socks5_connection_errors_handled(self, _enabled):
        """SOCKS5-Fehler und Timeout → Proxy gesetzt, Fehler vom Run abgefangen."""
        from onion_discovery.engine import DiscoveryPipeline
        from onion_discovery.seed_queue import SeedEntry

        seed_queue = MagicMock()
        seed_queue.get_next.side_effect = [
            SeedEntry(url="http://exampleaaaaaaaaaaaaaaaa.onion"),
            SeedEntry(url="http://examplebbbbbbbbbbbbbbbb.onion"),
        ]
        policy = MagicMock()
        policy.is_allowed.return_value.allowed = True

        pipeline = DiscoveryPipeline(
            seed_queue=seed_queue,
            policy_gateway=policy,
            max_pages_per_run=2,
            tor_proxy="socks5h://127.0.0.1:9050",
        )
        pipeline._session.get = MagicMock(
            side_effect=[
                requests.exceptions.ConnectionError("SOCKS refused"),
                requests.exceptions.Timeout("Tor timeout"),
            ]
        )

        stats = pipeline.run_once()

        assert pipeline._session.proxies == {
            "http": "socks5h://127.0.0.1:9050",
            "https": "socks5h://127.0.0.1:9050",
        }
        assert stats["errors"] == 2
        assert seed_queue.mark_error.call_count == 2


@pytest.mark.resilience
class TestChromaDBResilience:
    """ChromaDB-Korruptions-Szenarien."""

    def test_chromadb_client_failures_degrade_gracefully(self):
        """Permission Denied und korrupte Persistenz → Operationen liefern sichere Defaults."""
        from vectordb.store import VectorStore

        for error in [PermissionError("denied"), RuntimeError("corrupted")]:
            chromadb = types.SimpleNamespace(
                PersistentClient=MagicMock(side_effect=error)
            )
            with patch.dict(sys.modules, {"chromadb": chromadb}):
                store = VectorStore(
                    persist_directory="/tmp/chroma-resilience",
                    collection_name="chaos_test",
                )

                assert store.add_one("test", [0.1] * 3) is False
                assert store.query([0.1] * 3) == []
                assert store.count == 0

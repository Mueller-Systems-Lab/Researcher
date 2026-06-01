# =============================================================================
# Tests: Embedding Service (T-025 Coverage + Repair Coverage)
# =============================================================================
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Konfiguration & Leertext (existierende Tests)
# ---------------------------------------------------------------------------


def test_embedding_config():
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(base_url="http://localhost:11434", model="nomic-embed-text")
    assert svc.base_url == "http://localhost:11434"
    assert svc.model == "nomic-embed-text"
    assert isinstance(svc.is_available, bool)


def test_embedding_connection_error():
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(base_url="http://localhost:19999")
    with pytest.raises(ConnectionError):
        svc.embed("test")


def test_embedding_empty_text():
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(base_url="http://localhost:11434")
    # embed() wirft ValueError bei leerem Text (dokumentiertes Verhalten)
    import pytest

    with pytest.raises(ValueError, match="nicht-leeren Text"):
        svc.embed("")
    with pytest.raises(ValueError, match="nicht-leeren Text"):
        svc.embed("   ")


def test_embedding_batch_empty():
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(base_url="http://localhost:11434")
    assert svc.embed_batch([]) == []


# ---------------------------------------------------------------------------
# Mock-basierte Happy-Path-Tests (Repair Coverage)
# ---------------------------------------------------------------------------


def test_embed_success_mocked():
    """Test: Erfolgreiches Embedding mit gemockter Ollama-API."""
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(
        base_url="http://localhost:11434",
        model="nomic-embed-text:latest",
    )
    mock_embedding = [0.1, 0.2, 0.3, 0.4]

    with patch("vectordb.embedding.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": mock_embedding}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = svc.embed("Test text for embedding")
        assert result == mock_embedding
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert "json" in call_kwargs
        assert call_kwargs["json"]["model"] == "nomic-embed-text:latest"
        assert call_kwargs["timeout"] == 30


def test_embed_value_error_on_request_exception():
    """Test: ValueError bei requests.RequestException (nicht ConnectionError)."""
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(
        base_url="http://localhost:11434",
        model="nomic-embed-text",
    )

    with patch("vectordb.embedding.requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.Timeout("timeout")

        with pytest.raises(ValueError, match="Embedding-Fehler"):
            svc.embed("test")


def test_embed_value_error_on_json_decode_error():
    """Test: ValueError bei ungültigem JSON in Ollama-Response."""
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(
        base_url="http://localhost:11434",
        model="nomic-embed-text",
    )

    with patch("vectordb.embedding.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="Embedding-Fehler"):
            svc.embed("test")


def test_embed_batch_with_partial_failure():
    """Test: Batch-Embedding mit einem fehlschlagenden Item."""
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(
        base_url="http://localhost:11434",
        model="nomic-embed-text",
    )
    mock_embedding = [0.1, 0.2, 0.3]

    with patch("vectordb.embedding.requests.post") as mock_post:
        # Erstes embedding: success
        mock_response_ok = MagicMock()
        mock_response_ok.json.return_value = {"embedding": mock_embedding}
        mock_response_ok.status_code = 200

        # Zweites embedding: Timeout (wird als Exception gefangen)
        mock_response_fail = MagicMock()
        mock_response_fail.json.side_effect = requests.exceptions.Timeout("timeout")

        mock_post.side_effect = [
            mock_response_ok,
            mock_response_fail,
            mock_response_ok,
        ]

        results = svc.embed_batch(["text1", "text2", "text3"])
        assert len(results) == 3
        assert results[0] == mock_embedding
        assert results[1] == []  # Fehler → leere Liste
        assert results[2] == mock_embedding


def test_embedding_dimension_mocked():
    """Test: dimension-Property mit gemockter API."""
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(
        base_url="http://localhost:11434",
        model="nomic-embed-text",
    )
    mock_embedding = [0.0] * 768

    with patch("vectordb.embedding.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": mock_embedding}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        assert svc.dimension == 768


def test_embedding_is_available_mocked():
    """Test: is_available mit gemocktem API-Tags-Endpoint."""
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(
        base_url="http://localhost:11434",
        model="nomic-embed-text",
    )

    with patch("vectordb.embedding.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert svc.is_available is True
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)


def test_embed_batch_connection_error_propagates():
    """ConnectionError in batch embedding is re-raised."""
    from unittest.mock import patch
    import requests
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(base_url="http://localhost:11434")
    conn_err = requests.exceptions.ConnectionError("refused")

    with patch("vectordb.embedding.requests.post", side_effect=conn_err):
        try:
            svc.embed_batch(["text1", "text2"])
            assert False, "Should have raised"
        except ConnectionError:
            pass

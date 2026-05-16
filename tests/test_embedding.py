# =============================================================================
# Tests: Embedding Service (T-025 Coverage)
# =============================================================================
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_embedding_config():
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(base_url="http://localhost:11434", model="nomic-embed-text")
    assert svc.base_url == "http://localhost:11434"
    assert svc.model == "nomic-embed-text"
    # is_available hängt davon ab ob Ollama läuft (nicht deterministisch)
    assert isinstance(svc.is_available, bool)


def test_embedding_connection_error():
    from vectordb.embedding import EmbeddingService
    import pytest

    svc = EmbeddingService(base_url="http://localhost:19999")
    with pytest.raises(ConnectionError):
        svc.embed("test")


def test_embedding_empty_text():
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(base_url="http://localhost:11434")
    assert svc.embed("") == []
    assert svc.embed("   ") == []


def test_embedding_batch_empty():
    from vectordb.embedding import EmbeddingService

    svc = EmbeddingService(base_url="http://localhost:11434")
    assert svc.embed_batch([]) == []

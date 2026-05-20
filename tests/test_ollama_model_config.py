# =============================================================================
# Tests: config/ollama_models.py — Modellrollen, Fallback, Embedding-Schutz
# =============================================================================
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── load_ollama_model_config ──────────────────────────────────────────────────


def test_load_defaults():
    """Test: Default-Werte werden geladen wenn keine Env-Vars gesetzt."""
    from config.ollama_models import OllamaModelConfig, load_ollama_model_config

    with patch.dict(os.environ, {}, clear=True):
        config = load_ollama_model_config()
        assert config.base_url == OllamaModelConfig._DEFAULT_BASE_URL
        assert config.chat_model == OllamaModelConfig._DEFAULT_CHAT_MODEL
        assert config.embedding_model == OllamaModelConfig._DEFAULT_EMBEDDING_MODEL
        assert config.allow_model_fallback is False


def test_load_custom_env():
    """Test: Benutzerdefinierte Env-Vars werden geladen."""
    from config.ollama_models import load_ollama_model_config

    with patch.dict(
        os.environ,
        {
            "OLLAMA_BASE_URL": "http://custom:9999",
            "OLLAMA_CHAT_MODEL": "my-chat-model",
            "OLLAMA_EMBEDDING_MODEL": "my-embed-model",
            "ALLOW_OLLAMA_MODEL_FALLBACK": "true",
        },
        clear=True,
    ):
        config = load_ollama_model_config()
        assert config.base_url == "http://custom:9999"
        assert config.chat_model == "my-chat-model"
        assert config.embedding_model == "my-embed-model"
        assert config.allow_model_fallback is True


def test_load_fallback_yes():
    """Test: ALLOW_OLLAMA_MODEL_FALLBACK=yes erkannt."""
    from config.ollama_models import load_ollama_model_config

    with patch.dict(os.environ, {"ALLOW_OLLAMA_MODEL_FALLBACK": "yes"}, clear=True):
        config = load_ollama_model_config()
        assert config.allow_model_fallback is True


def test_load_fallback_one():
    """Test: ALLOW_OLLAMA_MODEL_FALLBACK=1 erkannt."""
    from config.ollama_models import load_ollama_model_config

    with patch.dict(os.environ, {"ALLOW_OLLAMA_MODEL_FALLBACK": "1"}, clear=True):
        config = load_ollama_model_config()
        assert config.allow_model_fallback is True


def test_config_is_frozen():
    """Test: OllamaModelConfig ist immutable (frozen dataclass)."""
    import pytest

    from config.ollama_models import OllamaModelConfig

    config = OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="chat-model",
        embedding_model="embed-model",
    )
    with pytest.raises(Exception):
        config.chat_model = "other"  # type: ignore[misc]


# ── is_embedding_model_name ────────────────────────────────────────────────────


def test_is_embedding_nomic():
    """Test: nomic-embed-text wird als Embedding-Modell erkannt."""
    from config.ollama_models import is_embedding_model_name

    assert is_embedding_model_name("nomic-embed-text:latest") is True
    assert is_embedding_model_name("nomic-embed-text") is True


def test_is_embedding_bge():
    """Test: bge- Modell wird als Embedding erkannt."""
    from config.ollama_models import is_embedding_model_name

    assert is_embedding_model_name("bge-large:latest") is True


def test_is_embedding_e5():
    """Test: e5- Modell wird als Embedding erkannt."""
    from config.ollama_models import is_embedding_model_name

    assert is_embedding_model_name("e5-mistral-7b") is True


def test_is_not_embedding_qwen():
    """Test: qwen3.5 ist KEIN Embedding-Modell."""
    from config.ollama_models import is_embedding_model_name

    assert is_embedding_model_name("qwen3.5-uncensored-no-thinking:latest") is False


def test_is_not_embedding_generic():
    """Test: Generische Chat-Modelle werden nicht als Embedding erkannt."""
    from config.ollama_models import is_embedding_model_name

    assert is_embedding_model_name("llama3:latest") is False
    assert is_embedding_model_name("mistral:7b") is False
    assert is_embedding_model_name("gemma4") is False


# ── resolve_chat_model ────────────────────────────────────────────────────────


def test_resolve_ok():
    """Test: Konfiguriertes Modell ist verfügbar."""
    from config.ollama_models import OllamaModelConfig, resolve_chat_model

    config = OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="my-chat-model",
        embedding_model="nomic-embed-text",
    )
    available = ["nomic-embed-text:latest", "my-chat-model"]

    result = resolve_chat_model(config, available)
    assert result.status == "ok"
    assert result.used_model == "my-chat-model"
    assert result.fallback_used is False


def test_resolve_fallback_allowed():
    """Test: Fallback wird verwendet wenn erlaubt."""
    from config.ollama_models import OllamaModelConfig, resolve_chat_model

    config = OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="my-chat-model",
        embedding_model="nomic-embed-text",
        allow_model_fallback=True,
    )
    available = ["nomic-embed-text:latest", "other-chat-model"]

    result = resolve_chat_model(config, available)
    assert result.status == "fallback"
    assert result.used_model == "other-chat-model"
    assert result.fallback_used is True


def test_resolve_fallback_skips_embedding_models():
    """Test: Embedding-Modell wird NICHT als Chat-Fallback gewählt."""
    from config.ollama_models import OllamaModelConfig, resolve_chat_model

    config = OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="my-chat-model",
        embedding_model="nomic-embed-text",
        allow_model_fallback=True,
    )
    # Nur Embedding-Modelle verfügbar, kein Chat-Modell
    available = ["nomic-embed-text:latest"]

    result = resolve_chat_model(config, available)
    assert result.status == "no_models"
    assert result.used_model is None
    assert result.fallback_used is False


def test_resolve_missing_strict_mode():
    """Test: Strict Mode: Chat-Modell fehlt, kein Fallback."""
    from config.ollama_models import OllamaModelConfig, resolve_chat_model

    config = OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="my-chat-model",
        embedding_model="nomic-embed-text",
        allow_model_fallback=False,
    )
    available = ["nomic-embed-text:latest", "other-model"]

    result = resolve_chat_model(config, available)
    assert result.status == "missing"
    assert result.used_model is None
    assert result.fallback_used is False


def test_resolve_empty_chat_model():
    """Test: Leerer OLLAMA_CHAT_MODEL → config_error."""
    from config.ollama_models import OllamaModelConfig, resolve_chat_model

    config = OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="",
        embedding_model="nomic-embed-text",
    )
    available = []  # type: ignore[var-annotated]

    result = resolve_chat_model(config, available)
    assert result.status == "config_error"
    assert result.used_model is None


def test_resolve_no_models_available():
    """Test: Keine Modelle verfügbar."""
    from config.ollama_models import OllamaModelConfig, resolve_chat_model

    config = OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="my-chat-model",
        embedding_model="nomic-embed-text",
        allow_model_fallback=True,
    )
    available: list[str] = []

    result = resolve_chat_model(config, available)
    assert result.status == "no_models"
    assert result.used_model is None


# ── validate_model_roles ──────────────────────────────────────────────────────


def test_validate_roles_ok():
    """Test: Korrekte Konfiguration → keine Fehler."""
    from config.ollama_models import OllamaModelConfig, validate_model_roles

    config = OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="qwen3.5-uncensored-no-thinking:latest",
        embedding_model="nomic-embed-text:latest",
    )
    errors = validate_model_roles(config)
    assert errors == []


def test_validate_roles_empty_chat():
    """Test: Leeres OLLAMA_CHAT_MODEL → Fehler."""
    from config.ollama_models import OllamaModelConfig, validate_model_roles

    config = OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="",
        embedding_model="nomic-embed-text:latest",
    )
    errors = validate_model_roles(config)
    assert len(errors) > 0
    assert any("CHAT_MODEL" in e for e in errors)


def test_validate_roles_empty_embedding():
    """Test: Leeres OLLAMA_EMBEDDING_MODEL → Fehler."""
    from config.ollama_models import OllamaModelConfig, validate_model_roles

    config = OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="qwen3.5",
        embedding_model="",
    )
    errors = validate_model_roles(config)
    assert len(errors) > 0
    assert any("EMBEDDING_MODEL" in e for e in errors)


def test_validate_roles_embedding_as_chat():
    """Test: Embedding-Modell als Chat-Modell → Fehler."""
    from config.ollama_models import OllamaModelConfig, validate_model_roles

    config = OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="nomic-embed-text:latest",
        embedding_model="nomic-embed-text:latest",
    )
    errors = validate_model_roles(config)
    assert len(errors) > 0
    assert any("Embedding" in e for e in errors)

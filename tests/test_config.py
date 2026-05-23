# =============================================================================
# Tests: config.py — Konfigurationsvalidierung (Repair Coverage)
# =============================================================================
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# validate_env
# ---------------------------------------------------------------------------


def test_validate_env_missing():
    """Test: Alle erforderlichen Variablen fehlen."""
    from config.config import validate_env

    with patch.dict(os.environ, {}, clear=True):
        result = validate_env()
        assert len(result) == 5
        assert "FAST_LLM" in result
        assert "SMART_LLM" in result
        assert "OLLAMA_BASE_URL" in result


def test_validate_env_all_set():
    """Test: Alle erforderlichen Variablen sind gesetzt."""
    from config.config import validate_env

    with patch.dict(
        os.environ,
        {
            "FAST_LLM": "ollama:qwen3",
            "SMART_LLM": "ollama:qwen3",
            "STRATEGIC_LLM": "ollama:qwen3",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "EMBEDDING": "ollama:nomic-embed-text",
        },
    ):
        result = validate_env()
        assert result == []


# ---------------------------------------------------------------------------
# validate_local_first
# ---------------------------------------------------------------------------


def test_validate_local_first_allowed_cloud():
    """Test: ALLOW_CLOUD=true → keine Fehler."""
    from config.config import validate_local_first

    with patch.dict(os.environ, {"ALLOW_CLOUD": "true"}, clear=True):
        result = validate_local_first()
        assert result == []


def test_validate_local_first_allowed_cloud_yes():
    """Test: ALLOW_CLOUD=yes → keine Fehler."""
    from config.config import validate_local_first

    with patch.dict(os.environ, {"ALLOW_CLOUD": "yes"}, clear=True):
        result = validate_local_first()
        assert result == []


def test_validate_local_first_no_cloud():
    """Test: Kein Cloud-Provider → keine Fehler."""
    from config.config import validate_local_first

    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "ollama",
            "FAST_LLM": "ollama:qwen3",
            "SMART_LLM": "ollama:qwen3",
            "STRATEGIC_LLM": "ollama:qwen3",
            "RETRIEVER": "searx",
        },
        clear=True,
    ):
        result = validate_local_first()
        assert result == []


def test_validate_local_first_cloud_provider_detected():
    """Test: OpenAI im LLM_PROVIDER ohne ALLOW_CLOUD → Fehler."""
    from config.config import validate_local_first

    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "openai",
        },
        clear=True,
    ):
        result = validate_local_first()
        assert len(result) > 0
        assert "ERROR" in result[0]
        assert "openai" in result[1].lower()


def test_validate_local_first_cloud_llm_detected():
    """Test: OpenAI im FAST_LLM ohne ALLOW_CLOUD → Fehler."""
    from config.config import validate_local_first

    with patch.dict(
        os.environ,
        {
            "FAST_LLM": "openai:gpt-4",
        },
        clear=True,
    ):
        result = validate_local_first()
        assert len(result) > 0
        assert "ERROR" in result[0]
        assert "FAST_LLM" in result[1]


def test_validate_local_first_tavily_retriever():
    """Test: Tavily Retriever ohne ALLOW_CLOUD → Fehler."""
    from config.config import validate_local_first

    with patch.dict(
        os.environ,
        {
            "RETRIEVER": "tavily",
        },
        clear=True,
    ):
        result = validate_local_first()
        assert len(result) > 0
        assert "ERROR" in result[0]
        assert "tavily" in result[1]


def test_validate_local_first_cloud_with_env_file():
    """Test: Cloud-Like env aber mit ALLOW_CLOUD=1 → OK."""
    from config.config import validate_local_first

    with patch.dict(
        os.environ,
        {
            "ALLOW_CLOUD": "1",
            "LLM_PROVIDER": "anthropic",
        },
        clear=True,
    ):
        result = validate_local_first()
        assert result == []


# ---------------------------------------------------------------------------
# ensure_local_first_or_die
# ---------------------------------------------------------------------------


def test_ensure_local_first_ok():
    """Test: Keine Cloud → läuft durch ohne Exit."""
    from config.config import ensure_local_first_or_die

    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "ollama",
            "RETRIEVER": "searx",
        },
        clear=True,
    ):
        # Sollte nicht crashen
        ensure_local_first_or_die()


def test_ensure_local_first_detected():
    """Test: Cloud erkannt → sys.exit(1)."""
    from config.config import ensure_local_first_or_die

    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "openai",
        },
        clear=True,
    ):
        with pytest.raises(SystemExit) as exc_info:
            ensure_local_first_or_die()
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# suggest_env
# ---------------------------------------------------------------------------


def test_suggest_env_no_env_file(capsys):
    """Test: Keine .env → Hinweis wird ausgegeben."""
    from config.config import PROJECT_ROOT, suggest_env

    # Sichern, falls .env existiert
    env_path = PROJECT_ROOT / ".env"
    env_exists = env_path.exists()

    try:
        if env_exists:
            os.rename(str(env_path), str(env_path) + ".backup_test")

        suggest_env()
        captured = capsys.readouterr()
        assert ".env nicht gefunden" in captured.out
    finally:
        if env_exists:
            os.rename(str(env_path) + ".backup_test", str(env_path))


# ---------------------------------------------------------------------------
# is_deterministic / print_config
# ---------------------------------------------------------------------------


def test_is_deterministic_default():
    """Test: Standardmäßig nicht deterministisch."""
    from config.config import is_deterministic

    with patch.dict(os.environ, {}, clear=True):
        assert is_deterministic() is False


def test_is_deterministic_enabled():
    """Test: RESEARCH_DETERMINISTIC=true aktiviert."""
    from config.config import is_deterministic

    with patch.dict(os.environ, {"RESEARCH_DETERMINISTIC": "true"}, clear=True):
        assert is_deterministic() is True


def test_print_config_basic(capsys):
    """Test: print_config gibt Basis-Konfiguration aus (keine Secrets)."""
    from config.config import print_config

    with patch.dict(os.environ, {}, clear=True):
        print_config()
        captured = capsys.readouterr()
        assert "Researcher — Konfiguration" in captured.out
        assert "FAST_LLM:" in captured.out
        assert "nicht gesetzt" in captured.out


def test_print_config_deterministic(capsys):
    """Test: print_config im deterministischen Modus."""
    from config.config import print_config

    with patch.dict(
        os.environ,
        {
            "RESEARCH_DETERMINISTIC": "true",
            "FAST_LLM": "ollama:qwen3",
        },
        clear=True,
    ):
        print_config()
        captured = capsys.readouterr()
        assert "TEMPERATURE:     0" in captured.out
        assert "LLM_SEED:        42" in captured.out

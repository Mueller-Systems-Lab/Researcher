# =============================================================================
# Researcher — Ollama Model Configuration (ADR-015, ADR-017)
# =============================================================================
# Zentrales Modul für Ollama-Modellkonfiguration und Modellauflösung.
# Trennt strikt Chat-/Summary- und Embedding-Modellrollen.
#
# WICHTIG (ADR-017): Primäres Chat-Modell ist Qwen3.5-Uncensored-HauhauCS via
# llama-server (Port 8082, alias qwen3.5-uncensored, 45 tok/s).
# OLLAMA_CHAT_MODEL ist NUR der Fallback-Pfad, wenn INFERENCE_BACKEND=ollama
# gesetzt ist. Siehe .env.example: FAST_LLM=openai:qwen3.5-uncensored.
#
# Regeln (aus docs/llm/model-selection-policy.md):
#   - OLLAMA_CHAT_MODEL: Textgenerierung, Summary, Report-Generierung (Ollama-Fallback)
#   - OLLAMA_EMBEDDING_MODEL: Embeddings, Vektorsuche (CPU-seitig, via Ollama)
#   - Embedding-Modelle (nomic-embed-text, etc.) dürfen NIE als Chatmodell dienen
#   - Fallback nur wenn ALLOW_OLLAMA_MODEL_FALLBACK=true
#   - Keine Cloud-Provider
#   - Standard-OLLAMA_CHAT_MODEL 'qwen3.5:9b' ist deprecated (ADR-016)
#
# Nutzung:
#   from config.ollama_models import load_ollama_model_config, resolve_chat_model
#   config = load_ollama_model_config()
#   resolution = resolve_chat_model(config, available_models)
# =============================================================================

import os
from dataclasses import dataclass
from typing import ClassVar

# ── Known embedding-only models ────────────────────────────────────────────────

_EMBEDDING_MODEL_PATTERNS: tuple[str, ...] = (
    "nomic-embed",
    "embed-",
    "-embed",
    "bge-",
    "e5-",
    "instructor-",
    "gte-",
    "stella-",
)


# ── Model Configuration ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class OllamaModelConfig:
    """Immutable Ollama-Modellkonfiguration aus Umgebungsvariablen.

    Trenn die Chat-/Summary- und Embedding-Rollen strikt.
    """

    base_url: str
    chat_model: str
    embedding_model: str
    allow_model_fallback: bool = False

    # Defaults aus .env.example / docs/llm/model-inventory.md / ADR-017
    # Primary Chat-Modell: Qwen3.5-Uncensored-HauhauCS via llama-server
    #   - Port 8082, alias qwen3.5-uncensored (45 tok/s)
    #   FAST_LLM=openai:qwen3.5-uncensored (siehe .env.example)
    # OLLAMA_CHAT_MODEL ist NUR der Fallback für den Ollama-Chat-Pfad,
    #       wenn INFERENCE_BACKEND=ollama gesetzt ist.
    # DEFAULT 'qwen3.5:9b': deprecated (alter Ollama-Pfad).
    #       Siehe docs/adr/ADR-017-qwen3.5-co-primary-model.md
    _DEFAULT_BASE_URL: ClassVar[str] = "http://localhost:11434"
    _DEFAULT_CHAT_MODEL: ClassVar[str] = "qwen3.5:9b"  # DEPRECATED (ADR-016)
    _DEFAULT_EMBEDDING_MODEL: ClassVar[str] = "nomic-embed-text:latest"


def load_ollama_model_config() -> OllamaModelConfig:
    """Lädt die Ollama-Modellkonfiguration aus Umgebungsvariablen.

    Returns:
        OllamaModelConfig mit base_url, chat_model, embedding_model,
        allow_model_fallback.
    """
    base_url = os.getenv("OLLAMA_BASE_URL", OllamaModelConfig._DEFAULT_BASE_URL)
    chat_model = os.getenv("OLLAMA_CHAT_MODEL", OllamaModelConfig._DEFAULT_CHAT_MODEL)
    embedding_model = os.getenv(
        "OLLAMA_EMBEDDING_MODEL", OllamaModelConfig._DEFAULT_EMBEDDING_MODEL
    )
    allow_fallback = os.getenv("ALLOW_OLLAMA_MODEL_FALLBACK", "").lower() in (
        "true",
        "1",
        "yes",
    )

    return OllamaModelConfig(
        base_url=base_url,
        chat_model=chat_model,
        embedding_model=embedding_model,
        allow_model_fallback=allow_fallback,
    )


# ── Model Classification ──────────────────────────────────────────────────────


def is_embedding_model_name(model_name: str) -> bool:
    """Prüft, ob der Modellname ein bekanntes Embedding-Modell bezeichnet.

    Args:
        model_name: Der zu prüfende Modellname (z.B. 'nomic-embed-text:latest').

    Returns:
        True wenn das Modell als Embedding-Modell klassifiziert wird.
    """
    name_lower = model_name.lower()
    for pattern in _EMBEDDING_MODEL_PATTERNS:
        if pattern in name_lower:
            return True
    return False


def _is_chat_candidate(model_name: str) -> bool:
    """Prüft, ob ein Modell als Chat-Kandidat in Frage kommt."""
    return not is_embedding_model_name(model_name)


# ── Model Resolution ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ModelResolution:
    """Ergebnis der Modellauflösung."""

    status: str  # 'ok', 'fallback', 'missing', 'no_models', 'config_error'
    requested_model: str
    used_model: str | None
    fallback_used: bool
    message: str


def resolve_chat_model(
    config: OllamaModelConfig,
    available_models: list[str],
) -> ModelResolution:
    """Löst das Chat-Modell basierend auf Konfiguration und Verfügbarkeit auf.

    Regeln:
    1. Konfiguriertes Chat-Modell bevorzugt, falls verfügbar.
    2. Verschiedene Schreibweisen des gleichen Modells werden erkannt
       (exakter Match).
    3. Fallback NUR wenn config.allow_model_fallback=true.
    4. Fallback wählt NUR nicht-Embedding-Modelle.
    5. Strict Mode: Fehler wenn Chat-Modell fehlt.

    Args:
        config: OllamaModelConfig mit chat_model und allow_model_fallback.
        available_models: Liste verfügbarer Modellnamen von Ollama /api/tags.

    Returns:
        ModelResolution mit Status, Modell und Diagnosemeldung.
    """
    # Konfiguration validieren
    if not config.chat_model:
        return ModelResolution(
            status="config_error",
            requested_model="",
            used_model=None,
            fallback_used=False,
            message="OLLAMA_CHAT_MODEL ist nicht gesetzt oder leer.",
        )

    # Best Case: konfiguriertes Modell ist verfügbar
    if config.chat_model in available_models:
        return ModelResolution(
            status="ok",
            requested_model=config.chat_model,
            used_model=config.chat_model,
            fallback_used=False,
            message=f"Chat-Modell '{config.chat_model}' gefunden.",
        )

    # Modell fehlt — Fallback oder Fehler
    chat_candidates = [m for m in available_models if _is_chat_candidate(m)]

    if not chat_candidates:
        return ModelResolution(
            status="no_models",
            requested_model=config.chat_model,
            used_model=None,
            fallback_used=False,
            message=(
                f"Keine Chat-Modelle verfügbar. "
                f"'{config.chat_model}' fehlt, "
                f"und keine nicht-Embedding-Modelle gefunden."
            ),
        )

    if config.allow_model_fallback:
        fallback = chat_candidates[0]
        return ModelResolution(
            status="fallback",
            requested_model=config.chat_model,
            used_model=fallback,
            fallback_used=True,
            message=(f"'{config.chat_model}' nicht verfügbar, Fallback: '{fallback}'."),
        )

    # Kein Fallback erlaubt
    return ModelResolution(
        status="missing",
        requested_model=config.chat_model,
        used_model=None,
        fallback_used=False,
        message=(
            f"'{config.chat_model}' nicht verfügbar. "
            f"Verfügbare Chat-Modelle: {', '.join(chat_candidates)}. "
            f"Setze OLLAMA_CHAT_MODEL=<model> oder ALLOW_OLLAMA_MODEL_FALLBACK=true"
        ),
    )


# ── Validation ────────────────────────────────────────────────────────────────


def validate_model_roles(config: OllamaModelConfig) -> list[str]:
    """Validiert die Modellrollen-Konfiguration.

    Prüft:
    - OLLAMA_CHAT_MODEL ist nicht leer.
    - OLLAMA_EMBEDDING_MODEL ist nicht leer.
    - OLLAMA_CHAT_MODEL ist kein bekanntes Embedding-Modell.
    - OLLAMA_CHAT_MODEL verwendet nicht den deprecated qwen3.5-Default.

    Args:
        config: Die zu validierende OllamaModelConfig.

    Returns:
        Liste von Fehlermeldungen (leer = alles OK).
    """
    errors: list[str] = []

    if not config.chat_model:
        errors.append("OLLAMA_CHAT_MODEL ist nicht gesetzt oder leer.")
    elif is_embedding_model_name(config.chat_model):
        errors.append(
            f"OLLAMA_CHAT_MODEL='{config.chat_model}' ist ein "
            f"Embedding-Modell und kann keine Texte generieren. "
            f"Setze OLLAMA_CHAT_MODEL auf ein Chat-/Summary-Modell."
        )
    elif config.chat_model == "qwen3.5:9b":
        errors.append(
            "OLLAMA_CHAT_MODEL='qwen3.5:9b' ist DEPRECATED (ADR-016). "
            "Der alte Ollama-qwen3.5-Pfad ist auf GTX 1070 hardware-blockiert."
            "Primary Chat-Modell ist Qwen3.5-Uncensored-HauhauCS via llama.cpp "
            "(Port 8082, 45 tok/s) — siehe ADR-017. "
            "Setze OLLAMA_CHAT_MODEL auf ein alternatives Chat-Modell "
            "oder ignoriere die Warnung bei INFERENCE_BACKEND=ollama."
        )

    if not config.embedding_model:
        errors.append("OLLAMA_EMBEDDING_MODEL ist nicht gesetzt oder leer.")

    return errors

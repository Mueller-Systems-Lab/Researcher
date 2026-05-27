# =============================================================================
# Researcher — GPT Researcher Konfiguration
# =============================================================================
# Dieses Modul ergänzt die GPT Researcher Umgebungskonfiguration.
# Es wird vor dem Start von gpt_researcher geladen, um sicherzustellen,
# dass alle Umgebungsvariablen korrekt gesetzt sind.
#
# GPT Researcher v0.14.8 liest Konfiguration primär aus Umgebungsvariablen.
# Siehe .env.example für alle verfügbaren Optionen.
# =============================================================================

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Projekt-Root ermitteln
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Cloud-Provider, die lokal-first ersetzen würden (Block 3.6)
_CLOUD_PROVIDERS = ["openai", "tavily", "google-genai", "anthropic"]


def validate_local_first() -> list[str]:
    """Startup-Check: Cloud-Provider fail-closed.

    Prüft, ob LLM_PROVIDER oder RETRIEVER auf Cloud-Dienste zeigen,
    ohne dass ALLOW_CLOUD=true gesetzt ist.

    Returns:
        Liste mit Fehlermeldungen (leer = alles OK).
    """
    if os.getenv("ALLOW_CLOUD", "").lower() in ("true", "1", "yes"):
        return []  # Cloud explizit erlaubt

    errors = []

    # Prüfe LLM-Provider
    llm_provider = os.getenv("LLM_PROVIDER", "").lower()
    for provider in _CLOUD_PROVIDERS:
        if provider in llm_provider:
            errors.append(f"LLM_PROVIDER='{llm_provider}'")

    # Prüfe FAST/SMART/STRATEGIC_LLM
    for llm_var in ("FAST_LLM", "SMART_LLM", "STRATEGIC_LLM"):
        val = os.getenv(llm_var, "").lower()
        for provider in _CLOUD_PROVIDERS:
            if val.startswith(provider + ":"):
                errors.append(f"{llm_var}='{val}'")
                break

    # Prüfe Retriever
    retriever = os.getenv("RETRIEVER", "").lower()
    if retriever == "tavily":
        errors.append("RETRIEVER='tavily'")

    if errors:
        providers_list = ", ".join(errors)
        return [
            "ERROR: Cloud provider detected without ALLOW_CLOUD=true.",
            f"  Detected: {providers_list}",
            "  Set LLM_PROVIDER=ollama or add ALLOW_CLOUD=true to .env",
            "  See .env.example for local-first configuration.",
        ]

    return []


def ensure_local_first_or_die():
    """Bricht den Startup ab, wenn Cloud-Provider ohne ALLOW_CLOUD=true
    erkannt werden."""
    errors = validate_local_first()
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        sys.exit(1)


def validate_env() -> list[str]:
    """Prüft, ob alle erforderlichen Umgebungsvariablen gesetzt sind.
    Gibt eine Liste mit fehlenden Variablen zurück (leer = alles OK)."""
    required = [
        "FAST_LLM",
        "SMART_LLM",
        "STRATEGIC_LLM",
        "OLLAMA_BASE_URL",
        "EMBEDDING",
    ]
    missing = [var for var in required if not os.getenv(var)]
    return missing


def suggest_env():
    """Gibt einen Hinweis aus, wenn .env nicht konfiguriert ist."""
    env_path = PROJECT_ROOT / ".env"
    example_path = PROJECT_ROOT / ".env.example"
    if not env_path.exists():
        logger.warning(
            ".env nicht gefunden. Kopiere %s nach %s "
            "und passe Werte an deine Umgebung an.",
            example_path,
            env_path,
        )


def is_deterministic() -> bool:
    """Prüft, ob der deterministische Modus aktiv ist.

    Im deterministischen Modus:
    - temperature=0 für reproduzierbare Ergebnisse
    - Random Seeds fixiert
    - Snapshots/Versionen eingefroren

    Returns:
        True wenn RESEARCH_DETERMINISTIC=true, sonst False.
    """
    return os.getenv("RESEARCH_DETERMINISTIC", "false").lower() in ("true", "1", "yes")


def apply_deterministic_config():
    """Wendet die deterministische Konfiguration an.

    Setzt Umgebungsvariablen für GPT Researcher, die Reproduzierbarkeit
    sicherstellen. Sollte VOR dem Start von gpt_researcher aufgerufen werden.
    """
    if not is_deterministic():
        return

    # Temperatur = 0 für deterministische LLM-Antworten
    os.environ.setdefault("LLM_TEMPERATURE", "0")
    os.environ.setdefault("TEMPERATURE", "0")
    # Top-P = 1 (kein Sampling)
    os.environ.setdefault("LLM_TOP_P", "1")
    # Seed fixieren für Reproduzierbarkeit
    os.environ.setdefault("LLM_SEED", "42")

    # GPT Researcher spezifisch (v0.14.8)
    os.environ.setdefault("FAST_LLM_TEMPERATURE", "0")
    os.environ.setdefault("SMART_LLM_TEMPERATURE", "0")
    os.environ.setdefault("STRATEGIC_LLM_TEMPERATURE", "0")


def print_config():
    """Gibt die aktuelle Konfiguration aus (ohne Secrets)."""
    logger.info("=" * 60)
    logger.info("  Researcher — Konfiguration")
    logger.info("=" * 60)
    logger.info("  FAST_LLM:        %s", os.getenv("FAST_LLM", "nicht gesetzt"))
    logger.info("  SMART_LLM:       %s", os.getenv("SMART_LLM", "nicht gesetzt"))
    logger.info("  STRATEGIC_LLM:   %s", os.getenv("STRATEGIC_LLM", "nicht gesetzt"))
    logger.info("  OLLAMA_BASE_URL: %s", os.getenv("OLLAMA_BASE_URL", "nicht gesetzt"))
    logger.info("  EMBEDDING:       %s", os.getenv("EMBEDDING", "nicht gesetzt"))
    logger.info("  RETRIEVER:       %s", os.getenv("RETRIEVER", "nicht gesetzt"))
    logger.info("  SEARX_URL:       %s", os.getenv("SEARX_URL", "nicht gesetzt"))
    logger.info(
        "  CHROMA_DB:       %s",
        os.getenv("CHROMA_PERSIST_DIRECTORY", "nicht gesetzt"),
    )
    logger.info("  DETERMINISTIC:   %s", os.getenv("RESEARCH_DETERMINISTIC", "false"))
    if is_deterministic():
        logger.info("  TEMPERATURE:     0 (fixiert)")
        logger.info("  LLM_SEED:        42 (fixiert)")
    logger.info("=" * 60)

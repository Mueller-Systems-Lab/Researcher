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

import os
from pathlib import Path

# Projekt-Root ermitteln
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


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
        print(f"  ⚠  .env nicht gefunden.")
        print(f"  →  Kopiere {example_path} nach {env_path}")
        print(f"  →  Passe die Werte in .env an deine Umgebung an.")


def print_config():
    """Gibt die aktuelle Konfiguration aus (ohne Secrets)."""
    print("=" * 60)
    print("  Researcher — Konfiguration")
    print("=" * 60)
    print(f"  FAST_LLM:        {os.getenv('FAST_LLM', 'nicht gesetzt')}")
    print(f"  SMART_LLM:       {os.getenv('SMART_LLM', 'nicht gesetzt')}")
    print(f"  STRATEGIC_LLM:   {os.getenv('STRATEGIC_LLM', 'nicht gesetzt')}")
    print(f"  OLLAMA_BASE_URL: {os.getenv('OLLAMA_BASE_URL', 'nicht gesetzt')}")
    print(f"  EMBEDDING:       {os.getenv('EMBEDDING', 'nicht gesetzt')}")
    print(f"  RETRIEVER:       {os.getenv('RETRIEVER', 'nicht gesetzt')}")
    print(f"  SEARX_URL:       {os.getenv('SEARX_URL', 'nicht gesetzt')}")
    print(
        f"  CHROMA_DB:       {os.getenv('CHROMA_PERSIST_DIRECTORY', 'nicht gesetzt')}"
    )
    print("=" * 60)

#!/usr/bin/env python3
"""Runtime Smoke Test — Prüft lokale Dienste (Ollama, SearXNG, Tor, Cloud-Blocker).

Nutzung:
    python3 scripts/runtime_smoke.py           # Standard (Warnungen)
    python3 scripts/runtime_smoke.py --only searxng  # Nur SearXNG
    REQUIRE_OLLAMA=true python3 scripts/runtime_smoke.py   # Ollama Pflicht
    SEARXNG_TIMEOUT_SECONDS=30 python3 scripts/runtime_smoke.py  # Custom timeout

Exit-Codes:
    0 — Alle geprüften Pflicht-Dienste OK
    1 — Mindestens ein Pflicht-Dienst fehlt
    2 — Cloud-Provider ohne ALLOW_CLOUD aktiv
    3 — SearXNG benötigt länger (Timeout-Warnung)
"""

import argparse
import os
import socket
import sys

import requests

# ── Konfiguration ─────────────────────────────────────────────────────────────

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
SEARXNG_URL = os.getenv("SEARX_URL", "http://localhost:8080")
SEARXNG_TIMEOUT = int(os.getenv("SEARXNG_TIMEOUT_SECONDS", "15"))
TOR_HOST = os.getenv("TOR_SOCKS_HOST", "127.0.0.1")
TOR_PORT = int(os.getenv("TOR_SOCKS_PORT", "9050"))

CLOUD_PROVIDERS = ["openai", "tavily", "google-genai", "anthropic"]

REQUEST_TIMEOUT = (5, 10)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _is_strict(service: str) -> bool:
    """Prüft, ob der Dienst im Strict-Modus gefordert wird."""
    env_var = f"REQUIRE_{service.upper()}"
    return os.getenv(env_var, "").lower() in ("true", "1", "yes")


def _status(ok: bool) -> str:
    return "✅" if ok else "❌"


# ── Healthchecks ──────────────────────────────────────────────────────────────


def check_ollama() -> bool:
    """Prüft Ollama: API, Embed-Modell, Chat-Modell."""
    embed_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
    chat_model = os.getenv("OLLAMA_CHAT_MODEL", "qwen3.5-uncensored-no-thinking:latest")

    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            print(f"  {_status(False)} Ollama API returned {r.status_code}")
            return False
        models = [m.get("name", "") for m in r.json().get("models", [])]

        # Check embed model
        if embed_model in models:
            print(f"  {_status(True)} Ollama embed: {embed_model}")
        else:
            print(f"  {_status(False)} Ollama embed: '{embed_model}' fehlt")
            print(f"     Verfügbar: {', '.join(models[:5])}...")
            return False

        # Check chat model
        if chat_model in models:
            print(f"  {_status(True)} Ollama chat: {chat_model}")
        else:
            print(f"  ⚠️  Ollama chat: '{chat_model}' fehlt")
            chat_candidates = [m for m in models if "embed" not in m.lower()]
            if chat_candidates:
                print(f"     Verfügbare Chat-Modelle: {', '.join(chat_candidates)}")
                print("     Setze OLLAMA_CHAT_MODEL=<model>")
            return False

        return True
    except requests.ConnectionError:
        print(f"  {_status(False)} Ollama nicht erreichbar ({OLLAMA_URL})")
        return False
    except requests.Timeout:
        print(f"  {_status(False)} Ollama Timeout ({OLLAMA_URL})")
        return False


def check_searxng() -> bool:
    """Prüft, ob SearXNG erreichbar ist und Ergebnisse liefert.

    Fehlerklassen: NOT_RUNNING, TIMEOUT, BAD_STATUS, BAD_JSON, NO_RESULTS, OK.
    Timeout konfigurierbar via SEARXNG_TIMEOUT_SECONDS (default: 15).
    """
    url = f"{SEARXNG_URL}/search?q=test&format=json"
    try:
        r = requests.get(
            f"{SEARXNG_URL}/search",
            params={"q": "test", "format": "json"},
            timeout=(5, SEARXNG_TIMEOUT),
        )
        if r.status_code != 200:
            print(f"  ❌ SearXNG BAD_STATUS ({r.status_code})")
            print(f"     URL: {url}")
            return False
        try:
            data = r.json()
        except ValueError:
            print("  ❌ SearXNG BAD_JSON — Antwort ist kein JSON")
            print(f"     URL: {url}")
            return False
        results = data.get("results", [])
        if not results:
            print("  ⚠️  SearXNG NO_RESULTS — erreichbar, aber keine Treffer")
            print(f"     URL: {url}")
            return False
        print(f"  ✅ SearXNG: {len(results)} results ({SEARXNG_URL})")
        return True
    except requests.ConnectionError:
        print(f"  ❌ SearXNG NOT_RUNNING ({SEARXNG_URL})")
        print("     Starte: make searxng-up")
        return False
    except requests.Timeout:
        print(f"  ⚠️  SearXNG TIMEOUT nach {SEARXNG_TIMEOUT}s")
        print(f"     URL: {url}")
        print("     Hint: Erhöhe SEARXNG_TIMEOUT_SECONDS oder prüfe Logs")
        print("     make searxng-logs")
        return False


def check_tor() -> bool:
    """Prüft, ob Tor SOCKS5-Proxy erreichbar ist (Socket-Test)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((TOR_HOST, TOR_PORT))
        sock.close()
        ok = result == 0
        print(f"  {_status(ok)} Tor SOCKS5 ({TOR_HOST}:{TOR_PORT})")
        return ok
    except OSError:
        print(f"  {_status(False)} Tor SOCKS5 nicht erreichbar ({TOR_HOST}:{TOR_PORT})")
        return False


def check_cloud_blocker() -> bool:
    """Prüft, ob Cloud-Provider ohne ALLOW_CLOUD aktiv sind."""
    if os.getenv("ALLOW_CLOUD", "").lower() in ("true", "1", "yes"):
        print("  ℹ️  Cloud-Provider erlaubt (ALLOW_CLOUD=true)")
        return True

    violations: list[str] = []
    for var in ("LLM_PROVIDER", "RETRIEVER"):
        val = os.getenv(var, "").lower()
        for provider in CLOUD_PROVIDERS:
            if provider in val:
                violations.append(f"{var}={val}")

    if violations:
        msg = f"Cloud-Provider ohne ALLOW_CLOUD: {', '.join(violations)}"
        print(f"  {_status(False)} {msg}")
        return False

    print("  ✅ Keine Cloud-Provider ohne ALLOW_CLOUD")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Runtime Smoke Test")
    parser.add_argument(
        "--only",
        choices=["ollama", "searxng", "tor", "cloud"],
        help="Nur einen Dienst prüfen",
    )
    args = parser.parse_args()
    only = args.only

    if not only:
        print("🔍 Researcher Runtime Smoke Test")
        print(f"   Ollama:  {OLLAMA_URL}")
        print(f"   SearXNG: {SEARXNG_URL} (Timeout: {SEARXNG_TIMEOUT}s)")
        print(f"   Tor:     {TOR_HOST}:{TOR_PORT}")
        print()

    exit_code = 0
    results: dict[str, bool] = {}

    # Cloud-Blocker (immer Pflicht, außer --only gesetzt)
    if only in (None, "cloud"):
        print("☁️  Cloud-Blocker:")
        results["cloud"] = check_cloud_blocker()
        if not results["cloud"]:
            exit_code = max(exit_code, 2)
        if not only:
            print()

    # Ollama
    if only in (None, "ollama"):
        print("🦙 Ollama:")
        results["ollama"] = check_ollama()
        if not results["ollama"] and _is_strict("ollama"):
            exit_code = max(exit_code, 1)
            print("   ❌ REQUIRE_OLLAMA=true → Fehler")
        elif not results["ollama"] and not only:
            print("   ℹ️  Ollama ist optional. Starte: ollama serve")
        if not only:
            print()

    # SearXNG
    if only in (None, "searxng"):
        print("🔎 SearXNG:")
        results["searxng"] = check_searxng()
        if not results["searxng"] and _is_strict("searxng"):
            exit_code = max(exit_code, 1)
            print("   ❌ REQUIRE_SEARXNG=true → Fehler")
        elif not results["searxng"] and not only:
            print("   ℹ️  SearXNG ist optional.")
            print("        Starte: make searxng-up")
        if not only:
            print()

    # Tor
    if only in (None, "tor"):
        print("🧅 Tor:")
        results["tor"] = check_tor()
        if not results["tor"] and _is_strict("tor"):
            exit_code = max(exit_code, 1)
            print("   ❌ REQUIRE_TOR=true → Fehler")
        elif not results["tor"] and not only:
            print("   ℹ️  Tor ist optional. Starte: sudo systemctl start tor")
        if not only:
            print()

    # Summary
    if not only:
        print("─" * 50)
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        print(f"Ergebnis: {passed}/{total} Dienste erreichbar")

    if exit_code == 0:
        print("✅ Alle Pflicht-Dienste OK")
    elif exit_code == 2:
        print("❌ Cloud-Provider ohne ALLOW_CLOUD aktiv!")
    else:
        print("❌ Mindestens ein Pflicht-Dienst fehlt")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

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

from config.ollama_models import (
    is_embedding_model_name,
    load_ollama_model_config,
)

# ── Konfiguration ─────────────────────────────────────────────────────────────

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLAMA_SERVER_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8085/v1")
LLAMA_SERVER_MODEL = "gemma4-obliterated"  # Aktuell aktives Chat-Modell
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
    """Prüft Ollama: API, Embed-Modell, Chat-Modell (zentrale Config)."""
    config = load_ollama_model_config()
    embed_model = config.embedding_model
    chat_model = config.chat_model

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

        # Check chat model — with embedding-model protection
        if chat_model in models:
            # Validate: is this actually a chat model?
            if is_embedding_model_name(chat_model):
                print(
                    f"  {_status(False)} Ollama chat: '{chat_model}' "
                    f"ist ein Embedding-Modell, kein Chat-Modell!"
                )
                print("     Setze OLLAMA_CHAT_MODEL auf ein Chat-/Summary-Modell.")
                return False
            print(f"  {_status(True)} Ollama chat: {chat_model}")
        else:
            print(f"  ⚠️  Ollama chat: '{chat_model}' fehlt")
            chat_candidates = [m for m in models if not is_embedding_model_name(m)]
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


def _check_gemma4_precision_trap() -> tuple[bool, str]:
    """Prüft, ob der laufende llama-server die Precision-Trap-Flags setzt.

    (ADR-016) Auf Pascal-GPUs (GTX 1070) muss der KV-Cache in FP32 laufen,
    sonst produziert Gemma 4 garbled Output. Erforderliche Flags:
      -ctk f32 -ctv f32

    Prüft über den Process-Name die Kommandozeilen-Argumente.
    Wenn der Server nicht läuft oder die Flags fehlen, wird gewarnt.

    Returns:
        (ok, message) — ok=True wenn Flags gesetzt oder Server nicht läuft.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if "llama-server" in line and "gemma4" in line.lower():
                if "-ctk f32" in line and "-ctv f32" in line:
                    return (True, "Precision-Trap-Flags gefunden (-ctk f32 -ctv f32)")
                else:
                    return (
                        False,
                        "WARNUNG: Gemma 4 ohne Precision-Trap-Flags! "
                        "Fehlen -ctk f32 -ctv f32 → garbled Output auf Pascal-GPUs. "
                        "Siehe ADR-016 und serve_gemma4_obliterated_researcher.sh",
                    )
        # Kein Gemma-4-Prozess gefunden → kein Precision-Trap-Risiko
        return (True, "Kein Gemma-4-Prozess aktiv (keine Prüfung nötig)")
    except (subprocess.SubprocessError, FileNotFoundError):
        return (True, "Precision-Trap-Check nicht ausführbar (ps nicht verfügbar)")


def check_llama_server() -> bool:
    """Prüft, ob llama-server (OpenAI-kompatibler Chat-Endpoint) erreichbar ist.

    Führt zusätzlich die Precision-Trap-Validierung durch (ADR-016).
    """
    model_url = f"{LLAMA_SERVER_URL}/models"
    chat_url = f"{LLAMA_SERVER_URL}/chat/completions"

    try:
        # Schritt 1: Models-Endpoint prüfen
        r = requests.get(model_url, timeout=(5, 10))
        if r.status_code != 200:
            print(f"  {_status(False)} llama-server API returned {r.status_code}")
            print(f"     URL: {model_url}")
            return False

        data = r.json()
        models: list[str] = []
        # llama-server kann Modelle in "models" (mit name) oder "data" (mit id) haben
        if "data" in data and isinstance(data["data"], list):
            models.extend(m.get("id", "") for m in data["data"])
        if "models" in data and isinstance(data["models"], list):
            models.extend(m.get("name", "") for m in data["models"])

        if LLAMA_SERVER_MODEL in models:
            print(f"  {_status(True)} llama-server model: {LLAMA_SERVER_MODEL}")
        else:
            print(f"  ⚠️  llama-server: '{LLAMA_SERVER_MODEL}' nicht gefunden")
            if models:
                print(f"     Verfügbar: {', '.join(models[:3])}")
            return False

        # Schritt 1b: Precision-Trap-Validierung (ADR-016)
        pt_ok, pt_msg = _check_gemma4_precision_trap()
        if pt_ok:
            print(f"  {_status(True)} {pt_msg}")
        else:
            print(f"  {_status(False)} {pt_msg}")

        # Schritt 2: Kurzen Chat-Test (optional, kein Fail wenn fehlschlägt)
        try:
            test = requests.post(
                chat_url,
                json={
                    "model": LLAMA_SERVER_MODEL,
                    "messages": [{"role": "user", "content": "OK"}],
                    "max_tokens": 4,
                    "temperature": 0.01,
                },
                timeout=(5, 15),
            )
            if test.status_code == 200:
                result = test.json()
                content = (
                    result.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                if content:
                    print(f"  {_status(True)} llama-server chat response: OK")
                else:
                    print("  ⚠️  llama-server chat: empty response")
            else:
                print(f"  ⚠️  llama-server chat test: HTTP {test.status_code}")
        except (requests.ConnectionError, requests.Timeout):
            print("  ⚠️  llama-server chat test: timeout (nicht kritisch)")

        return True
    except requests.ConnectionError:
        print(f"  {_status(False)} llama-server nicht erreichbar ({LLAMA_SERVER_URL})")
        print("     Starte: bash serve_gemma4_obliterated.sh")
        return False
    except requests.Timeout:
        print(f"  {_status(False)} llama-server Timeout ({LLAMA_SERVER_URL})")
        return False


def check_cloud_blocker() -> bool:
    """Prüft, ob Cloud-Provider ohne ALLOW_CLOUD aktiv sind."""
    if os.getenv("ALLOW_CLOUD", "").lower() in ("true", "1", "yes"):
        print("  ℹ️  Cloud-Provider erlaubt (ALLOW_CLOUD=true)")
        return True

    violations: list[str] = []
    for var in ("LLM_PROVIDER", "RETRIEVER", "FAST_LLM"):
        val = os.getenv(var, "").lower()
        for provider in CLOUD_PROVIDERS:
            # Bei FAST_LLM (Format "provider:model") nur den Provider-Teil prüfen
            if provider in val.split(":")[0]:
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
        choices=["ollama", "searxng", "tor", "cloud", "llama-server"],
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

    # Ollama (nur Embeddings)
    if only in (None, "ollama"):
        print("🦙 Ollama Embeddings:")
        results["ollama"] = check_ollama()
        if not results["ollama"] and _is_strict("ollama"):
            exit_code = max(exit_code, 1)
            print("   ❌ REQUIRE_OLLAMA=true → Fehler")
        elif not results["ollama"] and not only:
            print("   ℹ️  Ollama ist optional. Starte: ollama serve")
        if not only:
            print()

    # llama-server (Chat)
    if only in (None, "llama-server"):
        print("🌐 llama-server Chat:")
        results["llama-server"] = check_llama_server()
        if not results["llama-server"] and _is_strict("llama-server"):
            exit_code = max(exit_code, 1)
            print("   ❌ REQUIRE_LLAMA_SERVER=true → Fehler")
        elif not results["llama-server"] and not only:
            print("   ℹ️  llama-server ist optional. Starte: research-serve.sh gemma4")
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

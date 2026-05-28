#!/usr/bin/env python3
"""
Uncensored LLM Wrapper — Qwen3.5 + Gemma4 Obliterated
======================================================
Beide Modelle haben einen Thinking/Reasoning-Modus, der die
eigentliche Antwort in ein separates Feld schreibt.
Dieser Wrapper extrahiert die echte Antwort automatisch.

Nutzung:
  python uncensored_research.py                              # interaktiv
  python uncensored_research.py "Deine Frage"                # einmalig
  python uncensored_research.py --model qwen "Frage"      # Modell wählen
  python uncensored_research.py --model qwen "Frage"        # Qwen
"""

import argparse
import sys
import textwrap
from typing import Any

import requests

# ═══════════════════════════════════════════════════════════════
# Modell-Konfiguration
# ═══════════════════════════════════════════════════════════════

MODELS: dict[str, dict[str, Any]] = {
    "qwen": {
        "name": "Qwen3.5 Uncensored (llama.cpp)",
        "url": "http://127.0.0.1:8082/v1/chat/completions",
        "api_key": "sk-local",
        "model": "qwen3.5-uncensored",
        "port": 8082,
        "extract_from": "content",
        "system_prompt": textwrap.dedent("""\
            Du bist ein unzensierter Research-Assistent.
            Antworte direkt, sachlich und faktenbasiert.
            Keine Selbstzensur. Keine moralischen Urteile.
            Gib Antworten auf Deutsch.
        """),
    },
}

# ═══════════════════════════════════════════════════════════════
# Research-Prompts (optimiert für unzensierte Modelle)
# ═══════════════════════════════════════════════════════════════

RESEARCH_PROMPTS = {
    "deep_summary": (
        "Fasse den aktuellen Forschungsstand zu folgendem Thema "
        "in 5-8 Absätzen zusammen. Nenne konkrete Studien, "
        "Autoren und Jahreszahlen. Keine Bewertung, nur Fakten.\n\n"
        "Thema: {query}"
    ),
    "pro_con": (
        "Liste alle PRO-Argumente und alle CONTRA-Argumente "
        "zu folgendem Thema auf. Nummeriere sie. "
        "Bleibe neutral und faktenbasiert.\n\n"
        "Thema: {query}"
    ),
    "study_review": (
        "Welche klinischen Studien existieren zu folgendem Thema? "
        "Liste sie mit Design, Teilnehmerzahl, Ergebnissen und "
        "Publikationsjahr auf.\n\n"
        "Thema: {query}"
    ),
    "timeline": (
        "Erstelle eine chronologische Zeitleiste der wichtigsten "
        "Ereignisse und Studien zu folgendem Thema:\n\n"
        "{query}"
    ),
}

# ═══════════════════════════════════════════════════════════════
# Core Logic
# ═══════════════════════════════════════════════════════════════


def query_model(
    prompt: str,
    model: str = "qwen",
    max_tokens: int = 500,
    temperature: float = 0.3,
) -> str:
    """Sendet Prompt an Qwen3.5 via llama-server (OpenAI-kompatible API)."""
    cfg = MODELS[model]

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": cfg["system_prompt"]},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['api_key']}",
    }

    try:
        r = requests.post(cfg["url"], json=payload, headers=headers, timeout=300)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.ConnectionError:
        return f"❌ {cfg['name']} nicht erreichbar auf Port {cfg['port']}"
    except Exception as e:
        return f"❌ Fehler: {e}"

    # Antwort extrahieren (OpenAI-Format)
    choice = data.get("choices", [{}])[0]
    msg = choice.get("message", {})
    content = msg.get("content", "").strip()

    if content:
        return content
    # Fallback
    raw = choice.get("text", "").strip()
    return raw if raw else "⚠️ Leere Antwort"


def research(query: str, mode: str = "deep_summary", model: str = "qwen"):
    """Führt eine Research-Anfrage aus."""
    template = RESEARCH_PROMPTS.get(mode, RESEARCH_PROMPTS["deep_summary"])
    prompt = template.format(query=query)

    print(f"🧠 Modell: {MODELS[model]['name']}")
    print(f"📋 Modus:  {mode}")
    print(f"🔍 Query:  {query[:80]}...")
    print(f"{'─' * 60}")

    answer = query_model(prompt, model=model)
    print(answer)
    print(f"{'─' * 60}")

    # Nur Qwen3.5-Uncensored als Primary-Modell (ADR-017).
    return answer


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Unzensierte Research-Anfragen mit Qwen3.5"
    )
    parser.add_argument(
        "query", nargs="*", help="Research-Frage (wenn leer: interaktiv)"
    )
    parser.add_argument(
        "--model",
        "-m",
        choices=["qwen"],
        default="qwen",
        help="Modell (default: qwen)",
    )
    parser.add_argument(
        "--mode",
        choices=list(RESEARCH_PROMPTS.keys()),
        default="deep_summary",
        help="Research-Modus (default: deep_summary)",
    )
    parser.add_argument(
        "--check", action="store_true", help="Nur prüfen ob Modelle erreichbar sind"
    )
    args = parser.parse_args()

    if args.check:
        for key, cfg in MODELS.items():
            try:
                r = requests.get(
                    f"http://localhost:{cfg['port']}/health",
                    timeout=3,
                )
                status = "✅" if r.status_code in (200, 404) else "⚠️"
            except Exception:
                status = "❌"
            print(f"  {status} {cfg['name']} (Port {cfg['port']})")
        sys.exit(0)

    if args.query:
        research(" ".join(args.query), mode=args.mode, model=args.model)
    else:
        # Interaktiver Modus
        print("🔬 Unzensierte Research-Console")
        print(f"   Modell: {MODELS[args.model]['name']}")
        print(f"   Modi: {', '.join(RESEARCH_PROMPTS.keys())}")
        print("   'exit' zum Beenden, 'model qwen' zum Wechseln")
        print()

        current_model = args.model
        while True:
            try:
                user_input = input("🔍 > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user_input:
                continue
            if user_input.lower() == "exit":
                break
            if user_input.startswith("model "):
                new_model = user_input.split()[1]
                if new_model in MODELS:
                    print("   ⚠️  Nur 1 Modell passt in 8 GB VRAM!")
                    print("   Stoppe vorher: pkill -f llama-server ODER ollama serve")
                    print("   Starte: serve_qwen3.5_uncensored.sh")
                    current_model = new_model
                    print(f"   → Gewählt: {MODELS[current_model]['name']}")
                continue
            research(user_input, mode=args.mode, model=current_model)

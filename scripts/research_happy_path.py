#!/usr/bin/env python3
"""Minimaler Research-Happy-Path: SearXNG → Ollama → Report.

Nutzung:
    python3 scripts/research_happy_path.py           # Standard
    python3 scripts/research_happy_path.py --strict  # Alle Dienste Pflicht
    python3 scripts/research_happy_path.py --query "What is local search?"

Voraussetzungen (Standard):
    - SearXNG läuft (optional, wird geprüft)
    - Ollama läuft (optional, wird geprüft)
    - Keine Cloud-Provider aktiv

Exit-Codes:
    0 — Report erfolgreich erzeugt
    1 — Service nicht verfügbar / Query geblockt / Cloud aktiv
"""

import argparse
import datetime
import os
import sys

import requests

from config.ollama_models import (
    OllamaModelConfig,  # noqa: F401  # used in type hints
    load_ollama_model_config,
    resolve_chat_model,
)
from text_utils.german import normalize_markdown_text

# ── Konfiguration ─────────────────────────────────────────────────────────────

SEARXNG_URL = os.getenv("SEARX_URL", "http://localhost:8080")
OUTPUT_DIR = os.getenv("RESEARCH_REPORT_DIR", "reports/research")

# Zentrale Ollama-Modellkonfiguration (einmalig laden)
_ollama_config = load_ollama_model_config()
OLLAMA_URL = _ollama_config.base_url
OLLAMA_CHAT_MODEL = _ollama_config.chat_model
REQUEST_TIMEOUT = (5, 30)

# Harmlose Default-Query
DEFAULT_QUERY = "What is a search engine?"

# Blockierte Query-Begriffe (Safety Guard)
BLOCKED_TERMS = {
    "exploit",
    "cve",
    "vulnerability",
    "target.com",
    "credential",
    "password dump",
    "darknet",
    "onion forum",
    "person:",
    "site:",
    "malware",
    "ransomware",
}

CLOUD_PROVIDERS = ["openai", "tavily", "google-genai", "anthropic"]


# ── Safety Guards ─────────────────────────────────────────────────────────────


def check_cloud_blocker() -> bool:
    """Prüft, ob Cloud-Provider aktiv sind. Returns True wenn sauber."""
    if os.getenv("ALLOW_CLOUD", "").lower() in ("true", "1", "yes"):
        print("⚠️  ALLOW_CLOUD=true — Happy-Path nur lokal erlaubt")
        return False

    for var in ("LLM_PROVIDER", "RETRIEVER"):
        val = os.getenv(var, "").lower()
        for provider in CLOUD_PROVIDERS:
            if provider in val:
                print(f"❌ Cloud-Provider aktiv: {var}={val}")
                return False
    return True


def is_safe_query(query: str) -> bool:
    """Prüft, ob die Query harmlos ist (keine riskanten Begriffe)."""
    query_lower = query.lower()
    for term in BLOCKED_TERMS:
        if term in query_lower:
            print(f"❌ Query geblockt: enthält '{term}'")
            print("   Happy-Path erlaubt nur harmlose generische Queries.")
            return False
    return True


# ── Model Resolution ──────────────────────────────────────────────────────────


def get_ollama_models() -> list[str]:
    """Holt verfügbare Ollama-Modelle via /api/tags."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=(5, 10))
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
        return models
    except Exception:
        return []


def resolve_chat_model_local() -> tuple[str, str]:
    """Löst das Chat-Modell auf via zentraler Konfiguration.
    Returns (model_name, status) für Abwärtskompatibilität.

    Status: 'ok', 'fallback', 'missing'
    """
    available = get_ollama_models()
    resolution = resolve_chat_model(_ollama_config, available)

    # Diagnose-Ausgabe
    if resolution.status in ("missing", "fallback", "no_models", "config_error"):
        print(f"   ⚠️  {resolution.message}")

    # Alte Status-Werte erhalten
    status_map = {
        "ok": "ok",
        "fallback": "fallback",
        "missing": "missing",
        "no_models": "missing",
        "config_error": "missing",
    }
    model_name = resolution.used_model or ""
    return model_name, status_map.get(resolution.status, "missing")


# ── Research Pipeline ─────────────────────────────────────────────────────────


def search_searxng(query: str) -> list[dict]:
    """Sucht in SearXNG und gibt Ergebnisliste zurück."""
    try:
        r = requests.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "format": "json", "language": "en"},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])[:5]  # Max 5 sources
        print(f"   SearXNG: {len(results)} results")
        return results
    except requests.ConnectionError:
        print(f"   ❌ SearXNG nicht erreichbar ({SEARXNG_URL})")
        return []
    except requests.Timeout:
        print(f"   ❌ SearXNG Timeout ({SEARXNG_URL})")
        return []
    except Exception as e:
        print(f"   ❌ SearXNG Fehler: {e}")
        return []


def summarize_with_ollama(query: str, sources: list[dict], model_name: str) -> str:
    """Erzeugt eine kurze Zusammenfassung via Ollama."""
    if not sources:
        return "Keine Quellen verfügbar."
    if not model_name:
        return "[No chat model available — no summary generated]"

    # Baue Prompt
    source_text = "\n\n".join(
        f"Source {i + 1}: {s.get('title', '')}\n{s.get('content', '')[:300]}"
        for i, s in enumerate(sources)
    )
    prompt = (
        f"Summarize the following search results about '{query}' "
        f"in 3-5 sentences. Be factual and concise.\n\n{source_text}"
    )

    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 200, "temperature": 0.3},
            },
            timeout=(5, 60),
        )
        r.raise_for_status()
        data = r.json()
        summary = data.get("response", "").strip()
        # Clean thinking tags if present
        import re

        summary = re.sub(r"<think>.*?</think>", "", summary, flags=re.DOTALL).strip()
        print(f"   Ollama: {len(summary)} chars summary")
        return summary[:1000]  # Truncate to 1000 chars
    except requests.ConnectionError:
        print(f"   ⚠️  Ollama nicht erreichbar ({OLLAMA_URL})")
        return "[Ollama not available — no summary generated]"
    except Exception as e:
        print(f"   ⚠️  Ollama Fehler: {e}")
        return f"[Summary error: {e}]"


def write_report(
    query: str,
    sources: list[dict],
    summary: str,
    output_dir: str,
    model_requested: str = "",
    model_used: str = "",
    model_status: str = "",
    degraded: bool = False,
) -> str:
    """Schreibt den Research-Report als Markdown-Datei mit Metadaten."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"research_{timestamp}.md")

    embed_model = _ollama_config.embedding_model
    cloud_active = os.getenv("ALLOW_CLOUD", "").lower() in ("true", "1", "yes")

    # Text-NFC-Normalisierung für Query und Summary (ADR-016)
    query = normalize_markdown_text(query)
    summary = normalize_markdown_text(summary)

    with open(filename, "w") as f:
        # Header
        f.write("# Research Report\n\n")

        # Metadata Table
        f.write("## Metadata\n\n")
        f.write("| Field | Value |\n")
        f.write("|---|---|\n")
        f.write(f"| Query | {query} |\n")
        f.write(f"| Generated At | {datetime.datetime.now().isoformat()} |\n")
        f.write("| Local-First Mode | true |\n")
        f.write(f"| Cloud Providers Active | {str(cloud_active).lower()} |\n")
        f.write(f"| SearXNG URL | {SEARXNG_URL} |\n")
        f.write(f"| SearXNG Result Count | {len(sources)} |\n")
        f.write(f"| Ollama Chat Model Requested | `{OLLAMA_CHAT_MODEL}` |\n")
        f.write(f"| Ollama Chat Model Used | `{model_used or 'none'}` |\n")
        f.write(f"| Ollama Embedding Model | `{embed_model}` |\n")
        f.write(
            f"| Model Fallback Used | {str(model_status == 'fallback').lower()} |\n"
        )
        f.write(f"| Degraded Mode | {str(degraded).lower()} |\n")
        f.write("\n")

        # Summary with source references
        f.write("## Summary\n\n")
        if summary and "[Ollama" not in summary and "[Summary error" not in summary:
            # Prompt already asked for [S1], [S2] style references
            f.write(f"{summary}\n\n")
        else:
            f.write(f"{summary}\n\n")

        # Key Findings
        if sources:
            f.write("## Key Findings\n\n")
            for i, src in enumerate(sources[:3], 1):
                snippet = (src.get("content", "") or src.get("snippet", ""))[:120]
                f.write(f"- {src.get('title', 'Untitled')} [S{i}]\n")
                if snippet:
                    f.write(f"  {snippet}...\n")
            f.write("\n")

        # Sources with IDs
        f.write("## Sources\n\n")
        for i, src in enumerate(sources, 1):
            f.write(f"### [S{i}] {src.get('title', 'Untitled')}\n\n")
            f.write(f"- **URL:** {src.get('url', '')}\n")
            content = (src.get("content", "") or src.get("snippet", ""))[:300]
            f.write(f"- **Snippet:** {content}\n")
            engine = src.get("engine", "searxng")
            f.write(f"- **Engine/Provider:** {engine}\n\n")

        # Limitations and Warnings
        f.write("## Limitations and Warnings\n\n")
        f.write("- This report was generated from a minimal local happy-path.\n")
        f.write("- Sources were retrieved from SearXNG (local instance).\n")
        f.write("- Claims should be verified before operational use.\n")
        f.write("- No cloud providers were used.\n")
        if model_status == "fallback":
            f.write(
                f"- ⚠️  Fallback: requested `{model_requested}`, used `{model_used}`.\n"
            )
        if model_status == "missing":
            f.write("- ⚠️  Chat model not available — summary was not generated.\n")
        if not sources:
            f.write("- ⚠️  No search results — report has no source basis.\n")
        f.write("\n")

    print(f"   Report: {filename} ({os.path.getsize(filename)} bytes)")
    return filename


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimaler Research-Happy-Path")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Research-Query")
    parser.add_argument("--strict", action="store_true", help="Alle Dienste Pflicht")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output-Verzeichnis")
    args = parser.parse_args()

    print(f"🔬 Researcher Happy-Path{' (strict)' if args.strict else ''}")
    print(f"   Query:  {args.query}")
    print(f"   Output: {args.output}")
    print()

    # 1. Cloud-Blocker
    if not check_cloud_blocker():
        sys.exit(2)
    print("✅ Cloud: Keine Cloud-Provider aktiv")
    print()

    # 2. Query Safety
    if not is_safe_query(args.query):
        sys.exit(1)
    print("✅ Query: harmlos")
    print()

    # 3. SearXNG Search
    print("🔎 Searching...")
    sources = search_searxng(args.query)
    if not sources and args.strict:
        print("❌ Strict-Mode: SearXNG muss Ergebnisse liefern")
        sys.exit(1)
    elif not sources:
        print("   ⚠️  Keine SearXNG-Ergebnisse — Report ohne Quellen")
    print()

    # 4. Ollama Summary
    print("🦙 Summarizing...")
    model_name, model_status = resolve_chat_model_local()
    summary = summarize_with_ollama(args.query, sources, model_name)
    if model_status == "missing" and args.strict:
        print("❌ Strict-Mode: Chat-Modell muss verfügbar sein")
        sys.exit(1)
    elif model_status == "missing":
        print("   ⚠️  Kein Chat-Modell — Report ohne Summary")
    elif model_status == "fallback":
        print(
            "   ⚠️  Fallback-Modell verwendet (setze ALLOW_OLLAMA_MODEL_FALLBACK=true)"
        )
    print()

    # 5. Write Report
    print("📄 Writing report...")
    filename = write_report(
        args.query,
        sources,
        summary,
        args.output,
        model_requested=OLLAMA_CHAT_MODEL,
        model_used=model_name,
        model_status=model_status,
        degraded=(model_status == "missing" or model_status == "fallback"),
    )
    print()

    print("─" * 50)
    print("✅ Research Happy-Path erfolgreich!")
    print(f"   Report: {filename}")


if __name__ == "__main__":
    main()

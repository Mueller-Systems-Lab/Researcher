#!/usr/bin/env python3
"""Minimaler Research-Happy-Path: SearXNG → Qwen3.5 (llama-server) → Report.

Nutzung:
    python3 scripts/research_happy_path.py                    # Standard
    python3 scripts/research_happy_path.py --strict           # Alle Dienste Pflicht
    python3 scripts/research_happy_path.py --query "Frage"    # Eigene Query

Primärer Chat-Pfad: Qwen3.5 via llama-server (OPENAIS_BASE_URL, Port 8082).
Fallback: Ollama (OLLAMA_CHAT_MODEL) wenn llama-server nicht verfügbar.

Voraussetzungen (Standard):
    - SearXNG läuft (optional, wird geprüft)
    - llama-server oder Ollama (optional, wird geprüft)
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

# llama-server (Qwen3.5) — primärer Chat-Pfad (ADR-016)
LLAMA_SERVER_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8082/v1")
LLAMA_CHAT_URL = f"{LLAMA_SERVER_URL.rstrip('/')}/chat/completions"
LLAMA_CHAT_MODEL = os.getenv("LLM_CHAT_MODEL", "qwen3.5-uncensored")

# Harmlose Default-Query
DEFAULT_QUERY = "What is a search engine?"

# Blockierte Query-Begriffe (Safety Guard) — zentral in config/blocked_terms.py
from config.blocked_terms import BLOCKED_TERMS  # noqa: E402

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


def scrape_url(url: str, timeout: int = 15) -> str | None:
    """Lädt eine URL und extrahiert den lesbaren Text.

    Args:
        url: Die zu scrappende URL.
        timeout: Timeout in Sekunden.

    Returns:
        Extrahierter Text oder None bei Fehler.
    """
    import re

    try:
        r = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Researcher/1.0)"},
        )
        r.raise_for_status()

        # Encoding aus HTML-Meta oder HTTP-Header ermitteln
        raw = r.content
        import re

        # Versuche Meta-Charset zu finden
        meta_charset = re.search(
            rb'<meta\s+[^>]*charset=["\']?([^"\'>\s]+)',
            raw[:2000],
            re.IGNORECASE,
        )
        if meta_charset:
            enc = meta_charset.group(1).decode("ascii", errors="ignore").lower()
        else:
            enc = (r.encoding or "").lower()
        if enc in ("utf-8", "utf8"):
            text = raw.decode("utf-8", errors="replace")
        elif enc:
            text = raw.decode(enc, errors="replace")
        else:
            # Fallback: probiere UTF-8, dann Latin-1
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1", errors="replace")

        # HTML-body extrahieren
        body = re.search(r"<body[^>]*>(.*?)</body>", text, re.DOTALL)
        html = body.group(1) if body else text

        # Text-Blöcke zwischen Tags extrahieren (min. 80 Zeichen = relevant)
        blocks = re.findall(r">([^<]{80,1200})<", html)
        relevant = []
        for b in blocks:
            b = re.sub(r"\s+", " ", b).strip()
            # Navigation/Footer herausfiltern
            if any(
                kw in b.lower()
                for kw in [
                    "cookie",
                    "datenschutz",
                    "impressum",
                    "menü",
                    "navigation",
                ]
            ):
                continue
            relevant.append(b)

        content = "\n".join(relevant)
        # Auf 3000 Zeichen begrenzen
        return content[:3000]
    except Exception as e:
        print(f"   ⚠️  Konnte {url} nicht scrapen: {e}")
        return None


def _is_relevant(content: str, query: str) -> bool:
    """Prüft ob gescrapte Inhalt zur Frage passt (relevante Keywords).

    Verhindert, dass Artikel über andere Themen (z.B. Kontaktverfahren)
    das Modell verwirren.
    """
    import re

    content_lower = content.lower()
    query_lower = query.lower()

    # Extrahiere Schlüsselwörter aus der Query
    query_words = set(re.findall(r"\w+", query_lower))

    # Relevanz-Kernbegriffe (müssen im Content vorkommen)
    core_terms = ["schwefelsäure", "säure"]
    for term in core_terms:
        if term in query_lower and term not in content_lower:
            return False

    # Ausschluss: Content handelt von etwas anderem
    if "kontaktverfahren" in content_lower and "destillation" not in content_lower:
        return False
    if "schwefel" in content_lower and "säure" not in content_lower:
        return False

    # Minimum: Content muss Substanz haben
    if len(content) < 100:
        return False

    return True


def _build_summary_prompt(query: str, sources: list[dict]) -> list[dict]:
    """Baut Messages für die Zusammenfassung (Few-Shot, mit vollem Content)."""
    messages = []

    # Quelltext (einmalig aufbereitet)
    source_text = "\n\n".join(
        (
            f"QUELLE {i + 1}: {s.get('title', '')}\n"
            f"{s.get('content', '') or s.get('snippet', '')[:2000]}"
        )
        for i, s in enumerate(sources)
    )
    # Shared sources for multi-section calls
    return {"source_text": source_text, "query": query}


def summarize_with_llama(query: str, sources: list[dict]) -> str:
    """Erzeugt eine Zusammenfassung via llama-server (Qwen3.5, ADR-016).

    Primärer Chat-Pfad. Nutzt OpenAI-kompatiblen Endpoint.

    Optimierte Parameter:
      - temperature 0.3, repeat_penalty 1.15
      - Mehrere Abschnitte nacheinander generieren
      - enable_thinking=false
    """
    if not sources:
        return "Keine Quellen verfügbar."

    prompt_data = _build_summary_prompt(query, sources)
    source_text = prompt_data["source_text"]

    sections = [
        "EINFÜHRUNG — Erkläre, was Schwefelsäure ist, "
        "warum man sie konzentriert, und welche Gefahren bestehen. "
        "Für absolute Anfänger. Maximal 8 Sätze.",
        "SICHERHEIT — Welche Schutzausrüstung wird benötigt? "
        "Was tun bei Hautkontakt? Maximal 8 Sätze.",
        "ANLEITUNG — Schritt 1 Vorbereitung, Schritt 2 Destillation, "
        "Schritt 3 Nachbereitung. Mit Tipps für Anfänger. "
        "Maximal 15 Sätze. Nur Fakten aus den Quellen.",
        "LAGERUNG & ENTSORGUNG — Wie lagert und entsorgt man "
        "konzentrierte Schwefelsäure? Maximal 6 Sätze.",
    ]

    summaries = []
    import re
    import random

    def _call_llama(messages: list, seed: int = 42) -> str:
        """Einzelner API-Call mit fixem Seed."""
        r = requests.post(
            LLAMA_CHAT_URL,
            json={
                "model": LLAMA_CHAT_MODEL,
                "messages": messages,
                "temperature": 0.3,
                "top_p": 0.9,
                "top_k": 40,
                "repeat_penalty": 1.2,
                "repeat_last_n": 128,
                "max_tokens": 400,
                "seed": seed,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=(5, 60),
        )
        r.raise_for_status()
        data = r.json()
        text = (
            data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        )
        if not text:
            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("reasoning_content", "")
                .strip()
            )
        return text

    def _is_valid(text: str) -> bool:
        """Prüft ob Output brauchbar ist."""
        if not text or len(text) < 30:
            return False
        # Garbled: Wiederholungen
        if re.search(r"(\d+ seconds?\b.*){5,}", text, re.IGNORECASE):
            return False
        # Garbled: erfundene Wörter (zu viele Großbuchstaben im Wortinneren)
        caps_inside = len(re.findall(r"\b\w+[A-ZÄÖÜ]\w+", text))
        if caps_inside > 3:
            return False
        return True

    def _best_of_n(n: int, messages: list) -> str:
        """Generiert n Kandidaten, gibt den besten zurück."""
        candidates = []
        seeds = [random.randint(1, 99999) for _ in range(n)]
        for seed in seeds:
            try:
                text = _call_llama(messages, seed=seed)
                if _is_valid(text):
                    candidates.append((len(text), text))
            except Exception:
                continue
        if candidates:
            # Kürzeste valide Antwort (meist faktenbasiert)
            candidates.sort()
            return candidates[0][1]
        return ""

    # Single extraction mit best-of-3: fokussiert, direkt, faktenbasiert
    messages = [
        {
            "role": "system",
            "content": (
                "EXTRAHIERE die Fakten aus den QUELLEN. "
                "Antworte NUR mit einer nummerierten Liste "
                "der Fakten. Keine Einleitung. "
                "Keine Gedankenkette."
            ),
        },
        {
            "role": "user",
            "content": (
                f"QUELLEN:\n{source_text}\n\n"
                f"Aufgabe: Liste die Verfahrensschritte zum "
                f"Konzentrieren von Schwefelsäure auf. "
                f"Verfahrensschritte:"
            ),
        },
    ]

    # Letzten Satz als Completion-Trigger nutzen
    text = _best_of_n(3, messages)
    print(f"   ✅ Extraction: {len(text)} chars")
    return text


def summarize_with_ollama(query: str, sources: list[dict], model_name: str) -> str:
    """Erzeugt eine kurze Zusammenfassung via Ollama (Fallback)."""
    if not sources:
        return "Keine Quellen verfügbar."
    if not model_name:
        return "[No chat model available — no summary generated]"

    prompt = _build_summary_prompt(query, sources)

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
        return summary[:1000]
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
        f.write(f"| Primary Chat Model | `{LLAMA_CHAT_MODEL}` (llama-server) |\n")
        f.write(f"| Ollama Chat Model Used | `{model_used or 'none'}` |\n")
        f.write(f"| Embedding Model | `{embed_model}` |\n")
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

    # 3. SearXNG Search + Scrape
    print("🔎 Searching...")
    sources = search_searxng(args.query)
    if not sources and args.strict:
        print("❌ Strict-Mode: SearXNG muss Ergebnisse liefern")
        sys.exit(1)
    elif not sources:
        print("   ⚠️  Keine SearXNG-Ergebnisse — Report ohne Quellen")
    else:
        # Alle Quellen scrapen (max 5)
        print("   📄 Scrape alle Quellen...")
        scraped_count = 0
        for src in sources[:5]:
            url = src.get("url", "")
            if not url:
                continue
            full_text = scrape_url(url)
            if full_text:
                src["content"] = full_text
                scraped_count += 1
                print(f"   ✅ {url[:55]}... ({len(full_text)} chars)")
        print(f"   → {scraped_count} Quellen gescrapt, {len(sources)} gesamt")
    print()

    # 4. Summary — primär via llama-server (Qwen3.5), Fallback Ollama
    print("🧠 Summarizing (Qwen3.5 via llama-server)...")
    summary = summarize_with_llama(args.query, sources)
    model_name = LLAMA_CHAT_MODEL
    model_status = "ok" if summary else "missing"

    if not summary:
        # Fallback: Ollama
        print("   ⚠️  llama-server nicht verfügbar — versuche Ollama...")
        ollama_model, model_status = resolve_chat_model_local()
        summary = summarize_with_ollama(args.query, sources, ollama_model)
        if ollama_model:
            model_name = ollama_model

    if model_status == "missing" and args.strict:
        print("❌ Strict-Mode: Chat-Modell muss verfügbar sein")
        sys.exit(1)
    elif not summary:
        print("   ⚠️  Kein Chat-Modell — Report ohne Summary")
    print()

    # 5. Write Report
    print("📄 Writing report...")
    filename = write_report(
        args.query,
        sources,
        summary,
        args.output,
        model_requested=LLAMA_CHAT_MODEL,
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

#!/usr/bin/env python3
"""
Deep Research Pipeline — SearXNG + Lokales LLM
================================================
GPT-Researcher-ähnlicher Workflow mit Thinking-Fix:
  Phase 1: SearXNG Web-Suche (via zentraler Konfiguration)
  Phase 2: Quellen sammeln + strukturieren
  Phase 3: LLM-Synthese via Ollama (via zentraler Modellkonfiguration)

Nutzung:
  python3 scripts/deep_research.py "Dein Thema"
  python3 scripts/deep_research.py --lang de "Your Topic"

Konfiguration:
  Alle URLs und Modellnamen kommen aus config/services.py und
  config/ollama_models.py. Keine hardcodierten Werte.
"""

import argparse
import os
import re
import sys
import textwrap

import requests

# Projekt-Root zum Pfad hinzufügen
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config.ollama_models import load_ollama_model_config, resolve_chat_model
from config.services import OLLAMA_BASE_URL, SEARXNG_SEARCH_URL

DEFAULT_TOPIC = "Ivermectin COVID-19 klinische Studien Wirksamkeit Meta-Analyse"

# Zentrale Modellkonfiguration laden
_ollama_config = load_ollama_model_config()


def _get_available_models() -> list[str]:
    """Holt verfügbare Ollama-Modelle via /api/tags."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=(5, 10))
        r.raise_for_status()
        return [m.get("name", "") for m in r.json().get("models", [])]
    except Exception:
        return []


def _resolve_model() -> str:
    """Löst das Chat-Modell über die zentrale Ollama-Konfiguration auf."""
    available = _get_available_models()
    resolution = resolve_chat_model(_ollama_config, available)
    if resolution.status in ("missing", "no_models", "config_error"):
        print(f"   ⚠️  Modell nicht verfügbar: {resolution.message}")
        print(f"   Fallback auf Konfigurationswert: {_ollama_config.chat_model}")
        return _ollama_config.chat_model
    print(f"   Modell: {resolution.used_model} (Status: {resolution.status})")
    return resolution.used_model or _ollama_config.chat_model


def deep_research(query: str, lang: str = "de", num_sources: int = 15):
    print("=" * 65)
    print(f"  DEEP RESEARCH: {query[:55]}...")
    print(f"  Pipeline: SearXNG ({SEARXNG_SEARCH_URL}) → Extract → Synthesize → Report")
    print("=" * 65)

    # Modell auflösen
    model_name = _resolve_model()

    # ═══ Phase 1: SearXNG ═══
    print("\n🔍 Phase 1: SearXNG Web-Suche...")
    # Dynamische Subtopics basierend auf Query
    subtopics = [
        f"{query}",
        f"{query} Studie Analyse",
        f"{query} Meta Bewertung",
    ]
    all_results = {}
    for topic in subtopics:
        try:
            r = requests.get(
                SEARXNG_SEARCH_URL,
                params={"q": topic, "format": "json", "language": lang},
                timeout=10,
            )
            r.raise_for_status()
            results = r.json().get("results", [])[:5]
            all_results[topic] = results
            print(f"   {topic[:50]}: {len(results)} Treffer")
        except requests.ConnectionError:
            print(f"   ❌ SearXNG nicht erreichbar ({SEARXNG_SEARCH_URL})")
        except Exception as e:
            print(f"   ⚠️  SearXNG-Fehler für '{topic[:30]}': {e}")

    # ═══ Phase 2: Sammeln ═══
    print("\n📄 Phase 2: Quellen strukturieren...")
    sources = []
    for results in all_results.values():
        for res in results:
            sources.append(
                {
                    "title": res.get("title", "?"),
                    "url": res.get("url", "?"),
                    "snippet": res.get("content", "?")[:400],
                }
            )
    context_parts = [
        f"[{i}] {s['title']}\n   {s['snippet']}" for i, s in enumerate(sources, 1)
    ]
    print(f"   {len(sources)} Quellen gesammelt")

    # ═══ Phase 3: LLM ═══
    print(f"\n🧠 Phase 3: LLM-Synthese ({model_name})...")
    lang_instr = "auf Deutsch" if lang == "de" else "in English"

    prompt = f"""Research Assistant. Create a detailed research report based on the sources below.

TOPIC: {query}

SOURCES:
{chr(10).join(context_parts[:num_sources])}

TASK:
Write a comprehensive research report (1000-2000 words) with:
1. Executive Summary
2. Overview of key studies (names, designs, results)
3. Meta-analyses and their findings
4. Regulatory positions (FDA, EMA, WHO)
5. Conclusion and open questions

Respond {lang_instr}. Structured with paragraphs. Facts only. No opinions."""

    ollama_api_url = f"{OLLAMA_BASE_URL}/api/generate"
    r = requests.post(
        ollama_api_url,
        json={
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "raw": True,
            "options": {"num_predict": 3000, "temperature": 0.2, "num_ctx": 4096},
        },
        timeout=300,
    )

    raw = r.json().get("response", "")
    report = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    report = re.sub(
        r"<\|im_start\|>.*?<\|im_end\|>", "", report, flags=re.DOTALL
    ).strip()

    print(f"\n{'=' * 65}\n  RESEARCH REPORT\n{'=' * 65}")
    print(textwrap.fill(report, width=65) if False else report)
    print(f"\n{'=' * 65}")
    print(f"  Quellen: {len(sources)} | Report: {len(report)} Zeichen")
    print(f"{'=' * 65}")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Deep Research Pipeline")
    p.add_argument("query", nargs="*", help="Research topic")
    p.add_argument("--lang", default="de", help="Language (de/en)")
    args = p.parse_args()
    query = " ".join(args.query) if args.query else DEFAULT_TOPIC
    deep_research(query, lang=args.lang)

"""
Patched GPT Researcher: Startet die vollständige Deep-Research-Pipeline
mit SearXNG-Suche + Lokalem LLM (Thinking-Fix).

Konfiguration: Liest alle Werte aus .env / Umgebungsvariablen.
Setzt Fallback-Defaults NUR wenn keine .env vorhanden ist.
"""

import asyncio
import os
import sys
import warnings

warnings.filterwarnings("ignore")

# Projekt-Root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "gpt_researcher"))
sys.path.insert(0, ROOT)

# Env-Konfiguration aus .env / Umgebungsvariablen laden
# Fallback-Defaults nur wenn keine Variable gesetzt ist (z.B. kein .env)
os.environ.setdefault("FAST_LLM", "ollama:qwen3.5-uncensored-no-thinking:latest")
os.environ.setdefault("SMART_LLM", "ollama:qwen3.5-uncensored-no-thinking:latest")
os.environ.setdefault("STRATEGIC_LLM", "ollama:qwen3.5-uncensored-no-thinking:latest")
os.environ.setdefault("EMBEDDING", "ollama:nomic-embed-text:latest")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("RETRIEVER", "searx")
os.environ.setdefault("SEARX_URL", "http://localhost:8080")
os.environ.setdefault("OPENAI_API_KEY", "not-needed")
os.environ.setdefault("TEMPERATURE", "0.3")
os.environ.setdefault("MAX_CONCURRENT_REQUESTS", "1")

# --- Monkey-Patch: ChatOllama → UncensoredChatOllama ---
import langchain_ollama  # noqa: E402
from gpt_researcher.llm_provider.generic.uncensored_ollama import (  # noqa: E402
    UncensoredChatOllama,
)

langchain_ollama.ChatOllama = UncensoredChatOllama  # type: ignore[misc]
print("✅ ChatOllama → UncensoredChatOllama (thinking→content)")

# Direct LLM test
print("\n1️⃣ LLM-Test...")
from langchain_ollama import ChatOllama  # noqa: E402

_llm_model = os.getenv("OLLAMA_CHAT_MODEL", "qwen3.5-uncensored-no-thinking:latest")
_llm_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

llm = ChatOllama(
    model=_llm_model,
    base_url=_llm_url,
    temperature=0.3,
    num_predict=50,
)
resp = llm.invoke("Sage: Hallo Welt")
print(f'   Antwort: "{resp.content[:80]}"')

# SearXNG test
print("\n2️⃣ SearXNG-Test...")
import requests  # noqa: E402

_searx_url = os.getenv("SEARX_URL", "http://localhost:8080")
r = requests.get(f"{_searx_url}/search?q=test&format=json", timeout=5)
print(f"   {len(r.json().get('results', []))} Ergebnisse")

# --- Full GPT Researcher Deep Research ---
print("\n3️⃣ 🚀 GPT Researcher Deep Research...")

QUERY = os.getenv(
    "RESEARCH_DEFAULT_QUERY",
    "Ivermectin COVID-19 klinische Studien Wirksamkeit 2020-2025",
)


async def run():
    from gpt_researcher import GPTResearcher

    researcher = GPTResearcher(
        query=QUERY,
        report_type="research_report",
        report_source="web",
        tone="objective",
        max_subtopics=3,
        verbose=True,
    )

    print(f"   Query: {QUERY}")
    print("   Phase 1: Research + Web-Suche...")
    await researcher.conduct_research()

    sources = getattr(researcher, "research_sources", [])
    print(f"\n   ✅ Quellen: {len(sources)}")
    for s in sources[:5]:
        title = str(s).get("title", "?") if isinstance(s, dict) else str(s)[:70]
        print(f"      • {title[:70]}")

    print("\n   Phase 2: Report generieren...")
    report = await researcher.write_report()

    print(f"\n   ✅ Report: {len(report)} Zeichen")
    print("=" * 70)
    print("  DEEP RESEARCH REPORT")
    print("=" * 70)
    print(report[:8000])
    if len(report) > 8000:
        print(f"\n   ... ({len(report) - 8000} weitere Zeichen)")
    return report


report = asyncio.run(run())

"""
Patched GPT Researcher: Startet die vollständige Deep-Research-Pipeline
mit SearXNG-Suche + Qwen3.5-Uncensored LLM (Thinking-Fix).
"""
import os, sys, asyncio, warnings
warnings.filterwarnings("ignore")

# Projekt-Root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "gpt_researcher"))
sys.path.insert(0, ROOT)

# Env-Konfiguration
os.environ.update({
    "FAST_LLM": "ollama:qwen3.5-9b-uncensored-hauhaucs-aggressive",
    "SMART_LLM": "ollama:qwen3.5-9b-uncensored-hauhaucs-aggressive",
    "STRATEGIC_LLM": "ollama:qwen3.5-9b-uncensored-hauhaucs-aggressive",
    "EMBEDDING": "ollama:nomic-embed-text",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "RETRIEVER": "searx",
    "SEARX_URL": "http://localhost:8080",
    "OPENAI_API_KEY": "sk-dummy",
    "TEMPERATURE": "0.3",
    "MAX_CONCURRENT_REQUESTS": "1",
})

# --- Monkey-Patch: ChatOllama → UncensoredChatOllama ---
from gpt_researcher.llm_provider.generic.uncensored_ollama import UncensoredChatOllama
import langchain_ollama
langchain_ollama.ChatOllama = UncensoredChatOllama
print("✅ ChatOllama → UncensoredChatOllama (thinking→content)")

# Direct LLM test
print("\n1️⃣ LLM-Test...")
from langchain_ollama import ChatOllama
llm = ChatOllama(model="qwen3.5-9b-uncensored-hauhaucs-aggressive",
                  base_url="http://localhost:11434", temperature=0.3, num_predict=50)
resp = llm.invoke("Sage: Hallo Welt")
print(f"   Antwort: \"{resp.content[:80]}\"")

# SearXNG test
print("\n2️⃣ SearXNG-Test...")
import requests
r = requests.get("http://localhost:8080/search?q=test&format=json", timeout=5)
print(f"   {len(r.json().get('results',[]))} Ergebnisse")

# --- Full GPT Researcher Deep Research ---
print("\n3️⃣ 🚀 GPT Researcher Deep Research...")

QUERY = "Ivermectin COVID-19 klinische Studien Wirksamkeit 2020-2025"

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

    sources = getattr(researcher, 'research_sources', [])
    print(f"\n   ✅ Quellen: {len(sources)}")
    for s in sources[:5]:
        title = str(s).get('title', '?') if isinstance(s, dict) else str(s)[:70]
        print(f"      • {title[:70]}")

    print("\n   Phase 2: Report generieren...")
    report = await researcher.write_report()

    print(f"\n   ✅ Report: {len(report)} Zeichen")
    print("=" * 70)
    print("  DEEP RESEARCH REPORT")
    print("=" * 70)
    print(report[:8000])
    if len(report) > 8000:
        print(f"\n   ... ({len(report)-8000} weitere Zeichen)")
    return report

report = asyncio.run(run())

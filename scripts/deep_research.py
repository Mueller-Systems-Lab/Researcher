#!/usr/bin/env python3
"""
Deep Research Pipeline — SearXNG + Qwen3.5 Uncensored
======================================================
GPT-Researcher-ähnlicher Workflow mit Thinking-Fix:
  Phase 1: SearXNG Web-Suche (mehrere Sub-Themen)
  Phase 2: Quellen sammeln + strukturieren
  Phase 3: LLM-Synthese via Ollama raw generate

Nutzung:
  python3 scripts/deep_research.py "Dein Thema"
  python3 scripts/deep_research.py --lang de "Your Topic"
"""
import argparse, json, re, requests, sys, textwrap

DEFAULT_TOPIC = "Ivermectin COVID-19 klinische Studien Wirksamkeit Meta-Analyse"

def deep_research(query: str, lang: str = "de", num_sources: int = 15):
    print("=" * 65)
    print(f"  DEEP RESEARCH: {query[:55]}...")
    print(f"  Pipeline: SearXNG → Extract → Synthesize → Report")
    print("=" * 65)

    # ═══ Phase 1: SearXNG ═══
    print("\n🔍 Phase 1: SearXNG Web-Suche...")
    subtopics = [
        f"{query} RCT randomisierte Studien",
        f"{query} Meta-Analyse Cochrane Review",
        f"{query} Regulierungsbehörden FDA EMA Bewertung",
    ]
    all_results = {}
    for topic in subtopics:
        r = requests.get("http://localhost:8080/search", params={
            "q": topic, "format": "json", "language": lang
        }, timeout=10)
        results = r.json().get("results", [])[:5]
        all_results[topic] = results
        print(f"   {topic[:50]}: {len(results)} Treffer")

    # ═══ Phase 2: Sammeln ═══
    print("\n📄 Phase 2: Quellen strukturieren...")
    sources = []
    for results in all_results.values():
        for res in results:
            sources.append({
                "title": res.get("title", "?"),
                "url": res.get("url", "?"),
                "snippet": res.get("content", "?")[:400],
            })
    context_parts = [
        f"[{i}] {s['title']}\n   {s['snippet']}"
        for i, s in enumerate(sources, 1)
    ]
    print(f"   {len(sources)} Quellen gesammelt")

    # ═══ Phase 3: LLM ═══
    print("\n🧠 Phase 3: LLM-Synthese (Qwen3.5 Uncensored)...")
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

    r = requests.post("http://localhost:11434/api/generate", json={
        "model": "qwen3.5-9b-uncensored-hauhaucs-aggressive",
        "prompt": prompt,
        "stream": False,
        "raw": True,
        "options": {"num_predict": 3000, "temperature": 0.2, "num_ctx": 4096}
    }, timeout=300)

    raw = r.json().get("response", "")
    report = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
    report = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', report, flags=re.DOTALL).strip()

    print(f"\n{'='*65}\n  RESEARCH REPORT\n{'='*65}")
    print(textwrap.fill(report, width=65) if False else report)
    print(f"\n{'='*65}")
    print(f"  Quellen: {len(sources)} | Report: {len(report)} Zeichen")
    print(f"{'='*65}")
    return report

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Deep Research Pipeline")
    p.add_argument("query", nargs="*", help="Research topic")
    p.add_argument("--lang", default="de", help="Language (de/en)")
    args = p.parse_args()
    query = " ".join(args.query) if args.query else DEFAULT_TOPIC
    deep_research(query, lang=args.lang)

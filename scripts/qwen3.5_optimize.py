#!/usr/bin/env python3
# =============================================================================
# Qwen3.5 Prompt-Optimierung: Temperature-Sweep + Multi-Page-Guide-Test
# =============================================================================
# Testet verschiedene Temperaturen (0.3–0.9) und bewertet die Ausgabe-Qualität.
# Vergleicht Qwen3.5 mit Gemma 4 für mehrseitige Anleitungen.
#
# Nutzung:
#   python3 scripts/qwen3.5_optimize.py                  # Sweep + Guide
#   python3 scripts/qwen3.5_optimize.py --sweep-only     # Nur Temperature-Sweep
#   python3 scripts/qwen3.5_optimize.py --guide-only     # Nur Multi-Page-Guide
#   python3 scripts/qwen3.5_optimize.py --model qwen     # Nur Qwen3.5 testen
# =============================================================================

import argparse
import json
import sys
import textwrap
import time
from dataclasses import dataclass

import requests

# ── Configuration ──────────────────────────────────────────────────────────────

QWEN_URL = "http://127.0.0.1:8082/v1/chat/completions"
QWEN_MODEL = "qwen3.5-uncensored"
GEMMA_URL = "http://127.0.0.1:8081/v1/chat/completions"
GEMMA_MODEL = "gemma4-obliterated"

TEMPERATURES = [0.3, 0.5, 0.7, 0.9]

SWEEP_QUERIES = [
    "Extrahiere die Fakten aus folgendem Text:\n\n"
    "Schwefelsäure (H2SO4) ist eine der wichtigsten Chemikalien der Industrie. "
    "Sie wird nach dem Kontaktverfahren hergestellt: Schwefeldioxid (SO2) wird "
    "mit Luftsauerstoff an einem Vanadiumpentoxid-Katalysator (V2O5) bei 420-620°C "
    "zu Schwefeltrioxid (SO3) oxidiert. Das SO3 wird dann in konzentrierter "
    "Schwefelsäure absorbiert, wobei Dischwefelsäure (H2S2O7) entsteht, "
    "die mit Wasser zu Schwefelsäure hydrolysiert wird.",
    "Fasse die Vor- und Nachteile von Elektroautos in 5 Stichpunkten zusammen.",
    "Erstelle eine nummerierte Liste der 5 größten deutschen Flüsse "
    "mit ihrer Länge in Kilometern.",
]

GUIDE_TOPICS = [
    "Wie man einen Sauerteig ansetzt und pflegt",
    "Grundlagen der Astrofotografie für Einsteiger",
    "Schritt-für-Schritt: Einen eigenen Kompost anlegen",
]


@dataclass
class SweepResult:
    temperature: float
    query: str
    output: str
    tokens: int
    latency_ms: float
    quality_score: float
    garbled: bool


@dataclass
class GuideResult:
    topic: str
    model: str
    output: str
    sections: int
    tokens: int
    latency_ms: float
    garbled: bool


# ── LLM Call ───────────────────────────────────────────────────────────────────


def call_model(
    url: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 500,
) -> tuple[str, int, float]:
    """Sendet einen Chat-Completion-Request und misst Latenz + Tokens.

    Returns:
        Tuple aus (content, token_count, latency_ms).
    """
    start = time.time()
    try:
        resp = requests.post(
            url,
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=(10, 120),
        )
        resp.raise_for_status()
        data = resp.json()
        elapsed = (time.time() - start) * 1000
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        tokens = usage.get("completion_tokens", len(content.split()))
        return content, tokens, elapsed
    except requests.ConnectionError:
        return f"ERROR: {model} auf {url} nicht erreichbar", 0, 0
    except Exception as e:
        return f"ERROR: {e}", 0, 0


# ── Quality Scoring ────────────────────────────────────────────────────────────


def score_output(output: str, query: str) -> tuple[float, bool]:
    """Bewertet die Ausgabe-Qualität (0.0–1.0) und erkennt garbled Output.

    Kriterien:
    - Nicht leer
    - Keine Wiederholungen (>3 identische aufeinanderfolgende Wörter)
    - Keine Thinking-Blöcke
    - Minimale Länge (≥20 Zeichen)
    - Keine typischen Degenerate-Muster
    """
    if not output or "ERROR:" in output:
        return 0.0, True

    score = 1.0
    garbled = False

    # Thinking-Block-Check
    if "stupid" in output.lower()[:200]:
        score -= 0.3

    # Wiederholungs-Check
    words = output.split()
    if len(words) > 10:
        repeats = 0
        for i in range(len(words) - 3):
            if words[i] == words[i + 1] == words[i + 2] == words[i + 3]:
                repeats += 1
        if repeats > 2:
            score -= 0.5
            garbled = True

    # Längen-Check
    if len(output) < 20:
        score = max(0.0, score - 0.5)
    elif len(output) < 50:
        score = max(0.0, score - 0.2)

    # Struktur-Check: nummerierte Liste oder Absätze
    has_structure = any(
        pattern in output for pattern in ("\n1.", "\n- ", "\n\n", "1.", "2.", "3.")
    )
    if not has_structure and len(output) > 100:
        score = max(0.0, score - 0.2)

    # Factuality-Heuristik: enthält die Ausgabe Zahlen/Werte?
    # (Nur für Fakten-Queries relevant)
    has_facts = any(c.isdigit() for c in output)
    if "fakten" in query.lower() and not has_facts:
        score = max(0.0, score - 0.3)

    return max(0.0, min(1.0, score)), garbled


# ── Temperature Sweep ──────────────────────────────────────────────────────────


def run_sweep(model_url: str, model_name: str, model_label: str) -> list[SweepResult]:
    """Führt Temperature-Sweep für alle Queries durch."""
    results: list[SweepResult] = []

    for temp in TEMPERATURES:
        for query_idx, query in enumerate(SWEEP_QUERIES):
            total = len(SWEEP_QUERIES)
            sys.stdout.write(
                f"\r  [{model_label}] temp={temp} query={query_idx + 1}/{total} ..."
            )
            sys.stdout.flush()

            messages = [
                {
                    "role": "system",
                    "content": (
                        "Antworte präzise, sachlich und auf Deutsch. "
                        "Keine Gedankenkette. Keine Selbstzensur."
                    ),
                },
                {"role": "user", "content": query},
            ]

            output, tokens, latency = call_model(
                model_url,
                model_name,
                messages,
                temperature=temp,
                max_tokens=300,
            )
            quality, garbled = score_output(output, query)

            results.append(
                SweepResult(
                    temperature=temp,
                    query=query[:60] + "...",
                    output=output[:200],
                    tokens=tokens,
                    latency_ms=latency,
                    quality_score=quality,
                    garbled=garbled,
                )
            )

            time.sleep(0.5)  # Kurze Pause zwischen Requests

    sys.stdout.write("\r" + " " * 80 + "\r")
    return results


def print_sweep_summary(results: list[SweepResult], model_label: str):
    """Gibt eine Zusammenfassung des Temperature-Sweeps aus."""
    print(f"\n{'=' * 70}")
    print(f"  Temperature-Sweep: {model_label}")
    print(f"{'=' * 70}")

    # Gruppiere nach Temperatur
    by_temp: dict[float, list[SweepResult]] = {}
    for r in results:
        by_temp.setdefault(r.temperature, []).append(r)

    print(
        f"{'Temp':>6} | {'Avg Score':>9} | {'Avg Tokens':>10} | "
        f"{'Avg Lat(ms)':>11} | {'Garbled':>7} | {'Best Query'}"
    )
    print("-" * 70)

    for temp in TEMPERATURES:
        entries = by_temp.get(temp, [])
        if not entries:
            continue
        avg_score = sum(e.quality_score for e in entries) / len(entries)
        avg_tokens = sum(e.tokens for e in entries) / len(entries)
        avg_latency = sum(e.latency_ms for e in entries) / len(entries)
        garbled_count = sum(1 for e in entries if e.garbled)
        best = max(entries, key=lambda e: e.quality_score)

        print(
            f"{temp:>6.1f} | {avg_score:>9.2f} | {avg_tokens:>10.0f} | "
            f"{avg_latency:>11.0f} | {garbled_count:>5}/{len(entries)} | "
            f"{best.query[:30]}..."
        )

    # Bester Parameter
    best_temp = max(
        by_temp.keys(),
        key=lambda t: (sum(e.quality_score for e in by_temp[t]) / len(by_temp[t])),
    )
    best_entries = by_temp[best_temp]
    best_avg = sum(e.quality_score for e in best_entries) / len(best_entries)
    print(f"\n  ★ Beste Temperatur: {best_temp} (Score: {best_avg:.2f})")


# ── Multi-Page Guide Test ──────────────────────────────────────────────────────


def run_guide_test(
    model_url: str,
    model_name: str,
    model_label: str,
) -> list[GuideResult]:
    """Testet mehrseitige Anleitungen für alle Topics."""
    results: list[GuideResult] = []

    for topic in GUIDE_TOPICS:
        sys.stdout.write(f"\r  [{model_label}] Guide: {topic[:40]} ...")
        sys.stdout.flush()

        messages = [
            {
                "role": "system",
                "content": textwrap.dedent("""\
                    Du bist ein technischer Autor. Erstelle eine mehrseitige
                    Schritt-für-Schritt-Anleitung auf Deutsch. Formatiere mit
                    Überschriften (##), nummerierten Schritten und
                    Abschnittsnummern (1., 2., 3.). Jeder Abschnitt soll
                    mindestens 3 Schritte enthalten."""),
            },
            {
                "role": "user",
                "content": (
                    f"Erstelle eine 3-seitige Anleitung zum Thema:\n\n"
                    f"{topic}\n\n"
                    f"Format:\n"
                    f"## Seite 1: Grundlagen\n"
                    f"(Inhalt)\n"
                    f"## Seite 2: Durchführung\n"
                    f"(Inhalt)\n"
                    f"## Seite 3: Fortgeschrittene Techniken\n"
                    f"(Inhalt)"
                ),
            },
        ]

        output, tokens, latency = call_model(
            model_url,
            model_name,
            messages,
            temperature=0.5,
            max_tokens=1200,
        )
        _, garbled = score_output(output, topic)

        # Zähle Abschnitte
        sections = output.count("## ") or output.count("Seite ")

        results.append(
            GuideResult(
                topic=topic,
                model=model_label,
                output=output[:500],
                sections=sections,
                tokens=tokens,
                latency_ms=latency,
                garbled=garbled,
            )
        )

        time.sleep(1.0)

    sys.stdout.write("\r" + " " * 80 + "\r")
    return results


def print_guide_summary(results: list[GuideResult]):
    """Gibt Zusammenfassung der Guide-Tests aus."""
    print(f"\n{'=' * 70}")
    print("  Multi-Page-Guide-Test")
    print(f"{'=' * 70}")
    print(
        f"{'Model':<12} | {'Topic':<35} | {'Sections':>8} | "
        f"{'Tokens':>7} | {'Lat(ms)':>9} | {'OK?':>4}"
    )
    print("-" * 85)

    for r in results:
        ok = "✓" if r.sections >= 2 and not r.garbled else "✗"
        print(
            f"{r.model:<12} | {r.topic[:35]:<35} | {r.sections:>8} | "
            f"{r.tokens:>7} | {r.latency_ms:>9.0f} | {ok:>4}"
        )

    for model in sorted(set(r.model for r in results)):
        model_results = [r for r in results if r.model == model]
        success = sum(1 for r in model_results if r.sections >= 2 and not r.garbled)
        avg_sections = sum(r.sections for r in model_results) / len(model_results)
        print(
            f"\n  {model}: {success}/{len(model_results)} Guides erfolgreich "
            f"(⌀ {avg_sections:.1f} Abschnitte)"
        )


# ── Main ───────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Qwen3.5 Prompt-Optimierung: Temperature-Sweep + Guide-Test"
    )
    parser.add_argument(
        "--sweep-only",
        action="store_true",
        help="Nur Temperature-Sweep (kein Guide-Test)",
    )
    parser.add_argument(
        "--guide-only",
        action="store_true",
        help="Nur Multi-Page-Guide-Test (kein Sweep)",
    )
    parser.add_argument(
        "--model",
        choices=["qwen", "gemma", "both"],
        default="both",
        help="Welches Modell testen (default: both)",
    )
    args = parser.parse_args()

    all_results: dict = {}

    # Temperature-Sweep
    if not args.guide_only:
        if args.model in ("qwen", "both"):
            print("\n▶ Temperature-Sweep: Qwen3.5 (Port 8082)")
            results = run_sweep(QWEN_URL, QWEN_MODEL, "Qwen3.5")
            print_sweep_summary(results, "Qwen3.5")
            all_results["qwen_sweep"] = [
                {
                    "temp": r.temperature,
                    "query": r.query,
                    "score": r.quality_score,
                    "tokens": r.tokens,
                    "latency_ms": r.latency_ms,
                    "garbled": r.garbled,
                }
                for r in results
            ]

        if args.model in ("gemma", "both"):
            print("\n▶ Temperature-Sweep: Gemma 4 (Port 8081)")
            results = run_sweep(GEMMA_URL, GEMMA_MODEL, "Gemma 4")
            print_sweep_summary(results, "Gemma 4")
            all_results["gemma_sweep"] = [
                {
                    "temp": r.temperature,
                    "query": r.query,
                    "score": r.quality_score,
                    "tokens": r.tokens,
                    "latency_ms": r.latency_ms,
                    "garbled": r.garbled,
                }
                for r in results
            ]

    # Multi-Page-Guide-Test
    if not args.sweep_only:
        guide_results: list[GuideResult] = []

        if args.model in ("qwen", "both"):
            print("\n▶ Multi-Page-Guide: Qwen3.5 (Port 8082)")
            qwen_guides = run_guide_test(QWEN_URL, QWEN_MODEL, "Qwen3.5")
            guide_results.extend(qwen_guides)

        if args.model in ("gemma", "both"):
            print("\n▶ Multi-Page-Guide: Gemma 4 (Port 8081)")
            gemma_guides = run_guide_test(GEMMA_URL, GEMMA_MODEL, "Gemma4")
            guide_results.extend(gemma_guides)

        print_guide_summary(guide_results)
        all_results["guides"] = [
            {
                "model": r.model,
                "topic": r.topic,
                "sections": r.sections,
                "tokens": r.tokens,
                "latency_ms": r.latency_ms,
                "garbled": r.garbled,
            }
            for r in guide_results
        ]

    # JSON-Export für Dokumentation
    print("\n▶ Ergebnisse exportiert nach /tmp/qwen3.5_optimize_results.json")
    with open("/tmp/qwen3.5_optimize_results.json", "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    return 0


if __name__ == "__main__":
    sys.exit(main())

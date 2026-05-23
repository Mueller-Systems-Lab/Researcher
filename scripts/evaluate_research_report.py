#!/usr/bin/env python3
"""Research Report Quality Evaluation.

Bewertet Research-Reports auf Quellenbasis, Nachvollziehbarkeit,
Halluzinationsrisiko und Local-First-Compliance.

Nutzung:
    python3 scripts/evaluate_research_report.py report.md
    python3 scripts/evaluate_research_report.py --latest
    python3 scripts/evaluate_research_report.py --latest --min-score 70
"""

import argparse
import datetime
import json
import os
import re
import sys
from typing import Any

DEFAULT_REPORT_DIR = "reports/research"
DEFAULT_EVAL_DIR = "reports/evaluation"

# Riskante Wörter (Halluzinationsrisiko)
RISK_WORDS_EN = {
    "always",
    "never",
    "proves",
    "guaranteed",
    "definitely",
    "all experts agree",
    "without any doubt",
    "undoubtedly",
}

RISK_WORDS_DE = {
    "immer",
    "niemals",
    "beweist",
    "garantiert",
    "zweifelsfrei",
    "alle experten",
    "ohne jeden zweifel",
}

RISK_WORDS = RISK_WORDS_EN | RISK_WORDS_DE

CLOUD_PROVIDERS = ["openai", "tavily", "anthropic", "google-genai", "gemini"]


def find_latest_report(report_dir: str) -> str:
    """Findet den neuesten Report im Verzeichnis."""
    if not os.path.isdir(report_dir):
        raise FileNotFoundError(f"Report-Verzeichnis nicht gefunden: {report_dir}")

    files = [
        f
        for f in os.listdir(report_dir)
        if f.startswith("research_") and f.endswith(".md")
    ]
    if not files:
        raise FileNotFoundError(f"Keine Reports in {report_dir}")

    files.sort(reverse=True)
    return os.path.join(report_dir, files[0])


def parse_report(filepath: str) -> dict[str, Any]:
    """Parst einen Research-Report und extrahiert Metadaten."""
    with open(filepath) as f:
        content = f.read()

    result: dict[str, Any] = {
        "filepath": filepath,
        "filesize": os.path.getsize(filepath),
        "query": "",
        "source_count": 0,
        "summary": "",
        "has_source_section": False,
        "has_summary_section": False,
        "has_metadata_section": False,
        "has_limitations_section": False,
        "cloud_references": [],
        "model_mentioned": False,
        "model_requested": "",
        "model_used": "",
        "model_fallback": False,
        "degraded": False,
        "source_ids": 0,
        "total_lines": len(content.splitlines()),
    }

    # Extrahiere Query aus Metadata-Tabelle
    m = re.search(r"\|\s*Query\s*\|\s*(.+?)\s*\|", content)
    if m:
        result["query"] = m.group(1).strip()
    else:
        m = re.search(r"\*\*Query:\*\*\s+(.+)", content)
        if m:
            result["query"] = m.group(1).strip()

    # Extrahiere Source Count aus Metadata oder Legacy
    m = re.search(r"\|\s*SearXNG Result Count\s*\|\s*(\d+)", content)
    if m:
        result["source_count"] = int(m.group(1))
    else:
        m = re.search(r"\*\*Sources:\*\*\s+(\d+)", content)
        if m:
            result["source_count"] = int(m.group(1))

    # Metadata section
    result["has_metadata_section"] = "## Metadata" in content

    # Model info
    m = re.search(r"\|\s*Ollama Chat Model Requested\s*\|\s*`(.+?)`", content)
    if m:
        result["model_requested"] = m.group(1).strip()
        result["model_mentioned"] = True
    m = re.search(r"\|\s*Ollama Chat Model Used\s*\|\s*`(.+?)`", content)
    if m:
        result["model_used"] = m.group(1).strip()
    m = re.search(r"\|\s*Model Fallback Used\s*\|\s*true", content)
    if m:
        result["model_fallback"] = True
    m = re.search(r"\|\s*Degraded Mode\s*\|\s*true", content)
    if m:
        result["degraded"] = True

    # Legacy model fallback
    if not result["model_mentioned"]:
        result["model_mentioned"] = bool(
            re.search(r"(?:model|llm|ollama|qwen)", content, re.IGNORECASE)
        )

    # Prüfe Abschnitte
    result["has_source_section"] = "## Sources" in content
    result["has_summary_section"] = "## Summary" in content
    result["has_limitations_section"] = "## Limitations" in content

    # Source IDs [S1], [S2]
    result["source_ids"] = len(re.findall(r"\[S\d+\]", content))

    # Extrahiere Summary-Text
    m = re.search(r"## Summary\n\n(.+?)(?:\n##|\Z)", content, re.DOTALL)
    if m:
        result["summary"] = m.group(1).strip()

    # Extrahiere Summary-Text
    m = re.search(r"## Summary\n\n(.+?)(?:\n##|\Z)", content, re.DOTALL)
    if m:
        result["summary"] = m.group(1).strip()

    # Zähle Quellen (im neuen Format: [S1], [S2] oder alt: 1. **Title**)
    result["source_ids"] = len(re.findall(r"\[S\d+\]", content))
    source_pattern_new = len(re.findall(r"###\s*\[S\d+\]", content))
    source_pattern_old = len(re.findall(r"^\d+\.\s+\*\*", content, re.MULTILINE))
    result["sources_listed"] = max(
        source_pattern_new, source_pattern_old, result["source_ids"] // 2
    )

    # Prüfe Cloud-Referenzen
    for provider in CLOUD_PROVIDERS:
        if provider.lower() in content.lower():
            result["cloud_references"].append(provider)

    # Prüfe Modell-Erwähnung
    result["model_mentioned"] = bool(
        re.search(r"(?:model|llm|ollama|qwen)", content, re.IGNORECASE)
    )

    return result


# ── Scores ────────────────────────────────────────────────────────────────────


def score_source_coverage(report: dict[str, Any]) -> tuple[int, str]:
    """Bewertet Quellenbasis (0-100)."""
    score = 0
    notes = []

    if report["has_source_section"]:
        score += 30
    else:
        notes.append("Kein Quellenabschnitt")

    if report["source_count"] >= 5:
        score += 30
    elif report["source_count"] >= 3:
        score += 20
    elif report["source_count"] >= 1:
        score += 10
    else:
        notes.append("Keine Quellen dokumentiert")

    if report["sources_listed"] >= 3:
        score += 20
    elif report["sources_listed"] >= 1:
        score += 10

    if report["has_summary_section"]:
        score += 20

    return min(score, 100), "; ".join(notes) if notes else "OK"


def score_traceability(report: dict[str, Any]) -> tuple[int, str]:
    """Bewertet Rückverfolgbarkeit (0-100)."""
    score = 0
    notes = []

    if report["query"]:
        score += 15

    if report["has_metadata_section"]:
        score += 15

    if report["source_count"] > 0:
        score += 10

    if report["source_ids"] >= 3:
        score += 15
    elif report["source_ids"] >= 1:
        score += 5

    if report["model_requested"] or report["model_used"]:
        score += 20
        if not report.get("model_fallback", True):
            score += 5
    else:
        notes.append("Modell nicht dokumentiert")

    if report.get("has_limitations_section"):
        score += 15
    else:
        notes.append("Kein Limitations-Abschnitt")

    if report.get("degraded"):
        notes.append("Degraded Mode aktiv")

    if not notes:
        result_notes: str = "OK"
    else:
        result_notes = "; ".join(notes)

    return min(score, 100), result_notes


def score_hallucination_risk(report: dict[str, Any]) -> tuple[int, str]:
    """Bewertet Halluzinationsrisiko (0-100, höher = geringeres Risiko)."""
    score = 100
    risks = []

    summary_lower = report["summary"].lower()

    # Prüfe riskante Wörter
    found_risk = [w for w in RISK_WORDS if w in summary_lower]
    if found_risk:
        score -= len(found_risk) * 10
        risks.append(f"Riskante Wörter: {', '.join(found_risk)}")

    # Fehlender Quellenabschnitt = hohes Risiko
    if not report["has_source_section"]:
        score -= 30
        risks.append("Kein Quellenabschnitt")

    # Fehlende Quellen
    if report["source_count"] == 0:
        score -= 25
        risks.append("Keine Quellen")

    # Summary sehr lang ohne viele Quellen
    summary_len = len(report["summary"])
    if report["source_count"] < 2 and summary_len > 500:
        score -= 15
        risks.append("Lange Summary mit wenigen Quellen")

    return max(score, 0), "; ".join(risks) if risks else "OK"


def score_local_first(report: dict[str, Any]) -> tuple[int, str]:
    """Bewertet Local-First-Compliance (0-100)."""
    score = 100
    notes = []

    if report["cloud_references"]:
        score -= 50 * len(report["cloud_references"])
        notes.append(f"Cloud-Referenzen: {', '.join(report['cloud_references'])}")

    if report["model_mentioned"]:
        score = min(score, 100)

    return max(score, 0), "; ".join(notes) if notes else "OK"


def calculate_overall(scores: dict[str, int]) -> int:
    """Berechnet Overall-Score (gewichteter Durchschnitt)."""
    weights = {
        "source_coverage": 0.35,
        "traceability": 0.25,
        "hallucination_risk": 0.15,
        "local_first": 0.25,
    }
    overall = sum(scores[k] * weights.get(k, 0) for k in scores)
    return int(round(overall))


# ── Output ────────────────────────────────────────────────────────────────────


def generate_evaluation(report_path: str, eval_dir: str) -> dict[str, Any]:
    """Führt die vollständige Evaluation durch."""
    report = parse_report(report_path)

    source_score, source_notes = score_source_coverage(report)
    trace_score, trace_notes = score_traceability(report)
    hallu_score, hallu_notes = score_hallucination_risk(report)
    local_score, local_notes = score_local_first(report)

    scores = {
        "source_coverage": source_score,
        "traceability": trace_score,
        "hallucination_risk": hallu_score,
        "local_first": local_score,
    }
    overall = calculate_overall(scores)

    evaluation: dict[str, Any] = {
        "timestamp": datetime.datetime.now().isoformat(),
        "report": os.path.basename(report_path),
        "report_path": report_path,
        "scores": scores,
        "overall": overall,
        "details": {
            "source_coverage": source_notes,
            "traceability": trace_notes,
            "hallucination_risk": hallu_notes,
            "local_first": local_notes,
        },
        "report_metadata": {
            "query": report["query"],
            "source_count": report["source_count"],
            "sources_listed": report["sources_listed"],
            "has_source_section": report["has_source_section"],
            "has_summary_section": report["has_summary_section"],
            "model_mentioned": report["model_mentioned"],
            "cloud_references": report["cloud_references"],
        },
    }

    # Schreibe JSON
    os.makedirs(eval_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(eval_dir, f"research_eval_{timestamp}.json")
    with open(json_path, "w") as f:
        json.dump(evaluation, f, indent=2, ensure_ascii=False)

    # Schreibe Markdown
    md_path = os.path.join(eval_dir, f"research_eval_{timestamp}.md")
    with open(md_path, "w") as f:
        f.write("# Research Report Evaluation\n\n")
        f.write(f"**Report:** `{os.path.basename(report_path)}`\n\n")
        f.write(f"**Generated:** {evaluation['timestamp']}\n\n")
        f.write(f"## Overall Score: {overall}/100\n\n")
        f.write("| Score | Wert | Hinweise |\n")
        f.write("|---|---|---|\n")
        f.write(f"| Source Coverage | {source_score} | {source_notes} |\n")
        f.write(f"| Traceability | {trace_score} | {trace_notes} |\n")
        f.write(f"| Hallucination Risk | {hallu_score} | {hallu_notes} |\n")
        f.write(f"| Local-First | {local_score} | {local_notes} |\n")
        f.write("\n## Report Metadata\n\n")
        f.write(f"- Query: `{report['query']}`\n")
        f.write(f"- Sources: {report['source_count']}\n")
        f.write(f"- Model documented: {report['model_mentioned']}\n")
        if report["cloud_references"]:
            f.write(f"- ⚠️  Cloud references: {', '.join(report['cloud_references'])}\n")

    evaluation["json_path"] = json_path
    evaluation["md_path"] = md_path
    return evaluation


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Research Report Quality Evaluation")
    parser.add_argument("report_path", nargs="?", help="Pfad zum Report (Markdown)")
    parser.add_argument("--latest", action="store_true", help="Neuesten Report finden")
    parser.add_argument(
        "--min-score", type=int, default=0, help="Minimaler Overall-Score"
    )
    parser.add_argument(
        "--output-dir", default=DEFAULT_EVAL_DIR, help="Output-Verzeichnis"
    )
    args = parser.parse_args()

    # Report-Pfad bestimmen
    if args.latest:
        try:
            report_path = find_latest_report(DEFAULT_REPORT_DIR)
        except FileNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)
    elif args.report_path:
        report_path = args.report_path
        if not os.path.isfile(report_path):
            print(f"❌ Report nicht gefunden: {report_path}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    # Evaluation
    print("📊 Research Report Evaluation")
    print(f"   Report: {report_path}")
    print()

    evaluation = generate_evaluation(report_path, args.output_dir)

    # Console Summary
    scores = evaluation["scores"]
    print(f"  Source Coverage:     {scores['source_coverage']:>3}/100")
    print(f"  Traceability:        {scores['traceability']:>3}/100")
    print(f"  Hallucination Risk:  {scores['hallucination_risk']:>3}/100")
    print(f"  Local-First:         {scores['local_first']:>3}/100")
    print("  ─────────────────────────")
    print(f"  Overall:             {evaluation['overall']:>3}/100")
    print()

    # Rating
    overall = evaluation["overall"]
    if overall >= 90:
        rating = "✅ Sehr gut"
    elif overall >= 70:
        rating = "✅ Nutzbar"
    elif overall >= 50:
        rating = "⚠️  Verbesserungsbedürftig"
    else:
        rating = "❌ Nicht belastbar"
    print(f"  Bewertung: {rating}")

    # Details
    details = evaluation["details"]
    for key, notes in details.items():
        if notes != "OK":
            print(f"  ⚠️  {key}: {notes}")

    print()
    print(f"  JSON: {evaluation['json_path']}")
    print(f"  MD:   {evaluation['md_path']}")
    print()

    # Min-Score Check
    if args.min_score > 0 and overall < args.min_score:
        print(f"❌ Overall {overall} < min-score {args.min_score}")
        sys.exit(1)


if __name__ == "__main__":
    main()

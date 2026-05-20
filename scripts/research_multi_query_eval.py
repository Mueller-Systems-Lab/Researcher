#!/usr/bin/env python3
"""Multi-Query Research Evaluation — mehrere harmlose Queries + Evaluation.

Nutzung:
    python3 scripts/research_multi_query_eval.py --limit 3
    python3 scripts/research_multi_query_eval.py --limit 5 --min-overall 80
"""

import argparse
import datetime
import json
import os
import sys
from typing import Any

# Harmlose Standard-Queries
DEFAULT_QUERIES = [
    "What is a search engine?",
    "What is SearXNG?",
    "What is local-first software?",
    "What is open source software?",
    "What is a web crawler?",
]

# Blockierte Begriffe (Query-Safety-Guard)
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

RESEARCH_SCRIPT = os.path.join(os.path.dirname(__file__), "research_happy_path.py")
EVAL_SCRIPT = os.path.join(os.path.dirname(__file__), "evaluate_research_report.py")


def is_safe_query(query: str) -> bool:
    """Query-Safety-Guard."""
    for term in BLOCKED_TERMS:
        if term in query.lower():
            return False
    return True


def run_single_query(query: str) -> tuple[str, str, bool]:
    """Führt Research-Happy-Path für eine Query aus.
    Returns (report_path, eval_path, success)."""
    import subprocess

    env = os.environ.copy()
    env.setdefault("ALLOW_OLLAMA_MODEL_FALLBACK", "true")
    env.setdefault("SEARXNG_TIMEOUT_SECONDS", "30")

    # Run Happy Path
    result = subprocess.run(
        [sys.executable, RESEARCH_SCRIPT, "--query", query],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    if result.returncode != 0:
        print(f"   ❌ Happy-Path fehlgeschlagen (exit {result.returncode})")
        return "", "", False

    # Find latest report
    import glob

    reports = sorted(glob.glob("reports/research/research_*.md"), reverse=True)
    if not reports:
        print("   ❌ Kein Report erzeugt")
        return "", "", False
    report_path = reports[0]

    # Run Evaluation
    eval_result = subprocess.run(
        [sys.executable, EVAL_SCRIPT, report_path],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    evals = sorted(glob.glob("reports/evaluation/research_eval_*.json"), reverse=True)
    eval_path = evals[0] if evals else ""

    return report_path, eval_path, eval_result.returncode == 0


def load_evaluation_scores(eval_path: str) -> dict:
    """Lädt Scores aus einer JSON-Evaluation."""
    if not eval_path or not os.path.isfile(eval_path):
        return {}
    with open(eval_path) as f:
        data = json.load(f)
    return data.get("scores", {})


def generate_aggregate(results: list[dict], output_dir: str) -> str:
    """Erzeugt aggregierte JSON + Markdown Summary."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Calculate aggregates
    passed = [r for r in results if r["success"]]
    failed = len(results) - len(passed)

    def safe_mean(key: str) -> float:
        vals = [r["scores"].get(key, 0) for r in passed]
        return round(sum(vals) / len(vals), 1) if vals else 0.0

    aggregate: dict = {
        "generated_at": datetime.datetime.now().isoformat(),
        "query_count": len(results),
        "passed": len(passed),
        "failed": failed,
        "aggregate_scores": {
            "overall_mean": safe_mean("overall"),
            "overall_min": min(
                (r["scores"].get("overall", 0) for r in passed), default=0
            ),
            "source_coverage_mean": safe_mean("source_coverage"),
            "traceability_mean": safe_mean("traceability"),
            "hallucination_risk_mean": safe_mean("hallucination_risk"),
            "local_first_mean": safe_mean("local_first"),
        },
        "results": [
            {
                "query": r["query"],
                "success": r["success"],
                "report_path": r["report_path"],
                "evaluation_path": r["eval_path"],
                "scores": r["scores"],
                "overall": r["scores"].get("overall", 0),
            }
            for r in results
        ],
    }

    # Write JSON
    json_path = os.path.join(output_dir, f"multi_query_eval_{timestamp}.json")
    with open(json_path, "w") as f:
        json.dump(aggregate, f, indent=2, ensure_ascii=False)

    # Write Markdown
    md_path = os.path.join(output_dir, f"multi_query_eval_{timestamp}.md")
    agg = aggregate["aggregate_scores"]
    with open(md_path, "w") as f:
        f.write("# Multi-Query Research Evaluation\n\n")
        f.write(f"**Generated:** {aggregate['generated_at']}\n")
        f.write(
            f"**Queries:** {aggregate['query_count']} "
            f"({aggregate['passed']} passed, "
            f"{aggregate['failed']} failed)\n\n"
        )
        f.write("## Results\n\n")
        f.write("| Query | Source | Trace | Hallu | Local | Overall | Status |\n")
        f.write("|---|---:|---:|---:|---:|---:|---|\n")
        for r in aggregate["results"]:
            s = r["scores"]
            status = "✅" if r["success"] else "❌"
            esc = r["query"].replace("|", "\\|")
            f.write(
                f"| {esc[:40]} | {s.get('source_coverage', 0)} | "
                f"{s.get('traceability', 0)} | {s.get('hallucination_risk', 0)} | "
                f"{s.get('local_first', 0)} | {r['overall']} | {status} |\n"
            )
        f.write("\n## Aggregate\n\n")
        f.write("| Metric | Value |\n|---|---|\n")
        f.write(f"| Overall Mean | {agg['overall_mean']} |\n")
        f.write(f"| Overall Min | {agg['overall_min']} |\n")
        f.write(f"| Source Coverage Mean | {agg['source_coverage_mean']} |\n")
        f.write(f"| Traceability Mean | {agg['traceability_mean']} |\n")
        f.write(f"| Hallucination Risk Mean | {agg['hallucination_risk_mean']} |\n")
        f.write(f"| Local-First Mean | {agg['local_first_mean']} |\n")

    return json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-Query Research Evaluation")
    parser.add_argument("--limit", type=int, default=3, help="Anzahl Queries")
    parser.add_argument(
        "--min-overall", type=int, default=0, help="Minimaler Mean Overall"
    )
    parser.add_argument(
        "--min-query-overall", type=int, default=0, help="Minimaler Einzelquery Overall"
    )
    parser.add_argument(
        "--mode",
        choices=["live", "dry-run"],
        default="live",
        help="Ausführungsmodus",
    )
    parser.add_argument(
        "--baseline",
        default="",
        help="Pfad zur Baseline-JSON für Regression Guard",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit !=0 bei Regression",
    )
    args = parser.parse_args()

    queries = DEFAULT_QUERIES[: args.limit]

    # Filter unsafe queries
    safe_queries = [q for q in queries if is_safe_query(q)]
    if len(safe_queries) < len(queries):
        print(f"⚠️  {len(queries) - len(safe_queries)} unsichere Queries entfernt")

    print("📊 Multi-Query Research Evaluation")
    print(f"   Mode: {args.mode}")
    print(f"   Queries: {len(safe_queries)}")
    print()

    # Dry-run: nur Queries anzeigen, nichts ausführen
    if args.mode == "dry-run":
        for i, q in enumerate(safe_queries, 1):
            print(f"  [{i}] {q}")
        print("\n✅ Dry-run abgeschlossen (keine Ausführung)")
        return

    results: list[dict[str, Any]] = []
    for i, query in enumerate(safe_queries, 1):
        print(f"Query {i}/{len(safe_queries)}: {query}")
        report_path, eval_path, success = run_single_query(query)
        scores = load_evaluation_scores(eval_path)
        results.append(
            {
                "query": query,
                "success": success,
                "report_path": report_path,
                "eval_path": eval_path,
                "scores": scores,
            }
        )
        overall = scores.get("overall", "?")
        status = "✅" if success else "❌"
        print(f"   Overall: {overall}/100 {status}")
        print()

    # Generate aggregate
    json_path = generate_aggregate(results, "reports/evaluation")
    print(f"📄 Aggregate: {json_path}")

    # Min-Score checks
    if results:
        means: dict[str, float] = {
            "overall": round(
                sum(
                    r["scores"].get("overall", 0)  # type: ignore[union-attr]
                    for r in results
                    if r["success"]
                )
                / max(1, len([r for r in results if r["success"]])),
                1,
            ),
        }
        # failed queries tracked via aggregate results

        if args.min_overall > 0 and means["overall"] < args.min_overall:
            print(
                f"❌ Overall Mean {means['overall']} < min-overall {args.min_overall}"
            )
            sys.exit(1)

        if args.min_query_overall > 0:
            low = [
                r
                for r in results
                if r["scores"].get("overall", 0) < args.min_query_overall
            ]
            if low:
                print(
                    f"❌ {len(low)} Queries below "
                    f"min-query-overall {args.min_query_overall}"
                )
                sys.exit(1)

    # Regression Guard
    regressions: list[str] = []

    def safe_mean(key: str) -> float:  # noqa: E306
        vals = [r["scores"].get(key, 0) for r in results if r["success"]]
        return round(sum(vals) / len(vals), 1) if vals else 0.0

    if args.baseline and os.path.isfile(args.baseline) and results:
        with open(args.baseline) as f:
            baseline = json.load(f)
        thresholds = baseline.get("thresholds", {})
        reg_results: list[dict[str, Any]] = []

        checks = [
            ("Overall Mean", "overall_mean_min", means["overall"]),
            (
                "Source Coverage Mean",
                "source_coverage_mean_min",
                safe_mean("source_coverage"),
            ),
            ("Traceability Mean", "traceability_mean_min", safe_mean("traceability")),
            (
                "Hallucination Risk Mean",
                "hallucination_risk_mean_min",
                safe_mean("hallucination_risk"),
            ),
            ("Local-First Mean", "local_first_mean_min", safe_mean("local_first")),
        ]

        for name, key, actual in checks:
            threshold = thresholds.get(key, 0)
            if key == "local_first_mean_min":
                passed = actual >= threshold
            else:
                passed = actual >= threshold
            status = "✅ PASS" if passed else "❌ FAIL"
            reg_results.append(
                {
                    "check": name,
                    "threshold": threshold,
                    "actual": actual,
                    "status": status,
                }
            )
            if not passed:
                regressions.append(f"{name}: {actual} < {threshold}")

        # Append regression info to aggregate JSON
        agg_path = json_path
        if os.path.isfile(agg_path):
            with open(agg_path) as f:
                agg = json.load(f)
            agg["regression_guard"] = {
                "baseline": args.baseline,
                "regressions": regressions,
                "checks": reg_results,
            }
            with open(agg_path, "w") as f:
                json.dump(agg, f, indent=2, ensure_ascii=False)

    passed = len([r for r in results if r["success"]])
    failed_count = len(results) - passed
    print(f"\nAggregate: {passed} passed, {failed_count} failed")
    if means.get("overall"):
        print(f"Mean Overall: {means['overall']}/100")

    # Regression Guard Output
    if regressions:
        print(f"\n⚠️  Regression Guard: {len(regressions)} FAILURES")
        for r in regressions:
            print(f"   ❌ {r}")
        if args.fail_on_regression:
            sys.exit(3)
    elif args.baseline:
        print("\n✅ Regression Guard: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()

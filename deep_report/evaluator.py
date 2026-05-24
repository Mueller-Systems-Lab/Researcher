"""Report Evaluator — computes quality scores for Deep Research reports.

Scores:
- source_coverage: % of nodes with at least one evidence source
- traceability: % of claims backed by a citation
- evidence_diversity: unique domains / total sources
- node_completion: % of DAG nodes with findings
- hallucination_risk: heuristic risk score (lower is better)
- local_first: 100 if no cloud APIs detected, 0 otherwise
- injection_risk: 0-100 score based on flagged segments
- overall: weighted average
"""

from __future__ import annotations


def evaluate_report(
    *,
    node_count: int = 0,
    nodes_with_evidence: int = 0,
    total_citations: int = 0,
    total_claims: int = 0,
    unique_domains: int = 0,
    total_sources: int = 0,
    nodes_completed: int = 0,
    injection_flagged: int = 0,
    total_segments: int = 0,
    cloud_detected: bool = False,
) -> dict[str, float]:
    """Compute evaluation scores for a research report.

    Returns a dict of score_name → value.
    hallucination_risk is inverted in the overall calculation.
    """
    scores: dict[str, float] = {}

    # Source coverage: nodes backed by evidence
    scores["source_coverage"] = _pct(nodes_with_evidence, node_count)

    # Traceability: claims with citations
    scores["traceability"] = _pct(total_citations, total_claims)

    # Evidence diversity: unique domains ratio
    scores["evidence_diversity"] = _pct(unique_domains, total_sources)

    # Node completion: completed DAG nodes
    scores["node_completion"] = _pct(nodes_completed, node_count)

    # Hallucination risk: inverse of traceability + coverage
    trace = scores["traceability"]
    cov = scores["source_coverage"]
    scores["hallucination_risk"] = max(0, 100 - (trace * 0.6 + cov * 0.4))

    # Local-first: 100 if no cloud
    scores["local_first"] = 0.0 if cloud_detected else 100.0

    # Injection risk
    scores["injection_risk"] = _pct(injection_flagged, total_segments)

    # Overall: weighted average
    weights = {
        "source_coverage": 0.20,
        "traceability": 0.25,
        "evidence_diversity": 0.10,
        "node_completion": 0.15,
        "hallucination_risk": 0.10,  # inverted in formula
        "local_first": 0.15,
        "injection_risk": 0.05,  # inverted in formula
    }
    overall = 0.0
    for key, weight in weights.items():
        val = scores.get(key, 0)
        if key == "hallucination_risk":
            val = 100 - val  # invert: low risk = high score
        if key == "injection_risk":
            val = 100 - val  # invert: low injection = high score
        overall += val * weight
    scores["overall"] = round(overall, 1)

    return scores


def is_report_acceptable(scores: dict[str, float]) -> bool:
    """Check if a report meets minimum quality thresholds.

    Thresholds:
    - overall >= 90
    - source_coverage >= 80
    - traceability >= 90
    - local_first == 100 (must be strictly 100)
    """
    return (
        scores.get("overall", 0) >= 90
        and scores.get("source_coverage", 0) >= 80
        and scores.get("traceability", 0) >= 90
        and scores.get("local_first", 0) == 100
    )


def rejection_reasons(scores: dict[str, float]) -> list[str]:
    """Return human-readable reasons why a report was rejected."""
    reasons: list[str] = []
    if scores.get("overall", 0) < 90:
        reasons.append(f"overall={scores['overall']} < 90")
    if scores.get("source_coverage", 0) < 80:
        reasons.append(f"source_coverage={scores['source_coverage']} < 80")
    if scores.get("traceability", 0) < 90:
        reasons.append(f"traceability={scores['traceability']} < 90")
    if scores.get("local_first", 0) < 100:
        reasons.append(f"local_first={scores['local_first']} < 100")
    return reasons


def _pct(num: int, denom: int) -> float:
    """Safe percentage calculation."""
    if denom == 0:
        return 0.0
    return round((num / denom) * 100, 1)

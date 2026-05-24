"""Revision Loop — triggers follow-up research when report quality is too low.

When the evaluation scores are below threshold:
1. Identify missing evidence
2. Generate gap queries
3. Return revision request for the Orchestrator (DR-02)
"""

from __future__ import annotations


def revision_needed(scores: dict[str, float]) -> bool:
    """Check if a revision loop is needed based on scores."""
    from deep_report.evaluator import is_report_acceptable

    return not is_report_acceptable(scores)


def generate_gap_queries(
    scores: dict[str, float],
    *,
    original_query: str = "",
    node_questions: list[str] | None = None,
) -> list[str]:
    """Generate gap queries for the revision loop.

    Identifies weak areas from scores and creates targeted follow-up queries.
    """
    gaps: list[str] = []

    if scores.get("source_coverage", 100) < 80:
        gaps.append(f"{original_query} additional sources evidence")

    if scores.get("traceability", 100) < 90:
        for q in (node_questions or [])[:3]:
            gaps.append(f"{q} verifiable citation")

    if scores.get("evidence_diversity", 100) < 50:
        gaps.append(f"{original_query} diverse perspectives multiple domains")

    return gaps


def revision_request(
    scores: dict[str, float],
    *,
    original_query: str = "",
    node_questions: list[str] | None = None,
) -> dict:
    """Produce a revision request for the Orchestrator.

    Returns a dict with:
    - action: 'revise'
    - scores: current scores
    - gap_queries: suggested follow-up queries
    - reasons: human-readable rejection reasons
    """
    from deep_report.evaluator import rejection_reasons

    return {
        "action": "revise",
        "scores": scores,
        "gap_queries": generate_gap_queries(
            scores,
            original_query=original_query,
            node_questions=node_questions,
        ),
        "reasons": rejection_reasons(scores),
    }

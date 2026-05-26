"""Report Writer — generates a zitated Deep Research Markdown report.

Inputs:
- ResearchPlan DAG results (node_id → findings)
- Evidence Store data (sources, segments, citations)
- Evaluation scores

Output:
- Complete Markdown report with inline citations, source list, evaluation summary
"""

from __future__ import annotations

from datetime import UTC, datetime

from deep_report.citation_inserter import (
    generate_source_list,
    generate_source_table,
    insert_citations,
)
from deep_report.evaluator import evaluate_report, is_report_acceptable
from deep_report.outline import generate_outline
from deep_report.revision_loop import revision_request


def write_report(
    query: str,
    *,
    node_results: dict[str, str] | None = None,
    sources: list[dict] | None = None,
    citations: list[dict] | None = None,
    language: str = "en",
    cloud_detected: bool = False,
) -> str:
    """Generate a complete Deep Research Markdown report.

    Args:
        query: The original research question.
        node_results: Mapping of plan node_id → findings text.
        sources: Evidence source dicts (from Evidence Store).
        citations: Citation dicts with label, quote, url, segment_id.
        language: Report language.
        cloud_detected: Whether cloud APIs were detected (penalizes local_first).

    Returns:
        Complete Markdown report string.
    """
    node_results = node_results or {}
    sources = sources or []
    citations = citations or []

    node_titles = list(node_results.keys())
    _outline = generate_outline(query, node_titles=node_titles, language=language)

    lines: list[str] = []

    # 1. Title
    lines.append(f"# Deep Research Report: {query}")
    lines.append("")
    lines.append(
        f"*Generated: {datetime.now(UTC).isoformat()} — Local-First Researcher*"
    )
    lines.append("")

    # 2. Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    sources_count = len(sources)
    citations_count = len(citations)
    lines.append(
        f"This report presents findings from a Deep Research investigation "
        f"across {len(node_results)} research steps, "
        f"drawing on {sources_count} sources "
        f"with {citations_count} citations."
    )
    lines.append("")

    # 3. Research Question
    lines.append("## Research Question")
    lines.append("")
    lines.append(f"> {query}")
    lines.append("")

    # 4. Method / Search Plan
    lines.append("## Method / Search Plan")
    lines.append("")
    lines.append(f"The research was conducted in {len(node_results)} planned steps:")
    for idx, (node_id, _) in enumerate(node_results.items(), 1):
        lines.append(f"{idx}. Research Node `{node_id}`")
    lines.append("")

    # 5. Findings by DAG Node
    lines.append("## Findings by DAG Node")
    lines.append("")
    for node_id, findings in node_results.items():
        lines.append(f"### {node_id}")
        lines.append("")
        # Insert citations into findings
        cited_findings = insert_citations(findings, citations)
        lines.append(
            cited_findings if cited_findings.strip() else "*No findings recorded.*"
        )
        lines.append("")

    # 6. Evidence Table
    lines.append("## Evidence Table")
    lines.append("")
    lines.append(generate_source_table(sources))
    lines.append("")

    # 7. Limitations
    lines.append("## Limitations")
    lines.append("")
    lines.append(f"- Research scope limited to {len(node_results)} planned steps.")
    lines.append(f"- Sources: {sources_count} retrieved from web search.")
    lines.append("- Automated research may miss nuanced domain expertise.")
    lines.append("")

    # 8. Uncertainty
    lines.append("## Uncertainty")
    lines.append("")
    # Compute evaluation for uncertainty markers
    scores = evaluate_report(
        node_count=len(node_results),
        nodes_with_evidence=len([v for v in node_results.values() if v.strip()]),
        total_citations=citations_count,
        total_claims=max(citations_count, 1),
        unique_domains=len(set(s.get("domain", "") for s in sources)),
        total_sources=max(sources_count, 1),
        nodes_completed=len([v for v in node_results.values() if v.strip()]),
        injection_flagged=0,
        total_segments=max(len(node_results), 1),
        cloud_detected=cloud_detected,
    )
    lines.append(f"- **Traceability Score:** {scores['traceability']}%")
    lines.append(f"- **Source Coverage:** {scores['source_coverage']}%")
    lines.append(f"- **Hallucination Risk:** {scores['hallucination_risk']}%")
    lines.append(
        "- Findings are based on automated web research "
        "and should be independently verified."
    )
    lines.append("")

    # 9. Source List
    lines.append("## Source List")
    lines.append("")
    lines.append(generate_source_list(sources))
    lines.append("")

    # 10. Evaluation Summary
    lines.append("## Evaluation Summary")
    lines.append("")
    for key, val in scores.items():
        lines.append(f"- **{key}:** {val}")
    lines.append("")
    if is_report_acceptable(scores):
        lines.append("✅ **Report accepted** — all quality thresholds met.")
    else:
        reason = revision_request(scores, original_query=query)
        lines.append(f"⚠️ **Revision needed:** {', '.join(reason['reasons'])}")
        lines.append(f"   Gap queries: {', '.join(reason['gap_queries'])}")
    lines.append("")

    return "\n".join(lines)


def write_report_with_evaluation(
    query: str,
    *,
    node_results: dict[str, str] | None = None,
    sources: list[dict] | None = None,
    citations: list[dict] | None = None,
    cloud_detected: bool = False,
) -> dict:
    """Generate a report and evaluate it, returning both report and scores.

    Returns:
        Dict with 'report' (Markdown string) and 'scores' (evaluation dict).
    """
    report = write_report(
        query=query,
        node_results=node_results,
        sources=sources,
        citations=citations,
        cloud_detected=cloud_detected,
    )

    node_results = node_results or {}
    sources = sources or []
    citations = citations or []

    scores = evaluate_report(
        node_count=len(node_results),
        nodes_with_evidence=len([v for v in node_results.values() if v.strip()]),
        total_citations=len(citations),
        total_claims=max(len(citations), 1),
        unique_domains=len(set(s.get("domain", "") for s in sources)),
        total_sources=max(len(sources), 1),
        nodes_completed=len([v for v in node_results.values() if v.strip()]),
        injection_flagged=0,
        total_segments=max(len(node_results), 1),
        cloud_detected=cloud_detected,
    )

    return {
        "report": report,
        "scores": scores,
        "acceptable": is_report_acceptable(scores),
        "revision": (
            revision_request(scores, original_query=query)
            if not is_report_acceptable(scores)
            else None
        ),
    }

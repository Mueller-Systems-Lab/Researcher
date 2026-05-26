"""Gap Analyzer — detects missing evidence and generates follow-up queries.

Used by the Researcher Worker to identify knowledge gaps after a node's
dependencies have been executed and to produce targeted gap queries.
"""

from __future__ import annotations


def analyze_gaps(
    question: str,
    *,
    dependency_results: dict[str, str],
    expected_sources: list[str] | None = None,
) -> list[str]:
    """Analyze dependency results for gaps and generate follow-up queries.

    Args:
        question: The current node's research question.
        dependency_results: Mapping of dep_node_id → result text.
        expected_sources: Expected source types for coverage check.

    Returns:
        List of gap-driven follow-up queries (may be empty).
    """
    gaps: list[str] = []

    # Check each dependency result for explicit gap markers
    for dep_id, result_text in dependency_results.items():
        gap_queries = _extract_gaps_from_result(dep_id, result_text)
        gaps.extend(gap_queries)

    # Source coverage gap: expected vs found
    if expected_sources:
        source_gaps = _check_source_coverage(
            question, expected_sources, dependency_results
        )
        gaps.extend(source_gaps)

    return gaps


def _extract_gaps_from_result(dep_id: str, result_text: str) -> list[str]:
    """Extract gap queries from a dependency's result text."""
    gaps: list[str] = []
    result_lower = result_text.lower()

    gap_markers = [
        "missing:",
        "lücke:",
        "gap:",
        "fehlt:",
        "unbekannt:",
        "offene frage:",
        "open question:",
        "further research:",
        "weitere recherche:",
        "not found:",
        "nicht gefunden:",
    ]

    for marker in gap_markers:
        if marker in result_lower:
            idx = result_lower.index(marker) + len(marker)
            gap_text = result_text[idx:].strip().split("\n")[0].strip()
            if gap_text:
                gaps.append(f"[from {dep_id}] {gap_text}")

    return gaps


def _check_source_coverage(
    question: str,
    expected_sources: list[str],
    dependency_results: dict[str, str],
) -> list[str]:
    """Generate queries for missing source types."""
    gaps: list[str] = []
    all_text = " ".join(dependency_results.values()).lower()

    for src_type in expected_sources:
        if src_type.lower() not in all_text:
            gaps.append(f"{question} {src_type}")

    return gaps


def has_significant_gaps(
    gaps: list[str],
    *,
    min_gaps: int = 2,
) -> bool:
    """Check if gap analysis indicates a significant knowledge deficit."""
    return len(gaps) >= min_gaps

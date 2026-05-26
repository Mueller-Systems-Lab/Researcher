"""Researcher Worker — Orchestrator-compatible callback for query decomposition.

Implements the WorkerFn protocol: (node_id, question, context) → (ok, artifacts).

This is the integration point between the Orchestrator (DR-02) and the
Query Decomposer / Gap Analyzer. The worker does not execute searches —
it produces structured query artifacts for the Searcher Pipeline (DR-04).
"""

from __future__ import annotations

import json
import logging

from research_workers.gap_analyzer import analyze_gaps
from research_workers.query_decomposer import DecomposedQueries, decompose_node

logger = logging.getLogger(__name__)


def research_worker(
    node_id: str,
    question: str,
    context: dict,
) -> tuple[bool, list[str]]:
    """Orchestrator-compatible worker callback.

    Args:
        node_id: The plan node identifier.
        question: The research sub-question from the plan node.
        context: Context dict with:
            - rationale: str
            - expected_sources: list[str] (optional)
            - dependency_results: dict[str, str] (optional)
            - language: str (optional)
            - run_id: str (optional)

    Returns:
        (ok, artifacts) — ok=True if decomposition succeeded,
        artifacts is a list of JSON-serialized DecomposedQueries.
    """
    try:
        rationale = context.get("rationale", "")
        expected_sources = context.get("expected_sources", [])
        dependency_results = context.get("dependency_results", {})
        language = context.get("language", "unknown")

        # 1. Decompose the node into structured queries
        queries = decompose_node(
            node_id=node_id,
            question=question,
            rationale=rationale,
            expected_sources=expected_sources,
            context_from_dependencies=dependency_results,
            language=language,
        )

        # 2. Analyze gaps from dependency results
        gaps = analyze_gaps(
            question=question,
            dependency_results=dependency_results,
            expected_sources=expected_sources,
        )

        # Add gap queries to the decomposed set
        queries.gap_queries.extend(gaps)

        # 3. Serialize to JSON artifact
        artifact = queries_to_json(queries)
        logger.info(
            "Worker decomposed node %s → %d queries "
            "(%d primary, %d entity, %d gap, %d negative)",
            node_id,
            len(queries),
            len(queries.primary_queries),
            len(queries.entity_queries),
            len(queries.gap_queries),
            len(queries.negative_queries),
        )

        return True, [artifact]

    except Exception as exc:
        logger.exception("Worker failed for node %s: %s", node_id, exc)
        return False, []


def queries_to_json(queries: DecomposedQueries) -> str:
    """Serialize DecomposedQueries to JSON."""
    data = {
        "node_id": queries.node_id,
        "language": queries.language,
        "primary_queries": queries.primary_queries,
        "entity_queries": queries.entity_queries,
        "gap_queries": queries.gap_queries,
        "negative_queries": queries.negative_queries,
        "query_count": len(queries),
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def queries_from_json(json_str: str) -> DecomposedQueries:
    """Deserialize DecomposedQueries from JSON."""
    data = json.loads(json_str)
    return DecomposedQueries(
        node_id=data["node_id"],
        primary_queries=data.get("primary_queries", []),
        entity_queries=data.get("entity_queries", []),
        gap_queries=data.get("gap_queries", []),
        negative_queries=data.get("negative_queries", []),
        language=data.get("language", "unknown"),
    )

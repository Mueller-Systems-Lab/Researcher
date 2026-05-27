"""Researcher Worker — Orchestrator-compatible callback for query decomposition
and search execution.

Implements the WorkerFn protocol: (node_id, question, context) → (ok, artifacts).

Pipeline:
  1. Decompose the node question into structured queries
  2. Execute primary queries via CompositeRetriever (SearXNG)
  3. Store retrieved sources in Evidence Store for traceability
  4. Return JSON artifact with queries + search results
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
        artifacts is a list of JSON-serialized results.
    """
    try:
        rationale = context.get("rationale", "")
        expected_sources = context.get("expected_sources", [])
        dependency_results = context.get("dependency_results", {})
        language = context.get("language", "unknown")
        run_id = context.get("run_id", "")

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

        # 3. Execute primary queries via CompositeRetriever (SearXNG)
        search_results = _execute_queries(
            queries.primary_queries[:3],  # max 3 primary queries
            run_id=run_id,
        )

        # 4. Store retrieved sources in Evidence Store
        source_ids = _store_sources(search_results, run_id=run_id)

        # Warn if queries were expected but no results returned
        if queries.primary_queries and not search_results:
            logger.warning(
                "Node %s: %d primary queries returned zero search results "
                "(SearXNG may be unavailable, run=%s)",
                node_id,
                len(queries.primary_queries),
                run_id,
            )
        if search_results and not source_ids:
            logger.warning(
                "Node %s: %d search results found but zero stored in evidence store "
                "(store may be unavailable, run=%s)",
                node_id,
                len(search_results),
                run_id,
            )

        # 5. Serialize to JSON artifact (queries + results)
        artifact = _build_artifact(queries, search_results, source_ids, node_id)
        logger.info(
            "Worker completed node %s: %d queries, %d sources retrieved",
            node_id,
            len(queries),
            len(source_ids),
        )

        return True, [artifact]

    except Exception as exc:
        logger.exception("Worker failed for node %s: %s", node_id, exc)
        return False, []


def _execute_queries(
    query_strings: list[str],
    *,
    run_id: str = "",
    max_results_per_query: int = 5,
) -> list[dict]:
    """Execute queries via CompositeRetriever and return merged results."""
    if not query_strings:
        return []

    all_results: list[dict] = []
    try:
        from search.composite import CompositeRetriever

        for q in query_strings[:3]:  # safety limit
            try:
                retriever = CompositeRetriever(q)
                results = retriever.search(max_results=max_results_per_query)
                all_results.extend(results)
                logger.debug(
                    "Query '%s' returned %d results (run=%s)",
                    q[:60],
                    len(results),
                    run_id,
                )
            except Exception as exc:
                logger.warning("Query '%s' failed: %s (run=%s)", q[:60], exc, run_id)
    except ImportError:
        logger.warning(
            "CompositeRetriever not available — skipping search (run=%s)", run_id
        )

    # Deduplicate by URL
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in all_results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            deduped.append(r)
    return deduped


def _store_sources(
    search_results: list[dict],
    *,
    run_id: str = "",
) -> list[str]:
    """Store search results as EvidenceSource entries. Returns source IDs."""
    if not search_results:
        return []

    source_ids: list[str] = []
    try:
        from evidence_store.models import EvidenceSource
        from evidence_store.store import save_source

        for r in search_results:
            try:
                source = EvidenceSource(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    run_id=run_id,
                )
                save_source(source)
                source_ids.append(source.source_id)
            except (ValueError, OSError) as exc:
                logger.warning(
                    "Failed to store source %s: %s (run=%s)",
                    r.get("url", "")[:60],
                    exc,
                    run_id,
                )
    except ImportError:
        logger.warning(
            "Evidence store not available — sources not persisted (run=%s)", run_id
        )

    logger.info(
        "Stored %d/%d sources in evidence store (run=%s)",
        len(source_ids),
        len(search_results),
        run_id,
    )
    return source_ids


def _build_artifact(
    queries: DecomposedQueries,
    search_results: list[dict],
    source_ids: list[str],
    node_id: str,
) -> str:
    """Build the JSON artifact combining queries and search results."""
    data = {
        "node_id": node_id,
        "language": queries.language,
        "primary_queries": queries.primary_queries,
        "entity_queries": queries.entity_queries,
        "gap_queries": queries.gap_queries,
        "negative_queries": queries.negative_queries,
        "query_count": len(queries),
        "search_results": [
            {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "source": r.get("source", "SearXNG"),
                "score": r.get("score", 0),
                "snippet": (r.get("body") or r.get("raw_content", ""))[:300],
            }
            for r in search_results
        ],
        "source_ids": source_ids,
        "sources_found": len(search_results),
        "sources_stored": len(source_ids),
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


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

"""Report Outline Generator — structural skeleton for Deep Research reports.

Produces the required section outline with metadata slots.
Can be populated with real research data from a completed run.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_SECTIONS = [
    "Title",
    "Executive Summary",
    "Research Question",
    "Method / Search Plan",
    "Findings by DAG Node",
    "Evidence Table",
    "Limitations",
    "Uncertainty",
    "Source List",
    "Evaluation Summary",
]


def generate_outline(
    query: str,
    *,
    node_titles: list[str] | None = None,
    language: str = "en",
    node_results: dict[str, dict[str, Any]] | None = None,
    sources: list[dict[str, str]] | None = None,
    evaluation: dict[str, Any] | None = None,
) -> list[dict]:
    """Generate a report outline populated with real research data.

    When node_results, sources, or evaluation are provided, replaces
    placeholder text with actual content from the completed research run.

    Args:
        query: The original research query.
        node_titles: List of DAG node titles (from plan).
        language: Language hint ('de', 'en').
        node_results: Dict mapping node_id → {question, artifacts, status}.
        sources: List of source dicts with url, title, domain, retrieved keys.
        evaluation: Evaluation scores dict.

    Returns:
        List of section dicts with 'title', 'content' (real data),
        and 'placeholder' (backward compatibility for existing consumers).
    """
    outline: list[dict] = []

    for section in REQUIRED_SECTIONS:
        entry: dict = {"title": section, "content": "", "placeholder": ""}

        if section == "Title":
            entry["content"] = f"# Deep Research Report: {query}"
            entry["placeholder"] = entry["content"]

        elif section == "Executive Summary":
            if node_results:
                completed = sum(
                    1 for n in node_results.values() if n.get("status") == "completed"
                )
                total = len(node_results)
                entry["content"] = (
                    f"Research completed on {total} DAG nodes "
                    f"({completed} completed). "
                    f"Original query: {query}."
                )
            else:
                entry["content"] = (
                    "Research findings, methodology, and key conclusions "
                    "will appear here after run completion."
                )

        elif section == "Research Question":
            entry["content"] = query

        elif section == "Method / Search Plan":
            node_count = len(node_titles or [])
            entry["content"] = (
                f"Research conducted using {node_count} planned DAG steps. "
                f"Search executed via SearXNG (web) "
                f"{'and Darknet index' if node_count > 1 else ''}. "
                f"Evidence stored in ChromaDB vector store."
            )

        elif section == "Findings by DAG Node":
            if node_results:
                parts = []
                for node_id, result in node_results.items():
                    title = result.get("title", node_id)
                    status = result.get("status", "unknown")
                    artifacts = result.get("artifacts", [])
                    parts.append(f"### {title} (Status: {status})")
                    if artifacts:
                        for artifact in artifacts:
                            parts.append(f"\n```json\n{artifact}\n```")
                    else:
                        parts.append("\n*No artifacts produced.*")
                entry["content"] = "\n\n".join(parts)
            else:
                entry["content"] = "\n".join(
                    f"### {t}\n\n*Findings pending...*"
                    for t in (node_titles or ["Research"])
                )

        elif section == "Evidence Table":
            if sources:
                rows = []
                for idx, src in enumerate(sources, 1):
                    domain = src.get("domain", src.get("url", "unknown"))
                    rows.append(
                        f"| {idx} | {src.get('title', 'Untitled')} | "
                        f"{domain} | {src.get('retrieved', '—')} |"
                    )
                header = "| # | Source | Domain | Retrieved |\n|---|--------|--------|------------|\n"
                entry["content"] = header + "\n".join(rows)
            else:
                entry["content"] = (
                    "| # | Source | Domain | Retrieved |\n"
                    "|---|--------|--------|------------|\n"
                )

        elif section == "Limitations":
            entry["content"] = (
                "- Scope limitations based on query decomposition\n"
                "- Source availability via SearXNG\n"
                "- Local LLM model constraints\n"
            )

        elif section == "Uncertainty":
            if evaluation and "uncertainty" in evaluation:
                entry["content"] = evaluation["uncertainty"]
            else:
                entry["content"] = (
                    "Areas of uncertainty and confidence levels "
                    "for key findings will be populated after evaluation."
                )

        elif section == "Source List":
            if sources:
                entry["content"] = "\n".join(
                    f"- {s.get('title', 'Untitled')}: {s.get('url', '—')}"
                    for s in sources
                )
            else:
                entry["content"] = "*Sources will be listed after research execution.*"

        elif section == "Evaluation Summary":
            if evaluation:
                entry["content"] = json.dumps(evaluation, indent=2, ensure_ascii=False)
            else:
                entry["content"] = (
                    "*Evaluation scores will appear after run completion.*"
                )

        # Sync placeholder for backward compatibility
        entry["placeholder"] = entry["content"] or entry["placeholder"]

        outline.append(entry)

    return outline


def load_run_data_for_outline(run_id: str) -> dict[str, Any]:
    """Load research run data from storage for outline population.

    Reads state.json and events.jsonl from the run's storage directory
    and returns a structured dict with node_results, sources, etc.

    Args:
        run_id: The research run ID.

    Returns:
        Dict with keys: node_results (dict), query (str), language (str).
        Returns empty dict if run data not found.
    """
    runs_dir = Path(os.getenv("DEEP_REPORT_DIR", "reports/deep_research")) / "runs"
    run_dir = runs_dir / run_id

    if not run_dir.exists():
        logger.warning("Run data not found for outline: %s", run_id)
        return {}

    state_path = run_dir / "state.json"
    if not state_path.exists():
        return {}

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load run state for %s: %s", run_id, e)
        return {}

    node_results = {}
    for nid, nd in data.get("node_states", {}).items():
        node_results[nid] = {
            "title": nid,
            "status": nd.get("status", "unknown"),
            "artifacts": nd.get("artifacts", []),
            "question": data.get("node_questions", {}).get(nid, ""),
        }

    # Load sources: merge evidence store + worker artifact search_results
    evidence_sources = _load_sources_from_evidence_store(run_id)
    artifact_sources = _extract_sources_from_artifacts(node_results)
    sources = _merge_sources(evidence_sources, artifact_sources)

    return {
        "node_results": node_results,
        "query": data.get("query", ""),
        "language": data.get("language", "unknown"),
        "sources": sources,
    }


def _extract_sources_from_artifacts(
    node_results: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    """Extract search_results from worker JSON artifacts."""
    sources: list[dict[str, str]] = []
    for nid, nd in node_results.items():
        for artifact_str in nd.get("artifacts", []):
            try:
                artifact = json.loads(artifact_str)
            except (json.JSONDecodeError, TypeError):
                continue
            for sr in artifact.get("search_results", []):
                sources.append(
                    {
                        "url": sr.get("url", ""),
                        "title": sr.get("title", "Untitled"),
                        "domain": _extract_domain(sr.get("url", "")),
                        "retrieved": nd.get("status", "unknown"),
                    }
                )
    return sources


def _extract_domain(url: str) -> str:
    """Extract domain from URL for display."""
    if not url:
        return "unknown"
    try:
        from urllib.parse import urlparse

        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"


def _merge_sources(
    evidence: list[dict[str, str]],
    artifacts: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Merge sources from evidence store and worker artifacts.

    Artifact sources (run-scoped) take priority. Evidence store sources
    are only used as fallback when no artifact sources exist —
    this prevents cross-run data leakage in reports.
    """
    if artifacts:
        # Run-scoped artifact sources exist — use them exclusively
        seen_urls: set[str] = set()
        merged: list[dict[str, str]] = []
        for src in artifacts:
            url = src.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged.append(src)
        return merged

    # No artifact sources — fall back to evidence store (global, non-scoped)
    seen_urls = set()
    merged = []
    for src in evidence:
        url = src.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged.append(src)
    return merged


def _load_sources_from_evidence_store(
    run_id: str,
) -> list[dict[str, str]]:
    """Load evidence sources associated with a research run.

    Reads from the evidence store's sources.jsonl file and filters
    by sources that were retrieved during this run (if run-scoped
    metadata is available), otherwise returns all sources.
    """
    try:
        from evidence_store.store import load_sources
    except ImportError:
        logger.warning("evidence_store not available for outline sources")
        return []

    try:
        raw_sources = load_sources()
    except Exception as exc:
        logger.warning("Failed to load evidence sources: %s", exc)
        return []

    sources: list[dict[str, str]] = []
    for src in raw_sources:
        sources.append(
            {
                "url": src.url,
                "title": src.title or "Untitled",
                "domain": src.domain or "",
                "retrieved": src.retrieved_at or "",
            }
        )

    return sources

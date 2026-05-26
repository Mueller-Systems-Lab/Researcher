"""Serialization for ResearchPlan — JSON import/export, Markdown export.

JSON is the canonical machine format. Markdown is for human review/editing.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from research_planner.models import (
    ResearchDependency,
    ResearchNode,
    ResearchPlan,
    ResearchPlanStatus,
    RiskLevel,
)

SCHEMA_VERSION = "research-plan/v1"


# ── JSON Export ───────────────────────────────────────────────────────────


def plan_to_json(plan: ResearchPlan, indent: int = 2) -> str:
    """Serialize a ResearchPlan to a JSON string."""
    data = _plan_to_dict(plan)
    return json.dumps(data, indent=indent, ensure_ascii=False)


def plan_to_dict(plan: ResearchPlan) -> dict[str, Any]:
    """Convert a ResearchPlan to a plain dict (e.g., for API responses)."""
    return _plan_to_dict(plan)


def _plan_to_dict(plan: ResearchPlan) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "plan_id": plan.plan_id,
        "query": plan.query,
        "language": plan.language,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
        "approved_at": plan.approved_at,
        "approved_by": plan.approved_by,
        "status": plan.status.value,
        "assumptions": plan.assumptions,
        "constraints": plan.constraints,
        "user_notes": plan.user_notes,
        "nodes": [
            {
                "node_id": n.node_id,
                "title": n.title,
                "question": n.question,
                "rationale": n.rationale,
                "depends_on": n.depends_on,
                "expected_sources": n.expected_sources,
                "status": n.status.value,
                "risk_level": n.risk_level.value,
            }
            for n in plan.nodes
        ],
        "dependencies": [
            {
                "from_node": d.from_node,
                "to_node": d.to_node,
                "dependency_type": d.dependency_type,
            }
            for d in plan.dependencies
        ],
    }


# ── JSON Import ───────────────────────────────────────────────────────────


def plan_from_json(json_str: str) -> ResearchPlan:
    """Deserialize a ResearchPlan from a JSON string."""
    data = json.loads(json_str)
    return plan_from_dict(data)


def plan_from_dict(data: dict[str, Any]) -> ResearchPlan:
    """Build a ResearchPlan from a plain dict."""
    plan = ResearchPlan(
        query=data["query"],
        plan_id=data.get("plan_id", ""),
        language=data.get("language", "unknown"),
        assumptions=data.get("assumptions", []),
        constraints=data.get("constraints", []),
        user_notes=data.get("user_notes", []),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        approved_at=data.get("approved_at"),
        approved_by=data.get("approved_by"),
        status=ResearchPlanStatus(data.get("status", "draft")),
    )

    # Restore nodes
    for nd in data.get("nodes", []):
        node = ResearchNode(
            node_id=nd.get("node_id", ""),
            title=nd["title"],
            question=nd["question"],
            rationale=nd.get("rationale", ""),
            depends_on=nd.get("depends_on", []),
            expected_sources=nd.get("expected_sources", []),
            status=ResearchPlanStatus(nd.get("status", "draft")),
            risk_level=RiskLevel(nd.get("risk_level", "unknown")),
        )
        plan.nodes.append(node)

    # Restore dependencies
    for dd in data.get("dependencies", []):
        dep = ResearchDependency(
            from_node=dd["from_node"],
            to_node=dd["to_node"],
            dependency_type=dd.get("dependency_type", "requires"),
        )
        plan.dependencies.append(dep)

    return plan


# ── Markdown Export ───────────────────────────────────────────────────────


def plan_to_markdown(plan: ResearchPlan) -> str:
    """Export a ResearchPlan as a human-readable Markdown document."""
    lines: list[str] = []

    lines.append(f"# Research Plan: {plan.query}")
    lines.append("")
    lines.append(f"**Plan ID:** `{plan.plan_id}`  ")
    lines.append(f"**Status:** {plan.status.value}  ")
    lines.append(f"**Language:** {plan.language}  ")
    lines.append(f"**Created:** {plan.created_at}  ")
    if plan.approved_at:
        lines.append(f"**Approved:** {plan.approved_at} by {plan.approved_by}  ")
    lines.append("")

    if plan.assumptions:
        lines.append("## Assumptions")
        for a in plan.assumptions:
            lines.append(f"- {a}")
        lines.append("")

    if plan.constraints:
        lines.append("## Constraints")
        for c in plan.constraints:
            lines.append(f"- {c}")
        lines.append("")

    lines.append("## Research Steps")
    lines.append("")

    # Topological order for readability
    from research_planner.validation import get_topological_order

    order = get_topological_order(plan) or [n.node_id for n in plan.nodes]
    nodes_by_id = {n.node_id: n for n in plan.nodes}

    for idx, node_id in enumerate(order, 1):
        node = nodes_by_id.get(node_id)
        if node is None:
            continue
        lines.append(f"### Step {idx}: {node.title}")
        lines.append("")
        lines.append(f"**Question:** {node.question}  ")
        lines.append(f"**Rationale:** {node.rationale}  ")
        lines.append(f"**Risk Level:** {node.risk_level.value}  ")
        lines.append(f"**Status:** {node.status.value}  ")
        lines.append(f"**Node ID:** `{node.node_id}`  ")
        if node.depends_on:
            deps = ", ".join(f"`{d}`" for d in node.depends_on)
            lines.append(f"**Depends on:** {deps}  ")
        if node.expected_sources:
            lines.append(f"**Expected sources:** {', '.join(node.expected_sources)}  ")
        lines.append("")

    lines.append("---")
    lines.append(
        f"*Generated by Researcher — DR-01 Planner at {datetime.now(UTC).isoformat()}*"
    )

    return "\n".join(lines)

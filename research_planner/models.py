"""Research Plan data models — DR-01: Collaborative Planner + Research Plan DAG.

Uses dataclasses as the canonical data model (not Pydantic, not dicts).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class ResearchPlanStatus(str, Enum):
    """Status for a ResearchPlan and ResearchNode."""

    DRAFT = "draft"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    """Risk classification for a ResearchNode."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass
class ResearchNode:
    """A single research step within a ResearchPlan DAG.

    Each node represents one atomic research sub-question.
    Dependencies are expressed via `depends_on` (list of node_id strings).
    """

    title: str
    question: str
    rationale: str = ""
    depends_on: list[str] = field(default_factory=list)
    expected_sources: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: ResearchPlanStatus = ResearchPlanStatus.DRAFT

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.question.strip():
            raise ValueError("question must not be empty")


@dataclass
class ResearchDependency:
    """Explicit edge in the DAG: from_node -> to_node."""

    from_node: str
    to_node: str
    dependency_type: str = "requires"


@dataclass
class ResearchPlan:
    """Root container for a DAG-based research plan.

    Owns all ResearchNodes and ResearchDependencies.
    The plan_id is the stable identifier across orchestrator, evidence store,
    and report.
    """

    query: str
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    nodes: list[ResearchNode] = field(default_factory=list)
    dependencies: list[ResearchDependency] = field(default_factory=list)
    status: ResearchPlanStatus = ResearchPlanStatus.DRAFT
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    user_notes: list[str] = field(default_factory=list)
    language: str = "unknown"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    approved_at: str | None = None
    approved_by: str | None = None

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("query must not be empty")

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(UTC).isoformat()

    def add_node(self, node: ResearchNode) -> None:
        """Add a node to the plan."""
        self.nodes.append(node)
        self.touch()

    def add_dependency(
        self, from_node: str, to_node: str, dep_type: str = "requires"
    ) -> None:
        """Add a dependency edge between two nodes."""
        self.dependencies.append(
            ResearchDependency(
                from_node=from_node, to_node=to_node, dependency_type=dep_type
            )
        )
        self.touch()

    def get_node(self, node_id: str) -> ResearchNode | None:
        """Find a node by ID."""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def node_ids(self) -> set[str]:
        """Return the set of all node IDs."""
        return {n.node_id for n in self.nodes}

    def adjacency(self) -> dict[str, list[str]]:
        """Build adjacency list for topological operations."""
        adj: dict[str, list[str]] = {n.node_id: [] for n in self.nodes}
        for dep in self.dependencies:
            adj.setdefault(dep.from_node, []).append(dep.to_node)
        return adj

    def in_degree(self) -> dict[str, int]:
        """Compute in-degree for each node (number of incoming edges)."""
        degree: dict[str, int] = {n.node_id: 0 for n in self.nodes}
        for dep in self.dependencies:
            degree[dep.to_node] = degree.get(dep.to_node, 0) + 1
        return degree

"""Research Run State — the persistent state object for a single Deep Research run.

State is serialized as state.json in reports/deep_research/runs/<run_id>/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class RunStatus(str, Enum):
    """Overall run status."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeRunStatus(str, Enum):
    """Per-node execution status within a run."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # dependency failed


@dataclass
class NodeState:
    """Runtime state for a single plan node."""

    node_id: str
    status: NodeRunStatus = NodeRunStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    artifacts: list[str] = field(default_factory=list)


@dataclass
class RunState:
    """Persistent state for a single Deep Research run.

    Serialized to state.json. Events logged separately to events.jsonl.
    """

    run_id: str
    plan_id: str
    status: RunStatus = RunStatus.CREATED
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    started_at: str | None = None
    completed_at: str | None = None
    node_states: dict[str, NodeState] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    topo_order: list[str] = field(default_factory=list)
    node_deps: dict[str, list[str]] = field(default_factory=dict)
    max_parallel: int = 1

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC).isoformat()

    def set_node_status(self, node_id: str, status: NodeRunStatus) -> None:
        if node_id not in self.node_states:
            self.node_states[node_id] = NodeState(node_id=node_id)
        self.node_states[node_id].status = status
        now = datetime.now(UTC).isoformat()
        if status == NodeRunStatus.RUNNING and not self.node_states[node_id].started_at:
            self.node_states[node_id].started_at = now
        if status in (NodeRunStatus.COMPLETED, NodeRunStatus.FAILED):
            self.node_states[node_id].completed_at = now
        self.touch()

    def node_failed(self, node_id: str, error: str) -> None:
        self.set_node_status(node_id, NodeRunStatus.FAILED)
        self.node_states[node_id].error = error
        self.errors.append(f"[{node_id}] {error}")
        self.touch()

    def node_completed(self, node_id: str, artifacts: list[str] | None = None) -> None:
        self.set_node_status(node_id, NodeRunStatus.COMPLETED)
        if artifacts:
            self.node_states[node_id].artifacts = artifacts
        self.touch()

    def is_terminal(self) -> bool:
        return self.status in (
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        )

    def progress(self) -> tuple[int, int]:
        """Return (completed, total) node counts."""
        total = len(self.node_states)
        completed = sum(
            1
            for ns in self.node_states.values()
            if ns.status == NodeRunStatus.COMPLETED
        )
        return completed, total

"""Node scheduler — determines which DAG nodes are ready to execute.

Computes the set of ready nodes based on dependency resolution
and current execution state, respecting max_parallel limits.
"""

from __future__ import annotations

from research_orchestrator.state import NodeRunStatus, RunState
from research_planner.models import ResearchPlan


def compute_ready_nodes(plan: ResearchPlan, state: RunState) -> list[str]:
    """Return node_ids that are ready to execute.

    A node is ready if:
    - All its dependencies are COMPLETED
    - It is not already RUNNING or COMPLETED or FAILED
    - It is not BLOCKED (a dependency failed)
    """
    ready: list[str] = []

    for node in plan.nodes:
        ns = state.node_states.get(node.node_id)

        # Skip completed/failed/running nodes
        if ns and ns.status in (
            NodeRunStatus.COMPLETED,
            NodeRunStatus.FAILED,
            NodeRunStatus.RUNNING,
            NodeRunStatus.BLOCKED,
        ):
            continue

        # Check all dependencies
        deps_satisfied = True
        for dep_id in node.depends_on:
            dep_state = state.node_states.get(dep_id)
            if dep_state is None:
                deps_satisfied = False
                break
            if dep_state.status == NodeRunStatus.FAILED:
                # Mark this node as blocked
                state.set_node_status(node.node_id, NodeRunStatus.BLOCKED)
                deps_satisfied = False
                break
            if dep_state.status != NodeRunStatus.COMPLETED:
                deps_satisfied = False
                break

        if deps_satisfied:
            if ns is None or ns.status == NodeRunStatus.PENDING:
                state.set_node_status(node.node_id, NodeRunStatus.READY)
            ready.append(node.node_id)

    return ready


def count_running(state: RunState) -> int:
    """Count currently RUNNING nodes."""
    return sum(
        1 for ns in state.node_states.values() if ns.status == NodeRunStatus.RUNNING
    )


def slots_available(state: RunState) -> int:
    """Return how many more nodes can be started (parallel slots)."""
    running = count_running(state)
    available = state.max_parallel - running
    return max(0, available)

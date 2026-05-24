"""DAG validation for ResearchPlan — cycle detection, uniqueness, topological sort.

Uses Kahn's algorithm for topological ordering and cycle detection.
"""

from __future__ import annotations

from collections import deque

from research_planner.models import ResearchPlan


class DAGValidationError(ValueError):
    """Raised when a ResearchPlan fails DAG validation."""


def validate_plan(plan: ResearchPlan) -> list[str]:
    """Validate a ResearchPlan and return a topological execution order.

    Returns:
        List of node_ids in topological order (dependencies first).

    Raises:
        DAGValidationError: If the plan is invalid (cycles, missing refs, etc.)
    """
    if not plan.nodes:
        raise DAGValidationError("Plan must contain at least one node.")

    node_ids = plan.node_ids()

    # Check uniqueness
    if len(plan.nodes) != len(node_ids):
        raise DAGValidationError("Duplicate node_ids found in plan.")

    # Check all dependencies reference existing nodes
    for dep in plan.dependencies:
        if dep.from_node not in node_ids:
            raise DAGValidationError(
                f"Dependency from_node '{dep.from_node}' does not exist in plan nodes."
            )
        if dep.to_node not in node_ids:
            raise DAGValidationError(
                f"Dependency to_node '{dep.to_node}' does not exist in plan nodes."
            )
        if dep.from_node == dep.to_node:
            raise DAGValidationError(f"Node '{dep.from_node}' cannot depend on itself.")

    # Check node-level depends_on consistency
    for node in plan.nodes:
        for dep_id in node.depends_on:
            if dep_id not in node_ids:
                raise DAGValidationError(
                    f"Node '{node.node_id}' depends_on non-existent node '{dep_id}'."
                )
            if dep_id == node.node_id:
                raise DAGValidationError(
                    f"Node '{node.node_id}' cannot depend on itself."
                )

    # Topological sort (Kahn's algorithm) — also detects cycles
    return _topological_sort(plan)


def _topological_sort(plan: ResearchPlan) -> list[str]:
    """Kahn's algorithm: returns topologically sorted node_ids.

    Raises DAGValidationError if a cycle is detected.
    """
    in_degree = plan.in_degree()
    adj = plan.adjacency()

    # Start with all nodes that have no incoming edges
    queue: deque[str] = deque(node_id for node_id, deg in in_degree.items() if deg == 0)

    order: list[str] = []
    while queue:
        current = queue.popleft()
        order.append(current)
        for neighbor in adj.get(current, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(plan.nodes):
        remaining = {n for n in plan.node_ids() if n not in order}
        raise DAGValidationError(
            f"Cycle detected in DAG. Nodes not reachable: {remaining}"
        )

    return order


def get_topological_order(plan: ResearchPlan) -> list[str] | None:
    """Return topological order or None if invalid (non-raising variant)."""
    try:
        return validate_plan(plan)
    except DAGValidationError:
        return None


def has_cycle(plan: ResearchPlan) -> bool:
    """Check if the plan DAG contains a cycle."""
    try:
        _topological_sort(plan)
        return False
    except DAGValidationError:
        return True

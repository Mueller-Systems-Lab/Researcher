"""Master Orchestrator — drives a Deep Research run through a ResearchPlan DAG.

Lifecycle:
1. Load an approved ResearchPlan
2. Compute topological order
3. Execute nodes sequentially (default) or with limited parallelism
4. Persist state + events after each step
5. Support resume for interrupted runs
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from research_orchestrator.events import EventType, emit_event
from research_orchestrator.scheduler import (
    count_running,
    slots_available,
)
from research_orchestrator.state import (
    NodeRunStatus,
    RunState,
    RunStatus,
)
from research_orchestrator.storage import (
    append_events,
    load_state,
    save_state,
)
from research_planner.approval import assert_plan_approved
from research_planner.models import ResearchPlan
from research_planner.validation import validate_plan

logger = logging.getLogger(__name__)

# Type for a worker function: takes (node_id, question, context) → (ok, artifacts)
WorkerFn = Callable[[str, str, dict], tuple[bool, list[str]]]


class OrchestratorError(Exception):
    """Raised when the orchestrator encounters a fatal error."""


# ── Public API ───────────────────────────────────────────────────────────


def create_run(
    plan: ResearchPlan,
    *,
    max_parallel: int = 1,
) -> RunState:
    """Initialize a new run from an approved ResearchPlan.

    Raises PlanNotApprovedError if the plan is not approved.
    """
    assert_plan_approved(plan)

    run_id = uuid.uuid4().hex[:16]
    topo_order = validate_plan(plan)

    state = RunState(
        run_id=run_id,
        plan_id=plan.plan_id,
        max_parallel=max_parallel,
        topo_order=topo_order,
        status=RunStatus.CREATED,
    )

    # Initialize node states from plan
    for node_id in topo_order:
        state.node_states[node_id] = __import__(
            "research_orchestrator.state", fromlist=["NodeState"]
        ).NodeState(node_id=node_id)

    # Store dependency info from plan
    for node in plan.nodes:
        state.node_deps[node.node_id] = node.depends_on

    event = emit_event(EventType.RUN_CREATED, run_id, message=f"Plan: {plan.plan_id}")
    save_state(state)
    append_events(run_id, [event])

    logger.info(
        "Run %s created for plan %s with %d nodes.",
        run_id,
        plan.plan_id,
        len(topo_order),
    )
    return state


def start_run(
    state: RunState,
    worker: WorkerFn | None = None,
    *,
    resume: bool = False,
) -> RunState:
    """Execute the run through the plan DAG.

    Args:
        state: The RunState (must be CREATED or resuming an existing run).
        worker: A worker function that executes a single node.
                If None, uses a no-op dummy worker.
        resume: If True, skip already-completed nodes.

    Returns:
        The final RunState.
    """
    if worker is None:
        worker = _dummy_worker

    if state.status == RunStatus.CREATED or (
        resume and state.status == RunStatus.RUNNING
    ):
        state.status = RunStatus.RUNNING
        state.started_at = datetime.now(UTC).isoformat()
        event = emit_event(EventType.RUN_STARTED, state.run_id)
        append_events(state.run_id, [event])
        save_state(state)

    # Load plan data (minimal context for worker)
    node_contexts = _build_node_contexts(state)

    events_buffer: list[dict] = []

    while not state.is_terminal():
        # Check for completion
        all_done = all(
            ns.status
            in (NodeRunStatus.COMPLETED, NodeRunStatus.FAILED, NodeRunStatus.BLOCKED)
            for ns in state.node_states.values()
        )
        if all_done:
            any_failed = any(
                ns.status == NodeRunStatus.FAILED for ns in state.node_states.values()
            )
            if any_failed:
                state.status = RunStatus.FAILED
                state.completed_at = datetime.now(UTC).isoformat()
                event = emit_event(
                    EventType.RUN_FAILED,
                    state.run_id,
                    message="One or more nodes failed.",
                )
            else:
                state.status = RunStatus.COMPLETED
                state.completed_at = datetime.now(UTC).isoformat()
                event = emit_event(EventType.RUN_COMPLETED, state.run_id)
            events_buffer.append(event)
            break

        # Compute ready nodes (depends on dependency resolution)
        # We use plan nodes' topological order — scheduler handles readiness
        ready: list[str] = []
        for node_id in state.topo_order:
            ns = state.node_states.get(node_id)
            if ns is None:
                continue
            if resume and ns.status == NodeRunStatus.COMPLETED:
                continue
            if ns.status in (
                NodeRunStatus.COMPLETED,
                NodeRunStatus.FAILED,
                NodeRunStatus.RUNNING,
                NodeRunStatus.BLOCKED,
            ):
                continue

            # Check all dependencies
            deps_ok = _deps_satisfied(node_id, state)
            if deps_ok:
                state.set_node_status(node_id, NodeRunStatus.READY)
                events_buffer.append(
                    emit_event(EventType.NODE_READY, state.run_id, node_id=node_id)
                )
                ready.append(node_id)

        if not ready:
            # No nodes ready — if nothing is running, we're stuck
            if count_running(state) == 0:
                state.status = RunStatus.FAILED
                state.completed_at = datetime.now(UTC).isoformat()
                event = emit_event(
                    EventType.RUN_FAILED,
                    state.run_id,
                    message="No ready nodes and none running — deadlock.",
                )
                events_buffer.append(event)
            save_state(state)
            append_events(state.run_id, events_buffer)
            events_buffer.clear()
            # In real execution we'd wait, but for sequential we break
            break

        # Execute ready nodes (sequential: take first; parallel: up to slots)
        slots = slots_available(state)
        to_run = ready[:slots] if slots > 0 else ready[:1]  # at least 1 in sequential

        for node_id in to_run[:slots] if slots > 0 else to_run[:1]:
            state.set_node_status(node_id, NodeRunStatus.RUNNING)
            events_buffer.append(
                emit_event(EventType.NODE_STARTED, state.run_id, node_id=node_id)
            )

            context = node_contexts.get(node_id, {})
            question = context.get("question", "")
            try:
                ok, artifacts = worker(node_id, question, context)
            except Exception as exc:
                ok = False
                artifacts = []
                logger.exception("Worker for node %s crashed: %s", node_id, exc)

            if ok:
                state.node_completed(node_id, artifacts)
                events_buffer.append(
                    emit_event(
                        EventType.NODE_COMPLETED,
                        state.run_id,
                        node_id=node_id,
                        message=f"Artifacts: {artifacts}",
                    )
                )
            else:
                state.node_failed(node_id, "Worker returned failure.")
                events_buffer.append(
                    emit_event(EventType.NODE_FAILED, state.run_id, node_id=node_id)
                )
                # Block dependent nodes
                for other_id, other_ns in state.node_states.items():
                    if other_ns.status == NodeRunStatus.PENDING:
                        # Check if this node depends on the failed node
                        if _node_depends_on(other_id, node_id, state):
                            state.set_node_status(other_id, NodeRunStatus.BLOCKED)
                            events_buffer.append(
                                emit_event(
                                    EventType.NODE_BLOCKED,
                                    state.run_id,
                                    node_id=other_id,
                                    message=f"Blocked by failed node {node_id}",
                                )
                            )

        save_state(state)
        append_events(state.run_id, events_buffer)
        events_buffer.clear()

    # Final persist
    save_state(state)
    if events_buffer:
        append_events(state.run_id, events_buffer)

    return state


def resume_run(run_id: str, worker: WorkerFn | None = None) -> RunState | None:
    """Resume a previously interrupted run."""
    state = load_state(run_id)
    if state is None:
        logger.error("Run %s not found for resume.", run_id)
        return None
    if state.is_terminal():
        logger.info("Run %s already terminal (%s).", run_id, state.status.value)
        return state
    return start_run(state, worker=worker, resume=True)


# ── Helpers ──────────────────────────────────────────────────────────────


def _dummy_worker(node_id: str, question: str, context: dict) -> tuple[bool, list[str]]:
    """No-op worker for testing — always succeeds."""
    return True, []


def _deps_satisfied(node_id: str, state: RunState) -> bool:
    """Check if all dependencies of node_id are completed."""
    deps = state.node_deps.get(node_id, [])
    for dep_id in deps:
        dep_ns = state.node_states.get(dep_id)
        if dep_ns is None:
            return False
        if dep_ns.status == NodeRunStatus.FAILED:
            # This node should be BLOCKED — mark it
            state.set_node_status(node_id, NodeRunStatus.BLOCKED)
            return False
        if dep_ns.status != NodeRunStatus.COMPLETED:
            return False
    return True


def _node_depends_on(node_id: str, dep_id: str, state: RunState) -> bool:
    """Check if node_id directly depends on dep_id."""
    deps = state.node_deps.get(node_id, [])
    return dep_id in deps


def _build_node_contexts(state: RunState) -> dict[str, dict]:
    """Build context dicts for each node (minimal — full context from DR-03)."""
    contexts: dict[str, dict] = {}
    for node_id in state.topo_order:
        contexts[node_id] = {
            "node_id": node_id,
            "question": f"Research task: {node_id}",
            "run_id": state.run_id,
        }
    return contexts

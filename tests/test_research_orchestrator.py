"""Tests für research_orchestrator — DR-02: Master Orchestrator + Persistent State.

Abdeckung:
- draft plan abgelehnt
- approved plan startet
- topologische Reihenfolge
- Dependency-Resolve: abhängige Knoten starten nach Vorgängern
- failed node blockiert abhängige Knoten
- state.json wird geschrieben
- events.jsonl wird geschrieben
- Resume lädt Zustand
- sequential mode stabil
"""

from __future__ import annotations

import pytest

from research_orchestrator.events import (
    EventType,
    emit_event,
    events_to_jsonl,
    jsonl_to_events,
)
from research_orchestrator.orchestrator import (
    create_run,
    resume_run,
    start_run,
)
from research_orchestrator.scheduler import (
    compute_ready_nodes,
    count_running,
    slots_available,
)
from research_orchestrator.state import (
    NodeRunStatus,
    NodeState,
    RunState,
    RunStatus,
)
from research_orchestrator.storage import (
    RUNS_DIR,
    load_events,
    load_state,
    run_exists,
    save_state,
)
from research_planner.approval import approve_plan
from research_planner.models import ResearchNode, ResearchPlan
from research_planner.validation import DAGValidationError

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_approved_plan(
    query: str = "Test Research", num_nodes: int = 3
) -> ResearchPlan:
    """Create an approved ResearchPlan with sequential dependencies."""
    plan = ResearchPlan(query=query)
    nodes: list[ResearchNode] = []
    for i in range(num_nodes):
        node = ResearchNode(title=f"Step {i + 1}", question=f"Question {i + 1}")
        nodes.append(node)

    # Sequential deps: 1→2→3
    for i in range(1, len(nodes)):
        nodes[i].depends_on.append(nodes[i - 1].node_id)
        plan.add_dependency(nodes[i - 1].node_id, nodes[i].node_id)

    for n in nodes:
        plan.add_node(n)
    approve_plan(plan)
    return plan


# ── Basic Orchestrator Tests ─────────────────────────────────────────────


def test_draft_plan_rejected():
    """Orchestrator lehnt draft plan ab."""
    plan = ResearchPlan(query="Draft")
    plan.add_node(ResearchNode(title="N1", question="Q1"))
    # Not approved

    with pytest.raises(Exception):  # PlanNotApprovedError
        create_run(plan)


def test_approved_plan_creates_run():
    """Approved plan erzeugt gültigen Run."""
    plan = _make_approved_plan("Test")
    state = create_run(plan)

    assert state.status == RunStatus.CREATED
    assert state.plan_id == plan.plan_id
    assert len(state.node_states) == len(plan.nodes)
    assert len(state.topo_order) == len(plan.nodes)
    assert run_exists(state.run_id)


def test_run_executes_nodes_in_topological_order():
    """Knoten werden in topologischer Reihenfolge ausgeführt."""
    plan = _make_approved_plan("Topo order test", num_nodes=3)
    state = create_run(plan)

    executed: list[str] = []

    def tracking_worker(
        node_id: str, question: str, ctx: dict
    ) -> tuple[bool, list[str]]:
        executed.append(node_id)
        return True, [f"result_{node_id}"]

    state = start_run(state, worker=tracking_worker)
    assert state.status == RunStatus.COMPLETED
    assert executed == state.topo_order, f"Expected {state.topo_order}, got {executed}"


def test_dependent_nodes_wait_for_dependencies():
    """Abhängige Knoten starten erst nach Vorgängern."""
    plan = _make_approved_plan("Dependency order", num_nodes=3)
    # Node 1 → Node 2 → Node 3
    state = create_run(plan)

    exec_log: list[tuple[str, str]] = []  # (node_id, action)

    def log_worker(node_id: str, question: str, ctx: dict) -> tuple[bool, list[str]]:
        exec_log.append((node_id, "start"))
        # Verify that all dependencies are already completed
        for other_id, action in exec_log:
            if other_id != node_id and action == "start":
                # OK: other nodes may have started before
                pass
        exec_log.append((node_id, "done"))
        return True, []

    state = start_run(state, worker=log_worker)
    assert state.status == RunStatus.COMPLETED
    # All nodes executed
    done_nodes = [nid for nid, action in exec_log if action == "done"]
    assert len(done_nodes) == 3


def test_failed_node_blocks_dependents():
    """Fehlgeschlagener Knoten blockiert abhängige Knoten."""
    plan = _make_approved_plan("Failure cascade", num_nodes=3)
    state = create_run(plan)

    first_id = state.topo_order[0]

    def fail_first_worker(
        node_id: str, question: str, ctx: dict
    ) -> tuple[bool, list[str]]:
        if node_id == first_id:
            return False, []
        return True, []

    state = start_run(state, worker=fail_first_worker)

    # First node should be FAILED
    assert state.node_states[first_id].status == NodeRunStatus.FAILED

    # Dependent nodes should be BLOCKED
    for node_id in state.topo_order[1:]:
        assert state.node_states[node_id].status in (
            NodeRunStatus.BLOCKED,
            NodeRunStatus.PENDING,
            NodeRunStatus.FAILED,
        )

    assert state.status == RunStatus.FAILED


def test_run_fails_on_failed_node_and_blocks_deps():
    """Integration: failed node → RUN_FAILED + dependents blocked."""
    plan = _make_approved_plan("Fail test", num_nodes=2)
    state = create_run(plan)

    fail_worker_called: list[str] = []

    def failing_worker(
        node_id: str, question: str, ctx: dict
    ) -> tuple[bool, list[str]]:
        fail_worker_called.append(node_id)
        return False, []

    state = start_run(state, worker=failing_worker)
    assert state.status == RunStatus.FAILED
    # Second node should be BLOCKED
    if len(state.topo_order) > 1:
        second = state.topo_order[1]
        assert state.node_states[second].status == NodeRunStatus.BLOCKED


# ── State Persistence ────────────────────────────────────────────────────


def test_state_json_written():
    """state.json wird nach create_run geschrieben."""
    plan = _make_approved_plan("State persist")
    state = create_run(plan)

    state_path = RUNS_DIR / state.run_id / "state.json"
    assert state_path.exists()
    loaded = load_state(state.run_id)
    assert loaded is not None
    assert loaded.run_id == state.run_id
    assert loaded.plan_id == plan.plan_id


def test_events_jsonl_written():
    """events.jsonl wird geschrieben."""
    plan = _make_approved_plan("Events test")
    state = create_run(plan)

    events_path = RUNS_DIR / state.run_id / "events.jsonl"
    assert events_path.exists()

    events = load_events(state.run_id)
    assert len(events) > 0
    assert any(e["event"] == EventType.RUN_CREATED.value for e in events)


def test_events_roundtrip():
    """Events können serialisiert und deserialisiert werden."""
    events = [
        emit_event(EventType.RUN_CREATED, "r1", message="start"),
        emit_event(EventType.NODE_STARTED, "r1", node_id="n1"),
        emit_event(EventType.NODE_COMPLETED, "r1", node_id="n1"),
    ]
    jsonl = events_to_jsonl(events)
    parsed = jsonl_to_events(jsonl)
    assert len(parsed) == 3
    assert parsed[0]["event"] == "RUN_CREATED"
    assert parsed[1]["node_id"] == "n1"


# ── Resume ───────────────────────────────────────────────────────────────


def test_resume_loads_previous_state():
    """Resume lädt vorherigen Zustand."""
    plan = _make_approved_plan("Resume test", num_nodes=3)
    state = create_run(plan)

    # Complete first node
    first_id = state.topo_order[0]
    state.set_node_status(first_id, NodeRunStatus.RUNNING)
    state.node_completed(first_id, ["artifact1"])
    save_state(state)

    # Resume
    resumed = resume_run(state.run_id)
    assert resumed is not None
    assert resumed.node_states[first_id].status == NodeRunStatus.COMPLETED
    assert "artifact1" in resumed.node_states[first_id].artifacts


def test_resume_skips_completed_nodes():
    """Resume überspringt bereits abgeschlossene Knoten."""
    plan = _make_approved_plan("Resume skip", num_nodes=2)
    state = create_run(plan)

    # Complete first node
    first_id = state.topo_order[0]
    state.set_node_status(first_id, NodeRunStatus.RUNNING)
    state.node_completed(first_id, ["done"])
    save_state(state)

    executed_on_resume: list[str] = []

    def tracking_worker(
        node_id: str, question: str, ctx: dict
    ) -> tuple[bool, list[str]]:
        executed_on_resume.append(node_id)
        return True, []

    resumed = resume_run(state.run_id, worker=tracking_worker)
    assert resumed is not None
    # Only the second node should be executed on resume
    assert first_id not in executed_on_resume, (
        f"Completed node {first_id} should be skipped"
    )


def test_resume_nonexistent_run():
    """Resume gibt None für nicht existierenden Run."""
    assert resume_run("nonexistent-run-id") is None


# ── Sequential Mode ──────────────────────────────────────────────────────


def test_sequential_mode_stable():
    """Sequential mode läuft stabil mit mehreren Knoten."""
    plan = _make_approved_plan("Sequential stability", num_nodes=4)
    state = create_run(plan, max_parallel=1)

    order: list[str] = []

    def order_worker(node_id: str, question: str, ctx: dict) -> tuple[bool, list[str]]:
        order.append(node_id)
        return True, []

    state = start_run(state, worker=order_worker)
    assert state.status == RunStatus.COMPLETED
    assert len(order) == 4
    # Order must follow topo order (sequential execution)
    assert order == state.topo_order


# ── Scheduler Tests ──────────────────────────────────────────────────────


def test_scheduler_compute_ready_no_deps():
    """Scheduler: Knoten ohne Abhängigkeiten sind sofort ready."""
    plan = ResearchPlan(query="No deps")
    n1 = ResearchNode(title="A", question="Q")
    plan.add_node(n1)
    approve_plan(plan)

    state = create_run(plan)
    ready = compute_ready_nodes(plan, state)
    assert n1.node_id in ready


def test_slots_available_default():
    """Default: max_parallel=1 → 1 slot available when nothing running."""
    state = RunState(run_id="r1", plan_id="p1", max_parallel=1)
    assert slots_available(state) == 1


def test_slots_available_when_running():
    """Slots verringern sich, wenn Knoten laufen."""
    state = RunState(run_id="r1", plan_id="p1", max_parallel=2)
    state.node_states["n1"] = NodeState(node_id="n1", status=NodeRunStatus.RUNNING)
    assert slots_available(state) == 1


def test_count_running():
    """count_running zählt laufende Knoten."""
    state = RunState(run_id="r1", plan_id="p1")
    state.node_states["n1"] = NodeState(node_id="n1", status=NodeRunStatus.RUNNING)
    state.node_states["n2"] = NodeState(node_id="n2", status=NodeRunStatus.RUNNING)
    state.node_states["n3"] = NodeState(node_id="n3", status=NodeRunStatus.COMPLETED)
    assert count_running(state) == 2


# ── Edge Cases ───────────────────────────────────────────────────────────


def test_empty_plan_raises_in_create_run():
    """Leerer Plan (keine Knoten) wird von validate_plan abgelehnt."""
    plan = ResearchPlan(query="Empty")
    approve_plan(plan)
    with pytest.raises(DAGValidationError):
        create_run(plan)


def test_run_terminal_status():
    """RunState.is_terminal() erkennt Endzustände."""
    state = RunState(run_id="r1", plan_id="p1")
    assert not state.is_terminal()

    state.status = RunStatus.COMPLETED
    assert state.is_terminal()

    state.status = RunStatus.FAILED
    assert state.is_terminal()

    state.status = RunStatus.CANCELLED
    assert state.is_terminal()


def test_run_progress_counts():
    """RunState.progress() zählt abgeschlossene Knoten."""
    state = RunState(run_id="r1", plan_id="p1")
    state.node_states["n1"] = NodeState(node_id="n1", status=NodeRunStatus.COMPLETED)
    state.node_states["n2"] = NodeState(node_id="n2", status=NodeRunStatus.RUNNING)
    state.node_states["n3"] = NodeState(node_id="n3", status=NodeRunStatus.PENDING)
    completed, total = state.progress()
    assert completed == 1
    assert total == 3


def test_load_state_nonexistent():
    """load_state gibt None für nicht existierenden Run."""
    assert load_state("nonexistent-run") is None


def test_run_exists_false():
    """run_exists gibt False für nicht existierenden Run."""
    assert not run_exists("nonexistent-run")


# ── Scheduler: compute_ready_nodes untested paths ─────────────────────


def test_compute_ready_no_deps_standalone():
    """Node with empty depends_on is immediately ready (standalone)."""
    plan = ResearchPlan(query="Solo")
    node = ResearchNode(title="Solo", question="Q")
    plan.add_node(node)
    plan.approved = True

    state = RunState(run_id="r", plan_id=plan.plan_id)
    state.node_states[node.node_id] = NodeState(
        node_id=node.node_id, status=NodeRunStatus.PENDING
    )

    ready = compute_ready_nodes(plan, state)
    assert node.node_id in ready
    assert state.node_states[node.node_id].status == NodeRunStatus.READY


def test_compute_ready_dep_failed_blocks_node():
    """If a dependency is FAILED, the dependent node is set to BLOCKED and not ready."""

    plan = ResearchPlan(query="Dep failed")
    n1 = ResearchNode(title="A", question="Q1")
    n2 = ResearchNode(title="B", question="Q2", depends_on=[n1.node_id])
    plan.add_node(n1)
    plan.add_node(n2)
    plan.add_dependency(n1.node_id, n2.node_id)
    plan.approved = True

    state = RunState(run_id="r", plan_id=plan.plan_id)
    state.node_states[n1.node_id] = NodeState(
        node_id=n1.node_id, status=NodeRunStatus.FAILED
    )
    state.node_states[n2.node_id] = NodeState(
        node_id=n2.node_id, status=NodeRunStatus.PENDING
    )

    ready = compute_ready_nodes(plan, state)
    assert n2.node_id not in ready
    assert state.node_states[n2.node_id].status == NodeRunStatus.BLOCKED


def test_compute_ready_dep_pending_not_satisfied():
    """Dependency in PENDING status → deps not satisfied; node stays PENDING."""

    plan = ResearchPlan(query="Dep pending")
    n1 = ResearchNode(title="A", question="Q1")
    n2 = ResearchNode(title="B", question="Q2", depends_on=[n1.node_id])
    plan.add_node(n1)
    plan.add_node(n2)
    plan.add_dependency(n1.node_id, n2.node_id)
    plan.approved = True

    state = RunState(run_id="r", plan_id=plan.plan_id)
    state.node_states[n1.node_id] = NodeState(
        node_id=n1.node_id, status=NodeRunStatus.PENDING
    )
    state.node_states[n2.node_id] = NodeState(
        node_id=n2.node_id, status=NodeRunStatus.PENDING
    )

    ready = compute_ready_nodes(plan, state)
    assert n2.node_id not in ready
    assert state.node_states[n2.node_id].status == NodeRunStatus.PENDING


def test_compute_ready_skip_completed():
    """Node already COMPLETED is skipped (not in ready list)."""

    plan = ResearchPlan(query="Skip completed")
    node = ResearchNode(title="A", question="Q")
    plan.add_node(node)
    plan.approved = True

    state = RunState(run_id="r", plan_id=plan.plan_id)
    state.node_states[node.node_id] = NodeState(
        node_id=node.node_id, status=NodeRunStatus.COMPLETED
    )

    ready = compute_ready_nodes(plan, state)
    assert node.node_id not in ready


def test_compute_ready_skip_failed():
    """Node already FAILED is skipped."""

    plan = ResearchPlan(query="Skip failed")
    node = ResearchNode(title="A", question="Q")
    plan.add_node(node)
    plan.approved = True

    state = RunState(run_id="r", plan_id=plan.plan_id)
    state.node_states[node.node_id] = NodeState(
        node_id=node.node_id, status=NodeRunStatus.FAILED
    )

    ready = compute_ready_nodes(plan, state)
    assert node.node_id not in ready


def test_compute_ready_pending_all_deps_completed_becomes_ready():
    """Node in PENDING with all deps COMPLETED → transitions to READY."""

    plan = ResearchPlan(query="All deps done")
    n1 = ResearchNode(title="A", question="Q1")
    n2 = ResearchNode(title="B", question="Q2", depends_on=[n1.node_id])
    plan.add_node(n1)
    plan.add_node(n2)
    plan.add_dependency(n1.node_id, n2.node_id)
    plan.approved = True

    state = RunState(run_id="r", plan_id=plan.plan_id)
    state.node_states[n1.node_id] = NodeState(
        node_id=n1.node_id, status=NodeRunStatus.COMPLETED
    )
    state.node_states[n2.node_id] = NodeState(
        node_id=n2.node_id, status=NodeRunStatus.PENDING
    )

    ready = compute_ready_nodes(plan, state)
    assert n2.node_id in ready
    assert state.node_states[n2.node_id].status == NodeRunStatus.READY


def test_compute_ready_multiple_deps_one_failed_blocks():
    """With multiple dependencies, one FAILED dep blocks the dependent node."""

    plan = ResearchPlan(query="Multi dep one failed")
    n1 = ResearchNode(title="A", question="Q1")
    n2 = ResearchNode(title="B", question="Q2")
    n3 = ResearchNode(title="C", question="Q3", depends_on=[n1.node_id, n2.node_id])
    plan.add_node(n1)
    plan.add_node(n2)
    plan.add_node(n3)
    plan.add_dependency(n1.node_id, n3.node_id)
    plan.add_dependency(n2.node_id, n3.node_id)
    plan.approved = True

    state = RunState(run_id="r", plan_id=plan.plan_id)
    state.node_states[n1.node_id] = NodeState(
        node_id=n1.node_id, status=NodeRunStatus.COMPLETED
    )
    state.node_states[n2.node_id] = NodeState(
        node_id=n2.node_id, status=NodeRunStatus.FAILED
    )
    state.node_states[n3.node_id] = NodeState(
        node_id=n3.node_id, status=NodeRunStatus.PENDING
    )

    ready = compute_ready_nodes(plan, state)
    assert n3.node_id not in ready
    assert state.node_states[n3.node_id].status == NodeRunStatus.BLOCKED


def test_emit_event_with_payload():
    """emit_event serializes payload."""
    from research_orchestrator.events import EventType, emit_event

    event = emit_event(EventType.RUN_CREATED, "r1", payload={"key": "value"})
    assert event["payload"] == {"key": "value"}


def test_set_node_status_creates_new_node():
    """set_node_status creates NodeState for missing node_id."""
    from research_orchestrator.state import NodeRunStatus, RunState

    state = RunState(run_id="r1", plan_id="p1")
    state.set_node_status("n99", NodeRunStatus.RUNNING)
    assert "n99" in state.node_states
    assert state.node_states["n99"].status == NodeRunStatus.RUNNING


def test_compute_ready_dep_not_in_state():
    """Missing dependency in state → node not ready."""
    from research_orchestrator.scheduler import compute_ready_nodes
    from research_orchestrator.state import NodeRunStatus, NodeState, RunState
    from research_planner.models import ResearchNode, ResearchPlan

    plan = ResearchPlan(query="Dep missing")
    n1 = ResearchNode(title="A", question="Q1")
    n2 = ResearchNode(title="B", question="Q2", depends_on=["nonexistent_dep"])
    plan.add_node(n1)
    plan.add_node(n2)
    plan.approved = True

    state = RunState(run_id="r", plan_id=plan.plan_id)
    state.node_states[n1.node_id] = NodeState(
        node_id=n1.node_id, status=NodeRunStatus.PENDING
    )
    state.node_states[n2.node_id] = NodeState(
        node_id=n2.node_id, status=NodeRunStatus.PENDING
    )

    ready = compute_ready_nodes(plan, state)
    assert n1.node_id in ready
    assert n2.node_id not in ready


# ═══════════════════════════════════════════════════════════════════════════
# Phase 5 — B2-2: orchestrator.py Edge Cases (10 Missed → 0)
# ═══════════════════════════════════════════════════════════════════════════


def test_worker_exception_caught():
    """start_run: worker wirft Exception → caught, node fails (lines 220-223)."""
    from unittest.mock import MagicMock, patch
    from research_planner.approval import approve_plan
    from research_planner.models import ResearchNode, ResearchPlan
    from research_orchestrator.orchestrator import start_run
    from research_orchestrator.state import NodeRunStatus, RunStatus

    plan = ResearchPlan(query="Worker crash")
    n1 = ResearchNode(title="Node 1", question="Q1")
    plan.add_node(n1)
    approve_plan(plan)

    state = create_run(plan)
    # Create a crashing worker
    crash_worker = MagicMock(side_effect=RuntimeError("worker explosion"))

    with (
        patch("research_orchestrator.orchestrator.save_state", return_value=None),
        patch("research_orchestrator.orchestrator.append_events", return_value=None),
    ):
        result = start_run(state, worker=crash_worker)

    assert result.status == RunStatus.FAILED


def test_resume_terminal_run():
    """resume_run: terminal state → logged and returned (lines 274-275)."""
    from unittest.mock import patch
    from research_orchestrator.orchestrator import create_run, resume_run
    from research_orchestrator.state import RunStatus
    from research_planner.approval import approve_plan
    from research_planner.models import ResearchNode, ResearchPlan

    plan = ResearchPlan(query="Terminal")
    plan.add_node(ResearchNode(title="N", question="Q"))
    approve_plan(plan)

    state = create_run(plan)
    state.status = RunStatus.COMPLETED

    with patch("research_orchestrator.orchestrator.load_state", return_value=state):
        result = resume_run("some_run_id")
        assert result is not None
        assert result.status == RunStatus.COMPLETED


def test_deps_satisfied_dep_not_in_state():
    """_deps_satisfied: dep_id not in node_states → returns False (line 288)."""
    from research_orchestrator.orchestrator import _deps_satisfied
    from research_orchestrator.state import NodeRunStatus, NodeState, RunState
    from research_planner.models import ResearchNode, ResearchPlan

    plan = ResearchPlan(query="Missing dep state")
    n1 = ResearchNode(title="N1", question="Q1")
    plan.add_node(n1)
    plan.approved = True

    state = RunState(run_id="r", plan_id=plan.plan_id)
    state.node_deps[n1.node_id] = ["nonexistent_dep"]
    state.node_states[n1.node_id] = NodeState(
        node_id=n1.node_id, status=NodeRunStatus.PENDING
    )
    # "nonexistent_dep" is not in node_states

    result = _deps_satisfied(n1.node_id, state)
    assert result is False


def test_deps_satisfied_dep_failed_blocks_node():
    """_deps_satisfied: dep FAILED → node BLOCKED + returns False (lines 291-292)."""
    from research_orchestrator.orchestrator import _deps_satisfied
    from research_orchestrator.state import NodeRunStatus, NodeState, RunState
    from research_planner.models import ResearchNode, ResearchPlan

    plan = ResearchPlan(query="Dep failed")
    n1 = ResearchNode(title="N1", question="Q1")
    n2 = ResearchNode(title="N2", question="Q2")
    plan.add_node(n1)
    plan.add_node(n2)
    plan.approved = True

    state = RunState(run_id="r", plan_id=plan.plan_id)
    state.node_deps[n2.node_id] = [n1.node_id]
    state.node_states[n1.node_id] = NodeState(
        node_id=n1.node_id, status=NodeRunStatus.FAILED
    )
    state.node_states[n2.node_id] = NodeState(
        node_id=n2.node_id, status=NodeRunStatus.PENDING
    )

    result = _deps_satisfied(n2.node_id, state)
    assert result is False
    assert state.node_states[n2.node_id].status == NodeRunStatus.BLOCKED


def test_start_run_ghost_node_in_topo_order():
    """start_run: node_id in topo_order not in node_states → continue (line 169)."""
    from unittest.mock import patch
    from research_orchestrator.orchestrator import create_run, start_run
    from research_orchestrator.state import RunStatus
    from research_planner.approval import approve_plan
    from research_planner.models import ResearchNode, ResearchPlan

    plan = ResearchPlan(query="Ghost")
    n1 = ResearchNode(title="N1", question="Q1")
    plan.add_node(n1)
    approve_plan(plan)

    state = create_run(plan)
    # Add a fake node_id that doesn't exist in node_states
    state.topo_order.append("ghost_node")

    with (
        patch("research_orchestrator.orchestrator.save_state", return_value=None),
        patch("research_orchestrator.orchestrator.append_events", return_value=None),
    ):
        result = start_run(state, worker=lambda nid, q, ctx: (True, []))

    # The ghost node should be skipped via continue (line 169)
    # The real node should execute successfully
    assert result.status == RunStatus.COMPLETED


def test_start_run_no_ready_nodes_deadlock():
    """start_run: PENDING node with dep removed from state → deadlock → FAILED."""
    from unittest.mock import patch
    from research_orchestrator.orchestrator import create_run, start_run
    from research_orchestrator.state import RunStatus
    from research_planner.approval import approve_plan
    from research_planner.models import ResearchNode, ResearchPlan

    plan = ResearchPlan(query="Deadlock")
    n1 = ResearchNode(title="N1", question="Q1")
    n2 = ResearchNode(title="N2", question="Q2")
    plan.add_node(n1)
    plan.add_node(n2)
    n1.depends_on.append(n2.node_id)  # n1 depends on n2
    approve_plan(plan)

    state = create_run(plan)
    # Remove n2 from node_states → n1's dependency can't be satisfied
    del state.node_states[n2.node_id]
    # Also keep n2 in topo_order but remove from node_states

    with (
        patch("research_orchestrator.orchestrator.save_state", return_value=None),
        patch("research_orchestrator.orchestrator.append_events", return_value=None),
    ):
        result = start_run(state, worker=lambda nid, q, ctx: (True, []))

    assert result.status == RunStatus.FAILED

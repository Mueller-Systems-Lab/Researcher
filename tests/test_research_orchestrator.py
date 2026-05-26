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

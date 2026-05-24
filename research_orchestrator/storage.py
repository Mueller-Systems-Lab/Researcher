"""Filesystem-based storage for Research Run state and events.

State:   reports/deep_research/runs/<run_id>/state.json
Events:  reports/deep_research/runs/<run_id>/events.jsonl
"""

from __future__ import annotations

import json
from pathlib import Path

from research_orchestrator.state import RunState

RUNS_DIR = Path("reports/deep_research/runs")


def _run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def save_state(state: RunState) -> None:
    """Persist RunState to state.json."""
    run_dir = _run_dir(state.run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "run_id": state.run_id,
        "plan_id": state.plan_id,
        "status": state.status.value,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "started_at": state.started_at,
        "completed_at": state.completed_at,
        "max_parallel": state.max_parallel,
        "topo_order": state.topo_order,
        "errors": state.errors,
        "node_states": {
            nid: {
                "node_id": ns.node_id,
                "status": ns.status.value,
                "started_at": ns.started_at,
                "completed_at": ns.completed_at,
                "error": ns.error,
                "artifacts": ns.artifacts,
            }
            for nid, ns in state.node_states.items()
        },
    }

    state_path = run_dir / "state.json"
    state_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_state(run_id: str) -> RunState | None:
    """Load RunState from state.json. Returns None if not found."""
    state_path = _run_dir(run_id) / "state.json"
    if not state_path.exists():
        return None

    data = json.loads(state_path.read_text(encoding="utf-8"))

    from research_orchestrator.state import NodeRunStatus, NodeState, RunStatus

    state = RunState(
        run_id=data["run_id"],
        plan_id=data["plan_id"],
        status=RunStatus(data["status"]),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        started_at=data.get("started_at"),
        completed_at=data.get("completed_at"),
        max_parallel=data.get("max_parallel", 1),
        topo_order=data.get("topo_order", []),
        errors=data.get("errors", []),
    )

    for nid, nd in data.get("node_states", {}).items():
        ns = NodeState(
            node_id=nd["node_id"],
            status=NodeRunStatus(nd["status"]),
            started_at=nd.get("started_at"),
            completed_at=nd.get("completed_at"),
            error=nd.get("error"),
            artifacts=nd.get("artifacts", []),
        )
        state.node_states[nid] = ns

    return state


def load_events(run_id: str) -> list[dict]:
    """Load events from events.jsonl. Returns empty list if not found."""
    events_path = _run_dir(run_id) / "events.jsonl"
    if not events_path.exists():
        return []

    from research_orchestrator.events import jsonl_to_events

    return jsonl_to_events(events_path.read_text(encoding="utf-8"))


def append_events(run_id: str, events: list[dict]) -> None:
    """Append events to the run's events.jsonl."""
    run_dir = _run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    from research_orchestrator.events import events_to_jsonl

    events_path = run_dir / "events.jsonl"
    existing = events_path.read_text(encoding="utf-8") if events_path.exists() else ""
    new_lines = events_to_jsonl(events)
    content = existing + ("\n" if existing else "") + new_lines + "\n"
    events_path.write_text(content, encoding="utf-8")


def run_exists(run_id: str) -> bool:
    """Check if a run directory exists."""
    return _run_dir(run_id).exists()

"""Filesystem-based storage for Research Run state and events.

State:   reports/deep_research/runs/<run_id>/state.json
Events:  reports/deep_research/runs/<run_id>/events.jsonl

Thread-safe via atomic writes (tempfile + os.replace).
"""

from __future__ import annotations

import json
import tempfile
import threading
from pathlib import Path

from research_orchestrator.state import RunState

RUNS_DIR = Path("reports/deep_research/runs")
_lock = threading.Lock()


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically via tempfile + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(content)
        Path(tmp).replace(path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


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
        "query": state.query,
        "language": state.language,
        "node_questions": state.node_questions,
        "node_rationales": state.node_rationales,
        "node_expected_sources": {
            k: list(v) for k, v in state.node_expected_sources.items()
        },
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
    _atomic_write(state_path, json.dumps(data, indent=2, ensure_ascii=False))


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
        query=data.get("query", ""),
        language=data.get("language", "unknown"),
        node_questions=data.get("node_questions", {}),
        node_rationales=data.get("node_rationales", {}),
        node_expected_sources=data.get("node_expected_sources", {}),
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
    """Append events to the run's events.jsonl (thread-safe)."""
    run_dir = _run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    from research_orchestrator.events import events_to_jsonl

    events_path = run_dir / "events.jsonl"
    new_lines = events_to_jsonl(events)

    with _lock:
        existing = (
            events_path.read_text(encoding="utf-8") if events_path.exists() else ""
        )
        content = existing + ("\n" if existing and not existing.endswith("\n") else "")
        content += new_lines + "\n"
        _atomic_write(events_path, content)


def run_exists(run_id: str) -> bool:
    """Check if a run directory exists."""
    return _run_dir(run_id).exists()

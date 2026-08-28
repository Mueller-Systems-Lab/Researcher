"""Observable contracts for the public string enums.

These assertions intentionally capture the pre-UP042 behavior before the
enum bases are migrated.  They protect both the values used in persistence
and the legacy ``str(EnumMember)`` representation used by callers.
"""

import json

import pytest

from config.local_llm_runtime import RuntimeStatus
from research_orchestrator.events import EventType, emit_event, events_to_jsonl
from research_orchestrator.state import NodeRunStatus, NodeState, RunState, RunStatus
from research_orchestrator.storage import load_state, save_state
from research_planner.models import (
    ResearchNode,
    ResearchPlan,
    ResearchPlanStatus,
    RiskLevel,
)
from research_planner.serialization import plan_to_dict

ENUM_CONTRACTS = [
    (
        RuntimeStatus,
        {
            "LOCAL_LLM_READY": "LOCAL_LLM_READY",
            "LOCAL_LLM_PARTIAL": "LOCAL_LLM_PARTIAL",
            "LOCAL_LLM_BLOCKED": "LOCAL_LLM_BLOCKED",
            "MODEL_GARBLED": "MODEL_GARBLED",
            "MODEL_TIMEOUT": "MODEL_TIMEOUT",
            "MODEL_CRASH": "MODEL_CRASH",
            "CLOUD_BLOCKED": "CLOUD_BLOCKED",
            "LOCAL_OPENAI_COMPAT_ALLOWED": "LOCAL_OPENAI_COMPAT_ALLOWED",
        },
    ),
    (
        EventType,
        {
            "RUN_CREATED": "RUN_CREATED",
            "RUN_STARTED": "RUN_STARTED",
            "RUN_COMPLETED": "RUN_COMPLETED",
            "RUN_FAILED": "RUN_FAILED",
            "RUN_CANCELLED": "RUN_CANCELLED",
            "NODE_READY": "NODE_READY",
            "NODE_STARTED": "NODE_STARTED",
            "NODE_COMPLETED": "NODE_COMPLETED",
            "NODE_FAILED": "NODE_FAILED",
            "NODE_BLOCKED": "NODE_BLOCKED",
        },
    ),
    (
        RunStatus,
        {
            "CREATED": "created",
            "RUNNING": "running",
            "COMPLETED": "completed",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
        },
    ),
    (
        NodeRunStatus,
        {
            "PENDING": "pending",
            "READY": "ready",
            "RUNNING": "running",
            "COMPLETED": "completed",
            "FAILED": "failed",
            "BLOCKED": "blocked",
        },
    ),
    (
        ResearchPlanStatus,
        {
            "DRAFT": "draft",
            "APPROVED": "approved",
            "RUNNING": "running",
            "COMPLETED": "completed",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
        },
    ),
    (
        RiskLevel,
        {
            "LOW": "low",
            "MEDIUM": "medium",
            "HIGH": "high",
            "UNKNOWN": "unknown",
        },
    ),
]


@pytest.mark.parametrize("enum_type, expected", ENUM_CONTRACTS)
def test_string_enum_observable_contract(enum_type, expected):
    """Every member retains its value and legacy string formatting contract."""
    assert {member.name: member.value for member in enum_type} == expected

    for name, value in expected.items():
        member = enum_type[name]
        legacy_string = f"{enum_type.__name__}.{name}"

        assert member.name == name
        assert member.value == value
        assert str(member) == legacy_string
        assert repr(member) == f"<{legacy_string}: {value!r}>"
        assert f"{member}" == legacy_string
        assert format(member) == legacy_string
        assert member == value
        assert isinstance(member, str)
        assert json.dumps({"value": member}) == json.dumps({"value": value})


def test_event_serialization_uses_enum_value():
    event = emit_event(EventType.NODE_READY, "run-1", node_id="node-1")

    assert event["event"] == "NODE_READY"
    assert json.loads(events_to_jsonl([event]))["event"] == "NODE_READY"


def test_plan_api_serialization_uses_enum_values():
    node = ResearchNode(
        title="A node",
        question="A question",
        node_id="node-1",
        status=ResearchPlanStatus.APPROVED,
        risk_level=RiskLevel.HIGH,
    )
    plan = ResearchPlan(
        query="A query",
        plan_id="plan-1",
        nodes=[node],
        status=ResearchPlanStatus.RUNNING,
    )

    data = plan_to_dict(plan)

    assert data["status"] == "running"
    assert data["nodes"][0]["status"] == "approved"
    assert data["nodes"][0]["risk_level"] == "high"


def test_run_state_storage_uses_enum_values(tmp_path, monkeypatch):
    import research_orchestrator.storage as storage

    monkeypatch.setattr(storage, "RUNS_DIR", tmp_path)
    state = RunState(
        run_id="run-1",
        plan_id="plan-1",
        status=RunStatus.RUNNING,
        node_states={
            "node-1": NodeState(
                node_id="node-1",
                status=NodeRunStatus.COMPLETED,
            )
        },
    )

    save_state(state)
    stored = json.loads((tmp_path / "run-1" / "state.json").read_text())
    restored = load_state("run-1")

    assert stored["status"] == "running"
    assert stored["node_states"]["node-1"]["status"] == "completed"
    assert restored is not None
    assert restored.status is RunStatus.RUNNING
    assert restored.node_states["node-1"].status is NodeRunStatus.COMPLETED

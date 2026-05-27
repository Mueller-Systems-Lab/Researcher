"""Event log for research runs — JSONL format.

Events are appended to events.jsonl in reports/deep_research/runs/<run_id>/.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    RUN_CREATED = "RUN_CREATED"
    RUN_STARTED = "RUN_STARTED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"
    RUN_CANCELLED = "RUN_CANCELLED"
    NODE_READY = "NODE_READY"
    NODE_STARTED = "NODE_STARTED"
    NODE_COMPLETED = "NODE_COMPLETED"
    NODE_FAILED = "NODE_FAILED"
    NODE_BLOCKED = "NODE_BLOCKED"


def emit_event(
    event_type: EventType,
    run_id: str,
    node_id: str | None = None,
    message: str = "",
    payload: dict | None = None,
) -> dict[str, Any]:
    """Create an immutable event record."""
    event: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "event": event_type.value,
    }
    if node_id:
        event["node_id"] = node_id
    if message:
        event["message"] = message
    if payload:
        event["payload"] = payload
    return event


def events_to_jsonl(events: list[dict]) -> str:
    """Serialize a list of event dicts to JSONL string."""
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in events)


def jsonl_to_events(jsonl: str) -> list[dict]:
    """Parse JSONL string back to event dicts."""
    events: list[dict] = []
    for line in jsonl.strip().split("\n"):
        if line.strip():
            events.append(json.loads(line))
    return events

"""Deep Research API — endpoint handlers for the Dashboard integration.

Provides the handler functions for the Deep Research flow:
Plan → Approve → Run → Events → Report → Evaluation

Designed for stdlib http.server integration (no framework dependency).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC
from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


# ── State ────────────────────────────────────────────────────────────────

# In-memory registry for demo/testing.
# Production: uses research_planner + research_orchestrator + evidence_store.
_plans: dict[str, dict] = {}
_runs: dict[str, dict] = {}
_next_plan_id = 0
_next_run_id = 0


def _plan_id() -> str:
    global _next_plan_id
    _next_plan_id += 1
    return f"plan-{_next_plan_id}"


def _run_id() -> str:
    global _next_run_id
    _next_run_id += 1
    return f"run-{_next_run_id}"


# ── API Handlers ─────────────────────────────────────────────────────────


def handle_deep_research_plan(
    handler: BaseHTTPRequestHandler,
    body: dict | None = None,
) -> None:
    """POST /api/deep-research/plan — create a research plan."""
    if body is None or "query" not in body:
        _json_error(handler, 400, "Missing 'query' in request body")
        return

    pid = _plan_id()
    plan = {
        "plan_id": pid,
        "query": body["query"],
        "status": "draft",
        "nodes": body.get(
            "nodes",
            [{"node_id": f"{pid}-n1", "title": "Research", "question": body["query"]}],
        ),
        "dependencies": body.get("dependencies", []),
        "created_at": _now(),
    }
    _plans[pid] = plan
    _json_response(handler, 201, plan)


def handle_deep_research_get_plan(
    handler: BaseHTTPRequestHandler,
    plan_id: str,
) -> None:
    """GET /api/deep-research/plans/{id} — get a plan."""
    plan = _plans.get(plan_id)
    if plan is None:
        _json_error(handler, 404, f"Plan '{plan_id}' not found")
        return
    _json_response(handler, 200, plan)


def handle_deep_research_approve(
    handler: BaseHTTPRequestHandler,
    plan_id: str,
) -> None:
    """POST /api/deep-research/plans/{id}/approve — approve a plan."""
    plan = _plans.get(plan_id)
    if plan is None:
        _json_error(handler, 404, f"Plan '{plan_id}' not found")
        return
    plan["status"] = "approved"
    plan["approved_at"] = _now()
    _json_response(handler, 200, plan)


def handle_deep_research_run(
    handler: BaseHTTPRequestHandler,
    body: dict | None = None,
) -> None:
    """POST /api/deep-research/runs — start a research run."""
    if body is None or "plan_id" not in body:
        _json_error(handler, 400, "Missing 'plan_id' in request body")
        return

    plan_id = body["plan_id"]
    plan = _plans.get(plan_id)
    if plan is None:
        _json_error(handler, 404, f"Plan '{plan_id}' not found")
        return
    if plan["status"] != "approved":
        _json_error(
            handler, 400, f"Plan '{plan_id}' is not approved (status: {plan['status']})"
        )
        return

    rid = _run_id()
    run = {
        "run_id": rid,
        "plan_id": plan_id,
        "status": "running",
        "started_at": _now(),
        "events": [
            {"event": "RUN_CREATED", "run_id": rid, "timestamp": _now()},
            {"event": "RUN_STARTED", "run_id": rid, "timestamp": _now()},
        ],
        "node_states": {
            n["node_id"]: {"status": "pending"} for n in plan.get("nodes", [])
        },
        "report": None,
        "evaluation": None,
    }
    _runs[rid] = run

    # Simulate node progress (sequential, instant for demo)
    nodes = plan.get("nodes", [])
    for node in nodes:
        nid = node["node_id"]
        run["node_states"][nid] = {"status": "completed"}
        run["events"].append(
            {
                "event": "NODE_COMPLETED",
                "run_id": rid,
                "node_id": nid,
                "timestamp": _now(),
            }
        )

    run["status"] = "completed"
    run["completed_at"] = _now()
    run["events"].append(
        {
            "event": "RUN_COMPLETED",
            "run_id": rid,
            "timestamp": _now(),
        }
    )

    # Generate a demo report
    run["report"] = _generate_demo_report(plan, run)
    run["evaluation"] = {
        "source_coverage": 85.0,
        "traceability": 90.0,
        "evidence_diversity": 70.0,
        "node_completion": 100.0,
        "hallucination_risk": 15.0,
        "local_first": 100.0,
        "injection_risk": 0.0,
        "overall": 88.0,
    }

    _json_response(handler, 201, run)


def handle_deep_research_get_run(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id} — get run status."""
    run = _runs.get(run_id)
    if run is None:
        _json_error(handler, 404, f"Run '{run_id}' not found")
        return
    _json_response(handler, 200, run)


def handle_deep_research_get_events(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/events — get event stream."""
    run = _runs.get(run_id)
    if run is None:
        _json_error(handler, 404, f"Run '{run_id}' not found")
        return
    _json_response(handler, 200, {"events": run.get("events", [])})


def handle_deep_research_get_report(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/report — get report."""
    run = _runs.get(run_id)
    if run is None:
        _json_error(handler, 404, f"Run '{run_id}' not found")
        return
    report = run.get("report")
    if report is None:
        _json_error(handler, 404, "Report not yet generated")
        return
    _json_response(handler, 200, {"report": report, "format": "markdown"})


def handle_deep_research_get_evaluation(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/evaluation — get evaluation scores."""
    run = _runs.get(run_id)
    if run is None:
        _json_error(handler, 404, f"Run '{run_id}' not found")
        return
    evaluation = run.get("evaluation")
    if evaluation is None:
        _json_error(handler, 404, "Evaluation not yet available")
        return
    _json_response(handler, 200, evaluation)


def handle_deep_research_events_sse(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/events/stream — SSE event stream."""
    run = _runs.get(run_id)
    if run is None:
        _json_error(handler, 404, f"Run '{run_id}' not found")
        return

    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.end_headers()

    events = run.get("events", [])
    for event in events:
        data = f"data: {json.dumps(event)}\n\n"
        handler.wfile.write(data.encode())
    handler.wfile.write(b"event: done\ndata: stream-end\n\n")


# ── Router ───────────────────────────────────────────────────────────────


def route_deep_research(
    handler: BaseHTTPRequestHandler,
    path: str,
    method: str = "GET",
    body: dict | None = None,
) -> bool:
    """Route a Deep Research API request. Returns True if handled."""
    # POST /api/deep-research/plan
    if method == "POST" and path == "/api/deep-research/plan":
        handle_deep_research_plan(handler, body)
        return True

    # POST /api/deep-research/runs
    if method == "POST" and path == "/api/deep-research/runs":
        handle_deep_research_run(handler, body)
        return True

    # GET /api/deep-research/plans/{id}
    if method == "GET" and path.startswith("/api/deep-research/plans/"):
        plan_id = path.split("/")[-1]
        handle_deep_research_get_plan(handler, plan_id)
        return True

    # POST /api/deep-research/plans/{id}/approve
    if method == "POST" and "/approve" in path:
        plan_id = (
            path.split("/")[-2] if path.endswith("/approve") else path.split("/")[-1]
        )
        handle_deep_research_approve(handler, plan_id)
        return True

    # GET /api/deep-research/runs/{id}/events
    if method == "GET" and "/events" in path and "/stream" not in path:
        parts = path.split("/")
        run_id = parts[4] if len(parts) > 4 else ""
        handle_deep_research_get_events(handler, run_id)
        return True

    # GET /api/deep-research/runs/{id}/events/stream (SSE)
    if method == "GET" and "/events/stream" in path:
        parts = path.split("/")
        run_id = parts[4] if len(parts) > 4 else ""
        handle_deep_research_events_sse(handler, run_id)
        return True

    # GET /api/deep-research/runs/{id}/report
    if method == "GET" and "/report" in path:
        parts = path.split("/")
        run_id = parts[4] if len(parts) > 4 else ""
        handle_deep_research_get_report(handler, run_id)
        return True

    # GET /api/deep-research/runs/{id}/evaluation
    if method == "GET" and "/evaluation" in path:
        parts = path.split("/")
        run_id = parts[4] if len(parts) > 4 else ""
        handle_deep_research_get_evaluation(handler, run_id)
        return True

    # GET /api/deep-research/runs/{id}
    if method == "GET" and path.startswith("/api/deep-research/runs/"):
        run_id = path.split("/")[-1]
        handle_deep_research_get_run(handler, run_id)
        return True

    return False


# ── Helpers ──────────────────────────────────────────────────────────────


def _json_response(
    handler: BaseHTTPRequestHandler, status: int, data: dict | list
) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, ensure_ascii=False).encode())


def _json_error(handler: BaseHTTPRequestHandler, status: int, message: str) -> None:
    _json_response(handler, status, {"error": message})


def _now() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def _generate_demo_report(plan: dict, run: dict) -> str:
    """Generate a minimal demo report."""
    query = plan.get("query", "Research")
    nodes = plan.get("nodes", [])
    findings = "\n".join(
        f"### {n['title']}\n\nResearch completed for: {n['question']}" for n in nodes
    )
    return (
        f"# Deep Research Report: {query}\n\n"
        f"## Executive Summary\n\n"
        f"Research completed across {len(nodes)} steps.\n\n"
        f"## Findings\n\n{findings}\n\n"
        f"## Evaluation\n\n"
        f"- Source Coverage: 85%\n"
        f"- Traceability: 90%\n"
        f"- Local-First: 100%\n"
    )


def clear_state() -> None:
    """Clear all in-memory state (for testing)."""
    _plans.clear()
    _runs.clear()
    global _next_plan_id, _next_run_id
    _next_plan_id = 0
    _next_run_id = 0

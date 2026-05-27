"""Deep Research API — endpoint handlers for the Dashboard integration.

Provides handlers for: Plan → Approve → Run → Events → Report → Evaluation

Uses real implementations:
  - research_planner.planner.generate_plan  → Plan creation
  - research_planner.validation.validate_plan → DAG validation
  - research_planner.approval.approve_plan → Human-in-the-loop approval
  - research_planner.serialization.plan_to_dict → Plan serialization
  - research_orchestrator.orchestrator → Run creation + execution
  - research_orchestrator.storage → Run state persistence
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC
from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────

REPORT_DIR = os.getenv("DEEP_REPORT_DIR", "reports/deep_research")

# CORS: allow same-origin + configured origins
_ALLOWED_ORIGINS_STR = os.getenv(
    "DASHBOARD_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000,http://localhost:8888,"
    "http://127.0.0.1:3000,http://127.0.0.1:8000,http://127.0.0.1:8888",
)

# In-memory plan registry with filesystem persistence fallback.
# Plans are stored in reports/deep_research/plans/<plan_id>.json
# and cached in _plans dict for the lifetime of the process.
_PLANS_DIR = os.path.join(REPORT_DIR, "plans")
_plans: dict[str, dict] = {}


def _save_plan(plan_id: str, plan_data: dict) -> None:
    """Persist a plan to the filesystem as JSON."""
    os.makedirs(_PLANS_DIR, exist_ok=True)
    plan_path = os.path.join(_PLANS_DIR, f"{plan_id}.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan_data, f, indent=2, ensure_ascii=False)


def _load_plan(plan_id: str) -> dict | None:
    """Load a plan from the filesystem. Returns None if not found."""
    plan_path = os.path.join(_PLANS_DIR, f"{plan_id}.json")
    if not os.path.exists(plan_path):
        return None
    with open(plan_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Plan Endpoints ───────────────────────────────────────────────────────


def handle_deep_research_plan(
    handler: BaseHTTPRequestHandler,
    body: dict | None = None,
) -> None:
    """POST /api/deep-research/plan — create a research plan via the planner."""
    if body is None or "query" not in body:
        _json_error(handler, 400, "Missing 'query' in request body")
        return

    query = body["query"]

    try:
        from research_planner.planner import generate_plan
        from research_planner.validation import validate_plan
        from research_planner.serialization import plan_to_json

        plan = generate_plan(
            query,
            language="de" if any(ord(c) > 127 for c in query) else "unknown",
        )

        # Validate DAG
        validation_errors = validate_plan(plan)
        plan_as_dict = json.loads(plan_to_json(plan))
        plan_as_dict["status"] = "draft"
        plan_as_dict["created_at"] = _now()
        plan_as_dict["validation_errors"] = validation_errors or None

        # Store in registry (memory + filesystem)
        _plans[plan.plan_id] = plan_as_dict
        _save_plan(plan.plan_id, plan_as_dict)

        status = 201
        _json_response(handler, status, plan_as_dict)

    except ImportError as e:
        logger.error(f"research_planner not available: {e}", exc_info=True)
        _json_response(
            handler,
            501,
            {
                "error": "research_planner module not loaded",
                "detail": str(e),
            },
        )
    except Exception as e:
        logger.error(f"Plan creation failed: {e}", exc_info=True)
        _json_error(handler, 500, f"Plan creation failed: {e}")


def handle_deep_research_get_plan(
    handler: BaseHTTPRequestHandler,
    plan_id: str,
) -> None:
    """GET /api/deep-research/plans/{id} — get a plan by ID.

    Checks in-memory cache first, then falls back to filesystem persistence.
    """
    plan = _plans.get(plan_id)
    if plan is None:
        plan = _load_plan(plan_id)
        if plan is not None:
            _plans[plan_id] = plan  # cache in memory
    if plan is None:
        _json_error(handler, 404, f"Plan '{plan_id}' not found")
        return
    _json_response(handler, 200, plan)


def handle_deep_research_approve(
    handler: BaseHTTPRequestHandler,
    plan_id: str,
) -> None:
    """POST /api/deep-research/plans/{id}/approve — approve plan for execution."""
    plan = _plans.get(plan_id)
    if plan is None:
        plan = _load_plan(plan_id)
        if plan is not None:
            _plans[plan_id] = plan  # cache in memory
    if plan is None:
        _json_error(handler, 404, f"Plan '{plan_id}' not found")
        return

    try:
        from research_planner.approval import approve_plan
        from research_planner.models import ResearchPlan
        from research_planner.serialization import plan_from_dict

        plan_obj = plan_from_dict(plan)
        approve_plan(plan_obj)
        plan["status"] = "approved"
        plan["approved_at"] = _now()
        _save_plan(plan_id, plan)
        _json_response(handler, 200, {"plan_id": plan_id, "status": "approved"})
    except ImportError as e:
        # Fallback: manual approval
        plan["status"] = "approved"
        plan["approved_at"] = _now()
        plan["approved_by"] = "api"
        _save_plan(plan_id, plan)
        _json_response(handler, 200, {"plan_id": plan_id, "status": "approved"})
    except Exception as e:
        logger.error(f"Approval failed for {plan_id}: {e}", exc_info=True)
        _json_error(handler, 500, f"Plan approval failed: {e}")


# ── Run Endpoints ────────────────────────────────────────────────────────


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
        plan = _load_plan(plan_id)
        if plan is not None:
            _plans[plan_id] = plan  # cache in memory
    if plan is None:
        _json_error(handler, 404, f"Plan '{plan_id}' not found")
        return
    if plan.get("status") != "approved":
        _json_error(
            handler,
            400,
            f"Plan '{plan_id}' not approved (status: {plan.get('status', 'unknown')})",
        )
        return

    try:
        from research_orchestrator.orchestrator import create_run, resume_run
        from research_planner.models import ResearchPlan
        from research_planner.serialization import plan_from_dict

        plan_obj = plan_from_dict(plan)
        run = create_run(plan_obj)
        run_id = run.run_id

        # Start async execution via resume_run (loads RunState from storage)
        import threading

        def _run_background():
            try:
                resume_run(run_id)
            except Exception as e:
                logger.error(f"Run {run_id} failed: {e}", exc_info=True)

        t = threading.Thread(target=_run_background, daemon=True)
        t.start()

        _json_response(
            handler,
            201,
            {
                "run_id": run_id,
                "plan_id": plan_id,
                "status": "running",
                "message": f"Run started — check /api/deep-research/runs/{run_id}",
            },
        )
    except ImportError as e:
        logger.error(f"Orchestrator not available: {e}", exc_info=True)
        _json_response(
            handler,
            501,
            {
                "error": "research_orchestrator not loaded",
                "detail": str(e),
            },
        )
    except Exception as e:
        logger.error(f"Run start failed: {e}", exc_info=True)
        _json_error(handler, 500, f"Run start failed: {e}")


def handle_deep_research_get_run(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id} — get run status."""
    try:
        from research_orchestrator.storage import load_state

        state = load_state(run_id)
        if state is None:
            _json_error(handler, 404, f"Run '{run_id}' not found")
            return

        _json_response(
            handler,
            200,
            {
                "run_id": run_id,
                "status": state.status.value
                if hasattr(state.status, "value")
                else str(state.status),
                "node_states": {
                    nid: {
                        "status": ns.status.value
                        if hasattr(ns.status, "value")
                        else str(ns.status),
                    }
                    for nid, ns in state.node_states.items()
                },
                "started_at": getattr(state, "started_at", None),
                "completed_at": getattr(state, "completed_at", None),
            },
        )
    except ImportError:
        _json_error(handler, 501, "Orchestrator storage not available")
    except Exception as e:
        logger.error(f"Failed to load run {run_id}: {e}", exc_info=True)
        _json_error(handler, 500, f"Failed to load run: {e}")


def handle_deep_research_get_events(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/events — get event log."""
    try:
        from research_orchestrator.storage import load_events

        events = load_events(run_id)
        _json_response(handler, 200, {"run_id": run_id, "events": events})
    except ImportError:
        _json_error(handler, 501, "Orchestrator storage not available")
    except Exception as e:
        logger.error(f"Failed to load events for {run_id}: {e}", exc_info=True)
        _json_error(handler, 500, f"Failed to load events: {e}")


def handle_deep_research_get_report(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/report — get generated report.

    Tries to load a pre-generated report.md first. If not found,
    generates a live outline from run state data.
    """
    report_path = os.path.join(REPORT_DIR, "runs", run_id, "report.md")
    if os.path.exists(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report = f.read()
            _json_response(handler, 200, {"report": report, "format": "markdown"})
            return
        except (OSError, IOError) as e:
            logger.error("Failed to read report for %s: %s", run_id, e)

    # Fallback: generate outline from run state data
    try:
        from deep_report.outline import load_run_data_for_outline, generate_outline

        run_data = load_run_data_for_outline(run_id)
        if run_data:
            outline = generate_outline(
                query=run_data.get("query", "Unknown query"),
                node_results=run_data.get("node_results"),
                sources=run_data.get("sources"),
            )
            _json_response(
                handler,
                200,
                {
                    "report": _outline_to_markdown(outline),
                    "format": "markdown",
                    "status": "from_run_data",
                    "outline": outline,
                },
            )
            return
    except ImportError as e:
        logger.error("deep_report.outline not available: %s", e)
    except Exception as e:
        logger.error("Failed to generate outline for %s: %s", run_id, e)

    _json_response(
        handler,
        200,
        {
            "report": None,
            "format": "markdown",
            "status": "pending",
            "message": "Report not yet generated — run may still be in progress.",
        },
    )


def handle_deep_research_get_evaluation(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/evaluation — get evaluation scores.

    Tries to load a pre-generated evaluation.json first. If not found,
    computes basic evaluation from run state (node completion stats).
    """
    eval_path = os.path.join(REPORT_DIR, "runs", run_id, "evaluation.json")
    if os.path.exists(eval_path):
        try:
            with open(eval_path, "r", encoding="utf-8") as f:
                evaluation = json.load(f)
            _json_response(handler, 200, evaluation)
            return
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to read evaluation for %s: %s", run_id, e)

    # Fallback: compute basic evaluation from run state
    try:
        from research_orchestrator.storage import load_state

        state = load_state(run_id)
        if state is not None:
            completed = 0
            failed = 0
            total = len(state.node_states)
            for ns in state.node_states.values():
                if ns.status.value == "completed":
                    completed += 1
                elif ns.status.value == "failed":
                    failed += 1

            evaluation = {
                "status": state.status.value
                if hasattr(state.status, "value")
                else str(state.status),
                "nodes": {
                    "total": total,
                    "completed": completed,
                    "failed": failed,
                    "pending": total - completed - failed,
                },
                "completion_rate": round(completed / max(total, 1) * 100, 1),
                "has_errors": len(state.errors) > 0,
                "error_count": len(state.errors),
            }
            _json_response(
                handler,
                200,
                {
                    "evaluation": evaluation,
                    "status": "from_run_state",
                    "message": "Basic evaluation from run state. Run full evaluation pipeline for detailed scores.",
                },
            )
            return
    except ImportError:
        logger.error("research_orchestrator.storage not available for evaluation")
    except Exception as e:
        logger.error("Failed to compute evaluation for %s: %s", run_id, e)

    _json_response(
        handler,
        200,
        {
            "status": "pending",
            "message": "Evaluation not yet available — run may still be in progress.",
        },
    )


def handle_deep_research_events_sse(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/events/stream — SSE event stream."""
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.end_headers()

    try:
        from research_orchestrator.storage import load_events

        events = load_events(run_id)
        for event in events:
            data = f"data: {json.dumps(event)}\n\n"
            handler.wfile.write(data.encode())
    except ImportError:
        logger.error("research_orchestrator.storage not available for SSE")
        error_data = f"data: {json.dumps({'event': 'ERROR', 'message': 'Storage not available'})}\n\n"
        handler.wfile.write(error_data.encode())
    except Exception as e:
        logger.error("SSE stream error for run %s: %s", run_id, e, exc_info=True)
        error_data = f"data: {json.dumps({'event': 'ERROR', 'message': str(e)})}\n\n"
        handler.wfile.write(error_data.encode())
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
    if method == "GET" and path.endswith("/events"):
        run_id = path.split("/")[-2]
        handle_deep_research_get_events(handler, run_id)
        return True

    # GET /api/deep-research/runs/{id}/events/stream (SSE)
    if method == "GET" and "/events/stream" in path:
        run_id = path.split("/")[-3]
        handle_deep_research_events_sse(handler, run_id)
        return True

    # GET /api/deep-research/runs/{id}/report
    if method == "GET" and "/report" in path:
        run_id = path.split("/")[-2]
        handle_deep_research_get_report(handler, run_id)
        return True

    # GET /api/deep-research/runs/{id}/evaluation
    if method == "GET" and "/evaluation" in path:
        run_id = path.split("/")[-2]
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
    # Use configured origins — fallback to request origin for same-origin
    origin = ""
    try:
        origin = handler.headers.get("Origin", "")
    except AttributeError:
        pass  # Test handlers may not have headers
    origins = _ALLOWED_ORIGINS_STR.split(",")
    if origin in origins or not origin:
        handler.send_header("Access-Control-Allow-Origin", origin or "*")
        handler.send_header("Vary", "Origin")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, ensure_ascii=False).encode())


def _json_error(handler: BaseHTTPRequestHandler, status: int, message: str) -> None:
    _json_response(handler, status, {"error": message})


def _now() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def _outline_to_markdown(outline: list[dict]) -> str:
    """Convert an outline list of section dicts to Markdown string."""
    parts = []
    for section in outline:
        title = section.get("title", "")
        content = section.get("content", "")
        if title == "Title":
            parts.append(content)
        else:
            parts.append(f"## {title}\n\n{content}")
    return "\n\n---\n\n".join(parts)

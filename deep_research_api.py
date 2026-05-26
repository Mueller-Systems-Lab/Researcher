"""Deep Research API — endpoint handlers for the Dashboard integration.

Provides the handler functions for the Deep Research flow:
Plan → Approve → Run → Events → Report → Evaluation

Uses real implementations from:
  - research_planner  → Plan creation + DAG validation + serialization
  - research_orchestrator → Run execution + state machine + persistence
  - research_workers → Query decomposition + gap analysis
  - searcher_pipeline → Search execution + caching + reranking
  - evidence_store → Source/segment persistence + citation labels
  - deep_report → Report writing + evaluation + revision loop

Designed for stdlib http.server integration (no framework dependency).
"""

from __future__ import annotations

import json
import logging
import os
import traceback
from datetime import UTC
from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


# ── Configuration ────────────────────────────────────────────────────────

REPORT_DIR = os.getenv("DEEP_REPORT_DIR", "reports/deep_research")


# ── Plan Implementation ──────────────────────────────────────────────────


def handle_deep_research_plan(
    handler: BaseHTTPRequestHandler,
    body: dict | None = None,
) -> None:
    """POST /api/deep-research/plan — create a research plan using CollaborativePlanner."""
    if body is None or "query" not in body:
        _json_error(handler, 400, "Missing 'query' in request body")
        return

    query = body["query"]
    max_nodes = body.get("max_nodes", 10)

    try:
        from research_planner.planner import CollaborativePlanner
        from research_planner.validation import validate_plan
        from research_planner.serialization import plan_to_dict

        planner = CollaborativePlanner()
        plan = planner.create_plan(query, max_nodes=max_nodes)

        # Validate the DAG
        errors = validate_plan(plan)
        if errors:
            _json_response(
                handler,
                200,
                {
                    "plan_id": plan.plan_id,
                    "query": query,
                    "status": "draft",
                    "validation_errors": errors,
                    "nodes": [n.to_dict() for n in plan.nodes],
                    "dependencies": [
                        {"from": d.from_node, "to": d.to_node}
                        for d in plan.dependencies
                    ],
                    "created_at": _now(),
                    "warning": "Plan has validation errors — review before approval",
                },
            )
            return

        plan_dict = plan_to_dict(plan)
        plan_dict["status"] = "draft"
        plan_dict["created_at"] = _now()
        _json_response(handler, 201, plan_dict)

    except ImportError as e:
        logger.error(f"research_planner nicht verfügbar: {e}")
        _json_response(
            handler,
            501,
            {
                "error": "research_planner module not available",
                "detail": str(e),
                "hint": "Checkout branch issue/098-deep-research-planner-dag",
            },
        )
    except Exception as e:
        logger.error(f"Plan-Erstellung fehlgeschlagen: {e}", exc_info=True)
        _json_error(handler, 500, f"Plan creation failed: {e}")


def handle_deep_research_get_plan(
    handler: BaseHTTPRequestHandler,
    plan_id: str,
) -> None:
    """GET /api/deep-research/plans/{id} — get a plan from storage."""
    try:
        from research_orchestrator.storage import load_plan

        plan = load_plan(plan_id, base_dir=REPORT_DIR)
        if plan is None:
            _json_error(handler, 404, f"Plan '{plan_id}' not found")
            return
        _json_response(handler, 200, plan.to_dict())
    except ImportError:
        # Fallback: in-memory lookup
        _json_error(handler, 501, "Orchestrator storage not available")
    except Exception as e:
        logger.error(f"Fehler beim Laden von Plan {plan_id}: {e}", exc_info=True)
        _json_error(handler, 500, f"Error loading plan: {e}")


def handle_deep_research_approve(
    handler: BaseHTTPRequestHandler,
    plan_id: str,
) -> None:
    """POST /api/deep-research/plans/{id}/approve — approve a plan."""
    try:
        from research_orchestrator.storage import load_plan, save_plan
        from research_planner.approval import approve_plan

        plan = load_plan(plan_id, base_dir=REPORT_DIR)
        if plan is None:
            _json_error(handler, 404, f"Plan '{plan_id}' not found")
            return

        approved = approve_plan(plan)
        if not approved:
            _json_error(
                handler,
                400,
                f"Plan '{plan_id}' could not be approved — validation failed",
            )
            return

        save_plan(plan, base_dir=REPORT_DIR)
        _json_response(
            handler,
            200,
            {
                "plan_id": plan_id,
                "status": "approved",
                "approved_at": _now(),
            },
        )
    except ImportError as e:
        logger.error(f"Approval module not available: {e}")
        _json_error(handler, 501, f"Approval module not available: {e}")
    except Exception as e:
        logger.error(f"Fehler bei Approve {plan_id}: {e}", exc_info=True)
        _json_error(handler, 500, f"Error approving plan: {e}")


def handle_deep_research_run(
    handler: BaseHTTPRequestHandler,
    body: dict | None = None,
) -> None:
    """POST /api/deep-research/runs — start actual research via orchestrator."""
    if body is None or "plan_id" not in body:
        _json_error(handler, 400, "Missing 'plan_id' in request body")
        return

    plan_id = body["plan_id"]

    try:
        from research_orchestrator.storage import load_plan
        from research_orchestrator.orchestrator import ResearchOrchestrator
        from research_planner.approval import assert_plan_approved

        plan = load_plan(plan_id, base_dir=REPORT_DIR)
        if plan is None:
            _json_error(handler, 404, f"Plan '{plan_id}' not found")
            return

        # Verify approval
        try:
            assert_plan_approved(plan)
        except PermissionError as e:
            _json_error(
                handler,
                400,
                f"Plan '{plan_id}' is not approved: {e}",
            )
            return

        # Create and start run
        orchestrator = ResearchOrchestrator(
            base_dir=REPORT_DIR,
            model=os.getenv("FAST_LLM", "ollama:qwen3.5:9b"),
        )
        run = orchestrator.create_run(plan)
        run_id = run.run_id

        # Start execution in background (non-blocking for API)
        import threading

        def _run_in_background():
            try:
                orchestrator.start_run(run_id)
            except Exception as e:
                logger.error(f"Run {run_id} failed: {e}", exc_info=True)

        thread = threading.Thread(target=_run_in_background, daemon=True)
        thread.start()

        _json_response(
            handler,
            201,
            {
                "run_id": run_id,
                "plan_id": plan_id,
                "status": "running",
                "started_at": _now(),
                "message": "Research run started — check /api/deep-research/runs/{id} for status",
            },
        )

    except ImportError as e:
        logger.error(f"Orchestrator module not available: {e}")
        _json_response(
            handler,
            501,
            {
                "error": "research_orchestrator module not available",
                "detail": str(e),
                "hint": "Checkout branch issue/099-deep-research-orchestrator",
            },
        )
    except Exception as e:
        logger.error(f"Run-Start fehlgeschlagen: {e}", exc_info=True)
        _json_error(handler, 500, f"Research run failed to start: {e}")


def handle_deep_research_get_run(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id} — get run status from orchestrator."""
    try:
        from research_orchestrator.storage import load_run

        run = load_run(run_id, base_dir=REPORT_DIR)
        if run is None:
            _json_error(handler, 404, f"Run '{run_id}' not found")
            return
        _json_response(handler, 200, run.to_dict())
    except ImportError:
        _json_error(handler, 501, "Orchestrator storage not available")
    except Exception as e:
        logger.error(f"Fehler beim Laden von Run {run_id}: {e}", exc_info=True)
        _json_error(handler, 500, f"Error loading run: {e}")


def handle_deep_research_get_events(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/events — get event log from orchestrator."""
    try:
        from research_orchestrator.storage import load_run

        run = load_run(run_id, base_dir=REPORT_DIR)
        if run is None:
            _json_error(handler, 404, f"Run '{run_id}' not found")
            return

        events = getattr(run, "events", [])
        _json_response(
            handler,
            200,
            {
                "events": [e.to_dict() if hasattr(e, "to_dict") else e for e in events],
                "total": len(events),
            },
        )
    except ImportError:
        _json_error(handler, 501, "Orchestrator storage not available")
    except Exception as e:
        logger.error(f"Fehler beim Laden von Events {run_id}: {e}", exc_info=True)
        _json_error(handler, 500, f"Error loading events: {e}")


def handle_deep_research_get_report(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/report — get generated report."""
    report_path = os.path.join(REPORT_DIR, "runs", run_id, "report.md")
    report_dir = os.path.dirname(report_path)

    # Try the actual deep_report module first
    try:
        from research_orchestrator.storage import load_run

        run = load_run(run_id, base_dir=REPORT_DIR)
        if run is None:
            _json_error(handler, 404, f"Run '{run_id}' not found")
            return

        # Check if report was generated
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report = f.read()
            _json_response(handler, 200, {"report": report, "format": "markdown"})
        else:
            _json_response(
                handler,
                200,
                {
                    "report": None,
                    "format": "markdown",
                    "status": "pending",
                    "message": "Report not yet generated — run may still be in progress",
                },
            )
    except ImportError:
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report = f.read()
            _json_response(handler, 200, {"report": report, "format": "markdown"})
        else:
            _json_error(handler, 404, "Report not yet available")
    except Exception as e:
        logger.error(f"Fehler beim Laden des Reports {run_id}: {e}", exc_info=True)
        _json_error(handler, 500, f"Error loading report: {e}")


def handle_deep_research_get_evaluation(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/evaluation — get evaluation scores."""
    try:
        from research_orchestrator.storage import load_run

        run = load_run(run_id, base_dir=REPORT_DIR)
        if run is None:
            _json_error(handler, 404, f"Run '{run_id}' not found")
            return

        # Check for real evaluation data from deep_report.evaluator
        eval_path = os.path.join(REPORT_DIR, "runs", run_id, "evaluation.json")
        if os.path.exists(eval_path):
            with open(eval_path, "r", encoding="utf-8") as f:
                evaluation = json.load(f)
        else:
            evaluation = getattr(run, "evaluation", None)

        if evaluation is None:
            _json_response(
                handler,
                200,
                {
                    "status": "pending",
                    "message": "Evaluation not yet available — run still in progress",
                },
            )
            return

        _json_response(handler, 200, evaluation)
    except ImportError:
        _json_error(handler, 501, "Orchestrator storage not available")
    except Exception as e:
        logger.error(f"Fehler beim Laden der Evaluation {run_id}: {e}", exc_info=True)
        _json_error(handler, 500, f"Error loading evaluation: {e}")


def handle_deep_research_events_sse(
    handler: BaseHTTPRequestHandler,
    run_id: str,
) -> None:
    """GET /api/deep-research/runs/{id}/events/stream — SSE event stream."""
    try:
        from research_orchestrator.storage import load_run

        run = load_run(run_id, base_dir=REPORT_DIR)
        if run is None:
            _json_error(handler, 404, f"Run '{run_id}' not found")
            return

        events = getattr(run, "events", [])
    except ImportError:
        events = []
    except Exception as e:
        logger.error(f"Fehler beim Laden von Events {run_id}: {e}", exc_info=True)
        events = []

    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.end_headers()

    for event in events:
        evt = event.to_dict() if hasattr(event, "to_dict") else event
        data = f"data: {json.dumps(evt)}\n\n"
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

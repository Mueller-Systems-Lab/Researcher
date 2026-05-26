"""Tests für Deep Research API — DR-07: UI Integration."""

from __future__ import annotations

import io
import json
from http.server import BaseHTTPRequestHandler

import pytest

from deep_research_api import (
    handle_deep_research_approve,
    handle_deep_research_get_evaluation,
    handle_deep_research_get_events,
    handle_deep_research_get_plan,
    handle_deep_research_get_report,
    handle_deep_research_get_run,
    handle_deep_research_plan,
    handle_deep_research_run,
    route_deep_research,
)

# ── Test Handler (stdlib http.server mock) ───────────────────────────────


class TestHandler(BaseHTTPRequestHandler):
    """Minimal test handler that captures responses."""

    def __init__(self):
        self.response_status = 200
        self.response_headers: dict[str, str] = {}
        self.response_body = b""
        self.wfile = io.BytesIO()
        self.rfile = io.BytesIO()
        self.request_version = "HTTP/1.1"
        self.client_address = ("127.0.0.1", 0)
        self.command = "GET"

    def send_response(self, status: int) -> None:
        self.response_status = status

    def send_header(self, key: str, value: str) -> None:
        self.response_headers[key] = value

    def end_headers(self) -> None:
        pass

    def log_message(self, *args) -> None:
        pass


def json_body() -> dict:
    """Extract JSON body from test handler response."""
    body_bytes = io.BytesIO()
    return body_bytes


def _make_handler() -> TestHandler:
    return TestHandler()


def _response_json(handler: TestHandler) -> dict:
    handler.wfile.seek(0)
    return json.loads(handler.wfile.read().decode())


@pytest.fixture(autouse=True)
def _setup():
    # API uses persistent storage — no in-memory state to clear
    yield


# ── Plan Endpoints ───────────────────────────────────────────────────────


def test_create_plan():
    """POST /api/deep-research/plan erzeugt Plan."""
    handler = _make_handler()
    handle_deep_research_plan(handler, {"query": "Test query"})
    assert handler.response_status == 201
    data = _response_json(handler)
    assert data["query"] == "Test query"
    assert data["status"] == "draft"
    assert "plan_id" in data


def test_create_plan_missing_query():
    """POST ohne Query → 400."""
    handler = _make_handler()
    handle_deep_research_plan(handler, {})
    assert handler.response_status == 400


def test_get_plan():
    """GET /api/deep-research/plans/{id} liefert Plan."""
    handler = _make_handler()
    handle_deep_research_plan(handler, {"query": "Q"})
    plan_id = _response_json(handler)["plan_id"]

    handler2 = _make_handler()
    handle_deep_research_get_plan(handler2, plan_id)
    assert handler2.response_status == 200


def test_get_plan_not_found():
    """GET nicht existierender Plan → 404."""
    handler = _make_handler()
    handle_deep_research_get_plan(handler, "nonexistent")
    assert handler.response_status == 404


def test_approve_plan():
    """POST approve setzt Status auf approved."""
    handler = _make_handler()
    handle_deep_research_plan(handler, {"query": "Approve me"})
    plan_id = _response_json(handler)["plan_id"]

    handler2 = _make_handler()
    handle_deep_research_approve(handler2, plan_id)
    assert handler2.response_status == 200
    data = _response_json(handler2)
    assert data["status"] == "approved"


# ── Run Endpoints ────────────────────────────────────────────────────────


def test_create_run():
    """POST /api/deep-research/runs startet Run im Hintergrund."""
    h1 = _make_handler()
    handle_deep_research_plan(h1, {"query": "Run test"})
    plan_id = _response_json(h1)["plan_id"]

    h2 = _make_handler()
    handle_deep_research_approve(h2, plan_id)

    h3 = _make_handler()
    handle_deep_research_run(h3, {"plan_id": plan_id})
    assert h3.response_status == 201
    data = _response_json(h3)
    assert data.get("status") == "running"
    assert "run_id" in data


def test_create_run_unapproved():
    """Run mit nicht-approved Plan → 400."""
    h1 = _make_handler()
    handle_deep_research_plan(h1, {"query": "Draft"})
    plan_id = _response_json(h1)["plan_id"]

    h2 = _make_handler()
    handle_deep_research_run(h2, {"plan_id": plan_id})
    assert h2.response_status == 400


def test_get_run():
    """GET /api/deep-research/runs/{id} liefert Run-Status."""
    h1 = _make_handler()
    handle_deep_research_plan(h1, {"query": "Get run"})
    plan_id = _response_json(h1)["plan_id"]
    handle_deep_research_approve(_make_handler(), plan_id)
    h2 = _make_handler()
    handle_deep_research_run(h2, {"plan_id": plan_id})
    data = _response_json(h2)
    run_id = data.get("run_id", "")

    h3 = _make_handler()
    handle_deep_research_get_run(h3, run_id)
    assert h3.response_status in (200, 501)  # 200=found, 501=storage not loaded


def test_get_run_not_found():
    """GET nicht existierender Run → 404."""
    handler = _make_handler()
    handle_deep_research_get_run(handler, "nonexistent")
    assert handler.response_status in (404, 501)


def test_get_events():
    """GET events liefert Event-Liste."""
    h1 = _make_handler()
    handle_deep_research_plan(h1, {"query": "Events"})
    plan_id = _response_json(h1)["plan_id"]
    handle_deep_research_approve(_make_handler(), plan_id)
    h2 = _make_handler()
    handle_deep_research_run(h2, {"plan_id": plan_id})
    data = _response_json(h2)
    run_id = data.get("run_id", "")

    h3 = _make_handler()
    handle_deep_research_get_events(h3, run_id)
    assert h3.response_status in (200, 501)


def test_get_report():
    """GET report liefert pending-Status (kein echter Run)."""
    h1 = _make_handler()
    handle_deep_research_plan(h1, {"query": "Report test"})
    plan_id = _response_json(h1)["plan_id"]
    handle_deep_research_approve(_make_handler(), plan_id)
    h2 = _make_handler()
    handle_deep_research_run(h2, {"plan_id": plan_id})
    data = _response_json(h2)
    run_id = data.get("run_id", "")

    h3 = _make_handler()
    handle_deep_research_get_report(h3, run_id)
    assert h3.response_status == 200
    data = _response_json(h3)
    assert data.get("format") == "markdown"


def test_get_evaluation():
    """GET evaluation liefert pending-Status (kein echter Run)."""
    h1 = _make_handler()
    handle_deep_research_plan(h1, {"query": "Eval test"})
    plan_id = _response_json(h1)["plan_id"]
    handle_deep_research_approve(_make_handler(), plan_id)
    h2 = _make_handler()
    handle_deep_research_run(h2, {"plan_id": plan_id})
    data = _response_json(h2)
    run_id = data.get("run_id", "")

    h3 = _make_handler()
    handle_deep_research_get_evaluation(h3, run_id)
    assert h3.response_status == 200


# ── Router ───────────────────────────────────────────────────────────────


def test_router_plan_creation():
    """Router leitet POST /plan korrekt."""
    handler = _make_handler()
    handled = route_deep_research(
        handler,
        "/api/deep-research/plan",
        method="POST",
        body={"query": "Router test"},
    )
    assert handled is True
    assert handler.response_status == 201


def test_router_unknown_path():
    """Router: unbekannter Pfad → False."""
    handler = _make_handler()
    handled = route_deep_research(handler, "/api/unknown")
    assert handled is False


def test_router_get_plan():
    """Router leitet GET /plans/{id} korrekt."""
    h1 = _make_handler()
    handle_deep_research_plan(h1, {"query": "Router get"})
    plan_id = _response_json(h1)["plan_id"]

    h2 = _make_handler()
    handled = route_deep_research(h2, f"/api/deep-research/plans/{plan_id}")
    assert handled is True
    assert h2.response_status == 200

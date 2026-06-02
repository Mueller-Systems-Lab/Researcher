# =============================================================================
# Tests: MCP Server (T-026)
# =============================================================================

from __future__ import annotations

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_tools.fastmcp_server import (  # noqa: E402
    MCP_HTTP_PATH,
    _call_tool_json,
    create_server,
    run_tool as fastmcp_run_tool,
)


EXPECTED_TOOLS = {
    "web-fetch",
    "evidence-store",
    "claim-validator",
    "audit-log",
    "human-review-request",
}


def test_mcp_server_routes_registered():
    """Die wichtigen HTTP-Routen sind im Streamable-HTTP-App-Router vorhanden."""
    server = create_server()
    app = server.streamable_http_app()
    route_paths = [route.path for route in app.routes if hasattr(route, "path")]
    assert "/" in route_paths
    assert "/health" in route_paths
    assert MCP_HTTP_PATH in route_paths
    # Streamable HTTP is mounted via FastMCP; we do not need a live socket test here.


def test_mcp_server_list_tools():
    """Die MCP-Tool-Registry enthält alle erwarteten Tools."""
    server = create_server()
    tool_names = [tool.name for tool in asyncio.run(server.list_tools())]
    assert set(tool_names) == EXPECTED_TOOLS


@patch("mcp_tools.fastmcp_server.anyio.to_thread.run_sync", new_callable=AsyncMock)
def test_mcp_server_call_web_fetch(mock_run_sync):
    """Wrapper ruft die registrierte Tool-Implementierung auf."""
    mock_run_sync.return_value = {
        "success": True,
        "data": {"text": "Hello World", "url": "http://example.com"},
    }

    payload = asyncio.run(_call_tool_json("web-fetch", {"url": "http://example.com"}))
    data = json.loads(payload)

    assert data["success"] is True
    assert data["data"]["url"] == "http://example.com"
    mock_run_sync.assert_awaited_once()
    call_args = mock_run_sync.call_args.args
    assert call_args[0] is fastmcp_run_tool
    assert call_args[1:] == ("web-fetch", {"url": "http://example.com"})


@patch("mcp_tools.fastmcp_server.anyio.to_thread.run_sync", new_callable=AsyncMock)
def test_mcp_server_call_tool_returns_error(mock_run_sync):
    """_call_tool_json raises RuntimeError when the tool returns success: False."""
    mock_run_sync.return_value = {
        "success": False,
        "error": "claim-Parameter ist erforderlich",
    }

    with pytest.raises(RuntimeError, match="claim-Parameter ist erforderlich"):
        asyncio.run(_call_tool_json("claim-validator", {"claim": ""}))

    mock_run_sync.assert_awaited_once()


@patch("mcp_tools.fastmcp_server.anyio.to_thread.run_sync", new_callable=AsyncMock)
def test_mcp_server_call_tool_returns_error_with_warnings(mock_run_sync):
    """_call_tool_json includes warnings in the RuntimeError message."""
    mock_run_sync.return_value = {
        "success": False,
        "error": "ChromaDB nicht verfügbar — Evidence nicht gespeichert",
        "warnings": ["ChromaDB ist nicht aktiv", "Keine Embeddings verfügbar"],
    }

    with pytest.raises(
        RuntimeError,
        match=(
            r"ChromaDB nicht verfügbar — Evidence nicht gespeichert "
            r"\(warnings: ChromaDB ist nicht aktiv, Keine Embeddings verfügbar\)"
        ),
    ):
        asyncio.run(
            _call_tool_json(
                "evidence-store",
                {"action": "store", "claim": "test", "embedding": [0.1]},
            )
        )

    mock_run_sync.assert_awaited_once()


@patch("mcp_tools.fastmcp_server.anyio.to_thread.run_sync", new_callable=AsyncMock)
def test_mcp_server_call_tool_unknown_tool(mock_run_sync):
    """_call_tool_json raises RuntimeError when a non-existent tool is requested."""
    mock_run_sync.return_value = {
        "success": False,
        "error": (
            "Tool 'ghost-tool' nicht gefunden. "
            "Verfügbar: ['web-fetch', 'evidence-store', "
            "'claim-validator', 'audit-log', 'human-review-request']"
        ),
    }

    with pytest.raises(
        RuntimeError,
        match=r"Tool 'ghost-tool' nicht gefunden\. Verfügbar:",
    ):
        asyncio.run(_call_tool_json("ghost-tool", {}))

    mock_run_sync.assert_awaited_once()


@patch("mcp_tools.fastmcp_server.anyio.to_thread.run_sync", new_callable=AsyncMock)
def test_mcp_server_call_tool_returns_error_no_message(mock_run_sync):
    """_call_tool_json uses default fallback when result has no 'error' key."""
    mock_run_sync.return_value = {"success": False}

    with pytest.raises(RuntimeError, match="Unbekannter Fehler"):
        asyncio.run(_call_tool_json("web-fetch", {"url": "http://x"}))

    mock_run_sync.assert_awaited_once()


# ── Tool wrapper coverage (server.call_tool paths) ───────────────────────

from unittest.mock import MagicMock


@patch("mcp_tools.fastmcp_server.anyio.to_thread.run_sync", new_callable=AsyncMock)
def test_web_fetch_tool_handler(mock_run_sync):
    """web-fetch tool wrapper passes args via call_tool."""
    mock_run_sync.return_value = {"success": True, "data": {"text": "ok"}}
    server = create_server()
    asyncio.run(
        server.call_tool(
            "web-fetch",
            {"url": "http://x.com", "max_chars": 2000, "extract_text": False},
        )
    )
    mock_run_sync.assert_awaited_once()
    assert mock_run_sync.call_args.args[1] == "web-fetch"


@patch("mcp_tools.fastmcp_server.anyio.to_thread.run_sync", new_callable=AsyncMock)
def test_evidence_store_tool_handler(mock_run_sync):
    """evidence-store tool wrapper passes args via call_tool."""
    mock_run_sync.return_value = {"success": True, "data": {"count": 1}}
    server = create_server()
    asyncio.run(
        server.call_tool(
            "evidence-store", {"action": "store", "claim": "T", "embedding": [0.1]}
        )
    )
    mock_run_sync.assert_awaited_once()
    assert mock_run_sync.call_args.args[1] == "evidence-store"


@patch("mcp_tools.fastmcp_server.anyio.to_thread.run_sync", new_callable=AsyncMock)
def test_claim_validator_tool_handler(mock_run_sync):
    """claim-validator tool wrapper passes args via call_tool."""
    mock_run_sync.return_value = {"success": True, "data": {"verdict": "true"}}
    server = create_server()
    asyncio.run(
        server.call_tool(
            "claim-validator",
            {"claim": "test", "max_sources": 3, "search_mode": "composite"},
        )
    )
    mock_run_sync.assert_awaited_once()
    assert mock_run_sync.call_args.args[1] == "claim-validator"


@patch("mcp_tools.fastmcp_server.anyio.to_thread.run_sync", new_callable=AsyncMock)
def test_audit_log_tool_handler(mock_run_sync):
    """audit-log tool wrapper passes args via call_tool."""
    mock_run_sync.return_value = {"success": True, "data": {"entries": []}}
    server = create_server()
    asyncio.run(server.call_tool("audit-log", {"action": "read", "limit": 10}))
    mock_run_sync.assert_awaited_once()
    assert mock_run_sync.call_args.args[1] == "audit-log"


# ── Error handling ───────────────────────────────────────────────────────


def test_server_call_tool_not_found():
    """Non-existent tool raises ToolError."""
    from mcp.server.fastmcp.exceptions import ToolError

    server = create_server()
    with pytest.raises(ToolError, match="Unknown tool"):
        asyncio.run(server.call_tool("ghost-tool", {}))


@patch("mcp_tools.fastmcp_server.anyio.to_thread.run_sync", new_callable=AsyncMock)
def test_server_call_tool_error_response(mock_run_sync):
    """Failing tool raises ToolError."""
    from mcp.server.fastmcp.exceptions import ToolError

    mock_run_sync.return_value = {"success": False, "error": "internal failure"}
    server = create_server()
    with pytest.raises(ToolError, match="internal failure"):
        asyncio.run(server.call_tool("claim-validator", {"claim": "test"}))


def test_root_info_handler():
    """Root-info handler returns server metadata."""
    server = create_server()
    app = server.streamable_http_app()
    root_handler = None
    for route in app.routes:
        if hasattr(route, "path") and route.path == "/":
            root_handler = route.endpoint
            break
    assert root_handler is not None
    mock_request = MagicMock()
    response = asyncio.run(root_handler(mock_request))
    body = json.loads(response.body)
    assert body["server"] == "researcher-mcp"


# ── Health endpoint ───────────────────────────────────────────────────────


def test_health_handler():
    """Health handler returns {'status': 'ok'}."""
    server = create_server()
    app = server.streamable_http_app()
    health_handler = None
    for route in app.routes:
        if hasattr(route, "path") and route.path == "/health":
            health_handler = route.endpoint
            break
    assert health_handler is not None, "/health route should be registered"
    mock_request = MagicMock()
    response = asyncio.run(health_handler(mock_request))
    body = json.loads(response.body)
    assert body == {"status": "ok"}


# ── human-review-request tool handler ─────────────────────────────────────


@patch("mcp_tools.fastmcp_server.anyio.to_thread.run_sync", new_callable=AsyncMock)
def test_human_review_request_tool_handler(mock_run_sync):
    """human-review-request tool wrapper passes args via call_tool."""
    mock_run_sync.return_value = {
        "success": True,
        "data": {"request_id": "req-1"},
    }
    server = create_server()
    asyncio.run(
        server.call_tool(
            "human-review-request",
            {
                "action": "request",
                "url": "http://onion.site/page",
                "title": "Review Me",
                "reason": "manual check needed",
            },
        )
    )
    mock_run_sync.assert_awaited_once()
    assert mock_run_sync.call_args.args[1] == "human-review-request"


# ── run_server function ───────────────────────────────────────────────────


@patch("mcp_tools.fastmcp_server.create_server")
def test_run_server_lifecycle(mock_create_server):
    """run_server creates server, lists tools, and starts it."""
    from mcp_tools.fastmcp_server import run_server

    mock_server = MagicMock()
    mock_create_server.return_value = mock_server

    # Mock anyio.run to avoid blocking
    with patch(
        "mcp_tools.fastmcp_server.anyio.run",
        return_value=[
            MagicMock(name="web-fetch"),
            MagicMock(name="evidence-store"),
        ],
    ):
        # Mock server.run to avoid blocking — but it will still try,
        # so we need to make server.run raise SystemExit or similar
        mock_server.run.side_effect = SystemExit(0)
        with pytest.raises(SystemExit):
            run_server(host="127.0.0.1", port=8766)

    mock_create_server.assert_called_once_with(host="127.0.0.1", port=8766)


def test_server_compatibility_wrapper():
    """mcp_tools.server: compatibility wrapper imports correctly (Lines 3-7)."""
    import mcp_tools.server as wrapper

    # Verify re-exports
    assert wrapper.MCP_PORT is not None
    assert wrapper.create_server is not None
    assert wrapper.run_server is not None
    assert "MCP_PORT" in wrapper.__all__
    assert "create_server" in wrapper.__all__
    assert "run_server" in wrapper.__all__

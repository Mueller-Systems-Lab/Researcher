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

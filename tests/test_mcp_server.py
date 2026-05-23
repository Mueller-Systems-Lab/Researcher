# =============================================================================
# Tests: MCP Server (T-026)
# =============================================================================
import io
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_handler(method="POST", path="/mcp", body=None):
    """Erzeugt eine MCPHTTPHandler-Instanz mit Dummy-Anfrage."""
    from mcp_tools.server import MCPHTTPHandler

    MCPHTTPHandler.tools_initialized = False

    with patch.object(MCPHTTPHandler, "__init__", lambda self: None):
        handler = MCPHTTPHandler.__new__(MCPHTTPHandler)
        handler.command = method
        handler.path = path
        handler.headers = {"Content-Length": str(len(body or "{}"))}
        handler.rfile = io.BytesIO((body or "{}").encode())
        handler.wfile = io.BytesIO()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.close_connection = True
        return handler


def test_mcp_server_get_info():
    """GET /mcp gibt Server-Info zurück."""

    handler = _make_handler("GET", "/")
    handler.do_GET()

    # Inhalt aus wfile lesen
    written = handler.wfile.getvalue()
    data = json.loads(written)
    assert data["server"] == "researcher-mcp"
    assert "tools" in data


def test_mcp_server_health():
    """GET /health gibt Status zurück."""
    handler = _make_handler("GET", "/health")
    handler.do_GET()
    data = json.loads(handler.wfile.getvalue())
    assert data["status"] == "ok"


def test_mcp_server_list_tools():
    """POST /mcp mit tools/list gibt alle Tools zurück."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    handler = _make_handler(body=body)
    handler.do_POST()

    data = json.loads(handler.wfile.getvalue())
    assert data["id"] == 1
    assert "result" in data
    assert "tools" in data["result"]
    tool_names = [t["name"] for t in data["result"]["tools"]]
    assert "web-fetch" in tool_names
    assert "evidence-store" in tool_names
    assert "claim-validator" in tool_names
    assert "audit-log" in tool_names
    assert "human-review-request" in tool_names


def test_mcp_server_call_tool_no_name():
    """tools/call ohne name gibt Fehler zurück."""
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"arguments": {}},
        }
    )
    handler = _make_handler(body=body)
    handler.do_POST()

    data = json.loads(handler.wfile.getvalue())
    assert data["id"] == 2
    assert data["result"]["isError"] is True


def test_mcp_server_unknown_method():
    """Unbekannte Methode gibt Fehler zurück."""
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "unknown",
            "params": {},
        }
    )
    handler = _make_handler(body=body)
    handler.do_POST()

    data = json.loads(handler.wfile.getvalue())
    assert data["id"] == 3
    assert "error" in data


def test_mcp_server_parse_error():
    """Ungültiges JSON gibt Parse Error zurück."""
    handler = _make_handler(body="not valid json")
    handler.do_POST()

    data = json.loads(handler.wfile.getvalue())
    assert data["error"]["code"] == -32700


def test_mcp_server_wrong_path():
    """POST auf falschen Pfad gibt 404."""
    handler = _make_handler(path="/wrong", body="{}")
    handler.do_POST()

    data = json.loads(handler.wfile.getvalue())
    assert data["error"]["code"] == -32000


@patch("mcp_tools.server.run_tool")
def test_mcp_server_call_web_fetch(mock_run_tool):
    """tools/call ruft web-fetch auf."""
    mock_run_tool.return_value = {
        "success": True,
        "data": {"text": "Hello World", "url": "http://example.com"},
    }

    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "web-fetch", "arguments": {"url": "http://example.com"}},
        }
    )
    handler = _make_handler(body=body)
    handler.do_POST()

    data = json.loads(handler.wfile.getvalue())
    assert data["id"] == 4
    assert "result" in data
    assert "content" in data["result"]

    mock_run_tool.assert_called_with("web-fetch", {"url": "http://example.com"})


def test_mcp_server_404():
    """GET auf unbekannten Pfad gibt 404."""
    handler = _make_handler("GET", "/nonexistent")
    handler.do_GET()

    data = json.loads(handler.wfile.getvalue())
    assert "error" in data

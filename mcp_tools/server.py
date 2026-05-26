# =============================================================================
# MCP Server — HTTP JSON-RPC 2.0 Server für MCP-Tools
# =============================================================================
# Exponiert die 5 MCP-Tools über einen HTTP-Server im MCP-Protokoll-Format.
#
# MCP Methods:
#   tools/list          — Liste aller verfügbaren Tools
#   tools/call          — Ein Tool aufrufen
#   resources/list      — Ressourcen auflisten
#
# Nutzung:
#   python -m mcp_tools.server  →  http://localhost:8765
#   curl http://localhost:8765/mcp \
#     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
# =============================================================================

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from mcp_tools.registry import get_all_manifests, init_tools, run_tool

logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8765"))


class MCPHTTPHandler(BaseHTTPRequestHandler):
    """HTTP-Handler für MCP JSON-RPC 2.0."""

    # Tools einmalig initialisieren
    tools_initialized = False

    def do_GET(self):
        if self.path == "/mcp" or self.path == "/":
            self._respond_json(
                {
                    "server": "researcher-mcp",
                    "version": "0.1.0",
                    "protocol": "2025-06-18",
                    "tools": [m["name"] for m in get_all_manifests()],
                }
            )
        elif self.path == "/health":
            self._respond_json({"status": "ok"})
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not Found"}).encode())

    def do_POST(self):
        if self.path != "/mcp":
            self._respond_json(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32000, "message": "Not Found"},
                },
                status=404,
            )
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self._respond_json(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                },
            )
            return

        method = request.get("method", "")
        req_id = request.get("id", None)
        params = request.get("params", {})

        if method == "tools/list":
            result = self._handle_list_tools()
            self._respond_json(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": result,
                }
            )
        elif method == "tools/call":
            result = self._handle_call_tool(params)
            self._respond_json(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": result,
                }
            )
        elif method == "resources/list":
            self._respond_json(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"resources": []},
                }
            )
        else:
            self._respond_json(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }
            )

    def _handle_list_tools(self) -> dict:
        if not MCPHTTPHandler.tools_initialized:
            init_tools()
            MCPHTTPHandler.tools_initialized = True
        tools = get_all_manifests()
        return {"tools": tools}

    def _handle_call_tool(self, params: dict) -> dict:
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        if not name:
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": "Parameter 'name' ist erforderlich",
                    }
                ],
            }

        if not MCPHTTPHandler.tools_initialized:
            init_tools()
            MCPHTTPHandler.tools_initialized = True

        result = run_tool(name, arguments)

        if result.get("success"):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            result.get("data", {}), indent=2, ensure_ascii=False
                        ),
                    }
                ],
            }
        else:
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": result.get("error", "Unbekannter Fehler"),
                    }
                ],
            }

    def _respond_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, format, *args):
        """Weniger verbose Logging."""
        logger.debug(f"MCP: {format % args}")


def run_server(host: str = "127.0.0.1", port: int = MCP_PORT):
    """Startet den MCP-Server.

    Args:
        host: Bind-Addresse (default: 127.0.0.1).
        port: Port (default: 8765).
    """
    init_tools()
    MCPHTTPHandler.tools_initialized = True

    server = HTTPServer((host, port), MCPHTTPHandler)
    tool_names = [m["name"] for m in get_all_manifests()]
    logger.info("MCP-Server gestartet: http://%s:%s/mcp", host, port)
    logger.info("Health:     http://%s:%s/health", host, port)
    logger.info("Tools:      %s", tool_names)
    logger.info("Drücke Ctrl+C zum Beenden")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("MCP-Server gestoppt")
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_server()

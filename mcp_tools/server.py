"""Compatibility wrapper for the Researcher MCP server."""

from __future__ import annotations

from mcp_tools.fastmcp_server import MCP_PORT, create_server, run_server

__all__ = ["MCP_PORT", "create_server", "run_server"]


if __name__ == "__main__":  # pragma: no cover - module entry point
    run_server()

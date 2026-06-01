"""FastMCP-based MCP server for Researcher.

This module exposes the repo-local tools over MCP SSE at ``/mcp`` so
OpenCode can connect to the server directly.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Literal

import anyio
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from mcp.server.fastmcp import FastMCP

from mcp_tools.registry import get_tool, init_tools, run_tool

logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8766"))
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_HTTP_PATH = "/mcp"
# Backward-compatible alias for older tests and docs.
MCP_SSE_PATH = MCP_HTTP_PATH
MCP_MESSAGE_PATH = "/messages/"
MCP_PROTOCOL = "2025-06-18"
MCP_VERSION = "0.1.0"


def _tool_description(name: str) -> str:
    tool = get_tool(name)
    if tool is None:  # pragma: no cover - defensive guard
        raise RuntimeError(f"Tool '{name}' not registered")
    return tool.description


async def _call_tool_json(name: str, params: dict[str, Any]) -> str:
    """Run a registered tool and return a JSON payload as text."""
    result = await anyio.to_thread.run_sync(run_tool, name, params)
    if result.get("success"):
        return json.dumps(result, indent=2, ensure_ascii=False)

    error = result.get("error", "Unbekannter Fehler")
    warnings = result.get("warnings") or []
    if warnings:
        error = f"{error} (warnings: {', '.join(warnings)})"
    raise RuntimeError(error)


def create_server(host: str = MCP_HOST, port: int = MCP_PORT) -> FastMCP:
    """Create a FastMCP server exposing the repo-local tool registry."""
    init_tools()

    server = FastMCP(
        name="researcher-mcp",
        host=host,
        port=port,
        streamable_http_path=MCP_HTTP_PATH,
    )

    @server.custom_route("/", methods=["GET"], include_in_schema=False)
    async def root_info(request: Request) -> Response:
        tools = await server.list_tools()
        return JSONResponse(
            {
                "server": "researcher-mcp",
                "version": MCP_VERSION,
                "protocol": MCP_PROTOCOL,
                "transport": "streamable-http",
                "tools": [tool.name for tool in tools],
            }
        )

    @server.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health(request: Request) -> Response:
        return JSONResponse({"status": "ok"})

    @server.tool(name="web-fetch", description=_tool_description("web-fetch"))
    async def web_fetch(
        url: str,
        max_chars: int = 5000,
        extract_text: bool = True,
    ) -> str:
        return await _call_tool_json(
            "web-fetch",
            {
                "url": url,
                "max_chars": max_chars,
                "extract_text": extract_text,
            },
        )

    @server.tool(
        name="evidence-store",
        description=_tool_description("evidence-store"),
    )
    async def evidence_store(
        action: Literal["store", "search", "stats"],
        claim: str | None = None,
        source: str | None = None,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        query: str | None = None,
        query_embedding: list[float] | None = None,
        n_results: int = 10,
    ) -> str:
        return await _call_tool_json(
            "evidence-store",
            {
                "action": action,
                "claim": claim,
                "source": source,
                "embedding": embedding,
                "metadata": metadata,
                "query": query,
                "query_embedding": query_embedding,
                "n_results": n_results,
            },
        )

    @server.tool(
        name="claim-validator",
        description=_tool_description("claim-validator"),
    )
    async def claim_validator(
        claim: str,
        max_sources: int = 5,
        search_mode: Literal["composite", "fulltext", "all"] = "all",
    ) -> str:
        return await _call_tool_json(
            "claim-validator",
            {
                "claim": claim,
                "max_sources": max_sources,
                "search_mode": search_mode,
            },
        )

    @server.tool(name="audit-log", description=_tool_description("audit-log"))
    async def audit_log(
        action: Literal["write", "read", "stats"],
        event: str | None = None,
        actor: str = "mcp",
        details: dict[str, Any] | None = None,
        limit: int = 50,
        event_filter: str | None = None,
        since: str | None = None,
    ) -> str:
        return await _call_tool_json(
            "audit-log",
            {
                "action": action,
                "event": event,
                "actor": actor,
                "details": details,
                "limit": limit,
                "event_filter": event_filter,
                "since": since,
            },
        )

    @server.tool(
        name="human-review-request",
        description=_tool_description("human-review-request"),
    )
    async def human_review_request(
        action: Literal["request", "list_pending", "stats"],
        url: str | None = None,
        title: str | None = None,
        content: str | None = None,
        reason: str | None = None,
        topic: str = "unknown",
        risk_level: Literal["low", "medium", "high", "critical"] = "medium",
    ) -> str:
        return await _call_tool_json(
            "human-review-request",
            {
                "action": action,
                "url": url,
                "title": title,
                "content": content,
                "reason": reason,
                "topic": topic,
                "risk_level": risk_level,
            },
        )

    return server


def run_server(host: str = MCP_HOST, port: int = MCP_PORT) -> None:
    """Start the MCP server using Streamable HTTP transport."""
    server = create_server(host=host, port=port)
    tool_names = [tool.name for tool in anyio.run(server.list_tools)]

    logger.info("MCP-Server gestartet: http://%s:%s%s", host, port, MCP_HTTP_PATH)
    logger.info("Health:     http://%s:%s/health", host, port)
    logger.info("Tools:      %s", tool_names)
    logger.info("Drücke Ctrl+C zum Beenden")
    try:
        server.run("streamable-http")
    except KeyboardInterrupt:  # pragma: no cover - manual shutdown path
        logger.info("MCP-Server gestoppt")


__all__ = [
    "MCP_HOST",
    "MCP_MESSAGE_PATH",
    "MCP_HTTP_PATH",
    "MCP_PORT",
    "MCP_PROTOCOL",
    "MCP_SSE_PATH",
    "MCP_VERSION",
    "create_server",
    "run_server",
]

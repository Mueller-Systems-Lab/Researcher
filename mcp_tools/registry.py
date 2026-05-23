# =============================================================================
# MCP Tools — Registry
# =============================================================================
# Zentraler Zugang zu allen MCP-Tools. Erzeugt MCP-Manifest.
#
# Nutzung:
#   from mcp_tools.registry import get_tool, get_all_manifests
#   tool = get_tool("web-fetch")
#   result = tool.run({"url": "http://example.com"})
# =============================================================================

import logging

from mcp_tools.audit_log import AuditLog
from mcp_tools.base import MCPToolBase
from mcp_tools.claim_validator import ClaimValidator
from mcp_tools.evidence_store import EvidenceStore
from mcp_tools.human_review import HumanReviewTool
from mcp_tools.web_fetch import WebFetchTool

logger = logging.getLogger(__name__)

# Tool-Registry
_TOOLS: dict[str, MCPToolBase] = {}


def _register(tool: MCPToolBase):
    """Registriert ein Tool."""
    _TOOLS[tool.name] = tool


def init_tools():
    """Initialisiert und registriert alle MCP-Tools."""
    _register(WebFetchTool())
    _register(EvidenceStore())
    _register(ClaimValidator())
    _register(AuditLog())
    _register(HumanReviewTool())
    logger.info(f"{len(_TOOLS)} MCP-Tools registriert")


def get_tool(name: str) -> MCPToolBase | None:
    """Holt ein Tool anhand seines Namens."""
    return _TOOLS.get(name)


def list_tools() -> list[str]:
    """Listet alle registrierten Tool-Namen."""
    return list(_TOOLS.keys())


def get_all_manifests() -> list[dict]:
    """Erzeugt das vollständige MCP-Manifest aller Tools."""
    return [tool.get_manifest() for tool in _TOOLS.values()]


def run_tool(name: str, params: dict) -> dict:
    """Führt ein Tool anhand seines Namens aus.

    Args:
        name: Tool-Name (z.B. "web-fetch").
        params: Parameter für das Tool.

    Returns:
        Ergebnis-Dict.
    """
    tool = get_tool(name)
    if tool is None:
        return {
            "success": False,
            "error": f"Tool '{name}' nicht gefunden. Verfügbar: {list_tools()}",
        }
    try:
        return tool.run(params)
    except Exception as e:
        logger.exception(f"Fehler bei Tool {name}: {e}")
        return {
            "success": False,
            "error": f"Interner Fehler: {e}",
        }

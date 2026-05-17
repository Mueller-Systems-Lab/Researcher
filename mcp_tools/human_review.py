# =============================================================================
# MCP Tool: human-review-request
# =============================================================================
# Signalisiert Human Review bei riskanten/grenzwertigen Ergebnissen.
# Nutzt die vorhandene ReviewQueue.
# AUS SICHERHEITSGRÜNDEN: approve/reject NUR über CLI/UI, nicht via MCP.
# Siehe T-020.
#
# Nutzung:
#   tool = HumanReviewTool()
#   tool.run({"action": "request", "url": "...", "reason": "..."})
#   tool.run({"action": "list_pending"})
# =============================================================================

import hashlib
import logging
from typing import Optional

from mcp_tools.base import MCPToolBase, MCPToolResult
from onion_discovery.human_review import ReviewQueue

logger = logging.getLogger(__name__)


class HumanReviewTool(MCPToolBase):
    """MCP-Tool für Human-Review-Requests."""

    @property
    def name(self) -> str:
        return "human-review-request"

    @property
    def description(self) -> str:
        return (
            "Signalisiert Human Review bei riskanten/grenzwertigen "
            "Ergebnissen. Approve/Reject NUR über CLI (--approve/--reject)."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "request",
                        "list_pending",
                        "stats",
                    ],
                    "description": "Aktion: request, list_pending, stats",
                },
                "url": {
                    "type": "string",
                    "description": "URL des zu reviewenden Inhalts (für action=request)",
                },
                "title": {
                    "type": "string",
                    "description": "Titel (für action=request)",
                },
                "content": {
                    "type": "string",
                    "description": "Inhalt (für action=request)",
                },
                "reason": {
                    "type": "string",
                    "description": "Grund für Review (für action=request)",
                },
                "topic": {
                    "type": "string",
                    "description": "Thema (für action=request, default: unknown)",
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Risikostufe (für action=request)",
                },
            },
            "required": ["action"],
        }

    def __init__(self, review_queue: Optional[ReviewQueue] = None):
        self.review_queue = review_queue or ReviewQueue()

    def run(self, params: dict) -> dict:
        action = params.get("action", "")

        if action in ("approve", "reject"):
            return MCPToolResult(
                False,
                error=(
                    f"action={action} ist nicht über MCP verfügbar. "
                    "Approve/Reject nur über CLI: "
                    "python -m onion_discovery --approve <id> "
                    "oder --reject <id> <reason>"
                ),
            ).to_dict()

        if action == "request":
            return self._request_review(params)
        elif action == "list_pending":
            return self._list_pending()
        elif action == "stats":
            return self._get_stats()
        else:
            return MCPToolResult(
                False,
                error=f"Unbekannte action: {action}. "
                f"Erlaubt: request, list_pending, stats",
            ).to_dict()

    def _request_review(self, params: dict) -> dict:
        url = params.get("url", "")
        if not url:
            return MCPToolResult(
                False, error="url ist erforderlich für action=request"
            ).to_dict()

        item_id = hashlib.sha256(url.encode()).hexdigest()[:16]
        content = params.get("content", "")
        risk_level = params.get("risk_level", "medium")

        success = self.review_queue.add(
            item_id=item_id,
            url=url,
            title=params.get("title", ""),
            content=content,
            topic=params.get("topic", "unknown"),
            risk_level=risk_level,
            confidence=0.5,
            source_seed=url,
        )

        if success:
            return MCPToolResult(
                True,
                data={
                    "item_id": item_id,
                    "url": url,
                    "risk_level": risk_level,
                    "reason": params.get("reason", ""),
                    "message": "Review-Request erstellt — "
                    "menschliche Freigabe erforderlich",
                },
            ).to_dict()
        else:
            return MCPToolResult(
                False,
                error=f"Review-Item existiert bereits: {item_id}",
            ).to_dict()

    def _list_pending(self) -> dict:
        item = self.review_queue.get_next_pending()
        if item is None:
            return MCPToolResult(
                True,
                data={
                    "pending": 0,
                    "next_item": None,
                    "message": "Keine pending Review-Items",
                },
            ).to_dict()

        return MCPToolResult(
            True,
            data={
                "pending": self.review_queue.pending_count,
                "next_item": {
                    "id": item.id,
                    "url": item.url,
                    "title": item.title,
                    "topic": item.topic,
                    "risk_level": item.risk_level,
                    "discovered_at": item.discovered_at,
                },
            },
        ).to_dict()

    def _get_stats(self) -> dict:
        return MCPToolResult(
            True,
            data={
                "stats": self.review_queue.get_stats(),
            },
        ).to_dict()

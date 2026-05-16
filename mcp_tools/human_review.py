# =============================================================================
# MCP Tool: human-review-request
# =============================================================================
# Signalisiert Human Review bei riskanten/grenzwertigen Ergebnissen.
# Nutzt die vorhandene ReviewQueue.
# Erlaubt approve/reject via MCP.
#
# Nutzung:
#   tool = HumanReviewTool()
#   tool.run({"action": "request", "url": "...", "reason": "..."})
#   tool.run({"action": "approve", "item_id": "..."})
#   tool.run({"action": "reject", "item_id": "...", "reason": "..."})
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
            "Ergebnissen. Erlaubt approve/reject von Review-Items."
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
                        "approve",
                        "reject",
                        "list_pending",
                        "stats",
                    ],
                    "description": "Aktion",
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
                    "description": "Grund für Review (für action=request/reject)",
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
                "item_id": {
                    "type": "string",
                    "description": "ID des Review-Items (für action=approve/reject)",
                },
                "reviewer": {
                    "type": "string",
                    "description": "Name des Reviewers (für action=approve/reject)",
                    "default": "mcp",
                },
            },
            "required": ["action"],
        }

    def __init__(self, review_queue: Optional[ReviewQueue] = None):
        self.review_queue = review_queue or ReviewQueue()

    def run(self, params: dict) -> dict:
        action = params.get("action", "")

        if action == "request":
            return self._request_review(params)
        elif action == "approve":
            return self._approve(params)
        elif action == "reject":
            return self._reject(params)
        elif action == "list_pending":
            return self._list_pending()
        elif action == "stats":
            return self._get_stats()
        else:
            return MCPToolResult(
                False,
                error=f"Unbekannte action: {action}. "
                f"Erlaubt: request, approve, reject, "
                f"list_pending, stats",
            ).to_dict()

    def _request_review(self, params: dict) -> dict:
        url = params.get("url", "")
        if not url:
            return MCPToolResult(
                False, error="url ist erforderlich für action=request"
            ).to_dict()

        item_id = hashlib.md5(url.encode()).hexdigest()[:16]
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

    def _approve(self, params: dict) -> dict:
        item_id = params.get("item_id", "")
        if not item_id:
            return MCPToolResult(
                False, error="item_id ist erforderlich für action=approve"
            ).to_dict()

        reviewer = params.get("reviewer", "mcp")
        notes = params.get("reason", "")
        success = self.review_queue.approve(item_id, reviewer=reviewer, notes=notes)

        if success:
            return MCPToolResult(
                True,
                data={
                    "item_id": item_id,
                    "approved_by": reviewer,
                    "message": "Review-Item genehmigt — zur Indexierung freigegeben",
                },
            ).to_dict()
        else:
            return MCPToolResult(
                False,
                error=f"Review-Item nicht gefunden: {item_id}",
            ).to_dict()

    def _reject(self, params: dict) -> dict:
        item_id = params.get("item_id", "")
        if not item_id:
            return MCPToolResult(
                False, error="item_id ist erforderlich für action=reject"
            ).to_dict()

        reviewer = params.get("reviewer", "mcp")
        reason = params.get("reason", "")
        success = self.review_queue.reject(item_id, reviewer=reviewer, reason=reason)

        if success:
            return MCPToolResult(
                True,
                data={
                    "item_id": item_id,
                    "rejected_by": reviewer,
                    "reason": reason,
                    "message": "Review-Item abgelehnt — nicht indexiert",
                },
            ).to_dict()
        else:
            return MCPToolResult(
                False,
                error=f"Review-Item nicht gefunden: {item_id}",
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

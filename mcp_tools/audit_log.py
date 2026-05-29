# =============================================================================
# MCP Tool: audit-log
# =============================================================================
# Append-only Audit-Trail für das Research-System.
# Schreibt und liest Audit-Einträge. Einträge sind unveränderlich.
# Logs werden zeilenweise in einer JSONL-Datei gespeichert.
#
# Nutzung:
#   tool = AuditLog()
#   tool.run({"action": "write", "event": "research_started", ...})
#   tool.run({"action": "read", "limit": 10})
# =============================================================================

import json
import logging
import os
import threading
from datetime import datetime

from mcp_tools.base import MCPToolBase, MCPToolResult

logger = logging.getLogger(__name__)


class AuditLog(MCPToolBase):
    """Append-only Audit-Trail für MCP-gesteuerte Aktionen."""

    @property
    def name(self) -> str:
        return "audit-log"

    @property
    def description(self) -> str:
        return (
            "Append-only Audit-Trail. "
            "Schreibt und liest unveränderliche Audit-Einträge. "
            "Einträge können nicht gelöscht oder geändert werden."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["write", "read", "stats"],
                    "description": (
                        "Aktion: write=schreiben, read=lesen, stats=Statistiken"
                    ),
                },
                "event": {
                    "type": "string",
                    "description": "Event-Typ (für action=write)",
                },
                "actor": {
                    "type": "string",
                    "description": "Ausführender Akteur (für action=write)",
                    "default": "mcp",
                },
                "details": {
                    "type": "object",
                    "description": "Detailinformationen zum Event (für action=write)",
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Maximale Anzahl Einträge (für action=read, default: 50)"
                    ),
                    "default": 50,
                },
                "event_filter": {
                    "type": "string",
                    "description": "Optional: Filter auf Event-Typ (für action=read)",
                },
                "since": {
                    "type": "string",
                    "description": (
                        "Optional: ISO-Datum, nur Einträge ab diesem Zeitpunkt"
                    ),
                },
            },
            "required": ["action"],
        }

    def __init__(self, log_file: str | None = None):
        self.log_file = log_file or os.getenv("AUDIT_LOG_FILE", "./audit_trail.jsonl")
        self._lock = threading.Lock()

    def run(self, params: dict) -> dict:
        action = params.get("action", "")

        if action == "write":
            return self._write_entry(params)
        elif action == "read":
            return self._read_entries(params)
        elif action == "stats":
            return self._get_stats()
        else:
            return MCPToolResult(
                False,
                error=f"Unbekannte action: {action}. Erlaubt: write, read, stats",
            ).to_dict()

    def _write_entry(self, params: dict) -> dict:
        event = params.get("event", "")
        if not event:
            return MCPToolResult(
                False, error="event ist erforderlich für action=write"
            ).to_dict()

        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "actor": params.get("actor", "mcp"),
            "details": params.get("details", {}),
        }

        try:
            log_dir = os.path.dirname(self.log_file or ".") or "."
            os.makedirs(log_dir, exist_ok=True)
            with self._lock:
                with open(self.log_file or "audit_log.jsonl", "a") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return MCPToolResult(
                True,
                data={
                    "written": True,
                    "event": event,
                    "timestamp": entry["timestamp"],
                },
            ).to_dict()
        except OSError as e:
            logger.error(f"Audit-Log-I/O-Fehler: {e}", exc_info=True)
            return MCPToolResult(
                False, error=f"Audit-Log kann nicht geschrieben werden: {e}"
            ).to_dict()
        except (ValueError, TypeError) as e:
            logger.error(f"Audit-Log-Datenfehler: {e}", exc_info=True)
            return MCPToolResult(
                False, error=f"Audit-Log-Daten ungültig: {e}"
            ).to_dict()

    def _read_entries(self, params: dict) -> dict:
        limit = params.get("limit", 50)
        event_filter = params.get("event_filter", "")
        since = params.get("since", "")

        log_file = self.log_file or "audit_log.jsonl"
        if not os.path.exists(log_file):
            return MCPToolResult(
                True,
                data={
                    "entries": [],
                    "count": 0,
                    "file": self.log_file,
                },
            ).to_dict()

        try:
            entries = []
            with open(log_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if event_filter and entry.get("event") != event_filter:
                            continue
                        if since and entry.get("timestamp", "") < since:
                            continue
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue

            # Neueste zuerst
            entries.reverse()
            entries = entries[:limit]

            return MCPToolResult(
                True,
                data={
                    "entries": entries,
                    "count": len(entries),
                    "file": self.log_file,
                },
            ).to_dict()
        except Exception as e:
            logger.exception(f"Fehler beim Audit-Log-Lesen: {e}")
            return MCPToolResult(False, error=f"Kann nicht lesen: {e}").to_dict()

    def _get_stats(self) -> dict:
        count = 0
        events: dict[str, int] = {}

        log_file = self.log_file or "audit_log.jsonl"
        if os.path.exists(log_file):
            try:
                with open(log_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            count += 1
                            ev = entry.get("event", "unknown")
                            events[ev] = events.get(ev, 0) + 1
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.exception(f"Fehler beim Audit-Log-Stats: {e}")

        return MCPToolResult(
            True,
            data={
                "total_entries": count,
                "file": self.log_file,
                "events_by_type": events,
            },
        ).to_dict()

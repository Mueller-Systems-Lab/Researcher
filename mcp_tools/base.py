# =============================================================================
# MCP Tools — Basisklasse
# =============================================================================
# Alle MCP-Tools erben von MCPToolBase und implementieren:
#   run(params: dict) -> dict     — Tool-Ausführung
#   name                          — Tool-Name
#   description                   — Kurzbeschreibung
#   parameters                    — JSON-Schema der Parameter
# =============================================================================

from abc import ABC, abstractmethod
from typing import Any


class MCPToolResult:
    """Einheitliches Ergebnisformat für MCP-Tools."""

    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: str = "",
        warnings: list[str] | None = None,
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.warnings = warnings or []

    def to_dict(self) -> dict:
        result = {
            "success": self.success,
            "data": self.data,
        }
        if self.error:
            result["error"] = self.error
        if self.warnings:
            result["warnings"] = self.warnings
        return result


class MCPToolBase(ABC):
    """Abstrakte Basisklasse für MCP-Tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Eindeutiger Tool-Name (lowercase, mit Bindestrich)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Kurzbeschreibung des Tools."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """JSON-Schema der erwarteten Parameter."""
        ...

    @abstractmethod
    def run(self, params: dict) -> dict:
        """Führt das Tool aus und gibt Ergebnis-Dict zurück.

        Args:
            params: Tool-spezifische Parameter.

        Returns:
            Dict mit {success, data, error?, warnings?}.
        """
        ...

    def get_manifest(self) -> dict:
        """MCP-Manifest-Eintrag für dieses Tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

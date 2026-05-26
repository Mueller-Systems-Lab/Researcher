# =============================================================================
# MCP Tool: claim-validator (Orchestrator)
# =============================================================================
# Validiert einen Claim gegen verfügbare Evidenz.
# Orchestriert den Flow: retrieve → score → (index).
# Die Business-Logik ist in drei spezialisierte Module ausgelagert:
#   - claim_retriever.py  → Quellen finden & fetchen
#   - claim_scorer.py     → Scoring-Logik, Confidence-Werte
#   - claim_index_writer.py → Ergebnisse in Index schreiben
#
# Nutzung:
#   tool = ClaimValidator()
#   result = tool.run({"claim": "Behauptung", "max_sources": 5})
# =============================================================================

import logging

from mcp_tools.base import MCPToolBase, MCPToolResult
from mcp_tools.claim_retriever import retrieve_composite, retrieve_fulltext
from mcp_tools.claim_scorer import assess, calculate_confidence

logger = logging.getLogger(__name__)


class ClaimValidator(MCPToolBase):
    """MCP-Tool zur Validierung von Claims gegen gespeicherte Evidenz.

    Orchestriert den Validierungs-Flow:
    1. Retrieval (claim_retriever)
    2. Scoring (claim_scorer)
    3. Optional: Index-Schreiben (claim_index_writer)
    """

    @property
    def name(self) -> str:
        return "claim-validator"

    @property
    def description(self) -> str:
        return (
            "Validiert einen Claim gegen verfügbare Evidenz. "
            "Nutzt CompositeRetriever und/oder Volltextsuche im Index. "
            "Gibt Confidence-Score (0-1) und Quellen zurück."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "Der zu validierende Claim",
                },
                "max_sources": {
                    "type": "integer",
                    "description": "Maximale Anzahl Quellen (default: 5)",
                    "default": 5,
                },
                "search_mode": {
                    "type": "string",
                    "enum": ["composite", "fulltext", "all"],
                    "description": "Suchmodus (default: all)",
                    "default": "all",
                },
            },
            "required": ["claim"],
        }

    def run(self, params: dict) -> dict:
        claim = params.get("claim", "")
        max_sources = params.get("max_sources", 5)
        search_mode = params.get("search_mode", "all")
        if search_mode not in ("composite", "fulltext", "all"):
            search_mode = "all"

        if not claim:
            return MCPToolResult(
                False, error="claim-Parameter ist erforderlich"
            ).to_dict()

        warnings: list[str] = []
        results: list[dict] = []
        retriever_errors: dict = {}

        # 1. Retrieval (mit transparenter Fehlerweitergabe)
        if search_mode in ("composite", "all"):
            comp = retrieve_composite(claim, max_sources)
            results.extend(comp.get("results", []))
            if comp.get("errors"):
                retriever_errors["composite"] = comp["errors"]
                for bk, err in comp["errors"].items():
                    if err:
                        warnings.append(f"CompositeRetriever ({bk}): {err}")

        if search_mode in ("fulltext", "all"):
            ft = retrieve_fulltext(claim, max_sources)
            results.extend(ft.get("results", []))
            if ft.get("errors"):
                retriever_errors["fulltext"] = ft["errors"]
                for bk, err in ft["errors"].items():
                    if err:
                        warnings.append(f"Volltextsuche ({bk}): {err}")

        # 2. Scoring
        confidence = calculate_confidence(results, claim, max_sources)

        return MCPToolResult(
            True,
            data={
                "claim": claim,
                "confidence": round(confidence, 2),
                "sources": results[:max_sources],
                "source_count": len(results),
                "assessment": assess(confidence),
                "retriever_errors": retriever_errors or None,
            },
            warnings=warnings if warnings else None,
        ).to_dict()

    @staticmethod
    def _assess(confidence: float) -> str:
        """Legacy-Methode für Abwärtskompatibilität mit Tests."""
        return assess(confidence)

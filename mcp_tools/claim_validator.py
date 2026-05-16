# =============================================================================
# MCP Tool: claim-validator
# =============================================================================
# Validiert einen Claim gegen verfügbare Evidenz.
# Nutzt CompositeRetriever für Quellensuche.
# Gibt Confidence-Score und Quellen zurück.
#
# Nutzung:
#   tool = ClaimValidator()
#   result = tool.run({"claim": "Behauptung", "max_sources": 5})
# =============================================================================

import logging
import re
from typing import Optional

from mcp_tools.base import MCPToolBase, MCPToolResult

logger = logging.getLogger(__name__)


class ClaimValidator(MCPToolBase):
    """MCP-Tool zur Validierung von Claims gegen gespeicherte Evidenz."""

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

        if not claim:
            return MCPToolResult(
                False, error="claim-Parameter ist erforderlich"
            ).to_dict()

        results = []
        warnings = []

        # 1. CompositeRetriever (Web + Darknet)
        if search_mode in ("composite", "all"):
            try:
                from search.composite import CompositeRetriever

                retriever = CompositeRetriever(claim, searx_url="http://localhost:8080")
                retriever.darknet_enabled = False  # Nur Web für Validierung
                search_results = retriever.search(max_results=max_sources)
                for r in search_results:
                    results.append(
                        {
                            "url": r.get("url", ""),
                            "title": r.get("title", ""),
                            "snippet": r.get("body", "")[:300],
                            "source": r.get("source", "web"),
                            "score": r.get("score", 0),
                            "match_type": "keyword",
                        }
                    )
            except Exception as e:
                warnings.append(f"CompositeRetriever nicht verfügbar: {e}")

        # 2. Whoosh-Volltextsuche
        if search_mode in ("fulltext", "all"):
            try:
                from darknet_search.index import WhooshIndex

                idx = WhooshIndex()
                index_results = idx.search(claim, limit=max_sources)
                for r in index_results:
                    results.append(
                        {
                            "url": r.get("url", ""),
                            "title": r.get("title", ""),
                            "snippet": r.get("content", "")[:300],
                            "source": r.get("source", "index"),
                            "score": r.get("score", 0),
                            "match_type": "fulltext",
                        }
                    )
            except Exception as e:
                warnings.append(f"Whoosh-Index nicht verfügbar: {e}")

        # 3. Confidence berechnen
        if not results:
            confidence = 0.0
        else:
            # Basierend auf Anzahl Quellen und Scores
            source_score = min(1.0, len(results) / max_sources) * 0.5
            relevance = (
                sum(float(r.get("score", 0) or 0) for r in results) / len(results) * 0.3
                if results
                else 0
            )
            # Claim-Keywords in Snippets
            keywords = re.findall(r"\w+", claim.lower())
            keyword_hits = sum(
                1
                for r in results
                for kw in keywords
                if len(kw) > 3 and kw in r.get("snippet", "").lower()
            )
            keyword_score = min(1.0, keyword_hits / max(1, len(keywords))) * 0.2
            confidence = source_score + relevance + keyword_score
            confidence = max(0.0, min(1.0, confidence))

        return MCPToolResult(
            True,
            data={
                "claim": claim,
                "confidence": round(confidence, 2),
                "sources": results[:max_sources],
                "source_count": len(results),
                "assessment": self._assess(confidence),
            },
            warnings=warnings if warnings else None,
        ).to_dict()

    @staticmethod
    def _assess(confidence: float) -> str:
        if confidence >= 0.7:
            return "gut belegt"
        elif confidence >= 0.4:
            return "teilweise belegt"
        elif confidence >= 0.1:
            return "schwach belegt"
        return "nicht belegt"

# =============================================================================
# MCP Tool: evidence-store
# =============================================================================
# Speichert und durchsucht Evidence/Claims in ChromaDB.
# Versioniert mit Quellenangabe. Nutzt EmbeddingService für Vektorerzeugung.
#
# Nutzung:
#   tool = EvidenceStore()
#   tool.run({"action": "store", "claim": "...", "source": "...", "embedding": [...]})
#   tool.run({"action": "search", "query": "...", "n_results": 5})
# =============================================================================

import logging
from typing import Optional

from mcp_tools.base import MCPToolBase, MCPToolResult

logger = logging.getLogger(__name__)


class EvidenceStore(MCPToolBase):
    """MCP-Tool zum Speichern und Suchen von Evidence in ChromaDB."""

    @property
    def name(self) -> str:
        return "evidence-store"

    @property
    def description(self) -> str:
        return (
            "Speichert und durchsucht Evidence/Claims in ChromaDB. "
            "Erfordert einen Embedding-Vektor zum Speichern."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["store", "search", "stats"],
                    "description": "Aktion: store=speichern, search=suchen, stats=Statistiken",
                },
                "claim": {
                    "type": "string",
                    "description": "Der zu speichernde Claim/Text (für action=store)",
                },
                "source": {
                    "type": "string",
                    "description": "Quellen-URL (für action=store)",
                },
                "embedding": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Embedding-Vektor (für action=store)",
                },
                "metadata": {
                    "type": "object",
                    "description": "Zusätzliche Metadaten (für action=store)",
                },
                "query": {
                    "type": "string",
                    "description": "Suchbegriff (für action=search)",
                },
                "query_embedding": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Optional: Embedding für die Suche (für action=search)",
                },
                "n_results": {
                    "type": "integer",
                    "description": "Maximale Anzahl Suchergebnisse (default: 10)",
                    "default": 10,
                },
            },
            "required": ["action"],
        }

    def __init__(self, vector_store=None):
        self._store = vector_store

    def _get_store(self):
        if self._store is None:
            from vectordb.store import VectorStore

            self._store = VectorStore()
        return self._store

    def run(self, params: dict) -> dict:
        action = params.get("action", "")

        if action == "store":
            return self._store_evidence(params)
        elif action == "search":
            return self._search_evidence(params)
        elif action == "stats":
            return self._get_stats()
        else:
            return MCPToolResult(
                False,
                error=f"Unbekannte action: {action}. Erlaubt: store, search, stats",
            ).to_dict()

    def _store_evidence(self, params: dict) -> dict:
        claim = params.get("claim", "")
        if not claim:
            return MCPToolResult(
                False, error="claim ist erforderlich für action=store"
            ).to_dict()

        embedding = params.get("embedding")
        if not embedding:
            return MCPToolResult(
                False,
                error="embedding ist erforderlich für action=store. "
                "Nutze den EmbeddingService zur Erzeugung.",
            ).to_dict()

        metadata = params.get("metadata", {})
        metadata["source"] = params.get("source", "unknown")

        store = self._get_store()
        success = store.add_one(
            document=claim,
            embedding=embedding,
            metadata=metadata,
        )

        if success:
            return MCPToolResult(
                True,
                data={
                    "message": "Evidence gespeichert",
                    "claim": claim[:100],
                    "source": metadata["source"],
                },
            ).to_dict()
        else:
            return MCPToolResult(
                False,
                error="ChromaDB nicht verfügbar — Evidence nicht gespeichert",
                warnings=["ChromaDB ist nicht aktiv"],
            ).to_dict()

    def _search_evidence(self, params: dict) -> dict:
        query_embedding = params.get("query_embedding")
        if not query_embedding:
            return MCPToolResult(
                False,
                error="query_embedding ist erforderlich für action=search. "
                "Nutze den EmbeddingService zur Erzeugung.",
            ).to_dict()

        n_results = params.get("n_results", 10)
        store = self._get_store()
        results = store.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        return MCPToolResult(
            True,
            data={
                "results": results,
                "count": len(results),
            },
        ).to_dict()

    def _get_stats(self) -> dict:
        store = self._get_store()
        return MCPToolResult(
            True,
            data={
                "total_evidence": store.count,
                "chromadb_available": store._get_collection() is not None,
            },
        ).to_dict()

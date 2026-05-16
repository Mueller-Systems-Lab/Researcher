# =============================================================================
# Vector DB — Embedding Service (Ollama)
# =============================================================================
# Erzeugt Embeddings über die Ollama REST API.
# nomic-embed-text läuft auf CPU — kein GPU-VRAM-Verbrauch.
#
# Nutzung:
#   from vectordb.embedding import EmbeddingService
#   svc = EmbeddingService()
#   vector = svc.embed("Text, der embedded werden soll")
# =============================================================================

import json
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding-Service über Ollama REST API.

    Verwendet nomic-embed-text (CPU) für Vektorerzeugung.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.model = model or os.getenv(
            "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest"
        )
        self._api_url = f"{self.base_url}/api/embeddings"

    def embed(self, text: str) -> list[float]:
        """Erzeugt einen Embedding-Vektor für den gegebenen Text.

        Args:
            text: Der zu embeddende Text.

        Returns:
            Liste von floats (Embedding-Vektor).

        Raises:
            ConnectionError: Wenn Ollama nicht erreichbar ist.
            ValueError: Wenn die Antwort ungültig ist.
        """
        if not text or not text.strip():
            return []

        try:
            response = requests.post(
                self._api_url,
                json={"model": self.model, "prompt": text},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding", [])
            logger.debug(
                f"Embedding für {len(text)} Zeichen: {len(embedding)} Dimensionen"
            )
            return embedding

        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Ollama nicht erreichbar unter {self.base_url}. Starte: ollama serve"
            )
        except (requests.RequestException, json.JSONDecodeError) as e:
            raise ValueError(f"Embedding-Fehler: {e}")

    def embed_batch(self, texts: list[str], batch_size: int = 8) -> list[list[float]]:
        """Erzeugt Embeddings für mehrere Texte (batched).

        Args:
            texts: Liste von Texten.
            batch_size: Batch-Größe (klein halten für CPU).

        Returns:
            Liste von Embedding-Vektoren.
        """
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                try:
                    vec = self.embed(text)
                    results.append(vec)
                except Exception as e:
                    logger.warning(f"Embedding-Fehler bei Batch {i}: {e}")
                    results.append([])
        return results

    @property
    def is_available(self) -> bool:
        """Prüft, ob Ollama erreichbar ist."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    @property
    def dimension(self) -> int:
        """Gibt die Dimension des Embedding-Modells zurück."""
        test_vec = self.embed("test")
        return len(test_vec)

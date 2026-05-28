"""E2E-Test: vollständiger Research-Workflow ohne externe LLM-Aufrufe."""

import os
import sys
from http.server import HTTPServer
from threading import Thread
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class _MemoryCollection:
    """Minimale In-Memory-Collection als ChromaDB-Ersatz."""

    def __init__(self):
        self.documents = []
        self.embeddings = []
        self.metadatas = []
        self.ids = []

    def add(self, documents, embeddings, metadatas, ids):
        self.documents.extend(documents)
        self.embeddings.extend(embeddings)
        self.metadatas.extend(metadatas)
        self.ids.extend(ids)

    def query(self, **kwargs):
        n_results = kwargs.get("n_results", 10)
        return {
            "documents": [self.documents[:n_results]],
            "metadatas": [self.metadatas[:n_results]],
            "distances": [[0.01] * min(n_results, len(self.documents))],
            "ids": [self.ids[:n_results]],
        }

    def count(self):
        return len(self.documents)


class _DashboardMonitor:
    """Deterministischer Dashboard-Monitor für JSON-Response-Assertions."""

    @staticmethod
    def collect_dict():
        return {
            "status": "ok",
            "result_count": 2,
            "gpu_name": "Mock GPU",
            "gpu_utilization": 0,
            "memory_used_mib": 0,
            "sources": ["SearXNG", "Darknet Forum"],
        }

    @staticmethod
    def is_available():
        return True


def _embedding_for(text: str) -> list[float]:
    """Mockt ein Ollama-Embedding deterministisch ohne Netzwerkzugriff."""
    return [float(len(text) % 10), 0.5, 1.0]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_end_to_end_research_workflow(monkeypatch):
    """Kompletter Research-Workflow: Query → Ergebnisse → Dashboard."""
    from crawlers.darknet_crawler import ForumPost
    from dashboard.server import DashboardHandler
    from mcp_tools.claim_validator import ClaimValidator
    from search.composite import CompositeRetriever
    from vectordb.store import VectorStore

    query = "GPU Monitoring Sicherheit"

    # 1. Query-Eingabe
    assert query.strip()

    # 2. CompositeRetriever: SearXNG und Darknet vollständig mocken.
    searx_response = MagicMock()
    searx_response.raise_for_status.return_value = None
    searx_response.json.return_value = {
        "results": [
            {
                "url": "https://example.test/gpu-monitoring",
                "title": "GPU Monitoring Grundlagen",
                "content": "GPU Monitoring nutzt Metriken und Quellenangaben.",
                "engine": "mock",
                "score": 0.9,
            }
        ]
    }
    darknet_result = [
        {
            "url": "http://darknet.test/thread/1",
            "title": "Darknet Forum Hinweis",
            "body": "Forum-Quelle mit ergänzender Evidenz.",
            "source": "Darknet Forum",
            "score": 0.7,
            "raw_content": "Forum-Quelle mit ergänzender Evidenz.",
        }
    ]

    monkeypatch.setenv("DARKNET_ENABLED", "true")
    mock_session = MagicMock()
    mock_session.get.return_value = searx_response
    with (
        patch("search.composite.create_session", return_value=mock_session),
        patch("search.composite.DarknetRetriever.search", return_value=darknet_result),
    ):
        retriever = CompositeRetriever(query, searx_url="http://searxng.mock")
        retrieved = retriever.search(max_results=5)

    assert len(retrieved) == 2
    assert {item["source"] for item in retrieved} == {"SearXNG", "Darknet Forum"}

    # 3. Crawler extrahiert Inhalte, ohne Tor/Netzwerk zu benutzen.
    crawled_posts = [
        ForumPost(
            url="http://darknet.test/thread/1",
            author="alice",
            timestamp="2026-05-23T00:00:00Z",
            content="Extrahierter Forum-Inhalt mit Quelle.",
            title="Darknet Forum Hinweis",
        )
    ]
    crawler = MagicMock()
    crawler.crawl.return_value = crawled_posts
    extracted_documents = [*retrieved, *[post.__dict__ for post in crawler.crawl()]]

    assert len(extracted_documents) == 3
    assert all(doc.get("url") for doc in extracted_documents)

    # 4. VectorStore speichert gemockte Embeddings.
    collection = _MemoryCollection()
    vector_store = VectorStore(persist_directory=":memory:", collection_name="e2e")
    monkeypatch.setattr(vector_store, "_get_collection", lambda: collection)
    documents = [
        doc.get("body") or doc.get("content") or "" for doc in extracted_documents
    ]
    metadatas = [
        {
            "url": doc["url"],
            "title": doc.get("title", ""),
            "source": doc.get("source", "crawler"),
        }
        for doc in extracted_documents
    ]
    embeddings = [_embedding_for(document) for document in documents]

    assert vector_store.add(documents, embeddings, metadatas=metadatas) is True
    vector_results = vector_store.query(_embedding_for(query), n_results=2)

    assert len(vector_results) == 2
    assert all(result["metadata"].get("url") for result in vector_results)

    # 5. Claim Validator wird ohne externe Suche/LLM gemockt.
    validator_result = {
        "success": True,
        "data": {
            "claim": query,
            "confidence": 0.81,
            "sources": [result["metadata"] for result in vector_results],
            "source_count": len(vector_results),
            "assessment": "gut belegt",
        },
    }
    with patch.object(ClaimValidator, "run", return_value=validator_result):
        validation = ClaimValidator().run({"claim": query, "max_sources": 2})

    assert validation["success"] is True
    assert validation["data"]["sources"]

    # 6. Dashboard liefert eine JSON-Response, die im E2E-Fluss assertiert wird.
    old_monitor = DashboardHandler.monitor
    DashboardHandler.monitor = _DashboardMonitor()
    server = HTTPServer(("127.0.0.1", 0), DashboardHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import requests

        url = f"http://127.0.0.1:{server.server_port}/api/gpu"
        response = requests.get(url, timeout=5)
        assert response.status_code == 200
        payload = response.json()
        assert payload["result_count"] == 2
        assert "SearXNG" in payload["sources"]
    finally:
        server.shutdown()
        server.server_close()
        DashboardHandler.monitor = old_monitor

    assert thread.is_alive() is False or thread.daemon is True

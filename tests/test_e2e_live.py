# =============================================================================
# E2E-Tests: Systemvalidierung mit laufenden Diensten (T-028)
# =============================================================================
# Diese Tests prüfen das System mit laufenden Diensten (Ollama, SearXNG, Tor).
# Sie werden nur ausgeführt, wenn RUN_E2E_TESTS=true gesetzt ist.
#
# Ausführung:
#   RUN_E2E_TESTS=true python3 -m pytest tests/test_e2e_live.py -v
# =============================================================================
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_skip = os.getenv("RUN_E2E_TESTS", "").lower() not in ("true", "1", "yes")


@pytest.mark.skipif(_skip, reason="RUN_E2E_TESTS nicht gesetzt")
def test_e2e_ollama_available():
    """Ollama ist erreichbar."""
    import requests

    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "models" in data


@pytest.mark.skipif(_skip, reason="RUN_E2E_TESTS nicht gesetzt")
def test_e2e_searxng_available():
    """SearXNG ist erreichbar und liefert JSON."""
    import requests

    r = requests.get("http://localhost:8080/search?q=test&format=json", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "results" in data


@pytest.mark.skipif(_skip, reason="RUN_E2E_TESTS nicht gesetzt")
def test_e2e_dashboard_available():
    """GPU-Dashboard ist erreichbar."""
    import requests

    r = requests.get("http://localhost:8888/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data


@pytest.mark.skipif(_skip, reason="RUN_E2E_TESTS nicht gesetzt")
def test_e2e_mcp_server_available():
    """MCP-Server ist erreichbar."""
    import requests

    r = requests.get("http://localhost:8765/health", timeout=5)
    assert r.status_code == 200


@pytest.mark.skipif(_skip, reason="RUN_E2E_TESTS nicht gesetzt")
def test_e2e_composite_retriever():
    """CompositeRetriever funktioniert mit SearXNG."""
    from search.composite import CompositeRetriever

    retriever = CompositeRetriever("test")
    retriever.darknet_enabled = False
    results = retriever.search(max_results=3)
    assert isinstance(results, list)

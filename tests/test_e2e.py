# =============================================================================
# End-to-End-Tests: Systemvalidierung
# =============================================================================
# Strukturelle E2E-Tests: Prüfen, dass alle Module importierbar sind,
# die Konfiguration valide ist und das System grundlegend funktioniert.
#
# Echte E2E-Tests mit laufenden Diensten (Ollama, SearXNG) müssen
# manuell ausgeführt werden.
#
# Ausführung:
#   python3 -m pytest tests/test_e2e.py -v
# =============================================================================

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Erwartete Module
EXPECTED_PACKAGES = [
    "darknet_search",
    "search",
    "vectordb",
    "crawlers",
    "config",
]

EXPECTED_MODULES = [
    "darknet_search.index",
    "darknet_search.retriever",
    "search.composite",
    "vectordb.store",
    "vectordb.embedding",
    "crawlers.darknet_crawler",
    "crawlers.config",
]


def test_e2e_all_modules_importable():
    """E2E: Alle definierten Module sind importierbar."""
    for module_name in EXPECTED_MODULES:
        __import__(module_name)
    # Wenn wir hier ankommen, sind alle Imports erfolgreich


def test_e2e_all_packages_importable():
    """E2E: Alle Packages sind importierbar."""
    for pkg in EXPECTED_PACKAGES:
        __import__(pkg)


def test_e2e_config_module():
    """E2E: Konfigurationsmodul funktioniert."""
    from config.config import print_config, validate_env

    # validate_env sollte fehlende Variablen finden
    missing = validate_env()
    assert isinstance(missing, list)
    # print_config verwendet logger.info() (logging, stdout/stderr-neutral).
    # Wir leiten logging auf ein StringIO um.
    import io
    import logging

    logger = logging.getLogger("config.config")
    logger.setLevel(logging.INFO)

    with io.StringIO() as buf:
        handler = logging.StreamHandler(buf)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        try:
            print_config()
        finally:
            logger.removeHandler(handler)
        output = buf.getvalue()
    assert "Konfiguration" in output


def test_e2e_crawler_dataclass():
    """E2E: Crawler-ForumPost-Dataclass funktioniert."""
    from crawlers.darknet_crawler import ForumPost

    post = ForumPost(
        url="http://forum.onion/test",
        author="testuser",
        timestamp="2026-05-16T10:00:00",
        content="Test content",
        title="Test Post",
        forum_id="f1",
    )
    assert post.url == "http://forum.onion/test"
    assert post.author == "testuser"
    assert post.content == "Test content"

    # Als Dict
    as_dict = {
        "url": post.url,
        "author": post.author,
        "timestamp": post.timestamp,
        "content": post.content,
        "title": post.title,
        "forum_id": post.forum_id,
    }
    assert as_dict["url"] == post.url


def test_e2e_whoosh_index_to_retriever():
    """E2E: WhooshIndex → DarknetRetriever → GPT-Format Pipeline."""
    from datetime import datetime

    from darknet_search.index import WhooshIndex
    from darknet_search.retriever import DarknetRetriever

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        idx.add_post(
            {
                "url": "http://forum.onion/post/e2e",
                "author": "e2e_test",
                "title": "E2E Test",
                "timestamp": datetime.now(),
                "content": "End-to-end test content for validation.",
                "forum_id": "e2e",
            }
        )

        retriever = DarknetRetriever("validation", index_dir=tmpdir)
        results = retriever.search(max_results=5)

        assert len(results) >= 1
        result = results[0]
        assert "url" in result
        assert result["url"].startswith("darknet://")
        assert "title" in result
        assert "body" in result


def test_e2e_env_example_exists():
    """E2E: .env.example ist vorhanden und vollständig."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    assert os.path.exists(env_path), ".env.example fehlt"

    with open(env_path) as f:
        content = f.read()

    # Wichtige Variablen müssen dokumentiert sein
    required_vars = [
        "FAST_LLM",
        "SMART_LLM",
        "STRATEGIC_LLM",
        "OLLAMA_BASE_URL",
        "EMBEDDING",
        "RETRIEVER",
        "SEARX_URL",
    ]
    for var in required_vars:
        assert var in content, f"{var} fehlt in .env.example"

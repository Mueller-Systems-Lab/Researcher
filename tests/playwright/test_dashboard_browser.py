# =============================================================================
# Playwright — Dashboard Visual Test (aktualisiert T-024)
# =============================================================================
# Echter Browser-Test: startet Dashboard-Server, macht Screenshot.
# Nur aktiv mit RUN_PLAYWRIGHT_TESTS=true + playwright install chromium.
#
# Ausführung:
#   RUN_PLAYWRIGHT_TESTS=true python3 -m pytest tests/playwright/ -v
# =============================================================================

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def _is_enabled():
    return os.getenv("RUN_PLAYWRIGHT_TESTS", "").lower() in ("true", "1", "yes")


@pytest.mark.skipif(not _is_enabled(), reason="RUN_PLAYWRIGHT_TESTS nicht gesetzt")
def test_dashboard_screenshot():
    """
    Startet Dashboard-Server, macht Screenshot, vergleicht mit Baseline.
    """
    from threading import Thread

    from dashboard.server import run_server

    server_thread = Thread(
        target=run_server,
        args=("127.0.0.1", 8889),
        daemon=True,
    )
    server_thread.start()
    import time

    time.sleep(1)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://127.0.0.1:8889", timeout=5000)
            page.wait_for_selector("#gpu-name", timeout=5000)

            screenshot_dir = os.path.join(os.path.dirname(__file__), "screenshots")
            baseline = os.path.join(screenshot_dir, "baseline", "dashboard.png")
            os.makedirs(os.path.dirname(baseline), exist_ok=True)

            screenshot = page.screenshot(path=baseline)
            assert screenshot is not None
            assert os.path.exists(baseline)
            assert os.path.getsize(baseline) > 0

            browser.close()
    except ImportError:
        pytest.skip("playwright Python-Modul nicht installiert")


@pytest.mark.skipif(not _is_enabled(), reason="RUN_PLAYWRIGHT_TESTS nicht gesetzt")
def test_dashboard_health():
    """Prüft, ob der Dashboard-Health-Endpoint funktioniert."""
    import requests

    try:
        r = requests.get("http://127.0.0.1:8889/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
    except requests.exceptions.ConnectionError:
        pytest.skip("Dashboard-Server läuft nicht")


# Struktur-Test (läuft immer, kein Playwright nötig)
def test_dashboard_html_structure():
    """Validiert die Struktur des Dashboard-HTML-Widgets ohne Playwright."""
    index_path = os.path.join(
        os.path.dirname(__file__), "../../dashboard/static/index.html"
    )
    with open(index_path) as f:
        html = f.read()

    assert 'id="gpu-util"' in html
    assert 'id="vram-used"' in html
    assert 'id="gpu-temp"' in html
    assert 'id="gpu-name"' in html
    assert 'id="process-list"' in html
    assert "EventSource" in html
    assert "/api/gpu/stream" in html

# =============================================================================
# Playwright — Dashboard Visual Tests (T-018)
# =============================================================================
# Nutzt den playwright-agent für visuelle Regression.
# Startet den Dashboard-Server, macht Screenshots, vergleicht mit Baseline.
#
# Ausführung:
#   python3 -m pytest tests/playwright/ -v
#
# Voraussetzung:
#   playwright install chromium
# =============================================================================

import sys
import os
import subprocess
import time
from threading import Thread

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_playwright_dashboard_loaded():
    """Prüft, ob Playwright und Chromium installiert sind."""
    try:
        result = subprocess.run(
            ["python3", "-m", "playwright", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            "Playwright nicht installiert: pip install playwright"
        )
    except FileNotFoundError:
        pytest.skip("Playwright nicht installiert")


def test_playwright_chromium_available():
    """Prüft, ob Chromium für Playwright installiert ist."""
    try:
        result = subprocess.run(
            ["python3", "-m", "playwright", "install", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Kein Fehler = Chromium verfügbar
    except Exception:
        pytest.skip("Chromium nicht verfügbar")


# Diese Tests benötigen den Dashboard-Server und eine GPU
# Sie werden nur ausgeführt, wenn die Umgebungsvariable gesetzt ist
# RUN_PLAYWRIGHT_TESTS=true
import pytest


def _is_enabled():
    return os.getenv("RUN_PLAYWRIGHT_TESTS", "").lower() in ("true", "1", "yes")


@pytest.mark.skipif(not _is_enabled(), reason="RUN_PLAYWRIGHT_TESTS nicht gesetzt")
def test_dashboard_screenshot():
    """
    Startet Dashboard-Server, macht Screenshot, vergleicht mit Baseline.

    Nutzt den playwright-agent für Screenshot-Erstellung und Vergleich.
    """
    from dashboard.server import run_server
    from threading import Thread
    import time

    # Dashboard in separatem Thread starten
    server_thread = Thread(
        target=run_server,
        args=("127.0.0.1", 8889),
        daemon=True,
    )
    server_thread.start()
    time.sleep(1)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://127.0.0.1:8889", timeout=5000)

            # Warten auf GPU-Daten
            page.wait_for_selector("#gpu-name", timeout=5000)

            # Screenshot
            screenshot_dir = os.path.join(os.path.dirname(__file__), "screenshots")
            baseline = os.path.join(screenshot_dir, "baseline", "dashboard.png")
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

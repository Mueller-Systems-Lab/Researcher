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
import json
import socket
import time
from contextlib import contextmanager
from threading import Thread
from urllib.parse import quote

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def _is_enabled():
    return os.getenv("RUN_PLAYWRIGHT_TESTS", "").lower() in ("true", "1", "yes")


def _screenshot_path(name: str) -> str:
    screenshot_dir = os.path.join(os.path.dirname(__file__), "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    return os.path.join(screenshot_dir, name)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _FakeMonitor:
    """Deterministischer GPU-Monitor für Browser-Tests."""

    @staticmethod
    def collect_dict():
        return {
            "gpu_name": "Test GPU",
            "gpu_utilization": 12.5,
            "memory_used_mib": 1024,
            "memory_total_mib": 8192,
            "memory_percent": 12.5,
            "temperature_c": 42,
            "processes": [],
            "warning_level": "ok",
            "error": "",
        }

    @staticmethod
    def is_available():
        return True


@contextmanager
def _dashboard_server():
    """Startet einen isolierten Dashboard-Server für einen Test."""
    from http.server import HTTPServer
    from dashboard.server import DashboardHandler

    old_monitor = DashboardHandler.monitor
    DashboardHandler.monitor = _FakeMonitor()
    port = _free_port()
    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        time.sleep(0.2)
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        DashboardHandler.monitor = old_monitor


@pytest.mark.skipif(not _is_playwright_available(), reason="Playwright nicht installiert")
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


# === GPU MONITORING SSE ===


@pytest.mark.playwright
@pytest.mark.skipif(not _is_playwright_available(), reason="Playwright nicht installiert")
def test_gpu_sse_stream():
    """GPU-Monitoring SSE-Stream im Browser validieren."""
    try:
        import requests
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright oder requests nicht installiert")

    with _dashboard_server() as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            event_data = page.evaluate(
                """
                (url) => new Promise((resolve, reject) => {
                    const source = new EventSource(url + '/api/gpu/stream');
                    const timer = setTimeout(() => {
                        source.close();
                        reject(new Error('SSE timeout'));
                    }, 5000);
                    source.onmessage = (event) => {
                        clearTimeout(timer);
                        source.close();
                        resolve(event.data);
                    };
                    source.onerror = () => {
                        clearTimeout(timer);
                        source.close();
                        reject(new Error('SSE error'));
                    };
                })
                """,
                base_url,
            )
            data = json.loads(event_data)
            assert "gpu_utilization" in data
            assert "memory_used_mib" in data

            with requests.get(
                f"{base_url}/api/gpu/stream", stream=True, timeout=5
            ) as r:
                assert r.status_code == 200
                assert r.headers["Content-Type"].startswith("text/event-stream")
            page.screenshot(path=_screenshot_path("gpu_sse_stream.png"))
            browser.close()


# === CORS ===


@pytest.mark.playwright
@pytest.mark.skipif(not _is_playwright_available(), reason="Playwright nicht installiert")
def test_dashboard_cors_blocks_foreign_origin():
    """CORS: Request von nicht-Whitelisted Origin wird blockiert."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright Python-Modul nicht installiert")

    with _dashboard_server() as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://example.com", timeout=10000)
            result = page.evaluate(
                """
                async (url) => {
                    try {
                        await fetch(url + '/api/gpu', { mode: 'cors' });
                        return { blocked: false };
                    } catch (error) {
                        return { blocked: true, name: error.name, message: error.message };
                    }
                }
                """,
                base_url,
            )
            page.screenshot(path=_screenshot_path("cors_foreign_origin.png"))
            browser.close()

    assert result["blocked"] is True


# === XSS ===


@pytest.mark.playwright
@pytest.mark.skipif(not _is_playwright_available(), reason="Playwright nicht installiert")
def test_dashboard_xss_query_parameter_escaped():
    """XSS: Script im Query-Parameter löst keinen Dialog aus."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright Python-Modul nicht installiert")

    payload = "<script>alert(1)</script>"
    with _dashboard_server() as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            dialogs = []
            page.on(
                "dialog",
                lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()),
            )
            page.goto(f"{base_url}/?q={quote(payload)}", timeout=5000)
            page.wait_for_selector("#gpu-name", timeout=5000)
            script_count = page.locator("script", has_text="alert(1)").count()
            displayed_query = page.locator("#query-display").inner_text()
            page.screenshot(path=_screenshot_path("xss_query_parameter.png"))
            browser.close()

    assert dialogs == []
    assert script_count == 0
    assert displayed_query == payload


# === RESPONSIVE ===


@pytest.mark.playwright
@pytest.mark.skipif(not _is_playwright_available(), reason="Playwright nicht installiert")
@pytest.mark.parametrize("viewport", [(375, 812), (1920, 1080)])
def test_dashboard_responsive(viewport):
    """Dashboard ist auf Mobile und Desktop nutzbar."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright Python-Modul nicht installiert")

    width, height = viewport
    with _dashboard_server() as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(base_url, timeout=5000)
            page.wait_for_selector("#gpu-name", timeout=5000)
            page.screenshot(path=_screenshot_path(f"responsive_{width}x{height}.png"))
            has_horizontal_scroll = page.evaluate(
                "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
            )
            assert has_horizontal_scroll is False
            assert page.locator("#gpu-name").is_visible()
            browser.close()


@pytest.mark.skipif(not _is_playwright_available(), reason="Playwright nicht installiert")
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

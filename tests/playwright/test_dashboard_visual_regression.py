"""Real Playwright browser tests for the GPU dashboard.

Run with:
    RUN_PLAYWRIGHT_TESTS=true python -m pytest \
        tests/playwright/test_dashboard_visual_regression.py -v

The visual baseline is stored below tests/playwright/baselines/.  On the first
run the baseline image is created from the deterministic dashboard state; later
runs compare new screenshots against it.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - exercised only without Playwright
    PlaywrightError = Exception
    sync_playwright = None


ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = Path(__file__).resolve().parent / "baselines"
BASELINE_IMAGE = BASELINE_DIR / "dashboard_visual_regression.png"

sys.path.insert(0, str(ROOT))


def _is_enabled() -> bool:
    return os.getenv("RUN_PLAYWRIGHT_TESTS", "").lower() in {"true", "1", "yes"}


pytestmark = pytest.mark.skipif(
    not _is_enabled(), reason="RUN_PLAYWRIGHT_TESTS=true is required"
)


@pytest.fixture(scope="module")
def dashboard_server():
    """Start the dashboard server on a free local port and shut it down."""
    from dashboard.server import DashboardHandler

    server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://{host}:{port}"
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=10) as response:
            assert response.status == 200
        yield url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture()
def browser_page():
    """Create an isolated Chromium page with reduced motion enabled."""
    if sync_playwright is None:
        pytest.skip("playwright Python package is not installed")

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                reduced_motion="reduce",
            )
            page = context.new_page()
            yield page
            context.close()
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(
            "Playwright Chromium is not available; run `playwright install chromium` "
            f"first. Original error: {exc}"
        )


def _read_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as response:
        assert response.status == 200
        return json.loads(response.read().decode("utf-8"))


def _install_deterministic_event_source(page) -> None:
    """Replace EventSource before page load so visual screenshots are stable."""
    page.add_init_script(
        """
        (() => {
          const sample = {
            timestamp: '2026-01-01T12:00:00',
            gpu_index: 0,
            gpu_name: 'Visual Regression GPU',
            gpu_utilization: 42,
            memory_used_mib: 2048,
            memory_total_mib: 8192,
            memory_utilization: 25,
            memory_percent: 25,
            temperature_c: 55,
            warning_level: 'ok',
            processes: []
          };

          class MockEventSource extends EventTarget {
            constructor(url) {
              super();
              this.url = url;
              this.readyState = 0;
              setTimeout(() => {
                this.readyState = 1;
                const openEvent = new Event('open');
                this.dispatchEvent(openEvent);
                if (this.onopen) this.onopen(openEvent);

                const messageEvent = new MessageEvent('message', {
                  data: JSON.stringify(sample)
                });
                this.dispatchEvent(messageEvent);
                if (this.onmessage) this.onmessage(messageEvent);
              }, 0);
            }
            close() { this.readyState = 2; }
          }

          MockEventSource.CONNECTING = 0;
          MockEventSource.OPEN = 1;
          MockEventSource.CLOSED = 2;
          window.EventSource = MockEventSource;
        })();
        """
    )


def _assert_or_create_visual_baseline(screenshot: bytes) -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    if not BASELINE_IMAGE.exists():
        BASELINE_IMAGE.write_bytes(screenshot)
        return

    expected = BASELINE_IMAGE.read_bytes()
    if expected == screenshot:
        return

    try:
        from io import BytesIO

        from PIL import Image, ImageChops
    except ImportError:
        assert (
            hashlib.sha256(screenshot).hexdigest()
            == hashlib.sha256(expected).hexdigest()
        ), "Dashboard screenshot differs from visual baseline"
        return

    expected_image = Image.open(BytesIO(expected)).convert("RGBA")
    actual_image = Image.open(BytesIO(screenshot)).convert("RGBA")
    assert actual_image.size == expected_image.size

    diff = ImageChops.difference(expected_image, actual_image)
    changed_pixels = sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0, 0))
    total_pixels = actual_image.size[0] * actual_image.size[1]
    diff_ratio = changed_pixels / total_pixels
    assert diff_ratio <= 0.001, f"Dashboard visual diff too high: {diff_ratio:.4%}"


def test_dashboard_loads_and_shows_gpu_metrics_or_graceful_fallback(
    dashboard_server, browser_page
):
    api_data = _read_json(f"{dashboard_server}/api/gpu")

    browser_page.goto(dashboard_server, wait_until="domcontentloaded", timeout=30_000)
    browser_page.wait_for_selector("#gpu-name", timeout=30_000)

    assert browser_page.locator("h1").inner_text() == "⚙ GPU-Dashboard"
    assert browser_page.locator("#metrics .card").count() == 4

    if api_data.get("error"):
        browser_page.wait_for_selector("#error", state="visible", timeout=30_000)
        assert api_data["error"] in browser_page.locator("#error").inner_text()
    else:
        browser_page.wait_for_function(
            "document.querySelector('#gpu-util').textContent.trim() !== '--'",
            timeout=30_000,
        )
        assert "%" in browser_page.locator("#gpu-util").inner_text()
        assert "MiB" in browser_page.locator("#vram-used").inner_text()
        assert "°C" in browser_page.locator("#gpu-temp").inner_text()


def test_dashboard_sse_event_stream_connects(dashboard_server, browser_page):
    browser_page.add_init_script(
        """
        (() => {
          window.__dashboardSseEvents = [];
          const NativeEventSource = window.EventSource;
          window.EventSource = function(url, config) {
            window.__dashboardSseUrl = url;
            const source = new NativeEventSource(url, config);
            source.addEventListener('open', () => window.__dashboardSseEvents.push('open'));
            source.addEventListener('message', () => window.__dashboardSseEvents.push('message'));
            source.addEventListener('error', () => window.__dashboardSseEvents.push('error'));
            return source;
          };
          window.EventSource.prototype = NativeEventSource.prototype;
        })();
        """
    )

    browser_page.goto(dashboard_server, wait_until="domcontentloaded", timeout=30_000)
    browser_page.wait_for_function(
        "window.__dashboardSseUrl === '/api/gpu/stream'", timeout=30_000
    )
    browser_page.wait_for_function(
        "window.__dashboardSseEvents.includes('open') || "
        "window.__dashboardSseEvents.includes('message') || "
        "document.querySelector('#error').style.display === 'block'",
        timeout=30_000,
    )

    events = browser_page.evaluate("window.__dashboardSseEvents")
    assert "open" in events or "message" in events


def test_dashboard_visual_regression_screenshot(dashboard_server, browser_page):
    _install_deterministic_event_source(browser_page)
    browser_page.goto(dashboard_server, wait_until="networkidle", timeout=30_000)
    browser_page.wait_for_selector("text=Visual Regression GPU", timeout=30_000)
    browser_page.wait_for_timeout(100)

    screenshot = browser_page.screenshot(full_page=True)
    assert screenshot
    _assert_or_create_visual_baseline(screenshot)

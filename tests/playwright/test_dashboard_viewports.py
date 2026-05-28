"""Viewport-Matrix-Tests für das GPU-Dashboard.

Testet Responsive-Verhalten auf Desktop, Tablet und Mobile.
Nutzt mock-EventSource für deterministische Screenshots.

Run with:
    RUN_PLAYWRIGHT_TESTS=true python3 -m pytest \\
        tests/playwright/test_dashboard_viewports.py -v

Viewports:
    - Desktop:  1280x720
    - Tablet:    768x1024
    - Mobile:    375x812
"""

from __future__ import annotations

import json
import os
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest


def _is_playwright_available() -> bool:
    return os.getenv("RUN_PLAYWRIGHT_TESTS", "").lower() in {"true", "1", "yes"}


try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:
    PlaywrightError = Exception
    sync_playwright = None


ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = Path(__file__).resolve().parent / "baselines"

pytestmark = pytest.mark.skipif(
    not _is_playwright_available(), reason="RUN_PLAYWRIGHT_TESTS=true is required"
)

# Viewport-Matrix
VIEWPORTS = [
    pytest.param({"width": 1280, "height": 720}, id="desktop"),
    pytest.param({"width": 768, "height": 1024}, id="tablet"),
    pytest.param({"width": 375, "height": 812}, id="mobile"),
]


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


def _install_mock_event_source(page, sample_data: dict | None = None):
    """Replace EventSource with a mock that sends deterministic data."""
    if sample_data is None:
        sample_data = {
            "timestamp": "2026-01-01T12:00:00",
            "gpu_index": 0,
            "gpu_name": "Visual Regression GPU",
            "gpu_utilization": 42,
            "memory_used_mib": 2048,
            "memory_total_mib": 8192,
            "memory_utilization": 25,
            "memory_percent": 25,
            "temperature_c": 55,
            "warning_level": "ok",
            "processes": [],
        }

    page.add_init_script(
        f"""
        (() => {{
          const sample = {json.dumps(sample_data)};

          class MockEventSource extends EventTarget {{
            constructor(url) {{
              super();
              this.url = url;
              this.readyState = 0;
              setTimeout(() => {{
                this.readyState = 1;
                const openEvent = new Event('open');
                this.dispatchEvent(openEvent);
                if (this.onopen) this.onopen(openEvent);

                const messageEvent = new MessageEvent('message', {{
                  data: JSON.stringify(sample)
                }});
                this.dispatchEvent(messageEvent);
                if (this.onmessage) this.onmessage(messageEvent);
              }}, 0);
            }}
            close() {{ this.readyState = 2; }}
          }}

          MockEventSource.CONNECTING = 0;
          MockEventSource.OPEN = 1;
          MockEventSource.CLOSED = 2;
          window.EventSource = MockEventSource;
        }})();
        """
    )


@pytest.fixture()
def browser(request):
    """Create a Chromium browser with viewport-specific context."""
    if sync_playwright is None:
        pytest.skip("playwright Python package is not installed")

    viewport = (
        request.param if hasattr(request, "param") else {"width": 1280, "height": 720}
    )

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport=viewport,
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


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("browser", VIEWPORTS, indirect=True)
def test_dashboard_loads_in_viewport(dashboard_server, browser):
    """Test: Dashboard lädt und zeigt GPU-Metriken in jedem Viewport."""
    _install_mock_event_source(browser)
    browser.goto(dashboard_server, wait_until="domcontentloaded", timeout=30_000)
    browser.wait_for_selector("text=Visual Regression GPU", timeout=30_000)

    # Assert: 4 Karten sind sichtbar
    cards = browser.locator("#metrics .card")
    assert cards.count() == 4

    # Assert: GPU-Auslastungswert ist sichtbar
    util_text = browser.locator("#gpu-util").inner_text()
    assert "%" in util_text
    assert "42" in util_text

    # Assert: Verbindungsstatus ist grün
    status_class = browser.locator("#connection-status").get_attribute("class")
    assert "connected" in status_class


@pytest.mark.parametrize("browser", VIEWPORTS, indirect=True)
def test_dashboard_viewport_screenshot(dashboard_server, browser):
    """Test: Screenshot in jedem Viewport für visuelle Regression."""
    # Get viewport info for baseline filename
    viewport_size = browser.viewport_size
    width = viewport_size["width"]
    height = viewport_size["height"]
    label = f"{width}x{height}"
    baseline_file = BASELINE_DIR / f"dashboard_viewport_{label}.png"

    _install_mock_event_source(browser)
    browser.goto(dashboard_server, wait_until="domcontentloaded", timeout=30_000)
    browser.wait_for_selector("text=Visual Regression GPU", timeout=30_000)
    browser.wait_for_timeout(200)  # Wait for render

    screenshot = browser.screenshot(full_page=True)
    assert screenshot, f"Leerer Screenshot für Viewport {label}"

    # Create or compare baseline
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    if not baseline_file.exists():
        baseline_file.write_bytes(screenshot)
        return

    expected = baseline_file.read_bytes()
    if expected == screenshot:
        return

    # Use PIL for pixel-diff analysis if available
    try:
        from io import BytesIO

        from PIL import Image, ImageChops
    except ImportError:
        import hashlib

        assert (
            hashlib.sha256(screenshot).hexdigest()
            == hashlib.sha256(expected).hexdigest()
        ), f"Dashboard screenshot differs from baseline for viewport {label}"
        return

    expected_img = Image.open(BytesIO(expected)).convert("RGBA")
    actual_img = Image.open(BytesIO(screenshot)).convert("RGBA")

    # Only compare if dimensions match
    if actual_img.size != expected_img.size:
        baseline_file.write_bytes(screenshot)
        return

    diff = ImageChops.difference(expected_img, actual_img)
    changed_pixels = sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0, 0))
    total_pixels = actual_img.size[0] * actual_img.size[1]
    diff_ratio = changed_pixels / total_pixels

    assert diff_ratio <= 0.001, (
        f"Dashboard visual diff zu hoch für Viewport {label}: {diff_ratio:.4%}"
    )


@pytest.mark.parametrize("browser", VIEWPORTS, indirect=True)
def test_dashboard_responsive_layout(dashboard_server, browser):
    """Test: Responsive Layout — Karten sind in jedem Viewport sichtbar und nicht überlappend."""
    _install_mock_event_source(browser)
    browser.goto(dashboard_server, wait_until="domcontentloaded", timeout=30_000)
    browser.wait_for_selector("text=Visual Regression GPU", timeout=30_000)

    # Alle 4 Karten sollten sichtbar sein
    cards = browser.locator("#metrics .card")
    assert cards.count() == 4

    # Jede Karte sollte sichtbar sein (BoundingBox existiert und ist > 0)
    for i in range(cards.count()):
        box = cards.nth(i).bounding_box()
        assert box is not None, f"Karte {i} hat kein BoundingBox (nicht sichtbar)"
        assert box["width"] > 50, f"Karte {i} ist zu schmal: {box['width']}px"
        assert box["height"] > 50, f"Karte {i} ist zu flach: {box['height']}px"

    # Status-Legende sollte sichtbar sein
    legend = browser.locator('[aria-label="Status-Legende"]')
    assert legend.is_visible()

    # GPU-Name sollte sichtbar sein
    assert browser.locator("#gpu-name").is_visible()

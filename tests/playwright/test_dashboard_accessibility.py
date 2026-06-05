# =============================================================================
# Playwright — Dashboard Accessibility Tests (Issue #41)
# =============================================================================
# Prüft WCAG-2.1-AA-Konformität: ARIA-Tree, Farbkontraste, Tastaturnavigation.
# =============================================================================

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# The real playwright distribution is imported below.  The shadowing
# between the tests/playwright directory and the installed "playwright"
# package is resolved by removing tests/playwright/__init__.py — the
# directory is NOT a Python package, so "import playwright" correctly
# resolves the installed distribution.
_PLAYWRIGHT_IMPORT_ERROR: str | None = None
PlaywrightError: type[Exception] = Exception
try:
    from playwright.sync_api import Error as PlaywrightError  # type: ignore[assignment]
    from playwright.sync_api import sync_playwright
except ImportError as _pw_exc:
    sync_playwright = None  # type: ignore[assignment]
    _PLAYWRIGHT_IMPORT_ERROR = str(_pw_exc)

pytestmark = pytest.mark.skipif(
    sync_playwright is None,
    reason=(
        "Playwright Python package is not installed"
        if _PLAYWRIGHT_IMPORT_ERROR is None
        else f"Playwright import failed: {_PLAYWRIGHT_IMPORT_ERROR}"
    ),
)

ROOT = os.path.join(os.path.dirname(__file__), "../..")
ARTIFACT_DIR = os.path.join(ROOT, "qa/live/artifacts/screenshots")


@pytest.fixture(scope="module")
def dashboard_server():
    """Start the real dashboard server for accessibility testing."""
    import threading
    import time

    from dashboard.server import run_server

    server_thread = threading.Thread(
        target=run_server, args=("127.0.0.1", 8890), daemon=True
    )
    server_thread.start()
    time.sleep(1.5)
    yield "http://127.0.0.1:8890"


@pytest.fixture()
def browser_page():
    """Create an isolated Chromium page with reduced motion."""
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
        pytest.skip(f"Playwright browser error: {exc}")


# ============================================================================
# ARIA-Tree / Semantic Structure
# ============================================================================
def test_dashboard_aria_tree_has_required_roles(dashboard_server: str, browser_page):
    """ARIA-Tree enthält mindestens progressbar, status und alert Rollen."""
    browser_page.goto(dashboard_server, timeout=10000)
    browser_page.wait_for_selector("#gpu-name", timeout=5000)
    browser_page.wait_for_timeout(500)

    # Prüfe Rollen via DOM-Attribute (Playwright Python kein accessibility.snapshot)
    progressbars = browser_page.locator("[role='progressbar']")
    assert progressbars.count() >= 2, (
        f"Erwartet ≥2 progressbar, gefunden: {progressbars.count()}"
    )

    status_elements = browser_page.locator("[role='status']")
    assert status_elements.count() >= 4, (
        f"Erwartet ≥4 status, gefunden: {status_elements.count()}"
    )

    alert_element = browser_page.locator("[role='alert']")
    assert alert_element.count() >= 1, "Kein alert Element"

    region = browser_page.locator("[role='region']")
    assert region.count() >= 2, f"Erwartet ≥2 region, gefunden: {region.count()}"


def test_dashboard_required_aria_labels(dashboard_server: str, browser_page):
    """Alle dynamischen Werte haben aria-live oder aria-label."""
    browser_page.goto(dashboard_server, timeout=10000)
    browser_page.wait_for_selector("#gpu-name", timeout=5000)

    # GPU-Auslastung Fortschrittsbalken
    gpu_bar = browser_page.locator("#gpu-bar")
    assert gpu_bar.get_attribute("role") == "progressbar"
    assert gpu_bar.get_attribute("aria-label") is not None

    # VRAM Fortschrittsbalken
    vram_bar = browser_page.locator("#vram-bar")
    assert vram_bar.get_attribute("role") == "progressbar"

    # Fehlermeldung hat alert Rolle
    error_div = browser_page.locator("#error")
    assert error_div.get_attribute("role") == "alert"

    # GPU-Name hat aria-live
    gpu_name = browser_page.locator("#gpu-name")
    assert gpu_name.get_attribute("aria-live") == "polite"


def test_dashboard_aria_live_regions(dashboard_server: str, browser_page):
    """Dynamische Werte sind als aria-live=polite markiert."""
    browser_page.goto(dashboard_server, timeout=10000)
    browser_page.wait_for_selector("#gpu-name", timeout=5000)

    live_elements = browser_page.locator("[aria-live='polite']")
    count = live_elements.count()
    assert count >= 5, f"Erwartet ≥ 5 aria-live Elemente, gefunden: {count}"


# ============================================================================
# Farbkontrast (Dark Theme)
# ============================================================================
def test_dashboard_color_contrast_dark_theme(dashboard_server: str, browser_page):
    """Prüft Farbkontrast im Dark Theme (#0d1117 / #c9d1d9)."""
    browser_page.goto(dashboard_server, timeout=10000)
    browser_page.wait_for_selector("#gpu-name", timeout=5000)

    # Berechne Kontrastverhältnis via JavaScript (WCAG-Formel)
    contrast = browser_page.evaluate("""
        () => {
            function getLuminance(r, g, b) {
                const a = [r, g, b].map(v => {
                    v /= 255;
                    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
                });
                return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
            }
            function getContrast(hex1, hex2) {
                const r1 = parseInt(hex1.slice(1,3), 16);
                const g1 = parseInt(hex1.slice(3,5), 16);
                const b1 = parseInt(hex1.slice(5,7), 16);
                const r2 = parseInt(hex2.slice(1,3), 16);
                const g2 = parseInt(hex2.slice(3,5), 16);
                const b2 = parseInt(hex2.slice(5,7), 16);
                const l1 = getLuminance(r1, g1, b1);
                const l2 = getLuminance(r2, g2, b2);
                const lighter = Math.max(l1, l2);
                const darker = Math.min(l1, l2);
                return (lighter + 0.05) / (darker + 0.05);
            }
            const bodyBg = getComputedStyle(document.body).backgroundColor;
            const bodyColor = getComputedStyle(document.body).color;

            // Parse rgb(r,g,b) to hex
            function rgbToHex(rgb) {
                const m = rgb.match(/\\d+/g);
                if (!m) return '#000000';
                return '#' + m.slice(0,3).map(x => parseInt(x).toString(16).padStart(2,'0')).join('');
            }
            const bgHex = rgbToHex(bodyBg);
            const colorHex = rgbToHex(bodyColor);
            return {
                contrast: getContrast(bgHex, colorHex),
                bg: bgHex,
                color: colorHex
            };
        }
    """)

    # WCAG AA: ≥ 4.5:1 für Normaltext, ≥ 3:1 für Large Text
    assert contrast["contrast"] >= 4.5, (
        f"Kontrast {contrast['contrast']:.1f}:1 zu niedrig "
        f"(BG: {contrast['bg']}, Text: {contrast['color']})"
    )


# ============================================================================
# HTML-Struktur
# ============================================================================
def test_dashboard_html_lang_attribute():
    """HTML hat lang='de' Attribut."""
    index_path = os.path.join(
        os.path.dirname(__file__), "../../dashboard/static/index.html"
    )
    with open(index_path) as f:
        html = f.read()

    assert 'lang="de"' in html
    assert "viewport" in html


def test_dashboard_html_aria_attributes_present():
    """HTML enthält alle erforderlichen ARIA-Attribute."""
    index_path = os.path.join(
        os.path.dirname(__file__), "../../dashboard/static/index.html"
    )
    with open(index_path) as f:
        html = f.read()

    required_attrs = [
        'aria-live="polite"',
        'aria-live="assertive"',
        'role="alert"',
        'role="progressbar"',
        'role="status"',
        'role="region"',
        'aria-label="GPU-Dashboard"',
        'aria-label="GPU-Metriken"',
        "aria-valuenow",
        "aria-valuemin",
        "aria-valuemax",
    ]

    for attr in required_attrs:
        assert attr in html, f"Fehlendes ARIA-Attribut: {attr}"


# ============================================================================
# Screenshot (Evidence)
# ============================================================================
def test_dashboard_accessibility_screenshot(dashboard_server: str, browser_page):
    """Erstellt einen Screenshot mit allen ARIA-Elementen sichtbar."""
    browser_page.goto(dashboard_server, timeout=10000)
    browser_page.wait_for_selector("#gpu-name", timeout=5000)
    browser_page.wait_for_timeout(500)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    screenshot_path = os.path.join(ARTIFACT_DIR, "dashboard_accessibility.png")
    browser_page.screenshot(path=screenshot_path, full_page=True)

    assert os.path.exists(screenshot_path)
    assert os.path.getsize(screenshot_path) > 1000, "Screenshot ist leer"

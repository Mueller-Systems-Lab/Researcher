# =============================================================================
# Playwright — Dashboard Visual Test
# =============================================================================
# Beispiel: Screenshot des GPU-Dashboards und Vergleich mit Baseline.
#
# Ausführung:
#   RUN_PLAYWRIGHT_TESTS=true python3 -m pytest tests/playwright/ -v
# =============================================================================

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_dashboard_gpu_widget_structure():
    """
    Validiert die Struktur des Dashboard-HTML-Widgets.
    Läuft OHNE Playwright — prüft nur den HTML-Quelltext.
    """

    index_path = os.path.join(
        os.path.dirname(__file__), "../../dashboard/static/index.html"
    )
    with open(index_path) as f:
        html = f.read()

    # Erforderliche Elemente
    assert 'id="gpu-util"' in html
    assert 'id="vram-used"' in html
    assert 'id="gpu-temp"' in html
    assert 'id="gpu-name"' in html
    assert 'id="process-list"' in html
    assert 'id="timestamp"' in html

    # SSE-Verbindung
    assert "EventSource" in html
    assert "/api/gpu/stream" in html

    # Warnungslogik
    assert "warning_level" in html
    assert "critical-text" in html
    assert "warning-text" in html

    # Responsive Design
    assert "viewport" in html
    assert "grid-template-columns" in html


def test_dashboard_gpu_widget_accessibility():
    """
    Prüft grundlegende Accessibility-Merkmale des Dashboards.
    """
    index_path = os.path.join(
        os.path.dirname(__file__), "../../dashboard/static/index.html"
    )
    with open(index_path) as f:
        html = f.read()

    # Sprache
    assert 'lang="de"' in html

    # Meta-Viewport für Accessibility
    assert "viewport" in html

    # Strukturierte Überschriften
    assert "<h1>" in html

    # Alternativtext für visuelle Elemente
    assert "aria-label" in html or "role=" in html or "label" in html

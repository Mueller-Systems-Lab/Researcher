# =============================================================================
# Playwright — Konfiguration (conftest.py)
# =============================================================================
# Fixtures und Hilfsfunktionen für Playwright-Tests.
# Echte Browser-Tests in test_dashboard_browser.py.
#
# Ausführung:
#   RUN_PLAYWRIGHT_TESTS=true python3 -m pytest tests/playwright/ -v
#
# Voraussetzung:
#   pip install playwright
#   playwright install chromium
# =============================================================================

import os
import sys

# Projekt-Root zum Import-Pfad hinzufügen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

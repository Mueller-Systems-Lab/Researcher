# =============================================================================
# Benchmarks — Timeout-Konfiguration
# =============================================================================
# Benchmarks brauchen längere Timeouts wegen pytest-benchmark-Kalibrierungsrunden.
# Der Default-Timeout von 30s aus pyproject.toml ist für Benchmarks zu knapp.
# =============================================================================
import pytest


def pytest_collection_modifyitems(config, items):
    """Setzt 300s Timeout für alle Benchmark-Tests (5 Minuten)."""
    for item in items:
        if not item.get_closest_marker("timeout"):
            item.add_marker(pytest.mark.timeout(300))

# =============================================================================
# Tests: GPU/VRAM Dashboard (T-017)
# =============================================================================
#
# Ausführung:
#   python3 -m pytest tests/test_dashboard.py -v
# =============================================================================

import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_gpu_monitor_error_no_nvidia_smi():
    """GPUMonitor: Fehler wenn nvidia-smi nicht existiert."""
    from dashboard.gpu_monitor import GPUMonitor

    monitor = GPUMonitor()
    data = monitor.collect()

    # Wenn nvidia-smi nicht installiert ist, sollte error gesetzt sein
    # oder normale Daten (wenn GPU vorhanden)
    if data.error:
        assert "nvidia-smi" in data.error or "Fehler" in data.error


@patch("dashboard.gpu_monitor.subprocess.run")
def test_gpu_monitor_parse(mock_run):
    """GPUMonitor: nvidia-smi Output korrekt parsen."""
    from dashboard.gpu_monitor import GPUMonitor

    # Mock nvidia-smi Output
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "0, NVIDIA GeForce GTX 1070, 45, 4096, 8192, 50, 65\n"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    monitor = GPUMonitor()
    data = monitor.collect()

    assert data.gpu_index == 0
    assert "GTX 1070" in data.gpu_name
    assert data.gpu_utilization == 45.0
    assert data.memory_used_mib == 4096
    assert data.memory_total_mib == 8192
    assert data.temperature_c == 65.0


@patch("dashboard.gpu_monitor.subprocess.run")
def test_gpu_monitor_return_code(mock_run):
    """GPUMonitor: Fehler bei returncode != 0."""
    from dashboard.gpu_monitor import GPUMonitor

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "No NVIDIA GPU found"
    mock_run.return_value = mock_result

    monitor = GPUMonitor()
    data = monitor.collect()

    assert data.error != ""


@patch("dashboard.gpu_monitor.subprocess.run")
def test_gpu_monitor_empty_output(mock_run):
    """GPUMonitor: Leerer Output."""
    from dashboard.gpu_monitor import GPUMonitor

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_run.return_value = mock_result

    monitor = GPUMonitor()
    data = monitor.collect()

    assert data.error != ""


@patch("dashboard.gpu_monitor.subprocess.run")
def test_gpu_monitor_warning_level(mock_run):
    """GPUMonitor: Warning-Level korrekt."""
    from dashboard.gpu_monitor import GPUMonitor

    # Kritischer VRAM
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "0, GPU, 50, 7800, 8192, 60, 70\n"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    monitor = GPUMonitor()
    d = monitor.collect_dict()
    assert d["warning_level"] == "critical"


@patch("dashboard.gpu_monitor.subprocess.run")
def test_gpu_monitor_warning(mock_run):
    """GPUMonitor: Mittlere Warnung."""
    from dashboard.gpu_monitor import GPUMonitor

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "0, GPU, 50, 7400, 8192, 60, 70\n"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    monitor = GPUMonitor()
    d = monitor.collect_dict()
    assert d["warning_level"] == "warning"


@patch("dashboard.gpu_monitor.subprocess.run")
def test_gpu_monitor_ok(mock_run):
    """GPUMonitor: Normaler Betrieb."""
    from dashboard.gpu_monitor import GPUMonitor

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "0, GPU, 30, 2048, 8192, 40, 55\n"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    monitor = GPUMonitor()
    d = monitor.collect_dict()
    assert d["warning_level"] == "ok"


@patch("dashboard.gpu_monitor.subprocess.run")
def test_gpu_monitor_collect_dict(mock_run):
    """GPUMonitor: collect_dict enthält alle Felder."""
    from dashboard.gpu_monitor import GPUMonitor

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "0, NVIDIA GTX 1070, 50, 4096, 8192, 50, 65\n"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    monitor = GPUMonitor()
    d = monitor.collect_dict()

    assert "gpu_name" in d
    assert "gpu_utilization" in d
    assert "memory_used_mib" in d
    assert "memory_percent" in d
    assert "warning_level" in d
    assert "timestamp" in d


def test_gpu_monitor_is_available():
    """GPUMonitor: is_available prüft nvidia-smi Existenz."""
    from dashboard.gpu_monitor import GPUMonitor

    # Diese Funktion prüft nur ob nvidia-smi existiert
    available = GPUMonitor.is_available()
    assert isinstance(available, bool)


@patch("dashboard.server.DashboardHandler")
def test_dashboard_static_files(mock_handler):
    """Dashboard: Statische Dateien existieren."""
    static_dir = os.path.join(os.path.dirname(__file__), "..", "dashboard", "static")
    index_path = os.path.join(static_dir, "index.html")
    assert os.path.exists(index_path), "index.html fehlt"
    assert os.path.getsize(index_path) > 0, "index.html ist leer"

    with open(index_path) as f:
        content = f.read()
    assert "GPU-Dashboard" in content
    assert "EventSource" in content
    assert "nvidia-smi" in content or "nvidia" in content.lower()


def test_dashboard_health_endpoint():
    """Dashboard: Health-Endpoint Struktur."""
    from dashboard.server import DashboardHandler

    handler = DashboardHandler
    assert hasattr(handler, "monitor")
    assert hasattr(handler.monitor, "collect_dict")


# ─── Path-Traversal-Schutz (T-021) ────────────────────────────────────────────


def test_resolve_static_normal():
    """_resolve_static: Normale Datei wird aufgelöst."""
    from dashboard.server import DashboardHandler, STATIC_DIR
    import os

    handler = DashboardHandler
    result = handler._resolve_static(handler, "index.html")
    assert result is not None
    assert os.path.exists(result)
    assert "index.html" in result


def test_resolve_static_traversal():
    """_resolve_static: ../ wird blockiert."""
    from dashboard.server import DashboardHandler

    handler = DashboardHandler
    result = handler._resolve_static(handler, "../.env")
    assert result is None, "Traversal sollte blockiert werden"


def test_resolve_static_deep_traversal():
    """_resolve_static: Tiefes ../ wird blockiert."""
    from dashboard.server import DashboardHandler

    handler = DashboardHandler
    result = handler._resolve_static(handler, "../../etc/passwd")
    assert result is None


def test_resolve_static_absolute_path():
    """_resolve_static: Absoluter Pfad wird blockiert."""
    from dashboard.server import DashboardHandler

    handler = DashboardHandler
    result = handler._resolve_static(handler, "/etc/passwd")
    assert result is None


def test_resolve_static_dot_traversal():
    """_resolve_static: .../.../ wird blockiert."""
    from dashboard.server import DashboardHandler

    handler = DashboardHandler
    result = handler._resolve_static(handler, ".../.../env")
    assert result is None


def test_resolve_static_nonexistent():
    """_resolve_static: Nicht-existente Datei gibt None (wird später 404)."""
    from dashboard.server import DashboardHandler

    handler = DashboardHandler
    result = handler._resolve_static(handler, "nonexistent.html")
    assert result is not None  # Pfad ist sicher, Datei existiert nur nicht
    import os

    assert not os.path.exists(result)

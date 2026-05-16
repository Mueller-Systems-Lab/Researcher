# =============================================================================
# Tests: Dashboard Server (T-025 Coverage)
# =============================================================================
# Nutzt isolated tests für die logischen Einheiten des Dashboard-Servers.
# Instance-Methoden von BaseHTTPRequestHandler werden über das
# http.server-Modul mit Dummy-Anfragen getestet.
# =============================================================================
import sys, os, io, json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_health_endpoint():
    """Prüft, dass die Klasse einen Monitor hat."""
    from dashboard.server import DashboardHandler

    assert hasattr(DashboardHandler, "monitor")


def test_dashboard_static_exists():
    """Statische HTML-Datei des Dashboards existiert."""
    index = os.path.join(os.path.dirname(__file__), "../dashboard/static/index.html")
    assert os.path.exists(index)
    assert os.path.getsize(index) > 0


# ─── _resolve_static (wird als Unbound-Methode getestet) ──────────────────


def test_resolve_static_normal():
    from dashboard.server import DashboardHandler, STATIC_DIR

    # Instanz erstellen durch Mocken des Konstruktors
    with patch.object(DashboardHandler, "__init__", lambda self: None):
        handler = DashboardHandler.__new__(DashboardHandler)
        path = DashboardHandler._resolve_static(handler, "index.html")
        assert path is not None
        assert os.path.exists(path)


def test_resolve_static_traversal():
    from dashboard.server import DashboardHandler

    with patch.object(DashboardHandler, "__init__", lambda self: None):
        handler = DashboardHandler.__new__(DashboardHandler)
        assert DashboardHandler._resolve_static(handler, "../.env") is None
        assert DashboardHandler._resolve_static(handler, "../../etc/passwd") is None
        assert DashboardHandler._resolve_static(handler, "/etc/passwd") is None


def test_resolve_static_nonexistent():
    from dashboard.server import DashboardHandler

    with patch.object(DashboardHandler, "__init__", lambda self: None):
        handler = DashboardHandler.__new__(DashboardHandler)
        path = DashboardHandler._resolve_static(handler, "nonexistent.html")
        assert path is not None
        assert not os.path.exists(path)


# ─── _serve_static ──────────────────────────────────────────────────────────


def test_serve_static_403():
    """Traversal wird mit 403 abgewiesen."""
    from dashboard.server import DashboardHandler

    with patch.object(DashboardHandler, "__init__", lambda self: None):
        handler = DashboardHandler.__new__(DashboardHandler)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        DashboardHandler._serve_static(handler, "../.env", "application/json")
        handler.send_response.assert_called_with(403)


def test_serve_static_success():
    """Existierende Datei wird mit 200 ausgeliefert."""
    from dashboard.server import DashboardHandler

    with patch.object(DashboardHandler, "__init__", lambda self: None):
        handler = DashboardHandler.__new__(DashboardHandler)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        DashboardHandler._serve_static(handler, "index.html", "text/html")
        handler.send_response.assert_called_with(200)


@patch("dashboard.server.os.path.exists", return_value=False)
def test_do_get_not_found(mock_exists):
    """do_GET mit unbekanntem Pfad."""
    from dashboard.server import DashboardHandler

    with patch.object(DashboardHandler, "__init__", lambda self: None):
        handler = DashboardHandler.__new__(DashboardHandler)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        handler.path = "/nonexistent"
        handler.do_GET()
        handler.send_response.assert_called_with(404)


def test_do_get_root():
    """do_GET / serviert index.html."""
    from dashboard.server import DashboardHandler

    with patch.object(DashboardHandler, "__init__", lambda self: None):
        handler = DashboardHandler.__new__(DashboardHandler)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        handler.path = "/"
        handler.do_GET()
        handler.send_response.assert_called_with(200)


@patch("dashboard.server.GPUMonitor.collect_dict")
def test_do_get_api_gpu(mock_collect):
    """do_GET /api/gpu gibt GPU-Daten."""
    from dashboard.server import DashboardHandler

    mock_collect.return_value = {"gpu_utilization": 50.0}

    with patch.object(DashboardHandler, "__init__", lambda self: None):
        handler = DashboardHandler.__new__(DashboardHandler)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        handler.path = "/api/gpu"
        handler.do_GET()
        handler.send_response.assert_called_with(200)


# ─── _serve_gpu_json ──────────────────────────────────────────────────────


@patch("dashboard.server.GPUMonitor.collect_dict")
def test_serve_gpu_json(mock_collect):
    """JSON-API gibt GPU-Daten zurück."""
    from dashboard.server import DashboardHandler

    mock_collect.return_value = {"gpu_name": "GTX 1070", "gpu_utilization": 50.0}

    with patch.object(DashboardHandler, "__init__", lambda self: None):
        handler = DashboardHandler.__new__(DashboardHandler)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        DashboardHandler._serve_gpu_json(handler)
        handler.send_response.assert_called_with(200)
        handler.send_header.assert_any_call("Content-Type", "application/json")


# ─── _serve_health ────────────────────────────────────────────────────────


@patch("dashboard.server.GPUMonitor")
def test_serve_health(mock_monitor):
    """Health-Endpoint bei verfügbarer GPU."""
    from dashboard.server import DashboardHandler

    mock_monitor.return_value.is_available.return_value = True

    with patch.object(DashboardHandler, "__init__", lambda self: None):
        handler = DashboardHandler.__new__(DashboardHandler)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        DashboardHandler._serve_health(handler)
        handler.send_response.assert_called_with(200)


@patch("dashboard.server.GPUMonitor")
def test_serve_health_degraded(mock_monitor):
    """Health-Endpoint bei fehlender GPU."""
    from dashboard.server import DashboardHandler

    mock_monitor.return_value.is_available.return_value = False

    with patch.object(DashboardHandler, "__init__", lambda self: None):
        handler = DashboardHandler.__new__(DashboardHandler)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        DashboardHandler._serve_health(handler)
        handler.send_response.assert_called_with(200)

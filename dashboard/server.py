# =============================================================================
# Dashboard — HTTP + SSE Server
# =============================================================================
# Leichter HTTP-Server mit SSE-Unterstützung für Live-GPU-Daten.
# Serviert das Dashboard-Widget statisch und streamt GPU-Daten.
#
# Nutzung:
#   python -m dashboard.server  →  http://localhost:8888
# =============================================================================

import json
import logging
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import urlparse

from dashboard.gpu_monitor import GPUMonitor

logger = logging.getLogger(__name__)

DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8888"))
UPDATE_INTERVAL = 2.0  # Sekunden zwischen Updates
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.getenv("DASHBOARD_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
}


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP-Request-Handler für das GPU-Dashboard."""

    # Gemeinsamer Monitor (wiederverwendet)
    monitor = GPUMonitor()

    def do_GET(self):
        parsed = urlparse(self.path)
        request_path = parsed.path
        if request_path == "/" or request_path == "/index.html":
            self._serve_static("index.html", "text/html")
        elif request_path == "/api/gpu":
            self._serve_gpu_json()
        elif request_path == "/api/gpu/stream":
            self._serve_gpu_sse()
        elif request_path == "/health":
            self._serve_health()
        else:
            # Static files
            file_path = request_path.lstrip("/")
            if os.path.exists(os.path.join(STATIC_DIR, file_path)):
                content_type = "text/plain"
                if file_path.endswith(".css"):
                    content_type = "text/css"
                elif file_path.endswith(".js"):
                    content_type = "application/javascript"
                elif file_path.endswith(".png"):
                    content_type = "image/png"
                self._serve_static(file_path, content_type)
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Not Found"}).encode())

    def _send_cors_header(self):
        """Setzt CORS nur für erlaubte Origins; fremde Origins werden geblockt."""
        origin = self.headers.get("Origin")
        if not origin:
            return
        host_origin = f"http://{self.headers.get('Host', '')}"
        if origin == host_origin or origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _resolve_static(self, filename: str) -> Optional[str]:
        """Löst einen Dateinamen sicher innerhalb von STATIC_DIR auf.

        Verhindert Path-Traversal, indem der normalisierte Pfad
        auf STATIC_DIR-Präfix geprüft wird.

        Args:
            filename: Angeforderter Dateiname (relativ).

        Returns:
            Absoluter Pfad wenn sicher, None bei Traversal.
        """
        # Grundlegende Sicherheitsprüfung
        if ".." in filename or filename.startswith("/"):
            return None

        safe_path = os.path.realpath(os.path.join(STATIC_DIR, filename))
        static_real = os.path.realpath(STATIC_DIR)

        if not safe_path.startswith(static_real):
            return None
        return safe_path

    def _serve_static(self, filename: str, content_type: str):
        """Serviert eine statische Datei (mit Traversal-Schutz)."""
        safe_path = self._resolve_static(filename)
        if safe_path is None:
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Forbidden"}).encode())
            return

        if not os.path.exists(safe_path):
            self.send_response(404)
            self.end_headers()
            return

        try:
            with open(safe_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self._send_cors_header()
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            logger.error(f"Fehler beim Servieren von {filename}: {e}")
            self.send_response(500)
            self.end_headers()

    def _serve_gpu_json(self):
        """Serviert einmalige GPU-Daten als JSON."""
        data = self.monitor.collect_dict()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._send_cors_header()
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _serve_gpu_sse(self):
        """Serviert GPU-Daten als SSE-Stream (Server-Sent Events)."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self._send_cors_header()
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        try:
            while True:
                data = self.monitor.collect_dict()
                line = f"data: {json.dumps(data)}\n\n"
                self.wfile.write(line.encode())
                self.wfile.flush()
                time.sleep(UPDATE_INTERVAL)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Client disconnected
        except Exception as e:
            logger.debug(f"SSE-Client getrennt: {e}")

    def _serve_health(self):
        """Health-Check-Endpoint."""
        available = self.monitor.is_available()
        status = {
            "status": "ok" if available else "degraded",
            "gpu_monitor_available": available,
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(status).encode())

    def log_message(self, format, *args):
        """Weniger verbose Logging."""
        if "/api/gpu/stream" not in str(args):
            logger.debug(f"Dashboard: {format % args}")


def run_server(
    host: str = "127.0.0.1",
    port: int = DASHBOARD_PORT,
):
    """Startet den Dashboard-Server.

    Args:
        host: Bind-Addresse (default: 127.0.0.1).
        port: Port (default: 8888).
    """
    server = HTTPServer((host, port), DashboardHandler)
    logger.info("Dashboard gestartet: http://%s:%s", host, port)
    logger.info("Live-Stream:   http://%s:%s/api/gpu/stream", host, port)
    logger.info("JSON-API:      http://%s:%s/api/gpu", host, port)
    logger.info("Drücke Ctrl+C zum Beenden")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Dashboard-Server gestoppt")
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_server()

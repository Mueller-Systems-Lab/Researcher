#!/usr/bin/env python3
"""
Researcher — Combined Server: GPT Researcher Web-UI + GPU Dashboard
====================================================================
Startet die GPT-Researcher FastAPI-App und mountet das GPU-Dashboard
unter /dashboard.

Nutzung:
  python start-with-dashboard.py                     # Port 8000
  python start-with-dashboard.py --port 8080         # Anderer Port
  python start-with-dashboard.py --no-gpu            # Ohne GPU-Dashboard
"""

import argparse
import importlib.util
import logging
import os
import sys
from pathlib import Path

# Projekt-Root
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

# GPT Researcher App importieren
sys.path.insert(0, str(ROOT / "gpt_researcher"))
from backend.server.app import app as gpt_app
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles


def create_combined_app(enable_gpu: bool = True) -> FastAPI:
    """Erstellt eine kombinierte App mit GPT Researcher + GPU Dashboard."""

    # Dashboard-Routen direkt in die GPT-Researcher-App einhängen
    @gpt_app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard_page():
        """GPU/VRAM Live-Dashboard als Sub-Seite von GPT Researcher."""
        dashboard_html = ROOT / "dashboard" / "static" / "index.html"
        if dashboard_html.exists():
            html = dashboard_html.read_text(encoding="utf-8")
            # Basis-URL anpassen für eingebetteten Betrieb
            html = html.replace(
                "EventSource('/api/gpu/stream')",
                "EventSource('/dashboard/api/gpu/stream')",
            )
            html = html.replace(
                "src='/api/gpu/stream'", "src='/dashboard/api/gpu/stream'"
            )
            return html
        return HTMLResponse("<h1>Dashboard nicht gefunden</h1>", status_code=404)

    @gpt_app.get("/dashboard/api/gpu", include_in_schema=False)
    async def dashboard_gpu_json():
        """GPU-Daten als JSON (eingebettet)."""
        from dashboard.gpu_monitor import GPUMonitor

        monitor = GPUMonitor()
        return JSONResponse(monitor.collect_dict())

    @gpt_app.get("/dashboard/api/gpu/stream", include_in_schema=False)
    async def dashboard_gpu_stream(request: Request):
        """GPU-Daten als SSE-Stream (eingebettet)."""
        import asyncio
        import json
        from dashboard.gpu_monitor import GPUMonitor

        monitor = GPUMonitor()

        async def event_generator():
            try:
                while True:
                    data = monitor.collect_dict()
                    yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                pass

        from fastapi.responses import StreamingResponse

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )

    @gpt_app.get("/dashboard/health", include_in_schema=False)
    async def dashboard_health():
        """Health-Check für Dashboard."""
        from dashboard.gpu_monitor import GPUMonitor

        return JSONResponse(
            {
                "status": "ok" if GPUMonitor.is_available() else "degraded",
            }
        )

    logger.info("GPU-Dashboard unter /dashboard eingebettet")
    return gpt_app


def main():
    parser = argparse.ArgumentParser(
        description="Researcher — GPT Researcher + GPU Dashboard"
    )
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--no-gpu", action="store_true", help="GPU-Dashboard deaktivieren"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("  Researcher — Combined Server")
    print("=" * 60)
    print(f"  GPT Researcher: http://{args.host}:{args.port}")
    print(f"  GPU-Dashboard:  http://{args.host}:{args.port}/dashboard")
    print(f"  GPU-Daten:      http://{args.host}:{args.port}/dashboard/api/gpu")
    print("=" * 60)

    app = create_combined_app(enable_gpu=not args.no_gpu)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

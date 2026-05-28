# Live-Test-Plan — Researcher GPU-Dashboard

## Ziel

Beweisen, dass das GPU-Dashboard in der echten App läuft — per Screenshot, Log und Browser-Test.
Kein Mock: echter `dashboard/server.py`-Server, echter Chromium-Browser, echte HTTP-Requests.

## Getestete Flows

| # | Flow | Viewport | Test-Typ | Akzeptanz |
|---|---|---|---|---|
| 1 | Dashboard Screenshot | Desktop 1280x720 | Browser | Screenshot existiert, > 0 Bytes |
| 2 | Dashboard Health Endpoint | — | HTTP | Status 200, JSON `{"status":"ok"}` |
| 3 | HTML-Struktur (GPU Widgets) | — | HTML-Parse | Alle 5 Widget-IDs vorhanden |
| 4 | GPU Widget Accessibility | — | HTML-Check | `lang="de"`, `viewport`, `aria-label` |
| 5 | GPU Metrics (oder Fallback) | Desktop 1280x720 | Browser | Werte sichtbar oder Fallback-Meldung |
| 6 | SSE Event Stream | Desktop 1280x720 | Browser | EventSource verbindet, Daten empfangen |
| 7 | Visual Regression Screenshot | Desktop 1280x720 | Browser | Pixel-Vergleich mit Baseline < 0.1% Diff |

## Viewport-Matrix

| Name | Breite | Höhe | Status |
|---|---|---|---|
| Desktop | 1280 | 720 | ✅ Aktiv |
| Desktop-Large | 1920 | 1080 | ⬜ Geplant |
| Tablet | 768 | 1024 | ✅ Aktiv (Issue #42) |
| Mobile | 375 | 812 | ✅ Aktiv (Issue #42) |

Viewport-Tests in `tests/playwright/test_dashboard_viewports.py`:
- `test_dashboard_loads_in_viewport` — Lädt und zeigt Metriken in jedem Viewport
- `test_dashboard_viewport_screenshot` — Screenshot + Baseline-Visual-Regression
- `test_dashboard_responsive_layout` — Karten sichtbar, nicht überlappend, Legende sichtbar

## Fehlerfall-Tests

| Fehlerfall | Erwartetes Verhalten | Status |
|---|---|---|
| Dashboard-Server nicht erreichbar | pytest.skip / ConnectionError | ✅ Implizit |
| GPU nicht verfügbar (nvidia-smi fehlt) | Freundliche Fallback-Meldung | ⬜ Geplant (Issue #44) |
| SSE reconnect | Automatischer Reconnect + Meldung | ⬜ Geplant (Issue #44) |

## Akzeptanzkriterien (je Flow)

### Flow 1: Dashboard Screenshot
- GIVEN Dashboard-Server läuft auf Port 8889
- WHEN Playwright die URL `http://127.0.0.1:8889` öffnet
- THEN ist das Element `#gpu-name` sichtbar
- AND ein Screenshot wird in `qa/live/artifacts/screenshots/dashboard.png` gespeichert

### Flow 2: Dashboard Health
- GIVEN Dashboard-Server läuft
- WHEN `/health` Endpoint aufgerufen wird
- THEN Status-Code ist 200
- AND Response enthält `{"status": "ok"}`

## Nicht-Ziele dieses Testplans

- Keine GPT-Researcher-UI-Tests (externes Paket)
- Keine Crawler-Tests (separat, Issue #43)
- Keine Darknet-Suche-Tests

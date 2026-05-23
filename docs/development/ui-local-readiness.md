# UI Local Readiness

## Entscheidung

**UI PARTIAL**

## Begründung

Researcher besitzt ein funktionierendes lokales GPU-Dashboard mit Live-Metriken (SSE-Stream). Das Dashboard startet zuverlässig, lädt im Browser und zeigt GPU-Daten korrekt an. Es fehlt jedoch ein Research-Flow (Query-Eingabe → Report anzeigen). Die Research-Pipeline existiert als CLI/API, ist aber nicht über das UI bedienbar.

## Gefundene UI-Komponenten

| Komponente | Pfad | Status |
|---|---|---|
| GPU-Dashboard Server | `dashboard/server.py` (203 LOC) | ✅ Läuft |
| Dashboard HTML | `dashboard/static/index.html` (233 LOC) | ✅ Lädt |
| GPU-Monitor | `dashboard/gpu_monitor.py` | ✅ Live-Daten |
| Combined Server | `scripts/start-with-dashboard.py` | ✅ Startbar |
| Playwright Tests | `tests/playwright/` (5 Dateien) | ✅ 25+ passing |
| Accessibility Tests | `tests/playwright/test_dashboard_accessibility.py` | ✅ 7/7 |
| E2E Pipeline Test | `tests/e2e/test_full_research_flow.py` | ✅ Mock-basiert |

## Startbefehle

```bash
# GPU-Dashboard (Standalone, Port 8888)
python3 -m dashboard.server

# Combined Server (GPT Researcher + Dashboard, Port 8000)  
python3 scripts/start-with-dashboard.py
python3 scripts/start-with-dashboard.py --port 8080
```

## Lokale URL

- Dashboard: `http://127.0.0.1:8888`
- Combined: `http://127.0.0.1:8000`

## Screenshot

Pfad: `qa/ui/ui-smoke.png`

## Playwright Smoke

| Prüfung | Ergebnis |
|---|---|
| Seite lädt | ✅ HTTP 200 |
| HTTP Status | ✅ 200 |
| Body nicht leer | ✅ 200 Zeichen |
| Console Errors | ✅ 0 Errors |
| Screenshot erzeugt | ✅ qa/ui/ui-smoke.png |
| GPU-Metriken live | ✅ GTX 1070, 9% Util, VRAM, Temp |
| Accessibility (ARIA) | ✅ 7/7 Tests |

## UI-Funktionsumfang

| Funktion | Status |
|---|---|
| Runtime-Status sichtbar | ✅ GPU, VRAM, Temperatur |
| SSE Live-Stream | ✅ /api/gpu/stream |
| JSON API | ✅ /api/gpu |
| Query-Eingabe | ❌ Nicht vorhanden |
| Research starten | ❌ Nicht über UI |
| Report anzeigen | ❌ Nur CLI |
| Evaluation anzeigen | ❌ Nur CLI |
| Fehleranzeige | ✅ GPU-Fehler via SSE |

## Playwright-Teststatus (lokal)

```bash
RUN_PLAYWRIGHT_TESTS=true pytest tests/playwright/ -v
```

- **Passed**: 25 Tests (Browser-Smoke, Accessibility 7/7, GPU-Monitor)
- **Failed**: 2 (SSE-Stream-Test, XSS-Assertion-Präfix)
- **Skipped**: ~10 (RUN_PLAYWRIGHT_TESTS nicht gesetzt)
- **Kein** "Playwright Python package is not installed"-Fehler mehr

## Bekannte Grenzen

1. Kein Research-Flow im UI — nur GPU-Monitoring
2. Combined Server benötigt GPT-Researcher Submodul (FastAPI)
3. SSE-Stream kann `networkidle`-Wait in Playwright blockieren
4. XSS-Test-Assertion erwartet exakten String (Präfix-Fix nötig)

## Nächste UI-Issues

1. `[UI/MVP] Minimal Research Dashboard: Query → Run → Report List`
2. `[UI] Runtime Status Panel: Ollama + SearXNG Status`
3. `[UI] Report Viewer + Evaluation Summary`
4. `[FIX] Playwright SSE-Test + XSS-Assertion`

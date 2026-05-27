# UI Local Readiness

## Entscheidung

**UI PARTIAL**

## Stand 2026-05-27

GPU-Dashboard ✅ | GPT Researcher Backend startbar ✅ | LLM-Stabilität ✅ (Gemma 4)

## Begründung

Researcher besitzt ein funktionierendes lokales GPU-Dashboard (Port 8888) und das GPT-Researcher-Frontend aus dem Submodul ist über den Backend-Server (Port 8000) erreichbar. Die `.env`-Konfiguration ist vollständig Local-First (llama-server + SearXNG, keine Cloud-Keys nötig). Mit dem Umstieg auf Gemma 4 OBLITERATED (~3.8 GB VRAM, eigenständiger llama-server) läuft der Chat-Modell-Server stabil und startet in ~5s. Der volle Query→Research→Report-Flow kann jetzt getestet werden.

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

1. ~~LLM-Modell-Instabilität: qwen3.5 crasht~~ ✅ **Behoben**: Gemma 4 läuft stabil
2. ~~Backend-Startup: 120s+ ohne HTTP-ready~~ ✅ **Behoben**: llama-server startet in ~5s
3. SSE-Stream kann `networkidle`-Wait in Playwright blockieren
4. XSS-Test-Assertion erwartet exakten String (Präfix-Fix nötig)

## GPT Researcher Submodul

- `gpt_researcher/frontend/`: Lightweight HTML + NextJS
- `gpt_researcher/backend/`: FastAPI-Server
- Start: `python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --app-dir gpt_researcher`
- Frontend-URL: `http://127.0.0.1:8000`
- `.env`: FAST_LLM=ollama, RETRIEVER=searx — **keine Cloud-Keys nötig**

## Nächste UI-Issues

1. `[UI/MVP] Minimal Research Dashboard: Query → Run → Report List`
2. `[UI] Runtime Status Panel: Ollama + SearXNG Status`
3. `[UI] Report Viewer + Evaluation Summary`
4. `[FIX] Playwright SSE-Test + XSS-Assertion`

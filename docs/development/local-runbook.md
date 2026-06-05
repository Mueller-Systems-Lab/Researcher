# Researcher Local Runbook

## Local UI Status: **UI PARTIAL**

GPT Researcher ist lokal startbar und die Phase-8-Qualitätstests sind vorbereitet. Der volle Query→Research→Report-Flow sollte mit `make acceptance` validiert werden; für Dashboard-Screenshots wird der SSE-freie Static-Fallback genutzt.

## Phase 8 Architektur

| Dienst | Port | Backend | Rolle |
|---|---:|---|---|
| Ollama | 11434 | `ollama serve` | Embeddings only (`nomic-embed-text`) |
| llama-server | 8082 | `serve_qwen3.5_uncensored.sh` | Qwen3.5 Chat/Extraction, OpenAI-kompatibel |
| SearXNG | 8090 | Docker Compose | Metasuche |
| GPT Researcher | 28202 | Docker (`gptresearcher/gpt-researcher`) | Research backend |
| Dashboard | 8888 | `python3 -m dashboard.server` | GPU monitor + JSON/SSE |

## Autostart / systemd

### Service-Dateien

| Datei | Scope | Zweck |
|---|---|---|
| `researcher-ollama.service` | user | Ollama Embedding Service |
| `researcher-llama.service` | user | llama-server Qwen3.5 |
| `researcher-dashboard.service` | user | GPU Dashboard |
| `researcher-searxng.service` | system | SearXNG Metasearch |
| `researcher-gptr.service` | system | GPT Researcher Backend |

### Launcher

```bash
./start_all_services.sh
./start_all_services.sh --status
./start_all_services.sh --stop
```

Das Launcher-Skript startet alle 5 Kernservices mit Healthchecks, Retry-Logik und Logging unter `/var/log/researcher/`.

## Startbefehle

### GPU-Dashboard (Port 8888)
```bash
python3 -m dashboard.server
# http://127.0.0.1:8888
```

### Qwen3.5 llama-server (Port 8082)
Das Chat-/Extraction-Modell. Läuft eigenständig via llama.cpp, **unabhängig von Ollama**.

```bash
./serve_qwen3.5_uncensored.sh
# http://127.0.0.1:8082
# Alias im Server: qwen3.5-uncensored
# Fokus: Chat/Extraction, strukturiertes Output-Format
```

### GPT Researcher Backend (Port 8000)
```bash
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --app-dir gpt_researcher
# http://127.0.0.1:8000
```

**Hinweis:** Der erste Startup ist schnell (~5s), da kein LLM-Laden nötig — der llama-server läuft parallel.

### NextJS Frontend (Port 3000, optional)
```bash
cd gpt_researcher/frontend/nextjs
npm install
NEXT_PUBLIC_GPTR_API_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000
# http://127.0.0.1:3000
```

## Lokale Dienste

| Dienst | Port | Status | Zweck |
|---|---:|---|---|
| llama-server (Qwen3.5) | 8082 | ✅ | Chat/Extraction (OpenAI-kompatibel, eigenständig) |
| Ollama | 11434 | ✅ | Nur Embeddings (`nomic-embed-text`) |
| SearXNG | 8090 | ✅ | Metasuche (Docker Compose) |
| GPT Researcher | 28202 | ✅ | Research Backend (Docker, host networking) |
| Dashboard | 8888 | ✅ | GPU-Monitor (SSE + Static Fallback) |
| Tor (Proxy) | 9050 | ✅ | Optionaler Darknet-Zugriff |
| ChromaDB | — | ✅ | Vektordatenbank |

## Modelle

```bash
# Embedding (via Ollama):
ollama list | grep nomic-embed-text

# Chat / Extraction (via llama-server, unabhängig von Ollama):
# Läuft als eigener Prozess: ./serve_qwen3.5_uncensored.sh
# Port 8082, Alias: qwen3.5-uncensored
```

| Modell | Typ | Backend | Größe | Status |
|---|---|---|---|---|
| qwen3.5-uncensored | Chat/Extraction | llama-server (Port 8082) | ~5.3 GB VRAM | ✅ Stabil |
| nomic-embed-text | Embedding | Ollama (Port 11434) | 274 MB | ✅ Stabil |

### Historisch (ersetzt)
| qwen3.5-uncensored-no-thinking | Chat (deprecated) | Ollama | 6.6 GB | ❌ Instabil — ersetzt durch Qwen3.5 |

## Acceptance Gate

```bash
make acceptance
```

Das Ziel nutzt `scripts/ci_acceptance.py` und prüft:

1. alle 5 Services per HTTP-Healthcheck
2. Research-Pipeline (`/report/`)
3. Report-Qualität (Größe, Quellen, Claims)
4. SearXNG-Direktabfrage

Weitere Modi:

```bash
python3 scripts/ci_acceptance.py --skip-research
python3 scripts/ci_acceptance.py --json-output
```

## Optional: LLM Smoke Test

Für isolierte LLM-Validierung:

```bash
LM_STUDIO_LIVE_TEST=1 \
LOCAL_LLM_ENDPOINT=http://127.0.0.1:8082 \
LOCAL_LLM_MODEL=qwen3.5-uncensored \
python -m cli.llm_smoke
```

Der Check ist opt-in und prüft Endpoint, Modell, Generierung und Ausgabe-Marker.

## Known Issues

1. **SSE blockiert Playwright**: `networkidle`-Wait hängt wegen SSE-Stream; für Screenshots den Static-Fallback nutzen.
2. **Qwen3.5 Precision Trap**: `-ctk f32 -ctv f32` ist auf Pascal (GTX 1070) nötig, sonst droht garbled Output.
3. **ChromaDB 1.5.9 count()**: Gibt `-1` statt `0` bei fehlender Verbindung (lokal in `vectordb/store.py` abgefangen).
4. **Ollama nur für Embeddings**: Chat/Extraction läuft vollständig über llama-server.
5. **SearXNG-Engines**: Phase 8 hat 10+ Suchmaschinen aktiviert; bei CAPTCHA-Risiko einzelne Engines in `searxng/settings.yml` deaktivieren.

## Dashboard Screenshot (Static Fallback)

Für Playwright-Screenshots gibt es eine SSE-freie statische Fallback-Seite:

http://127.0.0.1:8888/static-fallback.html

Datei: `dashboard/static/static-fallback.html`

Die Seite nutzt einen einmaligen `/api/gpu` JSON-Fetch statt des persistierenden SSE-Streams.
Siehe `docs/development/dashboard-screenshot-fix.md`.

## UI Smoke Test

```bash
UI_BASE_URL=http://127.0.0.1:8000 \
UI_TIMEOUT_SECONDS=120 \
python3 scripts/ui_smoke.py
```

## Playwright Tests

```bash
RUN_PLAYWRIGHT_TESTS=true python3 -m pytest tests/playwright/ -v
```

## Evaluation

```bash
make research-evaluate
```

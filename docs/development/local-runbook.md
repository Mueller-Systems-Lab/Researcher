# Researcher Local Runbook

## Local UI Status: **UI PARTIAL**

GPT Researcher Submodul ist vorhanden und grundsätzlich startbar. Der volle Query→Research→Report-Flow konnte wegen historischer LLM-Ladezeiten (qwen3.5-Ära) noch nicht vollständig verifiziert werden. Mit dem Umstieg auf Qwen3.5-Uncensored (eigener llama-server, ~3.8 GB VRAM) ist die Runtime deutlich stabiler.

## Startbefehle

### GPU-Dashboard (Port 8888)
```bash
python3 -m dashboard.server
# http://127.0.0.1:8888
```

### Qwen3.5-Uncensored Chat-Server (Port 8082)
Das Chat-/Summary-Modell. Läuft eigenständig via llama.cpp, **unabhängig von Ollama**.

```bash
./serve_qwen3.5_obliterated_researcher.sh
# http://127.0.0.1:8081
# Alias im Server: qwen3.5-uncensored
# VRAM: ~3.8 GB von 8 GB
```

### Qwen3.5 Uncensored Chat-/Extraction-Server (Port 8082)
Das Co-Primary-Modell für schnelle Extraktion (45 tok/s) und strukturierte Ausgaben. Läuft ebenfalls eigenständig via llama.cpp.

```bash
./serve_qwen3.5_uncensored.sh
# http://127.0.0.1:8082
# Alias im Server: qwen3.5-uncensored
# Fokus: Chat/Extraction, Scraping
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
|--------|------|--------|-------|
| llama-server (Qwen3.5) | 8081 | ✅ | Chat/Summary (llama.cpp, eigenständig) |
| llama-server (Qwen3.5) | 8082 | ✅ | Chat/Extraction (≈45 tok/s, llama.cpp, eigenständig) |
| Ollama | 11434 | ✅ | Nur noch für Embedding (nomic-embed-text) |
| SearXNG (Suche) | 8080 | ✅ | Metasuchmaschine |
| Tor (Proxy) | 9050 | ✅ | Darknet-Zugriff (optional) |
| ChromaDB | — | ✅ | Vektordatenbank |

Qwen3.5 und Qwen3.5 können parallel auf getrennten Ports laufen; je nach Aufgabe wird das passende Modell gestartet.

## Modelle

```bash
# Embedding (via Ollama):
ollama list | grep nomic-embed-text

# Chat (via llama-server, unabhängig von Ollama):
# Läuft als eigener Prozess: ./serve_qwen3.5_obliterated_researcher.sh
# Port 8082, Alias: qwen3.5-uncensored

# Extraction/Chat (via llama-server, unabhängig von Ollama):
# Läuft als eigener Prozess: ./serve_qwen3.5_uncensored.sh
# Port 8082, Alias: qwen3.5-uncensored
```

| Modell | Typ | Backend | Größe | Status |
|--------|-----|---------|-------|--------|
| qwen3.5-uncensored | Chat/Summary | llama-server (Port 8082) | ~3.8 GB VRAM | ✅ Stabil |
| qwen3.5-uncensored | Chat/Extraction | llama-server (Port 8082) | ~5.3 GB VRAM | ✅ Co-Primary |
| nomic-embed-text | Embedding | Ollama (Port 11434) | 274 MB | ✅ Stabil |

### Historisch (ersetzt)
| qwen3.5-uncensored-no-thinking | Chat (deprecated) | Ollama | 6.6 GB | ❌ Instabil — ersetzt durch Qwen3.5 |

## Known Issues

1. **SSE blockiert Playwright**: `networkidle`-Wait hängt wegen SSE-Stream
2. **Qwen3.5 Precision Trap**: `-ctk f32 -ctv f32` zwingend erforderlich auf Pascal (GTX 1070), da FP16-KV-Cache bei Qwen3.5 zu garbled Output führt
3. **ChromaDB 1.5.9 count()**: Gibt `-1` statt `0` bei fehlender Verbindung (lokal in `vectordb/store.py` abgefangen)
4. **Keine Ollama-Abhängigkeit für Chat**: Qwen3.5 läuft eigenständig via llama.cpp — Ollama wird nur noch für nomic-embed-text benötigt

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

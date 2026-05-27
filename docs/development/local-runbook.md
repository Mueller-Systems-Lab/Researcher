# Researcher Local Runbook

## Local UI Status: **UI PARTIAL**

GPT Researcher Submodul ist vorhanden und grundsätzlich startbar. Der volle Query→Research→Report-Flow konnte wegen historischer LLM-Ladezeiten (qwen3.5-Ära) noch nicht vollständig verifiziert werden. Mit dem Umstieg auf Gemma 4 OBLITERATED (eigener llama-server, ~3.8 GB VRAM) ist die Runtime deutlich stabiler.

## Startbefehle

### GPU-Dashboard (Port 8888)
```bash
python3 -m dashboard.server
# http://127.0.0.1:8888
```

### Gemma 4 OBLITERATED Chat-Server (Port 8081)
Das Chat-/Summary-Modell. Läuft eigenständig via llama.cpp, **unabhängig von Ollama**.

```bash
./serve_gemma4_obliterated_researcher.sh
# http://127.0.0.1:8081
# Alias im Server: gemma4-obliterated
# VRAM: ~3.8 GB von 8 GB
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
| llama-server (Gemma 4) | 8081 | ✅ | Chat/Summary (llama.cpp, eigenständig) |
| Ollama | 11434 | ✅ | Nur noch für Embedding (nomic-embed-text) |
| SearXNG (Suche) | 8080 | ✅ | Metasuchmaschine |
| Tor (Proxy) | 9050 | ✅ | Darknet-Zugriff (optional) |
| ChromaDB | — | ✅ | Vektordatenbank |

## Modelle

```bash
# Embedding (via Ollama):
ollama list | grep nomic-embed-text

# Chat (via llama-server, unabhängig von Ollama):
# Läuft als eigener Prozess: ./serve_gemma4_obliterated_researcher.sh
# Port 8081, Alias: gemma4-obliterated
```

| Modell | Typ | Backend | Größe | Status |
|--------|-----|---------|-------|--------|
| gemma4-obliterated | Chat/Summary | llama-server (Port 8081) | ~3.8 GB VRAM | ✅ Stabil |
| nomic-embed-text | Embedding | Ollama (Port 11434) | 274 MB | ✅ Stabil |

### Historisch (ersetzt)
| qwen3.5-uncensored-no-thinking | Chat (deprecated) | Ollama | 6.6 GB | ❌ Instabil — ersetzt durch Gemma 4 |

## Known Issues

1. **SSE blockiert Playwright**: `networkidle`-Wait hängt wegen SSE-Stream
2. **Gemma 4 Precision Trap**: `-ctk f32 -ctv f32` zwingend erforderlich auf Pascal (GTX 1070), da FP16-KV-Cache bei Gemma 4 zu garbled Output führt
3. **ChromaDB 1.5.9 count()**: Gibt `-1` statt `0` bei fehlender Verbindung (lokal in `vectordb/store.py` abgefangen)
4. **Keine Ollama-Abhängigkeit für Chat**: Gemma 4 läuft eigenständig via llama.cpp — Ollama wird nur noch für nomic-embed-text benötigt

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

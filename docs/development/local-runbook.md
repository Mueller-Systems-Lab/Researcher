# Researcher Local Runbook

## Local UI Status: **UI PARTIAL**

GPT Researcher Submodul ist vorhanden und grundsätzlich startbar. Der volle Query→Research→Report-Flow konnte wegen lokaler LLM-Ladezeiten und Modell-Instabilität noch nicht vollständig verifiziert werden.

## Startbefehle

### GPU-Dashboard (Port 8888)
```bash
python3 -m dashboard.server
# http://127.0.0.1:8888
```

### GPT Researcher Backend (Port 8000)
```bash
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --app-dir gpt_researcher
# http://127.0.0.1:8000
```

**Hinweis:** Der erste Start kann 40-120s dauern, da lokale LLM-Modelle (qwen3.5 ~6.6GB) geladen werden müssen.

### NextJS Frontend (Port 3000, optional)
```bash
cd gpt_researcher/frontend/nextjs
npm install
NEXT_PUBLIC_GPTR_API_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000
# http://127.0.0.1:3000
```

## Lokale Dienste

| Dienst | Port | Status |
|--------|------|--------|
| Ollama (LLM) | 11434 | ✅ |
| SearXNG (Suche) | 8080 | ✅ |
| Tor (Proxy) | 9050 | ✅ |
| ChromaDB | — | ✅ |

## Chat-Modelle

```bash
ollama list
```

| Modell | Größe | Status |
|--------|-------|--------|
| qwen3.5-uncensored-no-thinking:latest | 6.6 GB | ⚠️ Instabil |
| qwen3.5:9b | 6.6 GB | ⚠️ Instabil |
| nomic-embed-text:latest | 274 MB | ✅ |

## Known Issues

1. **LLM-Modell-Instabilität**: qwen3.5-Modelle crashen gelegentlich ("llama runner process has terminated")
2. **Startup-Zeit**: Backend braucht 40-120s bis HTTP-ready wegen Modell-Laden
3. **SSE blockiert Playwright**: `networkidle`-Wait hängt wegen SSE-Stream

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

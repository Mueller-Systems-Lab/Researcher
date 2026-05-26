# Issue DR-08 — Local Model Runtime Guard für Deep Research

## Ziel

Sichere den Deep-Research-Loop gegen instabile lokale LLM-Runtime ab, insbesondere mit unzensiertem Qwen3.5-kompatiblem Modell auf GTX 1070.

---

# Kontext

Deep Research erzeugt lange Laufzeiten und viele LLM-Aufrufe. Ein Modell, das beim ersten Prompt garbled Output erzeugt oder crasht, darf keinen Research-Run starten.

---

# Betroffene Module

Erweitert:

```text
scripts/runtime_smoke.py
config/ollama_models.py
config/local_llm_runtime.py
docs/runtime/qwen35-uncensored-gtx1070-runtime.md
tests/test_local_llm_runtime_guard.py
```

---

# Anforderungen

Runtime Guard prüft:

```text
model present
endpoint reachable
minimal generation works
output not garbled
latency measured
max context supported
provider local-only
cloud disabled
```

---

# Provider

Erlaubt:

```text
llama_server on 127.0.0.1
ollama embeddings on 127.0.0.1
```

Nicht erlaubt:

```text
external OpenAI base URL
Tavily
Anthropic
unknown cloud endpoint
```

---

# Statusklassen

```text
LOCAL_LLM_READY
LOCAL_LLM_PARTIAL
LOCAL_LLM_BLOCKED
MODEL_GARBLED
MODEL_TIMEOUT
MODEL_CRASH
CLOUD_BLOCKED
LOCAL_OPENAI_COMPAT_ALLOWED
```

---

# Tests

- localhost OpenAI-compatible erlaubt
- externe OpenAI URL blockiert
- minimal generation OK
- garbled detector erkennt kaputten Output
- timeout wird sauber klassifiziert
- qwen3.5 alias bleibt erhalten
- kein 7B fallback

---

# Akzeptanzkriterien

Given local llama-server antwortet stabil  
When runtime guard läuft  
Then Status ist LOCAL_LLM_READY.

Given Modell garbled Output erzeugt  
When guard läuft  
Then Status ist MODEL_GARBLED und Deep Research startet nicht.

Given Cloud endpoint gesetzt  
When guard läuft  
Then Start wird blockiert.

---

# Validierung

```bash
python3 -m pytest tests/test_local_llm_runtime_guard.py -q
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
make quality
make coverage
```

---

# Nicht-Ziele

- kein Modell-Download
- kein Treiberwechsel
- keine Cloud

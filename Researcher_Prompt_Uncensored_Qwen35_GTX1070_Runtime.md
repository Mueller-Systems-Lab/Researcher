# Researcher — Prompt: Unzensiertes Qwen3.5-kompatibles Modell auf GTX 1070 stabil betreiben

## Rolle

Du bist ein Senior Local-LLM Runtime Engineer, llama.cpp Engineer, Model Validation Engineer und Researcher Integration Agent.

Du arbeitest im Repository `xxammaxx/Researcher`.

Dein Ziel ist NICHT, auf ein zensiertes oder kleineres Ersatzmodell auszuweichen.

Dein Ziel ist, ein **unzensiertes Qwen3.5-kompatibles Modell** lokal stabil auf einer **NVIDIA GTX 1070 mit 8 GB VRAM** zu betreiben und Researcher/GPT-Researcher darauf zu konfigurieren.

---

# Harte Nutzeranforderung

Es ist zwingend erforderlich:

```text
unzensiertes Modell
Qwen3.5-kompatibel / qwen3.5-uncensored-no-thinking-kompatibel
lokal
keine Cloud
lauffähig auf GTX 1070 8 GB
für Researcher / GPT-Researcher UI nutzbar
```

Nicht akzeptabel:

```text
7B-Fallback als endgültige Lösung
zensiertes Modell
Cloud-API
OpenAI/Tavily/Anthropic als Pflicht
Modellwechsel ohne Uncensored-Eigenschaft
```

---

# Validierte externe Fakten

## LuffyTheFox-Kandidat

Das Hugging-Face-Modell:

```text
LuffyTheFox/Qwen3.5-9B-Claude-4.6-Opus-Uncensored-Distilled-GGUF
```

ist ein realer Kandidat.

Validierte Fakten:

- Repository existiert auf Hugging Face.
- Tags/Metadaten enthalten:
  - Text Generation
  - GGUF
  - Qwen / Qwen3.5
  - uncensored
  - Not-For-All-Audiences
  - License: Apache-2.0
- Die Hugging-Face-Seite dokumentiert `Qwen3.5-9B.Q4_K_M.gguf`.
- Die Seite zeigt Nutzung mit `llama.cpp` / `llama-server`.
- Beispiel von Hugging Face:
  ```bash
  llama-server -hf LuffyTheFox/Qwen3.5-9B-Claude-4.6-Opus-Uncensored-Distilled-GGUF:Q4_K_M
  ```

## llama.cpp / llama-server

`llama.cpp` unterstützt GGUF und lokale Inferenz. Der `llama-server` stellt einen lokalen OpenAI-kompatiblen Server bereit, der über `/v1/chat/completions` angesprochen werden kann.

## GTX 1070

Die GTX 1070 hat 8 GB GDDR5 VRAM. Deshalb ist für ein 9B-Modell realistisch:

```text
Q4_K_M bevorzugen
Q8_0 vermeiden
GPU-Offload schrittweise testen
nicht alle Layer blind auf GPU laden
```

---

# Ausgangsproblem

Das bisherige HauhauCS-Modell beziehungsweise `qwen3.5-uncensored-no-thinking` erzeugt über mehrere Konfigurationen hinweg garbled Output oder crasht über Ollama.

Hypothesen:

1. HauhauCS-GGUF ist beschädigt, inkompatibel oder falsch quantisiert.
2. Ollama-CGO-Runner ist mit CUDA 13 / NVIDIA 580.x und größeren GGUF-Modellen instabil.
3. Ein direkt getestetes, sauberes GGUF über `llama-server` kann das Problem umgehen.

Wichtig:

```text
HauhauCS ist verdächtig, aber nicht endgültig als korrupt bewiesen.
Nicht löschen.
Nicht überschreiben.
Erst sauberen Kandidaten validieren.
```

---

# Oberstes Ziel

Finde und validiere einen stabilen Runtime-Pfad:

```text
LuffyTheFox Qwen3.5 9B Uncensored GGUF
→ llama-server
→ lokaler OpenAI-kompatibler Endpoint
→ Researcher / GPT-Researcher UI
→ Report
→ Evaluation
```

Zielentscheidung:

```text
UNCENSORED_QWEN35_GTX1070_READY
```

oder:

```text
UNCENSORED_QWEN35_GTX1070_PARTIAL
```

oder:

```text
UNCENSORED_QWEN35_GTX1070_BLOCKED
```

---

# Harte Nicht-Ziele

Dieses Issue darf NICHT:

- ein zensiertes Modell als Lösung akzeptieren
- ein 7B-Modell als endgültige Lösung akzeptieren
- Cloud-Fallbacks aktivieren
- externe OpenAI/Tavily/Anthropic APIs erforderlich machen
- NVIDIA-Treiber automatisch ändern
- Ollama PR #16031 sofort als erste Lösung bauen
- alte Modelle löschen
- HauhauCS überschreiben
- Quality Gates lockern
- Tests löschen
- Release-Tag erstellen
- GitHub Release veröffentlichen
- gefährliche oder illegale Testprompts verwenden

---

# Sichere Testprompts

Nur harmlose Funktionstests verwenden:

```text
Antworte nur mit OK.
Was ist eine Suchmaschine?
Fasse in einem Satz zusammen, was lokale KI bedeutet.
Schreibe einen neutralen Satz über Open-Source-Software.
```

Nicht verwenden:

```text
Exploit
Malware
Credentials
Darknet
Bypass
illegale Anleitungen
Waffen
Phishing
```

Das Modell darf unzensiert sein, aber die Validierung muss harmlos bleiben.

---

# Phase 0 — Systemzustand erfassen

Führe aus:

```bash
git branch --show-current
git rev-parse --short HEAD
git status --short

nvidia-smi || true
ollama --version || true
ollama list || true
```

Dokumentiere:

| Bereich | Wert |
|---|---|
| Branch | |
| Commit | |
| GPU | GTX 1070 |
| VRAM | 8 GB |
| NVIDIA Driver | |
| CUDA laut nvidia-smi | |
| Ollama Version | |
| bisheriges Modell | |
| Embeddingmodell | |

---

# Phase 1 — Kandidatenmodell festlegen

Primärer Kandidat:

```text
Repository:
LuffyTheFox/Qwen3.5-9B-Claude-4.6-Opus-Uncensored-Distilled-GGUF

Datei:
Qwen3.5-9B.Q4_K_M.gguf

Eigenschaft:
uncensored
Qwen3.5
GGUF
Q4_K_M
```

Optionaler zweiter Kandidat aus demselben Repo:

```text
Qwen3.5-9B-Genesis.Q4_K_M.gguf
```

Nicht primär nutzen:

```text
Q8_0
```

Begründung:

```text
Q8_0 ist für GTX 1070 / 8 GB VRAM wahrscheinlich zu groß oder nur mit starkem CPU-Offload sinnvoll.
Q4_K_M ist der realistischere Kandidat.
```

---

# Phase 2 — Download kontrolliert durchführen

Erstelle Modellverzeichnis:

```bash
mkdir -p models/qwen35/luffythefox
cd models/qwen35/luffythefox
```

Bevorzugter Download:

```bash
huggingface-cli download \
  LuffyTheFox/Qwen3.5-9B-Claude-4.6-Opus-Uncensored-Distilled-GGUF \
  Qwen3.5-9B.Q4_K_M.gguf \
  --local-dir .
```

Falls `huggingface-cli` fehlt:

```bash
pip install -U "huggingface_hub[cli]"
```

Alternative mit `llama-server -hf` nur als Test, aber für reproduzierbare Projektkonfiguration ist ein lokaler Dateipfad besser.

Nach Download:

```bash
ls -lh
sha256sum Qwen3.5-9B.Q4_K_M.gguf | tee SHA256SUMS.local
```

Regeln:

- HauhauCS nicht löschen.
- Keine alten GGUFs überschreiben.
- SHA256 dokumentieren.
- `models/` entweder bewusst ignorieren oder Modellpfad außerhalb Repo dokumentieren.
- Keine 5+ GB Modellgewichte committen.

---

# Phase 3 — llama.cpp / llama-server bereitstellen

Prüfen:

```bash
which llama-server || true
llama-server --help || true
```

Wenn nicht vorhanden:

```bash
mkdir -p ~/src
git clone https://github.com/ggml-org/llama.cpp ~/src/llama.cpp
cd ~/src/llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j"$(nproc)"
./build/bin/llama-server --help
```

Wenn CUDA-Build scheitert:

- Fehler dokumentieren.
- CPU-Build als Stabilitätstest versuchen.
- NVIDIA-Treiber nicht automatisch ändern.

CPU-Fallback nur als Diagnose:

```bash
cmake -B build-cpu
cmake --build build-cpu --config Release -j"$(nproc)"
```

---

# Phase 4 — GGUF lädt und produziert lesbaren Output?

Teste zuerst mit `llama-cli`:

```bash
~/src/llama.cpp/build/bin/llama-cli \
  -m models/qwen35/luffythefox/Qwen3.5-9B.Q4_K_M.gguf \
  -p "Antworte nur mit OK." \
  -n 32 \
  -ngl 0
```

Dann:

```bash
~/src/llama.cpp/build/bin/llama-cli \
  -m models/qwen35/luffythefox/Qwen3.5-9B.Q4_K_M.gguf \
  -p "Was ist eine Suchmaschine?" \
  -n 128 \
  -ngl 0
```

Bewertung:

| Test | Erwartung |
|---|---|
| Modell lädt | ja |
| keine GGUF-/Tokenizer-Fehler | ja |
| Output lesbar | ja |
| Output nicht garbled | ja |
| Antwort folgt ungefähr Prompt | ja |

Wenn schon `-ngl 0` garbled ist:

```text
Kandidat wahrscheinlich ungeeignet.
Dann Qwen3.5-9B-Genesis.Q4_K_M.gguf testen.
```

---

# Phase 5 — llama-server Stabilität auf GTX 1070 testen

Starte mit konservativem CPU/GPU-Offload:

```bash
~/src/llama.cpp/build/bin/llama-server \
  -m models/qwen35/luffythefox/Qwen3.5-9B.Q4_K_M.gguf \
  --host 127.0.0.1 \
  --port 8081 \
  -ngl 0 \
  -c 4096
```

Test:

```bash
curl -s http://127.0.0.1:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-uncensored-no-thinking",
    "messages": [
      {"role": "user", "content": "Antworte nur mit OK."}
    ],
    "temperature": 0.1,
    "max_tokens": 32
  }' | python3 -m json.tool
```

Dann GPU-Offload schrittweise testen:

```text
-ngl 0
-ngl 8
-ngl 12
-ngl 16
-ngl 20
-ngl 24
-ngl 28
-ngl 32
```

Für jede Stufe:

```bash
nvidia-smi
curl -s http://127.0.0.1:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-uncensored-no-thinking",
    "messages": [
      {"role": "user", "content": "Was ist eine Suchmaschine?"}
    ],
    "temperature": 0.2,
    "max_tokens": 128
  }' | python3 -m json.tool
```

Dokumentiere:

| `-ngl` | lädt | VRAM | lesbar | stabil | Tokens/s | Entscheidung |
|---:|---|---:|---|---|---:|---|
| 0 | | | | | | |
| 8 | | | | | | |
| 12 | | | | | | |
| 16 | | | | | | |
| 20 | | | | | | |
| 24 | | | | | | |
| 28 | | | | | | |
| 32 | | | | | | |

Wähle:

```text
höchster stabiler -ngl-Wert ohne VRAM-OOM, ohne Crash, ohne garbled Output
```

---

# Phase 6 — HauhauCS Vergleichstest

Teste HauhauCS und Luffy mit exakt denselben harmlosen Prompts und derselben Runtime.

| Modell | Runtime | Prompt | Output lesbar? | Bewertung |
|---|---|---|---|---|
| HauhauCS | llama-server | OK-Test | | |
| HauhauCS | llama-server | Suchmaschine | | |
| Luffy Q4_K_M | llama-server | OK-Test | | |
| Luffy Q4_K_M | llama-server | Suchmaschine | | |

Wenn Luffy lesbar und HauhauCS garbled:

```text
HauhauCS model-level issue strongly suspected.
```

Nicht schreiben:

```text
HauhauCS garantiert korrupt.
```

---

# Phase 7 — Researcher lokal auf llama-server konfigurieren

Lokale `.env`:

```env
LOCAL_CHAT_PROVIDER=llama_server
LOCAL_CHAT_BASE_URL=http://127.0.0.1:8081/v1
LOCAL_CHAT_MODEL=qwen3.5-uncensored-no-thinking

FAST_LLM=openai:qwen3.5-uncensored-no-thinking
SMART_LLM=openai:qwen3.5-uncensored-no-thinking
STRATEGIC_LLM=openai:qwen3.5-uncensored-no-thinking

OPENAI_API_BASE=http://127.0.0.1:8081/v1
OPENAI_BASE_URL=http://127.0.0.1:8081/v1
OPENAI_API_KEY=local-not-used

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest

ALLOW_CLOUD=false
ALLOW_OLLAMA_MODEL_FALLBACK=false
```

Wichtig:

- `openai:` heißt hier nur API-Kompatibilität.
- Endpoint muss `127.0.0.1` oder `localhost` sein.
- Externe OpenAI-Endpunkte bleiben verboten.
- Keine Cloud-Fallbacks.

Falls Cloud-Blocker lokale OpenAI-kompatible Endpunkte blockiert:

Regel ergänzen:

```text
OpenAI-compatible provider is allowed only when base URL host is 127.0.0.1 or localhost.
```

---

# Phase 8 — Runtime-Smoke anpassen

`scripts/runtime_smoke.py` soll erkennen:

```json
{
  "chat_provider": "llama_server",
  "chat_model": "qwen3.5-uncensored-no-thinking",
  "chat_base_url": "http://127.0.0.1:8081/v1",
  "chat_status": "ok",
  "embedding_provider": "ollama",
  "embedding_model": "nomic-embed-text:latest",
  "embedding_status": "ok",
  "cloud_status": "blocked"
}
```

Statusklassen:

```text
LLAMA_SERVER_CHAT_OK
LLAMA_SERVER_CHAT_TIMEOUT
LLAMA_SERVER_CHAT_GARBLED
LLAMA_SERVER_CHAT_UNAVAILABLE
OLLAMA_EMBEDDING_OK
CLOUD_BLOCKED
LOCAL_OPENAI_COMPAT_ALLOWED
```

Test:

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
```

---

# Phase 9 — GPT-Researcher UI/E2E mit unzensiertem Modell testen

Terminal 1:

```bash
~/src/llama.cpp/build/bin/llama-server \
  -m models/qwen35/luffythefox/Qwen3.5-9B.Q4_K_M.gguf \
  --host 127.0.0.1 \
  --port 8081 \
  -ngl <STABLE_NGL> \
  -c 4096
```

Terminal 2:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Terminal 3:

```bash
UI_BASE_URL=http://127.0.0.1:8000 \
UI_TIMEOUT_SECONDS=120 \
RESEARCH_TIMEOUT_SECONDS=600 \
python3 scripts/gpt_researcher_ui_smoke.py --run-research
```

Danach:

```bash
make research-evaluate
```

Erwartung:

- UI lädt.
- Query startet.
- qwen3.5-uncensored-no-thinking läuft über llama-server.
- Report wird erzeugt.
- Evaluation läuft.
- Keine Cloud.
- Kein 7B-Fallback.

---

# Phase 10 — Doku aktualisieren

Aktualisiere:

```text
docs/runtime/qwen35-uncensored-gtx1070-runtime.md
docs/runtime/ollama-cuda-known-issues.md
docs/development/local-runbook.md
docs/development/ui-local-readiness.md
README.md
.env.example
```

Pflichtinhalt für `qwen35-uncensored-gtx1070-runtime.md`:

```markdown
# qwen3.5 Uncensored Runtime on GTX 1070

## Entscheidung

Für lokale unzensierte Qwen3.5-Nutzung auf GTX 1070 wird `llama-server` mit einem validierten Q4_K_M-GGUF genutzt.

## Modellanforderung

- unzensiert
- Qwen3.5-kompatibel
- 9B-Klasse
- Q4_K_M
- lauffähig auf 8 GB VRAM mit kontrolliertem GPU-Offload

## Validierter Kandidat

- Repository: LuffyTheFox/Qwen3.5-9B-Claude-4.6-Opus-Uncensored-Distilled-GGUF
- Datei: Qwen3.5-9B.Q4_K_M.gguf
- Lokaler Alias: qwen3.5-uncensored-no-thinking
- SHA256: <lokal gemessen>
- stabiler -ngl: <Wert>

## Warum nicht HauhauCS?

HauhauCS erzeugte über mehrere Runtime-/Template-Konfigurationen hinweg garbled Output. Model-level issue suspected, not conclusively proven.

## Warum nicht Ollama Chat?

Auf der lokalen CUDA/Ollama-Kombination crasht der Ollama Runner oder erzeugt instabile Ergebnisse. `llama-server` umgeht diesen Pfad.

## Start

```bash
llama-server \
  -m models/qwen35/luffythefox/Qwen3.5-9B.Q4_K_M.gguf \
  --host 127.0.0.1 \
  --port 8081 \
  -ngl <STABLE_NGL> \
  -c 4096
```

## Researcher ENV

```env
LOCAL_CHAT_PROVIDER=llama_server
LOCAL_CHAT_BASE_URL=http://127.0.0.1:8081/v1
LOCAL_CHAT_MODEL=qwen3.5-uncensored-no-thinking
OPENAI_API_BASE=http://127.0.0.1:8081/v1
OPENAI_API_KEY=local-not-used
OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest
ALLOW_CLOUD=false
ALLOW_OLLAMA_MODEL_FALLBACK=false
```

## Test

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
UI_BASE_URL=http://127.0.0.1:8000 RESEARCH_TIMEOUT_SECONDS=600 python3 scripts/gpt_researcher_ui_smoke.py --run-research
make research-evaluate
```
```

---

# Phase 11 — Entscheidung

## UNCENSORED_QWEN35_GTX1070_READY

Nur wenn:

- Luffy Q4_K_M lädt.
- Output ist lesbar.
- stabiler `-ngl`-Wert gefunden.
- Researcher nutzt exakt den lokalen qwen3.5-uncensored Alias.
- Kein 7B-Fallback.
- Keine Cloud.
- Report wird erzeugt.
- Evaluation läuft.

## UNCENSORED_QWEN35_GTX1070_PARTIAL

Wenn:

- Modell in llama-server läuft.
- Aber Researcher/UI-Anbindung noch fehlt.
- Oder Performance langsam, aber funktional ist.
- Oder Report erzeugt wird, aber UI/Evaluation noch nicht vollständig ist.

## UNCENSORED_QWEN35_GTX1070_BLOCKED

Wenn:

- Luffy Q4_K_M garbled ist.
- Genesis Q4_K_M auch garbled ist.
- Modell auf GTX 1070 mit keinem Offload stabil läuft.
- Researcher den lokalen Endpoint nicht verwenden kann.
- Ohne Treiber-/Runtimewechsel kein stabiler Betrieb möglich ist.

---

# Abschlussbericht

```markdown
# Uncensored Qwen3.5 GTX1070 Runtime Abschlussbericht

## Entscheidung

`UNCENSORED_QWEN35_GTX1070_READY` / `UNCENSORED_QWEN35_GTX1070_PARTIAL` / `UNCENSORED_QWEN35_GTX1070_BLOCKED`

## Ergebnis

| Bereich | Status |
|---|---|
| Unzensierter Kandidat ausgewählt | |
| Q4_K_M heruntergeladen | |
| SHA256 dokumentiert | |
| GTX 1070 / 8GB berücksichtigt | |
| llama.cpp / llama-server bereit | |
| GGUF lädt | |
| Output lesbar | |
| HauhauCS Vergleich durchgeführt | |
| stabiler `-ngl` gefunden | |
| Researcher auf llama-server konfiguriert | |
| Runtime-Smoke angepasst | |
| GPT-Researcher UI getestet | |
| Report erzeugt | |
| Evaluation erfolgreich | |
| Kein 7B-Fallback | |
| Keine Cloud-Fallbacks | |
| Kein Release-Tag | |

## Modellmatrix

| Modell | Ergebnis | Entscheidung |
|---|---|---|
| HauhauCS qwen3.5 | | |
| Luffy Qwen3.5 Q4_K_M | | |
| Luffy Genesis Q4_K_M | | |

## Performance / Stabilität

| `-ngl` | VRAM | Ergebnis | Entscheidung |
|---:|---:|---|---|
| 0 | | | |
| 8 | | | |
| 12 | | | |
| 16 | | | |
| 20 | | | |
| 24 | | | |
| 28 | | | |
| 32 | | | |

## Validierte Befehle

```bash
# Download
# sha256sum
# llama-cli
# llama-server
# curl /v1/chat/completions
# runtime-smoke
# UI E2E
# research-evaluate
```

## Bekannte Grenzen

## Nächster Schritt
```

---

# Fallback-Plan

Wenn `Qwen3.5-9B.Q4_K_M.gguf` nicht funktioniert:

1. `Qwen3.5-9B-Genesis.Q4_K_M.gguf` testen.
2. Danach anderen uncensored Qwen3.5/Qwen-kompatiblen Q4_K_M-Kandidaten suchen.
3. Erst danach Ollama PR #16031 testen.
4. Treiber/CUDA-Downgrade nur dokumentieren, nicht automatisch ausführen.

---

# Akzeptanzkriterien

Dieses Issue ist abgeschlossen, wenn:

- ein unzensiertes Qwen3.5-kompatibles Modell getestet wurde
- GTX 1070 / 8 GB VRAM explizit berücksichtigt wurde
- stabiler Runtime-Pfad dokumentiert ist
- Researcher-Konfiguration dokumentiert ist
- kein 7B-Fallback verwendet wurde
- keine Cloud verwendet wurde
- finale READY/PARTIAL/BLOCKED-Entscheidung getroffen wurde

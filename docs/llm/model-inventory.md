---
title: Lokales LLM-Model-Inventar
date: 2026-05-27
---

# Local LLM Model Inventory

## Stand

2026-05-27 — Aktuelles Chat-Modell: **Gemma 4 E4B OBLITERATED** via llama-server.  
qwen3.5-Ära beendet (deprecated, durch Gemma 4 obliterated ersetzt).

## Aktuelle Modelle (2026-05)

| Modell | Rolle | Backend | Port | VRAM | Start |
|--------|-------|---------|------|------|-------|
| **gemma4-obliterated** | Chat / Summary / Report | llama-server (eigenständig) | 8081 | ~3.8 GB | `./serve_gemma4_obliterated_researcher.sh` |
| **nomic-embed-text:latest** | Embedding | Ollama | 11434 | 274 MB (CPU-seitig) | `ollama run nomic-embed-text` |

## Internet-Recherche: Bestätigungen und Korrekturen

- `nomic-embed-text:latest` ist ein reines Embedding-Modell und kann **keinen Text generieren**. Quellen: https://ollama.com/library/nomic-embed-text, https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
- **Gemma 4 E4B OBLITERATED** ist ein Community-Uncensored-Fork von Googles Gemma 4 (E4B = Expert-4B). Läuft via llama.cpp/llama-server, nicht via Ollama. Quelle: Projekt-eigene GGUF-Datei in `/home/xxammaxx/Schreibtisch/gemma4/llama.cpp/models/`.
- **qwen3.5-Ära (deprecated)**: Historisches Chat-Modell. `qwen3.5-uncensored-no-thinking:latest` war ein lokaler Modelfile-Name im Projekt, Basis `Qwen/Qwen3.5-9B`. Ersetzt durch Gemma 4 obliterated (stabiler, weniger VRAM).

## Hardware-Kontext (verifiziert im Projekt)

- Zielsystem: NVIDIA GTX 1070 (8 GB VRAM) + 16 GB RAM.
- Das Projekt reduziert den Kontext für das Qwen-Modell auf 2048/4096 je nach Startpfad, um im VRAM-Budget zu bleiben.
- `nomic-embed-text` wird CPU-seitig genutzt und blockiert die GPU nicht.
- Projektnotizen kalkulieren für das Qwen-Q4_K_M-Setup grob: Gewichte ~5.6 GB, KV-Cache ~0.3 GB, Overhead ~0.3 GB ⇒ ~6.2 GB gesamt.

## Im Repository gefundene Modellvariablen

| Modell / Variable | Rolle | Fundstelle | Aktueller Default | Bemerkung |
|---|---|---|---|---|
| `OLLAMA_CHAT_MODEL` | Chat/Summary (Ollama-Fallback) | `.env.example`, `scripts/runtime_smoke.py`, `scripts/research_happy_path.py`, `config/ollama_models.py` | `qwen3.5:9b` | Offizielles Ollama-Basismodell. Primäres Chat-Modell ist `gemma4-obliterated` via llama-server. |
| `OLLAMA_EMBEDDING_MODEL` | Embeddings | `.env.example`, `gpt_researcher/gpt_researcher/config/config.py:119` | `nomic-embed-text:latest` | Standard-Ollama-Embedding-Modell |
| `FAST_LLM` | Fast LLM (Deprecated-Rolle) | `.env.example:16` | `ollama:qwen3.5-9b-uncensored-hauhaucs-aggressive:latest` | Historischer/alternativer Name; mappt auf HauhauCS-Fork |
| `SMART_LLM` | Smart LLM (Deprecated-Rolle) | `.env.example:17` | `ollama:qwen3.5-9b-uncensored-hauhaucs-aggressive:latest` | Historischer/alternativer Name |
| `STRATEGIC_LLM` | Strategic LLM (Deprecated-Rolle) | `.env.example:18` | `ollama:qwen3.5-9b-uncensored-hauhaucs-aggressive:latest` | Historischer/alternativer Name |
| `EMBEDDING` | Embedding Provider+Model | `.env.example:35` | `ollama:nomic-embed-text:latest` | GPT-Researcher-Format `<provider>:<model>` |
| `INFERENCE_BACKEND` | Inference Runtime | `.env.example:28` | `ollama` | `ollama` oder `llama-server` |
| `OLLAMA_BASE_URL` | Ollama API URL | `.env.example:21` | `http://localhost:11434` | Standard-Ollama-Port |

## Aktuelle Modellrollen

| Rolle | Variable | Default | Zweck |
|---|---|---|---|
| Chat / Text-Generierung / Summary | `FAST_LLM` / `SMART_LLM` / `STRATEGIC_LLM` (primär, via llama-server) | `openai:gemma4-obliterated` | Generierung von Research-Summaries, Chat-Responses via llama-server (Port 8081) |
| Chat / Text-Generierung / Summary (Ollama-Fallback) | `OLLAMA_CHAT_MODEL` | `qwen3.5:9b` | Fallback für den Ollama-Chat-Pfad |
| Embeddings / Vektorsuche | `OLLAMA_EMBEDDING_MODEL` / `EMBEDDING` | `nomic-embed-text:latest` | Vektorisierung von Dokumenten für ChromaDB |
| GPT-Researcher Fast LLM | `FAST_LLM` | `ollama:qwen3.5-9b-uncensored-hauhaucs-aggressive:latest` | GPT-Researcher-intern (Deprecated-Format) |
| GPT-Researcher Smart LLM | `SMART_LLM` | `ollama:qwen3.5-9b-uncensored-hauhaucs-aggressive:latest` | GPT-Researcher-intern (Deprecated-Format) |
| GPT-Researcher Strategic LLM | `STRATEGIC_LLM` | `ollama:qwen3.5-9b-uncensored-hauhaucs-aggressive:latest` | GPT-Researcher-intern (Deprecated-Format) |

## Gefundene Modellnamen

1. **`qwen3.5-uncensored-no-thinking:latest`** — Lokaler Name via Ollama-Modelfile. Basis ist `qwen3.5:9b` (6.6 GB, 256K Kontext). Der Suffix `-no-thinking` signalisiert den direkten Antwortmodus ohne Thinking-Block. Quellen: https://ollama.com/library/qwen3.5, https://huggingface.co/Qwen/Qwen3.5-9B, https://github.com/ollama/ollama/blob/main/docs/api.md
2. **`nomic-embed-text:latest`** — Offizielles Ollama-Embedding-Modell. 274 MB, 2K Kontext, nur Embeddings. Quellen: https://ollama.com/library/nomic-embed-text, https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
3. **`qwen3.5-9b-uncensored-hauhaucs-aggressive`** — Community-/Dritt-uncensored-Modell. Historischer Name, lokal aus `Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive` abgeleitet. Entspricht im HF-Kontext `HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive`. Quelle: https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive
4. **`qwen3.5:9b`** — Offizielles Ollama-Qwen3.5-9B-Basismodell (6.6 GB, 256K Kontext). Quellen: https://ollama.com/library/qwen3.5, https://huggingface.co/Qwen/Qwen3.5-9B

## Internetrecherche: Modellfakten

### nomic-embed-text

- Ollama Library: 274 MB, 2K Kontextfenster, embedding-only. Quelle: https://ollama.com/library/nomic-embed-text
- Hugging Face: Apache-2.0-Lizenz, ~137M Parameter, 8192 native Sequenzlänge, 768 Ausgabedimensionen. Quelle: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
- Matryoshka-Dimensionen: 512 / 256 / 128 / 64 werden unterstützt. Quelle: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
- Trainingsdaten sind englischzentriert (StackExchange, Quora, Amazon Reviews, News-Summaries). Quelle: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
- Deutsch-Unterstützung ist **nicht offiziell zugesagt**. **UNVERIFIED**: keine expliziten deutschen Benchmarks im offiziellen Card-Text gefunden. Quelle: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5

### Qwen3.5 Chat/Summary

- Offizielle Basis: `Qwen/Qwen3.5-9B` (HF) / `qwen3.5:9b` (Ollama). Quellen: https://huggingface.co/Qwen/Qwen3.5-9B, https://ollama.com/library/qwen3.5
- Parameter/Kontext: 9B, 262,144 nativ; YaRN kann auf ~1,010,000 Tokens erweitern. Quellen: https://huggingface.co/Qwen/Qwen3.5-9B
- Lizenz: Apache 2.0. Quelle: https://huggingface.co/Qwen/Qwen3.5-9B
- Sprachabdeckung: 201 Sprachen/Dialekte. Deutsch ist sehr wahrscheinlich enthalten, aber **nicht einzeln ausgewiesen**. **UNVERIFIED**. Quelle: https://huggingface.co/Qwen/Qwen3.5-9B
- Ollama `qwen3.5:9b`: 6.6 GB, 256K Kontext. Quelle: https://ollama.com/library/qwen3.5
- Thinking ist standardmäßig aktiv; Non-Thinking wird über API-Parameter deaktiviert. Quellen: https://huggingface.co/Qwen/Qwen3.5-9B, https://github.com/ollama/ollama/blob/main/docs/api.md
- Offizielle Non-Thinking-Sampling-Empfehlung: temperature=0.7, top_p=0.8, top_k=20, presence_penalty=1.5. Quelle: https://huggingface.co/Qwen/Qwen3.5-9B

### Community-Uncensored-Varianten

Gefundene Varianten in der Recherche (nicht offiziell, daher **UNVERIFIED** als Produktiv-Empfehlung):

- `HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive` — Quelle: https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive
- `LEONW24/...` — **UNVERIFIED** (Recherchehinweis, aber keine belastbare Repo-URL im Projektkontext)
- `huihui-ai/...` — **UNVERIFIED**
- `lukey03/...` — **UNVERIFIED**

Risiko: geringere Safety/Refusal-Mechanismen, unklare Provenienz, mögliche rechtliche/ethische Risiken. Bewertung auf Basis der uncensored Natur der Forks und der fehlenden offiziellen Freigabe.

## Unsicherheiten

- Der exakte Name `qwen3.5-uncensored-no-thinking` ist eine lokale Namenskonvention; öffentlich ist nur die Qwen3.5-Basis belegt. Quelle: https://huggingface.co/Qwen/Qwen3.5-9B
- Die `uncensored`-Forks sind Community-Artefakte; offizielle Alibaba/Qwen-Freigabe liegt dafür nicht vor. Quelle: https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive
- In `.env.example` und Skripten existieren noch unterschiedliche Benennungen (`qwen3.5-9b-uncensored-hauhaucs-aggressive` vs. `qwen3.5-uncensored-no-thinking`). Quelle: `.env.example`, `scripts/runtime_smoke.py`, `scripts/research_happy_path.py`
- Das Verhalten unzensierter Modelle bei sicherheitskritischen oder deutschen Fachbegriffen ist **UNVERIFIED** und wurde im Projekt nicht systematisch benchmarked.

## Hardware-Hinweise

- `nomic-embed-text` bleibt auf CPU und ist für die GTX 1070 unkritisch. Quelle: `vectordb/embedding.py`, https://ollama.com/library/nomic-embed-text
- Qwen-Chatmodell: für die GTX 1070 ist realistisch nur **ein** Modellserver gleichzeitig sinnvoll. Quelle: `README.md`, `tests/test_vram.py`
- Das Modelfile nutzt `num_ctx 4096` und `repeat_penalty 1.1`; in der Laufzeitkonfiguration ist `temperature 0.7` gesetzt. Quelle: `Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive`
- Der Projekt-Spawn nutzt bei Bedarf reduzierte Kontexte, um VRAM zu sparen. Quelle: `README.md`, `serve_qwen3.5_uncensored.sh`

## Quellen

- `.env.example` (Repository)
- `scripts/runtime_smoke.py` (Repository)
- `scripts/research_happy_path.py` (Repository)
- `Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive` (Repository)
- `docs/uncensored-llm-guide.md` (Repository)
- `README.md` (Repository)
- `vectordb/embedding.py` (Repository)
- `tests/test_vram.py` (Repository)
- Ollama Library: https://ollama.com/library/nomic-embed-text
- Ollama Library: https://ollama.com/library/qwen3.5
- Hugging Face Nomic Model Card: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
- Hugging Face Qwen Organization: https://huggingface.co/Qwen
- Hugging Face Qwen3.5-9B: https://huggingface.co/Qwen/Qwen3.5-9B
- Hugging Face HauhauCS Fork: https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive
- Ollama API Docs: https://github.com/ollama/ollama/blob/main/docs/api.md
- Ollama Modelfile Reference: https://raw.githubusercontent.com/ollama/ollama/main/docs/modelfile.mdx

---
title: Ollama-Modelle im Researcher
date: 2026-05-20
---

# Ollama Models used by Researcher

## Stand

2026-05-20 — basiert auf Repo-Scan plus Internetrecherche.

## Ollama Runtime

- Relevante Endpunkte: `/api/tags` (Modelle auflisten), `/api/generate`, `/api/chat`. Quelle: https://github.com/ollama/ollama/blob/main/docs/api.md
- Ollama bietet Modellnamen im Format `model:tag`; `:latest` ist der Default-Tag. Quelle: https://github.com/ollama/ollama/blob/main/docs/api.md
- Für lokale Modelle gelten `ollama list` / `ollama ls`; `ollama ps` zeigt, ob ein Modell auf GPU oder CPU läuft. Quelle: https://github.com/ollama/ollama/blob/main/docs/api.md
- OpenAI-kompatible Nutzung erfolgt über die `/v1/...`-Schnittstelle des lokalen Servers. Quelle: https://github.com/ollama/ollama/blob/main/docs/api.md
- Wichtige Umgebungsvariablen im Projekt: `OLLAMA_HOST`, `OLLAMA_NUM_PARALLEL`, `OLLAMA_CONTEXT_LENGTH`, `OLLAMA_KEEP_ALIVE`, `OLLAMA_MAX_LOADED_MODELS`, `OLLAMA_FLASH_ATTENTION`, `OLLAMA_KV_CACHE_TYPE`. Quelle: https://github.com/ollama/ollama/blob/main/docs/api.md
- Modelfiles nutzen u. a. `FROM`, `PARAMETER`, `TEMPLATE`, `SYSTEM` und können aus GGUF-Dateien gebaut werden. Quelle: https://raw.githubusercontent.com/ollama/ollama/main/docs/modelfile.mdx

## Chat/Summary Model: Qwen3.5 Uncensored No-Thinking

- Exakter lokaler Modellname: `qwen3.5-uncensored-no-thinking:latest`
- Öffentlich belegbarer Ursprung: `Qwen/Qwen3.5-9B` bzw. `qwen3.5:9b`
- Ursprung des lokalen Uncensored-Forks: `HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive`

| Merkmal | Wert | Quelle |
|---|---|---|
| Parameter | 9B | https://huggingface.co/Qwen/Qwen3.5-9B |
| Native Kontextlänge | 262,144 Tokens | https://huggingface.co/Qwen/Qwen3.5-9B |
| Erweiterbar via YaRN | bis ca. 1,010,000 Tokens | https://huggingface.co/Qwen/Qwen3.5-9B |
| Lizenz | Apache 2.0 | https://huggingface.co/Qwen/Qwen3.5-9B |
| Ollama-Größe | 6.6 GB | https://ollama.com/library/qwen3.5 |
| Ollama-Kontext | 256K | https://ollama.com/library/qwen3.5 |
| Non-Thinking Default | über API-Parameter deaktivierbar | https://huggingface.co/Qwen/Qwen3.5-9B, https://github.com/ollama/ollama/blob/main/docs/api.md |

- Eignung für Research-Summaries: gut für faktengebundene Zusammenfassungen, wenn der Prompt auf Quellen, Genauigkeit und knappe Ausgabe ausgerichtet ist. Quelle: https://huggingface.co/Qwen/Qwen3.5-9B
- Prompting-Empfehlung für Reports: systematisch, Deutsch, Quellen nennen lassen, `temperature` niedrig halten. Qwen empfiehlt im Non-Thinking-Modus `temperature=0.7`, `top_p=0.8`, `top_k=20`, `presence_penalty=1.5`. Quelle: https://huggingface.co/Qwen/Qwen3.5-9B
- Thinking/No-Thinking Modus: Qwen3.5 denkt standardmäßig; direkte Antworten werden über `think: false` bzw. `chat_template_kwargs: {"enable_thinking": False}` erzielt. Quelle: https://huggingface.co/Qwen/Qwen3.5-9B, https://github.com/ollama/ollama/blob/main/docs/api.md
- Risiken unzensierter Modelle: reduzierte Refusal-/Safety-Grenzen, unklare Provenienz der Community-Forks, mögliche Compliance-Risiken. Quelle: https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive

## Embedding Model: nomic-embed-text

## Offizielle Quellen

- Ollama Library: https://ollama.com/library/nomic-embed-text
- Hugging Face: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5

| Merkmal | Wert | Quelle |
|---|---|---|
| Größe | 274 MB | https://ollama.com/library/nomic-embed-text |
| Kontextfenster | 2K | https://ollama.com/library/nomic-embed-text |
| Parameter | ca. 137M | https://huggingface.co/nomic-ai/nomic-embed-text-v1.5 |
| Native Sequenzlänge | 8192 Tokens | https://huggingface.co/nomic-ai/nomic-embed-text-v1.5 |
| Ausgabedimensionen | 768 | https://huggingface.co/nomic-ai/nomic-embed-text-v1.5 |
| Matryoshka-Dimensionen | 512 / 256 / 128 / 64 | https://huggingface.co/nomic-ai/nomic-embed-text-v1.5 |
| Lizenz | Apache 2.0 | https://huggingface.co/nomic-ai/nomic-embed-text-v1.5 |

- Deutsch-Eignung: **nicht offiziell garantiert**; die Dokumentation ist englischzentriert. **UNVERIFIED** für gutes Deutsch-Retrieval. Quelle: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
- Nicht verwenden für Textgenerierung: das Modell kann nur Embeddings erzeugen. Quelle: https://ollama.com/library/nomic-embed-text

## Diagnostics

- `ollama list` / `ollama ls` zeigt installierte lokale Modelle.
- `curl localhost:11434/api/tags` listet dieselben Modelle per API. Quelle: https://github.com/ollama/ollama/blob/main/docs/api.md
- `ollama ps` zeigt GPU-/CPU-Platzierung.
- Typische Fehler: HTTP 404 bzw. `model not found` bedeuten im Projektkontext meist, dass das Modell lokal noch nicht gepullt wurde. **UNVERIFIED** als generelle Ollama-Regel.

## Quellen

- https://github.com/ollama/ollama/blob/main/docs/api.md
- https://raw.githubusercontent.com/ollama/ollama/main/docs/modelfile.mdx
- https://ollama.com/library/nomic-embed-text
- https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
- https://ollama.com/library/qwen3.5
- https://huggingface.co/Qwen/Qwen3.5-9B
- https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive

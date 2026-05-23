---
title: Model-Auswahlrichtlinie
date: 2026-05-20
---

# Model Selection Policy

## Stand

2026-05-20

## Ziel

- Nur lokale Modelle, kein Cloud-Fallback.
- Ziel ist reproduzierbares Verhalten auf der GTX-1070-Workstation.

## Chat/Summary-Modell

- Aktuelle Wahl: `qwen3.5-uncensored-no-thinking:latest`
- Herkunft: Community-Uncensored-Fork von `Qwen/Qwen3.5-9B`
- Fallback: `qwen3.5:9b` (offiziell, falls Uncensored nicht verfügbar)
- Eignung: Research-Summaries und Report-Generierung auf Deutsch

Quelle: https://huggingface.co/Qwen/Qwen3.5-9B, https://ollama.com/library/qwen3.5, https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive

## Embedding-Modell

- Aktuelle Wahl: `nomic-embed-text:latest`
- Kein Fallback nötig; läuft CPU-seitig und ist damit VRAM-schonend.
- Einschränkung: Deutsch ist nicht offiziell zugesagt.

Quelle: https://ollama.com/library/nomic-embed-text, https://huggingface.co/nomic-ai/nomic-embed-text-v1.5

## Technische Umsetzung

- Die zentrale technische Quelle der Modellkonfiguration ist `config/ollama_models.py`.
- `load_ollama_model_config()` lädt die aktiven Werte aus der Umgebung, darunter `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_BASE_URL` und `ALLOW_OLLAMA_MODEL_FALLBACK`.
- `resolve_chat_model()` löst das Chat-Modell mit Fallback-Schutz auf; Embedding-Modelle werden dabei nie als Chat-Modell verwendet.
- `validate_model_roles()` prüft die Rollen vor der Nutzung und unterstützt die Statuswerte `ok`, `fallback`, `missing`, `no_models` und `config_error`.

## Kein Cloud-Fallback

- Kein OpenAI
- Kein Anthropic
- Kein Google
- Kein Tavily
- `ALLOW_CLOUD=true` nur für explizite Ausnahmen

Quelle: `scripts/runtime_smoke.py` (Repository)

## Hardware-/VRAM-Hinweise

- GTX 1070: maximal 1 Modell gleichzeitig sinnvoll.
- Embedding läuft CPU-seitig.
- Zielkontext für knappen GTX-1070-Betrieb: 2048; das aktuelle Modelfile steht jedoch noch auf `num_ctx 4096`. **UNVERIFIED** als Laufzeitziel, verifiziert als Modelfile-Wert.

Quelle: `README.md`, `tests/test_vram.py`, `Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive`

## Prompting-Regeln

- System-Prompt: faktenbasiert, sachlich, Deutsch.
- Temperature: 0.1–0.3 für Research.
- Thinking deaktiviert für direkte Antworten.
- Quellenangaben einfordern.

Quelle: https://huggingface.co/Qwen/Qwen3.5-9B, https://github.com/ollama/ollama/blob/main/docs/api.md, `docs/uncensored-llm-guide.md`

## Quellen

- https://ollama.com/library/nomic-embed-text
- https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
- https://ollama.com/library/qwen3.5
- https://huggingface.co/Qwen/Qwen3.5-9B
- https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive
- https://github.com/ollama/ollama/blob/main/docs/api.md
- `README.md`
- `scripts/runtime_smoke.py`
- `tests/test_vram.py`
- `Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive`

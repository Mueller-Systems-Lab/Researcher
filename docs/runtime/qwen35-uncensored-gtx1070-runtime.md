---
title: Qwen3.5 Uncensored auf GTX 1070 — Runtime-Notiz
date: 2026-05-24
---

# Qwen3.5 9B Uncensored auf GTX 1070

**Status:** BLOCKED

## Kurzfassung

- **Qwen3.5 9B uncensored** ist auf der **GTX 1070** blockiert.
- Ursache: **Pascal FP16-Inkompatibilität** (`GP104`, **1/64 FP16-Throughput**, **keine Tensor Cores**).
- **Gemma 4 E4B OBLITERATED** ist die funktionierende Alternative.

## Warum Qwen3.5 blockiert ist

- Pascal/GP104 kann FP16 nur sehr langsam ausführen.
- Qwen3.5 nutzt FP16-Operationen, die auf dieser Karte nicht korrekt bzw. nicht stabil genug laufen.
- Ergebnis: instabiler Start, garbled Output oder Laufzeitfehler.

## Working Alternative

- Modell: **Gemma 4 OBLITERATED v3.1**
- Parameter: **7.5B**
- Quantisierung: **Q4_K_M**
- Alias: `gemma4-obliterated`

## Build-Anforderung für llama.cpp

Für die GTX 1070 muss `llama.cpp` mit CUDA-Support und Pascal-Ziel gebaut werden:

```bash
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=61
cmake --build build --config Release -j"$(nproc)"
```

## Working Server Start

```bash
llama-server \
  -m /home/xxammaxx/Schreibtisch/gemma4/llama.cpp/models/gemma-4-E4B-it-OBLITERATED-Q4_K_M.gguf \
  --n-gpu-layers 999 -np 1 --threads 8 \
  -ctk f32 -ctv f32 --flash-attn off \
  --jinja --alias gemma4-obliterated \
  --host 127.0.0.1 --port 8081 -c 8192
```

## Empfohlene `.env`-Konfiguration

```env
FAST_LLM=openai:gemma4-obliterated
SMART_LLM=openai:gemma4-obliterated
STRATEGIC_LLM=openai:gemma4-obliterated
OPENAI_BASE_URL=http://127.0.0.1:8081/v1
OPENAI_API_KEY=not-needed
EMBEDDING=ollama:nomic-embed-text:latest
```

## Performance (gemessen auf Zielsystem)

- **59 tok/s**
- **3.8 GB VRAM used**
- **2.1 GB free**

## Test-Kommandos

### Health / Models

```bash
curl http://127.0.0.1:8081/v1/models
```

### Chat

```bash
curl -s http://127.0.0.1:8081/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"gemma4-obliterated","messages":[{"role":"user","content":"Hallo"}]}'
```

### Embeddings

```bash
curl -s http://127.0.0.1:8081/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model":"gemma4-obliterated","input":"Test"}'
```

## SHA256

- **Model file:** `gemma-4-E4B-it-OBLITERATED-Q4_K_M.gguf`
- **SHA256:** _local checksum not yet recorded in this repository_

> Hinweis: Den finalen Hash bitte lokal mit `sha256sum` gegen die Datei ermitteln und hier eintragen.

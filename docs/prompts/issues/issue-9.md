# Issue Prompt: T-009

## Ziel
VRAM-Optimierungen für die GTX 1070: `num_ctx` auf 4096 setzen, GPU-Layers begrenzen, `MAX_CONCURRENT_REQUESTS=1`, `OLLAMA_NUM_PARALLEL=1`, Embedding-Batch-Size auf 8, VRAM-Monitoring einrichten und dokumentieren.

## Kontext
Die GTX 1070 hat nur 8 GB VRAM. Das LLM in Q4_K_M belegt ~4.8 GB, der KV-Cache bei ctx=4096 ~1 GB. Das ergibt ~5.8 GB. Der Rest (2.2 GB) ist Puffer. Ohne sorgfältiges Tuning droht VRAM-Überlauf.

## Betroffene Module
- `LLM_Service`

## Relevante Dateien
- `Modelfile.qwen3-uncensored` (Parameter anpassen)
- `.env` (MAX_CONCURRENT_REQUESTS, EMBEDDING_BATCH_SIZE)

## Architekturregeln
- `num_ctx` = 4096 (reduziert KV-Cache)
- `num_gpu` = max. 35 Layers auf GPU
- `MAX_CONCURRENT_REQUESTS=1` in `.env`
- `OLLAMA_NUM_PARALLEL=1` als Ollama-Environment-Variable
- `EMBEDDING_BATCH_SIZE=8` in `.env`
- Embeddings MÜSSEN auf CPU laufen
- Gesamt-VRAM-Verbrauch MUSS unter 7.5 GB bleiben

## Best Practices
- `nvidia-smi` im Watch-Modus zur Überwachung: `watch -n 1 nvidia-smi`
- Ollama-Start mit `OLLAMA_NUM_PARALLEL=1 ollama serve`
- Bei VRAM-Überlauf: `num_ctx` weiter reduzieren (2048) oder `num_gpu` verringern
- VRAM-Auslastung dokumentieren (Screenshots oder Logs)

## Akzeptanzkriterien
- **GIVEN** alle Tuning-Parameter sind gesetzt **WHEN** das System unter Last läuft (LLM-Anfrage + Embedding-Berechnung) **THEN** bleibt der VRAM-Verbrauch unter 7.5 GB.
- **GIVEN** eine Embedding-Anfrage läuft **WHEN** gleichzeitig eine LLM-Anfrage kommt **THEN** wird sequenziell verarbeitet (kein VRAM-Overflow).
- **GIVEN** das System läuft **WHEN** `nvidia-smi` ausgeführt wird **THEN** ist die VRAM-Auslastung dokumentiert und plausibel.

## Tests
- `nvidia-smi` → VRAM < 7.5 GB unter Last
- LLM-Anfrage während Embedding → sequenziell, kein Fehler
- `ollama ps` → zeigt laufende Modelle und VRAM
- Lasttest: 3 Recherchen hintereinander → VRAM stabil

## Risiken
- 🔴 Hoch – VRAM-Überlauf macht das System unbenutzbar; konstantes Monitoring nötig

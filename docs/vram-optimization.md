# VRAM-Optimierung für GTX 1070 (8 GB)

## Ziel

Das System muss auf einer NVIDIA GTX 1070 mit 8 GB VRAM laufen. Dies erfordert sorgfältige
Optimierung aller Komponenten, die GPU-Speicher belegen.

## VRAM-Budget

| Komponente | Verbrauch (geschätzt) |
|---|---|---|
| Gemma 4 E4B OBLITERATED Q4_K_M | ~3.3 GB |
| KV-Cache (num_ctx=8192) | ~0.5 GB |
| Overhead/Puffer | ~0.5 GB |
| **Gesamt LLM** | **~3.8 GB** |
| Verfügbar | 8.0 GB |
| **Reserve** | **~4.2 GB** |

> **Historisch:** Qwen3.5-9B benötigte ~6.8 GB (4.8 GB Gewichte + 1.0 GB KV-Cache + 1.0 GB Puffer).
> Gemma 4 spart ~3 GB VRAM und ermöglicht größere Kontexte oder paralleles GPU-Dashboard.

**Wichtig:** Embeddings laufen auf CPU, nicht GPU! nomic-embed-text ist mit 137M Parametern
klein genug für CPU-Betrieb und belegt keinen GPU-VRAM.

## Optimierungsparameter

### Modelfile (Ollama)

```dockerfile
PARAMETER num_ctx 4096    # Reduziert KV-Cache von ~4 GB auf ~1 GB
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
```

### Umgebung (.env)

```ini
# Keine parallelen LLM-Anfragen
MAX_CONCURRENT_REQUESTS=1
OLLAMA_NUM_PARALLEL=1

# Embedding auf CPU (kein GPU-VRAM)
EMBEDDING=ollama:nomic-embed-text:latest
```

### llama-server (direkter Start)

```bash
./serve_gemma4_obliterated_researcher.sh
# Enthält: --n-gpu-layers 999, -np 1, -c 8192, --flash-attn off (Pascal!), -ctk f32 -ctv f32
```

## Monitoring

### Einmalige Abfrage

```bash
./scripts/check-vram.sh
```

### Dauerhaftes Monitoring (alle 2s)

```bash
./scripts/check-vram.sh --watch
```

### JSON-Ausgabe für Scripts

```bash
./scripts/check-vram.sh --json
```

## Fehlersuche bei VRAM-Problemen

| Symptom | Ursache | Lösung |
|---|---|---|
| CUDA Out of Memory | VRAM > 8 GB | num_ctx reduzieren, andere Prozesse stoppen |
| Modell startet nicht | Zu viele GPU-Layers | --n-gpu-layers reduzieren (z.B. 28 statt 35) |
| System ruckelt | GPU-Auslastung > 90% | MAX_CONCURRENT_REQUESTS=1 prüfen |
| Embedding auf GPU | Falsche Konfiguration | EMBEDDING=ollama:nomic-embed-text setzen |

## Empfohlene Betriebsreihenfolge

1. Alle anderen GPU-Prozesse beenden
2. `ollama serve` starten
3. VRAM prüfen: `./scripts/check-vram.sh`
4. SearXNG und andere CPU-Dienste starten
5. GPT Researcher starten

Nur **ein** Modellserver gleichzeitig. Aktuell: Gemma 4 via llama-server (Port 8081, ~3.8 GB).

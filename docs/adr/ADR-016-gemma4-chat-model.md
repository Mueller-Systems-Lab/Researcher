# ADR-016: Gemma 4 E4B OBLITERATED als Chat-Modell

**Status:** Accepted  
**Date:** 2026-05-27  
**Deciders:** Architecture Review Agent  
**Supersedes:** [ADR-015](ADR-015-local-llm-model-policy.md) (Chat/Summary-Rolle)  
**Context:** Migration von qwen3.5 auf Gemma 4 OBLITERATED als primäres Chat-/Summary-Modell

---

## Context

Das Researcher-Projekt benötigt ein lokales Chat-/Summary-Modell für Report-Generierung, Zusammenfassungen und Research-Planung. Die bisherige Wahl war `qwen3.5-uncensored-no-thinking:latest` (via Ollama, ~6.6 GB VRAM).

Im Betrieb zeigten sich folgende Probleme mit qwen3.5:

1. **Instabilität:** Regelmäßige Abstürze mit "llama runner process has terminated", insbesondere bei längeren Generierungen.
2. **VRAM-Druck:** 6.6 GB VRAM ließen wenig Reserve auf der GTX 1070 (8 GB).
3. **Langsamer Startup:** Modell-Laden via Ollama blockierte den Backend-Start für 120s+.
4. **Ollama-Abhängigkeit:** Chat und Embedding hingen beide an einem Ollama-Prozess.

Als Alternative wurde Gemma 4 E4B OBLITERATED evaluiert — ein Community-Uncensored-Fork von Googles Gemma 4, der via llama.cpp/llama-server betrieben wird.

## Decision

### Primäres Chat-Modell: Gemma 4 E4B OBLITERATED

Das Projekt setzt ab sofort **Gemma 4 E4B OBLITERATED** als primäres Chat-/Summary-Modell ein:

| Eigenschaft | Wert |
|---|---|
| Modell | `gemma-4-E4B-it-OBLITERATED-Q4_K_M.gguf` |
| Alias im Server | `gemma4-obliterated` |
| Backend | llama-server (eigenständig) |
| Port | 8081 |
| VRAM | ~3.8 GB |
| Kontextlänge | 8192 Tokens |
| Start | `./serve_gemma4_obliterated_researcher.sh` |
| GGUF-Pfad | `/home/xxammaxx/Schreibtisch/gemma4/llama.cpp/models/` |

### Warum llama-server statt Ollama

1. **Eigenständiger Prozess:** Chat läuft unabhängig vom Ollama-Embedding-Dienst. Kein single-point-of-failure.
2. **Stabilität:** llama-server ist robuster bei langen Generierungen; kein "llama runner process has terminated".
3. **VRAM-Effizienz:** ~3.8 GB statt 6.6 GB — ~3 GB VRAM-Ersparnis.
4. **Schneller Startup:** llama-server startet in ~5s (Modell ist vorinitialisiert im GGUF).
5. **OpenAI-kompatible API:** `/v1/chat/completions`-Endpunkt — native Kompatibilität mit GPT-Researcher-Providern.

### Precision Trap (Lessons Learned)

Auf Pascal-GPUs (GTX 1070, Compute Capability 6.1) produzierte Gemma 4 mit FP16-KV-Cache garbled Output. Der Fehler zeigte sich als sinnfreie, sich wiederholende Token-Sequenzen.

**Lösung:** FP32 KV-Cache erzwingen:

```bash
-ctk f32 -ctv f32
```

Zusätzlich ist `--flash-attn off` nötig, da Pascal keine Tensor Cores besitzt.

Diese Flags sind in `serve_gemma4_obliterated_researcher.sh` dokumentiert und gesetzt.

### qwen3.5-Deprecation

- qwen3.5 ist **deprecated** und wird nicht mehr aktiv betrieben.
- Das GGUF `Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf` bleibt im Projektordner.
- `Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive` bleibt als Referenz erhalten.
- `serve_qwen3.5_uncensored.sh` bleibt für Notfälle im Repository, ist aber deprecated.
- `OLLAMA_CHAT_MODEL` in `.env.example` und `config/services.py` zeigt jetzt auf `qwen3.5:9b` als Fallback für den Ollama-Chat-Pfad.

### Embedding bleibt via Ollama

Die Embedding-Rolle (nomic-embed-text) bleibt unverändert via Ollama (Port 11434, CPU-seitig). Diese Trennung entspricht der in ADR-015 definierten Rollentrennung.

## Alternatives Considered

### Alternative A: Gemma 4 via Ollama

- **Pros:** Einheitliches Backend für Chat und Embedding; keine zwei Prozesse.
- **Cons:** Ollama-Chat crasht bei Pascal-Treibern (CUDA 13+); kein separater Chat-Prozess.
- **Decision:** Verworfen. Eigenständiger llama-server ist stabiler.

### Alternative B: qwen3.5 mit reduziertem Kontext beibehalten

- **Pros:** Keine Migration nötig; bewährte Konfiguration.
- **Cons:** Bleibt instabil; 6.6 GB VRAM; 120s+ Startup; Ollama-Abhängigkeit.
- **Decision:** Verworfen. Gemma 4 ist in allen Punkten überlegen.

### Alternative C: Cloud-LLM (OpenAI, Anthropic)

- **Pros:** Höhere Qualität; kein lokales VRAM-Management.
- **Cons:** Local-First-Prinzip verletzt; Datenschutz; Kosten; Abhängigkeit.
- **Decision:** Verworfen. Widerspricht der Projekt-Architektur.

## Consequences

### Positive

1. **Stabilität:** Keine "llama runner process has terminated"-Abstürze mehr. Chat läuft zuverlässig.
2. **VRAM-Entlastung:** 3.8 GB statt 6.6 GB — ~3 GB Reserve für GPU-Dashboard oder größere Kontexte.
3. **Schneller Startup:** ~5s statt 120s+ für den Chat-Server.
4. **Trennung der Concerns:** Chat (llama-server, Port 8081) und Embedding (Ollama, Port 11434) sind unabhängig.
5. **OpenAI-kompatibler Endpunkt:** Native Integration in GPT-Researcher ohne Wrapper.

### Negative

1. **Zwei Prozesse statt einem:** Chat und Embedding brauchen separate Dienste.
2. **Precision Trap erkannt:** FP32-KV-Cache nötig, leicht erhöhter VRAM-Verbrauch im KV-Cache.
3. **Pfad-Abhängigkeit:** Das GGUF liegt außerhalb des Repositories (`/home/xxammaxx/Schreibtisch/gemma4/`). Der Pfad ist im Serve-Script hardcoded.
4. **Kein Ollama-Fallback für Chat:** Wenn der llama-server ausfällt, gibt es keinen automatischen Fallback auf qwen3.5 via Ollama.

### Risiken

| Risiko | Impact | Mitigation |
|---|---|---|
| GGUF-Pfad ungültig | Chat startet nicht | Serve-Script prüft Datei-Existenz |
| Precision Trap bei neuer GPU | Garbled Output | `-ctk f32 -ctv f32` in CI testen |
| Gemma 4 Community-Fork ungepflegt | Keine Updates | Fallback auf offizielles Gemma 4 möglich |
| FP32-KV erhöht VRAM | ~0.2 GB mehr als FP16 | Akzeptabel bei 3.8 GB Gesamt-VRAM |

## Architecture Review Checklist

- [x] New dependency justified? **Keine neue Dependency — llama-server ist bereits vorhanden.**
- [x] Module coupling acceptable? **Verbessert durch Trennung von Chat und Embedding.**
- [x] Data flow documented and secure? **Lokale Eingaben → lokaler llama-server → Reports; kein Cloud-Fallback.**
- [x] Error handling strategy consistent? **Serve-Script mit Fehlerprüfung; research_planner mit Timeout und Fallback.**
- [x] Scaling bottlenecks identified? **GTX-1070-VRAM limitiert parallele GPU-Modelle; Embedding CPU-seitig.**
- [x] Security boundaries clearly defined? **Community-Uncensored-Modell dokumentiert; kein Cloud-Dependency.**
- [x] Testing strategy adequate? **Smoke-Tests für Chat-Verfügbarkeit; Modell-Tests mit gemocktem llama-server.**

## References

- Issue #109: Restliche Doku-Bereinigung qwen3.5 → Gemma 4
- `docs/adr/ADR-015-local-llm-model-policy.md` — Superseded (Chat-Rolle)
- `docs/llm/model-selection-policy.md` — Aktualisiert für Gemma 4
- `docs/llm/model-inventory.md` — Aktuelles Modell-Inventar
- `docs/development/local-runbook.md` — Startbefehle und Dienste
- `serve_gemma4_obliterated_researcher.sh` — Serve-Script mit Precision-Trap-Flags
- Google Gemma 4: https://huggingface.co/google/gemma-4

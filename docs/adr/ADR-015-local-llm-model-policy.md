# ADR-015: Local LLM Model Policy

**Status:** Proposed  
**Date:** 2026-05-20  
**Deciders:** Architecture Review Agent  
**Context:** Lokale Modellrichtlinie für Chat/Summary und Embeddings; Issue #62 für Namensabgleich

---

## Context

Das Researcher-Projekt folgt einer local-first Architektur und nutzt lokale Ollama-Modelle statt Cloud-LLMs. Dafür müssen Modellrollen, Fallbacks, Sicherheitsgrenzen und Hardware-Grenzen explizit dokumentiert werden.

Aktuell gibt es zwei aktive Modellrollen:

1. **Chat/Summary:** `qwen3.5-uncensored-no-thinking:latest`
   - Lokaler Ollama-Modelfile-Name im Projekt.
   - Grundlage ist eine Community-Uncensored-Variante (`HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive`) der offiziellen `Qwen/Qwen3.5-9B`-Basis.
   - Die offizielle Qwen-Basis ist Apache-2.0-lizenziert; die Community-Fork-Provenienz muss separat bewertet werden.
   - Der Suffix `no-thinking` ist eine lokale Konvention: Thinking wird zur Laufzeit per API-Parameter deaktiviert.
2. **Embedding:** `nomic-embed-text:latest`
   - Offizielles Ollama-Embedding-Modell.
   - 274 MB, 2K Kontextfenster in Ollama, ca. 137M Parameter, 768 Dimensionen, Apache 2.0.
   - Das Modell generiert keine Texte, sondern nur Embeddings.

Zusätzlich existieren historische GPT-Researcher-Variablen `FAST_LLM`, `SMART_LLM` und `STRATEGIC_LLM`, die auf `qwen3.5-9b-uncensored-hauhaucs-aggressive` verweisen. Die aktiven Projektvariablen sind dagegen `OLLAMA_CHAT_MODEL` und `OLLAMA_EMBEDDING_MODEL`.

Hardware-Ziel ist eine Single-Workstation mit NVIDIA GTX 1070 (8 GB VRAM) und 16 GB RAM. Dadurch ist der gleichzeitige Betrieb mehrerer GPU-Modellserver nicht realistisch.

## Decision

### 1. Rollenbasierte Modellauswahl

Das Projekt trennt Chat/Summary und Embeddings strikt:

| Rolle | Variable | Default | Fallback | Laufzeitort |
|---|---|---|---|---|
| Chat/Summary | `OLLAMA_CHAT_MODEL` | `qwen3.5-uncensored-no-thinking:latest` | `qwen3.5:9b` | GPU/Ollama |
| Embeddings | `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text:latest` | keiner erforderlich | CPU-seitig |

### 2. Chat/Summary-Modell

Für Chat, Zusammenfassungen und Report-Generierung verwendet das Projekt `OLLAMA_CHAT_MODEL` mit der lokalen uncensored Qwen-Variante. Falls dieses lokale Modelfile nicht verfügbar ist, ist `qwen3.5:9b` der definierte Fallback, weil es die offizielle Ollama/Qwen-Basis ist.

Thinking wird für direkte Antworten deaktiviert (`"think": false`), damit Antworten ohne Thinking-Blöcke und mit reproduzierbarerem Ausgabeformat erzeugt werden.

### 3. Embedding-Modell

Für Embeddings verwendet das Projekt `OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest`. Dieses Modell läuft CPU-seitig und belegt damit nicht das knappe GTX-1070-VRAM-Budget.

### 4. Legacy-Variablen

`FAST_LLM`, `SMART_LLM` und `STRATEGIC_LLM` sind deprecated, bleiben aber für GPT-Researcher-interne Kompatibilität erhalten. Neue Projektlogik darf diese Variablen nicht als primäre Quelle verwenden, sondern muss `OLLAMA_CHAT_MODEL` und `OLLAMA_EMBEDDING_MODEL` bevorzugen.

### 5. Cloud- und Betriebsgrenzen

- Kein Cloud-Fallback ohne explizites `ALLOW_CLOUD=true`.
- Es ist wegen 8 GB VRAM nur ein GPU-Modellserver gleichzeitig aktiv.
- Modellnamen in `.env.example`, Skripten und Dokumentation müssen reconciled werden; diese Arbeit ist in Issue #62 nachzuverfolgen.

## Alternatives Considered

### Alternative A: Rollenbasierte lokale Ollama-Modelle

- **Pros:** Klare Trennung zwischen Generierung und Embeddings; kein Cloud-Abfluss sensibler Daten; gute Kohäsion der Modellrollen; VRAM-Budget bleibt kontrollierbar; spätere Modellwechsel sind über Variablen möglich.
- **Cons:** Lokale Modelle benötigen Betriebspflege; uncensored Community-Modelle erhöhen Provenienz-, Compliance- und Safety-Risiken; Embedding-Qualität für Deutsch ist bei `nomic-embed-text` nicht offiziell garantiert.
- **Decision:** Gewählt. Diese Alternative passt am besten zur local-first Architektur und zur GTX-1070-Hardware.

### Alternative B: Nur offizielle Modelle ohne Community-Uncensored-Variante

- **Pros:** Geringeres Provenienz- und Compliance-Risiko; klarere Lizenz- und Upstream-Situation; besser dokumentierter Fallback über `qwen3.5:9b`.
- **Cons:** Ändert das aktuell gewünschte Antwortverhalten; kann stärkere Safety-/Refusal-Mechanismen haben; erfordert erneute Prompt- und Qualitätstests für Research-Summaries.
- **Decision:** Nicht als Default gewählt, aber als Fallback definiert.

### Alternative C: Cloud-LLM-Fallback

- **Pros:** Höhere Verfügbarkeit; potentiell bessere Qualität und längere Kontexte; weniger lokale Hardware-Abhängigkeit.
- **Cons:** Widerspricht local-first und zero-API-dependency; erhöht Datenschutz-, Kosten-, Compliance- und Secret-Management-Risiken; koppelt Research-Läufe an externe Provider.
- **Decision:** Abgelehnt als Default. Nur mit explizitem `ALLOW_CLOUD=true` zulässig.

### Alternative D: Ein einziges Modell für Chat und Embeddings

- **Pros:** Weniger Konfigurationsvariablen; scheinbar einfacherer Betrieb.
- **Cons:** Chatmodelle sind nicht automatisch gute Embedding-Modelle; `nomic-embed-text` ist embedding-only; Vermischung der Rollen verschlechtert Kohäsion und erschwert Tests.
- **Decision:** Abgelehnt. Rollen müssen getrennt bleiben.

## Consequences

### Positive

- Klare Modellrollen reduzieren Kopplung zwischen Chat-, Summary- und Vektorindex-Code.
- `OLLAMA_CHAT_MODEL` und `OLLAMA_EMBEDDING_MODEL` werden als aktive Schnittstellen stabilisiert.
- Lokaler Betrieb schützt sensible Research-Daten vor unbeabsichtigtem Cloud-Abfluss.
- CPU-seitige Embeddings entlasten das knappe VRAM-Budget der GTX 1070.
- Explizite Fallback-Regel ermöglicht spätere Modellwechsel ohne Architekturbruch.

### Negative

- Deutsche Embedding-Qualität ist bei `nomic-embed-text` nicht offiziell garantiert.
- Uncensored Community-Modelle tragen Provenienz-, Compliance- und Safety-Risiken.
- Modellnamen unterscheiden sich aktuell zwischen `.env.example` und aktiven Skripten; der Abgleich bleibt notwendig und ist in Issue #62 zu verfolgen.
- Lokaler Modellbetrieb erfordert Startup-/Smoke-Checks und klare Fehlermeldungen bei fehlenden Modellen.

### Risiken

| Risiko | Impact | Mitigation |
|---|---|---|
| Community-Modell mit unklarer Provenienz | Compliance-/Safety-Risiko | Offizielle Basis und Fork dokumentieren; Fallback `qwen3.5:9b`; keine Cloud ohne Opt-in |
| VRAM-Überlauf auf GTX 1070 | Instabile Laufzeit oder OOM | Nur ein GPU-Modellserver aktiv; Kontext begrenzen; Embeddings CPU-seitig halten |
| Modellnamensdrift | Fehlkonfiguration und Smoke-Test-Fehler | Issue #62; zentrale Variablen `OLLAMA_CHAT_MODEL`/`OLLAMA_EMBEDDING_MODEL` |
| Deutsch-Embedding-Schwäche | Schlechtere Retrieval-Qualität | Tests mit deutschen Queries; späterer Swap auf deutsches/multilinguales Embedding-Modell möglich |
| Unbeabsichtigter Cloud-Fallback | Datenschutz- und Kostenrisiko | `ALLOW_CLOUD=true` als explizite Schranke; Default lokal |

## Architecture Review Checklist

- [x] New dependency justified? **Keine neue Dependency; Nutzung bestehender lokaler Ollama-Modelle.**
- [x] Module coupling acceptable? **Verbessert durch Rollenvariablen statt verstreuter Modellnamen.**
- [x] Data flow documented and secure? **Lokale Eingaben → lokaler Ollama-Chat/Embedding-Endpunkt → lokale Reports/Indizes; kein Cloud-Fallback ohne Opt-in.**
- [x] Error handling strategy consistent? **Fehlende Modelle müssen über Smoke-/Startup-Checks sichtbar werden.**
- [x] Scaling bottlenecks identified? **GTX-1070-VRAM limitiert parallele GPU-Modelle; Embeddings bleiben CPU-seitig.**
- [x] Security boundaries clearly defined? **Community-Modell-Provenienz dokumentiert; Cloud nur mit `ALLOW_CLOUD=true`.**
- [x] Testing strategy adequate? **Smoke-Tests für Modellverfügbarkeit, direkte Antworten mit `think=false`, deutsche Retrieval-Queries.**

## References

- Issue #62: Abgleich der Modellnamen zwischen `.env.example`, Skripten und Dokumentation.
- `docs/llm/model-inventory.md` — Lokales Modellinventar.
- `docs/llm/model-selection-policy.md` — Model-Auswahlrichtlinie.
- `README.md` — Hardware- und Betriebsnotizen.
- `tests/test_vram.py` — VRAM-Annahmen für GTX 1070.
- `scripts/runtime_smoke.py` — Runtime-Smoke-Checks und Cloud-Schranke.
- `scripts/research_happy_path.py` — Aktive Ollama-Modellvariablen.
- `Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive` — Lokale Qwen-Modelfile-Konfiguration.
- Ollama `nomic-embed-text`: <https://ollama.com/library/nomic-embed-text>
- Hugging Face `nomic-ai/nomic-embed-text-v1.5`: <https://huggingface.co/nomic-ai/nomic-embed-text-v1.5>
- Ollama `qwen3.5`: <https://ollama.com/library/qwen3.5>
- Hugging Face `Qwen/Qwen3.5-9B`: <https://huggingface.co/Qwen/Qwen3.5-9B>
- Hugging Face `HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive`: <https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive>
- Ollama API Docs: <https://github.com/ollama/ollama/blob/main/docs/api.md>

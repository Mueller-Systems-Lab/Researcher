# Changelog – Iteration 1

## Metadaten

- **Datum:** 2026-05-16
- **Typ:** Erste Projektiteration – Spezifikation, Infrastruktur, Ollama und Dokumentation
- **Bereich:** Planung, Setup, Betriebsdoku

## Git-Commits dieser Iteration

| Commit | Änderung |
|---|---|
| `e6f8be9` | `spec: Erster Durchlauf – OpenSpec-Artefakte, Dokumentation, 11 GitHub-Issues` |
| `1540494` | `feat(infrastructure): add .env.example and requirements.txt for T-001` |
| `5015181` | `feat(ollama): add Qwen3.5-9B-Uncensored-HauhauCS-Aggressive model setup (T-002)` |

## Task-Status (T-001 bis T-011)

| Task | Status | Bemerkung |
|---|---|---|
| T-001 | abgeschlossen | Basis-Umgebung, `.env.example`, `requirements.txt` |
| T-002 | abgeschlossen | Ollama-/Qwen3.5-Setup über Modelfile |
| T-003 | offen | SearXNG-Docker-Setup |
| T-004 | offen | GPT-Researcher-Fork konfigurieren |
| T-005 | offen | Darknet-Crawler implementieren |
| T-006 | offen | Whoosh-Index + DarknetRetriever |
| T-007 | offen | CompositeRetriever |
| T-008 | offen | ChromaDB + Embeddings |
| T-009 | offen | VRAM-Optimierungen |
| T-010 | offen | Integrationstests & Systemvalidierung |
| T-011 | abgeschlossen | README, Troubleshooting und Changelog finalisiert |

## Erstellte Dateien und Artefakte

### Projektgrundlage

- `openspec/config.yaml`
- `proposal.md`
- `specs/delta-specs.md`
- `design.md`
- `tasks.md`
- `blueprint.md`

### Dokumentation

- `docs/architecture.md`
- `docs/blueprint-analysis.md`
- `docs/module-map.md`
- `docs/dependency-graph.md`
- `docs/integration-plan.md`
- `docs/workflows/issue-resolution.md`
- `README.md`
- `docs/troubleshooting.md`
- `docs/changelog/iteration-1.md`
- `docs/searxng-local-setup.md`

### Issue-Prompts

- `docs/prompts/issues/issue-1.md` bis `docs/prompts/issues/issue-11.md`

### Laufzeit- und Infrastrukturdateien

- `.env.example`
- `requirements.txt`
- `.gitignore`
- `Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive`
- `research-serve.sh`
- `serve_qwen3.5_uncensored.sh`

## Implementierte Features / Komponenten

- Lokales LLM-Setup mit Ollama und Qwen3.5-9B-Uncensored-HauhauCS-Aggressive **(deprecated, ersetzt durch Gemma 4 OBLITERATED)**
- Lokales Embedding-Setup mit `nomic-embed-text`
- Lokale Websuche über SearXNG
- Modellserver-Verwaltung per `research-serve.sh`
- Direktstart des Qwen3.5-Servers per `serve_qwen3.5_uncensored.sh` **(deprecated)**
- Architektur- und Betriebsdokumentation für das komplette lokale Research-System

> **Aktuelles Chat-Modell (seit v0.1.0-local-alpha):** Gemma 4 E4B OBLITERATED via llama-server (Port 8081, ~3.8 GB VRAM). Siehe `docs/adr/ADR-016-gemma4-chat-model.md`.

## Offene Punkte / Bekannte Einschränkungen

- T-003 bis T-010 sind im Git-Log noch nicht als fertige Implementierung sichtbar.
- Für T-003 liegt jetzt eine dokumentierte Zielkonfiguration auf Basis der offiziellen SearXNG-Doku vor.
- Auf der GTX 1070 sollte immer nur ein Modellserver gleichzeitig laufen.
- Embeddings sind CPU-basiert und dürfen die GPU nicht verdrängen.
- Der Darknet-Crawler benötigt Tor und eine gesonderte rechtliche Prüfung.
- Alle hier gelisteten Commits sind die im lokalen Git-Log nachvollziehbaren Änderungen dieser Iteration.

## Status

- Dokumentation dieser Iteration ist abgeschlossen.
- Die funktionalen Implementierungen außerhalb von T-001 und T-002 sind im Repository-Log noch nicht belegt.

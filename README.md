# Researcher — Lokales, unzensiertes Research-System

[![CI](https://github.com/Mueller-Systems-Lab/Researcher/actions/workflows/test.yml/badge.svg)](https://github.com/Mueller-Systems-Lab/Researcher/actions/workflows/test.yml)
[![Coverage](https://img.shields.io/badge/coverage-78%25-green)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![Positron-tested](https://img.shields.io/badge/positron-tested-7B2FF5?logo=github)]()

> **Current Status:** v0.2.4 — Release Candidate
> **Release:** [Changelog](CHANGELOG.md) · [Release Notes](RELEASE_NOTES.md) · [Known Limitations](docs/release/known-limitations.md)

Researcher ist ein vollständig lokales Research-System auf Basis von GPT Researcher. Es nutzt ein lokales LLM, lokale Websuche, einen Darknet-Crawler und einen lokalen Vektorspeicher — ohne externe API-Aufrufe.

<p align="left">
  <img src="docs/brand/mueller-systems-lab-icon.svg" alt="Mueller-Systems-Lab" width="96">
</p>

Entwickelt von [Mueller-Systems-Lab](https://github.com/Mueller-Systems-Lab). Researcher bleibt ein eigenständiges internes System.

## Shortcuts

```bash
make quality      # Lint + Typecheck + Security + Tests + Coverage (30s)
make runtime-smoke    # Prüft Ollama, SearXNG, Tor, Cloud (5s)
make research-happy-path  # Query → SearXNG → Ollama → Report
make research-evaluate    # Report Quality (Overall: 99/100)
```

## Developer Quickstart (keine externen Dienste nötig)

```bash
# 1. Clone & Setup
git clone https://github.com/xxammaxx/Researcher.git
cd Researcher
git submodule update --init --recursive

# 2. Virtuelle Umgebung
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Quality Gates (alle grün erwartet)
make quality        # lint + typecheck + security + tests (~30s)
make coverage       # Coverage >=78% (~10s)
make test-e2e       # E2E Pipeline (~1s)

# 4. Optional: kompletter CI-Lauf
make ci-local       # quality + coverage + e2e (~45s)
```

> **Hinweis:** Für den Developer-Quickstart werden KEINE externen Dienste (Ollama, SearXNG, Tor, GPU) benötigt. Alle Tests laufen mit Mocks.

## Kurzstart (mit Runtime-Diensten)

1. Voraussetzungen installieren: Python, Docker, Ollama, Tor.
2. Repository klonen und virtuelle Umgebung anlegen.
3. `.env.example` nach `.env` kopieren und anpassen.
4. Ollama starten, Modell registrieren, Embeddings laden.
5. SearXNG per Docker Compose starten.
6. Web-UI starten und eine Test-Recherche ausführen.

## Optional: Runtime-Smoke-Test

```bash
make runtime-smoke        # Prüft Ollama, SearXNG, Tor, Cloud-Blocker
make runtime-smoke-strict # Strict-Mode: alle Dienste müssen laufen
```

> Diese Tests sind optional und nicht Bestandteil von `make quality` oder CI.

## Architekturübersicht

```text
Nutzer
  |
  v
GPT Researcher (Web-UI + Orchestrator)
  |
  v
CompositeRetriever
  |---------------------------|
  |                           |
  v                           v
SearXNG (lokale Websuche)     Darknet-Crawler + Whoosh
  |                           |
  |                           v
  |                     Darknet-Index (ADR-008: SQLite FTS5 geplant)
  |                           |
  |---------------------------|
               |
               v
    llama-server (Gemma 4 Chat)    Ollama (nomic-embed-text, CPU)
               |                               |
               v                               v
         Report-Generierung               ChromaDB
```

## Voraussetzungen

| Komponente | Anforderung |
|---|---|
| GPU | NVIDIA GTX 1070 (8 GB VRAM) oder vergleichbar |
| RAM | 16 GB oder mehr |
| Speicher | 50 GB freier SSD-Platz oder mehr |
| Betriebssystem | Linux (getestet) |
| Python | >= 3.11 |
| Container | Docker für SearXNG |
| LLM Chat | llama-server (Gemma 4 OBLITERATED, Port 8081, ~3.8 GB VRAM) |
| LLM Embedding | Ollama + nomic-embed-text (Port 11434, CPU-seitig) |
| Darknet-Zugriff | Tor für den Crawler |

## Setup

### 1) Repository klonen

```bash
git clone https://github.com/xxammaxx/Researcher.git
cd Researcher
```

### 2) Python-Virtualenv erstellen und Abhängigkeiten installieren

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Umgebungskonfiguration anlegen

```bash
cp .env.example .env
```

Danach `.env` an die lokale Umgebung anpassen. Die vollständige Referenz steht weiter unten.

Die aktiven Modellvariablen sind in `.env.example` dokumentiert. Chat: `gemma4-obliterated` via llama-server (Port 8081). Embedding: `nomic-embed-text:latest` via Ollama (Port 11434, CPU).

### 4) Gemma 4 Chat-Modell starten (via llama-server)

```bash
./serve_gemma4_obliterated_researcher.sh
```

Der Server läuft auf `127.0.0.1:8081` mit Alias `gemma4-obliterated`.
VRAM: ~3.8 GB. Precision Trap: `-ctk f32 -ctv f32` zwingend auf Pascal (GTX 1070).

> **Hinweis:** Chat läuft via llama-server (eigenständig), **nicht** via Ollama.
> qwen3.5 ist deprecated — siehe `docs/adr/ADR-016-gemma4-chat-model.md`.

### 5) Embedding-Modell laden (Ollama, CPU-seitig)

### 6) Embedding-Modell laden

```bash
ollama pull nomic-embed-text
```

### 7) SearXNG starten

```bash
docker compose -f searxng/docker-compose.yml up -d
```

### 8) Darknet-Crawler konfigurieren

- Tor muss lokal auf `127.0.0.1:9050` laufen.
- Der Crawler schreibt aktuell in den lokalen Whoosh-Index unter `DARKNET_INDEX_PATH`; die Ablösung durch SQLite FTS5 ist in `docs/adr/ADR-014-whoosh-migration.md` dokumentiert.
- Darknet-Zugriffe nur mit rechtlicher Prüfung und klarer Zielsetzung durchführen.

### 9) GPT Researcher Web-UI starten

```bash
python -m gpt_researcher --stream
```

### 10) Browser öffnen

```text
http://localhost:8000
```

## Betriebsanleitung

### Terminal-Layout für den Normalbetrieb

```text
Terminal 1: ./serve_gemma4_obliterated_researcher.sh   ← Chat-Modell (Port 8081)
Terminal 2: ollama serve                                ← Embedding (Port 11434, CPU)
Terminal 3: docker compose -f searxng/docker-compose.yml up -d
Terminal 4: ./scripts/start-researcher.sh                ← GPT Researcher + Dashboard
```

**GPU-Dashboard:** Öffne `http://localhost:8000/dashboard` im Browser, um
GPU-Auslastung, VRAM-Verbrauch und Temperatur live zu überwachen.
Das Dashboard ist direkt in die GPT-Researcher-Web-UI eingebettet.

Dashboard ohne GPU-Überwachung starten:
```bash
./scripts/start-researcher.sh --no-dashboard
```

### research-serve.sh

Das Skript verwaltet die lokalen Modellserver für die 8-GB-VRAM-Workstation. Es stellt sicher, dass nur ein Modell gleichzeitig läuft.

```bash
./research-serve.sh qwen
./research-serve.sh qwen3.5
./research-serve.sh gemma
./research-serve.sh gemma4
./research-serve.sh status
./research-serve.sh stop
./research-serve.sh restart-qwen
./research-serve.sh restart-gemma
```

### serve_gemma4_obliterated_researcher.sh

Start des Gemma 4 Chat-Modells via llama-server (eigenständig, kein Ollama):

```bash
./serve_gemma4_obliterated_researcher.sh
```

Der Server lauscht lokal auf `127.0.0.1:8081`. Alias: `gemma4-obliterated`.

> **Historisch:** `serve_qwen3.5_uncensored.sh` (qwen3.5, Port 8086) ist deprecated.

### Wichtige Kontrollbefehle

```bash
ollama list
curl http://localhost:8080/search?q=test&format=json
curl http://127.0.0.1:8081/v1/models
./research-serve.sh status
```

## Local UI

GPU-Dashboard läuft lokal unter `http://127.0.0.1:8888`. Details: [UI Local Readiness](docs/development/ui-local-readiness.md).

## Tests

- Echte Playwright-Browser-/Screenshot-Tests liegen unter `tests/playwright/`.
- Ausführung: `RUN_PLAYWRIGHT_TESTS=true python -m pytest tests/playwright/test_dashboard_visual_regression.py -v`

## `.env`-Konfigurationsreferenz

| Variable | Beschreibung |
|---|---|
| `LLM_PROVIDER` | Provider für die Textgenerierung; aktuell `openai` (llama-server). |
| `OPENAI_BASE_URL` | Basis-URL des llama-Servers (z. B. `http://127.0.0.1:8081/v1`). |
| `FAST_LLM` / `SMART_LLM` / `STRATEGIC_LLM` | GPT-Researcher-Modellvariablen; aktuell `openai:gemma4-obliterated`. |
| `OLLAMA_CHAT_MODEL` | Chat-Modell für den Ollama-Fallback-Pfad; siehe `docs/llm/model-selection-policy.md`. |
| `OLLAMA_EMBEDDING_MODEL` | Embedding-Modell in Ollama; siehe `docs/llm/model-selection-policy.md`. |
| `ALLOW_OLLAMA_MODEL_FALLBACK` | Erlaubt einen Chat-Modell-Fallback, falls das konfigurierte Modell fehlt; Embedding-Modelle werden nie als Chat-Fallback genutzt. |
| `RETRIEVER` | Retriever-Modus; `custom` aktiviert den CompositeRetriever. |
| `SEARX_URL` | Basis-URL des lokalen SearXNG-Dienstes. |
| `SEARX_MAX_RESULTS` | Maximale Trefferzahl pro SearXNG-Abfrage. |
| `DARKNET_ENABLED` | Aktiviert oder deaktiviert die Darknet-Suche. |
| `DARKNET_INDEX_PATH` | Pfad zum lokalen Darknet-Index (aktuell Whoosh; Migration zu SQLite FTS5 via ADR-008 geplant). |
| `EMBEDDING_PROVIDER` | Provider für Embeddings; aktuell `ollama`. |
| `EMBEDDING` | Legacy-GPT-Researcher-Embedding-Setting im Format `ollama:<model>`; in `.env.example` aktuell `ollama:nomic-embed-text:latest`. |
| `CHROMA_PERSIST_DIRECTORY` | Persistenzverzeichnis für ChromaDB. |
| `CHROMA_COLLECTION` | Name der ChromaDB-Collection. |
| `EMBEDDING_BATCH_SIZE` | Batch-Größe für Embeddings; klein halten für CPU-Betrieb. |
| `MAX_SEARCH_RESULTS_PER_QUERY` | Gesamtzahl der Suchergebnisse pro Query. |
| `MAX_SUBTOPICS` | Maximale Anzahl an Subtopics pro Recherche. |
| `REPORT_SOURCE` | Quelle für den Report; aktuell `web`. |
| `MAX_CONCURRENT_REQUESTS` | Maximale Anzahl gleichzeitiger LLM-Anfragen. |
| `OLLAMA_NUM_PARALLEL` | Interne Ollama-Parallelisierung; für GTX 1070 auf `1` setzen. |

## Verzeichnisstruktur

| Pfad | Zweck |
|---|---|
| `README.md` | Einstieg, Setup und Betriebsanleitung. |
| `requirements.txt` | Python-Abhängigkeiten. |
| `.env.example` | Vorlage für die lokale Konfiguration. |
| `serve_gemma4_obliterated_researcher.sh` | Start des Gemma 4 Chat-Modells via llama-server. |
| `Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive` | Historische Ollama-Modelldefinition (qwen3.5, deprecated). |
| `research-serve.sh` | Umschalten und Verwalten der lokalen Modellserver. |
| `serve_qwen3.5_uncensored.sh` | Historischer Qwen3.5-Start via llama.cpp (deprecated). |
| `docs/architecture.md` | Architektur- und Laufzeitdokumentation. |
| `docs/troubleshooting.md` | Fehlerdiagnosen und Lösungen. |
| `docs/changelog/iteration-1.md` | Änderungsprotokoll der ersten Iteration. |
| `docs/changelog/iteration-2.md` | Änderungsprotokoll der Audit- und Repair-Iteration. |
| `docs/prompts/issues/` | Issue-Prompts für die Dokumentations- und Implementierungsschritte. |

## Hinweise

- Auf der GTX 1070 ist nur **ein** Modellserver gleichzeitig sinnvoll.
- Embeddings laufen CPU-seitig und sollen die GPU nicht blockieren.
- Der Darknet-Crawler benötigt Tor und eine separate rechtliche Prüfung.
- Whoosh ist derzeit noch aktiv, aber per ADR-008 als Ablöse-Kandidat markiert.
- Wenn ein Backend ausfällt, arbeitet der CompositeRetriever mit den verbleibenden Quellen weiter.
- SearXNG wird lokal per `127.0.0.1:8080` bereitgestellt; Details stehen in `docs/searxng-local-setup.md`.

## Test-Recherche

Nach dem Start aller Komponenten eine kurze Probeabfrage ausführen und prüfen, ob Quellen aus SearXNG oder dem Darknet-Index im Bericht erscheinen.

## Weiterführend

- `docs/architecture.md`
- `docs/troubleshooting.md`
- `docs/changelog/iteration-1.md`
- `docs/changelog/iteration-2.md`
- `docs/searxng-local-setup.md`

# Researcher — Lokales, unzensiertes Research-System

[![CI](https://github.com/xxammaxx/Researcher/actions/workflows/test.yml/badge.svg)](https://github.com/xxammaxx/Researcher/actions/workflows/test.yml)
[![Coverage](https://img.shields.io/badge/coverage-75%25-yellowgreen)]()

Researcher ist ein vollständig lokales Research-System auf Basis von GPT Researcher. Es nutzt ein lokales LLM, lokale Websuche, einen Darknet-Crawler und einen lokalen Vektorspeicher — ohne externe API-Aufrufe.

## Kurzstart

1. Voraussetzungen installieren: Python, Docker, Ollama, Tor.
2. Repository klonen und virtuelle Umgebung anlegen.
3. `.env.example` nach `.env` kopieren und anpassen.
4. Ollama starten, Modell registrieren, Embeddings laden.
5. SearXNG per Docker Compose starten.
6. Web-UI starten und eine Test-Recherche ausführen.

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
  |                     Darknet-Index
  |                           |
  |---------------------------|
              |
              v
   Ollama (Qwen3.5 + Embeddings)
              |
              v
           ChromaDB
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
| LLM | Ollama für Textgenerierung und Embeddings |
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

### 4) Ollama installieren und starten

```bash
ollama serve
```

### 5) Qwen3.5-Modell bereitstellen

```bash
ollama create qwen3.5-9b-uncensored-hauhaucs-aggressive -f Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive
```

Alternative mit llama.cpp:

```bash
./serve_qwen3.5_uncensored.sh
```

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
- Der Crawler schreibt in den Whoosh-Index unter `DARKNET_INDEX_PATH`.
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
Terminal 1: ollama serve
Terminal 2: docker compose -f searxng/docker-compose.yml up -d
Terminal 3: ./research-serve.sh qwen
Terminal 4: ./scripts/start-researcher.sh    ← GPT Researcher + Dashboard
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

### serve_qwen3.5_uncensored.sh

Direkter Start des Qwen3.5-Servers via llama.cpp:

```bash
./serve_qwen3.5_uncensored.sh
```

Der Server lauscht lokal auf `127.0.0.1:8086`.

### Wichtige Kontrollbefehle

```bash
ollama list
curl http://localhost:8080/search?q=test&format=json
curl http://127.0.0.1:8086/v1/models
./research-serve.sh status
```

## `.env`-Konfigurationsreferenz

| Variable | Beschreibung |
|---|---|
| `LLM_PROVIDER` | Provider für die Textgenerierung; aktuell `ollama`. |
| `OLLAMA_BASE_URL` | Basis-URL des lokalen Ollama-Servers. |
| `LLM_MODEL` | Modellname in Ollama, z. B. `qwen3.5-9b-uncensored-hauhaucs-aggressive:latest`. |
| `RETRIEVER` | Retriever-Modus; `custom` aktiviert den CompositeRetriever. |
| `SEARX_URL` | Basis-URL des lokalen SearXNG-Dienstes. |
| `SEARX_MAX_RESULTS` | Maximale Trefferzahl pro SearXNG-Abfrage. |
| `DARKNET_ENABLED` | Aktiviert oder deaktiviert die Darknet-Suche. |
| `DARKNET_INDEX_PATH` | Pfad zum Whoosh-Index für Darknet-Inhalte. |
| `EMBEDDING_PROVIDER` | Provider für Embeddings; aktuell `ollama`. |
| `OLLAMA_EMBEDDING_MODEL` | Embedding-Modell in Ollama, z. B. `nomic-embed-text:latest`. |
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
| `Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive` | Ollama-Modelldefinition. |
| `research-serve.sh` | Umschalten und Verwalten der lokalen Modellserver. |
| `serve_qwen3.5_uncensored.sh` | Direkter Qwen3.5-Start via llama.cpp. |
| `docs/architecture.md` | Architektur- und Laufzeitdokumentation. |
| `docs/troubleshooting.md` | Fehlerdiagnosen und Lösungen. |
| `docs/changelog/iteration-1.md` | Änderungsprotokoll der ersten Iteration. |
| `docs/prompts/issues/` | Issue-Prompts für die Dokumentations- und Implementierungsschritte. |

## Hinweise

- Auf der GTX 1070 ist nur **ein** Modellserver gleichzeitig sinnvoll.
- Embeddings laufen CPU-seitig und sollen die GPU nicht blockieren.
- Der Darknet-Crawler benötigt Tor und eine separate rechtliche Prüfung.
- Wenn ein Backend ausfällt, arbeitet der CompositeRetriever mit den verbleibenden Quellen weiter.
- SearXNG wird lokal per `127.0.0.1:8080` bereitgestellt; Details stehen in `docs/searxng-local-setup.md`.

## Test-Recherche

Nach dem Start aller Komponenten eine kurze Probeabfrage ausführen und prüfen, ob Quellen aus SearXNG oder dem Darknet-Index im Bericht erscheinen.

## Weiterführend

- `docs/architecture.md`
- `docs/troubleshooting.md`
- `docs/changelog/iteration-1.md`
- `docs/searxng-local-setup.md`

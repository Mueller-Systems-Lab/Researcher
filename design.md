# Technisches Design: Lokales Research-System

## Metadaten
- **Status:** Draft
- **Erstellt:** 2026-05-16
- **Basiert auf:** blueprint.md, proposal.md

## Architekturübersicht

```
┌─────────────┐        ┌──────────────────────┐
│   User      │  HTTP  │  GPT Researcher Web  │
│ (Browser)   ├───────►│  UI / API            │
└─────────────┘        └──────────┬───────────┘
                                  │
                         ┌────────▼────────┐
                         │ Orchestrator     │
                         │ (conduct_res.)   │
                         └────────┬────────┘
                                  │
          ┌───────────────────────┼───────────────────┐
          │                       │                   │
 ┌────────▼───────┐    ┌─────────▼──────┐    ┌───────▼──────┐
 │ Composite Search│    │ LLM (Ollama)  │    │ ChromaDB     │
 │ (SearXNG +     │    │ Qwen3.5-9B    │    │ (w/ nomic-   │
 │  Darknet)      │    │ local GPU     │    │ embed-text)  │
 └────────┬───────┘    └───────┬────────┘    └───────▲──────┘
          │                    │                     │
 ┌────────▼───────┐   ┌───────▼────────┐            │
 │ SearXNG (Docker│   │ Tor (SOCKS5    │   Embedding│
 │ :8080)         │   │ :9050)         │   (CPU)    │
 └────────┬───────┘   └───────┬────────┘            │
          │                   │                     │
 ┌────────▼───────┐   ┌───────▼────────┐            │
 │ Internet (Web) │   │ Darknet Crawl  │            │
 └────────────────┘   │ + Whoosh Index ├────────────┘
                      └────────────────┘
```

## Entwurfsentscheidungen (ADR)

### ADR-001: Ollama statt llama.cpp direkt
- **Entscheidung:** Ollama als LLM-Serving-Backend
- **Grund:** Einfachere Modellverwaltung, REST-API, Embedding-Integration aus einer Hand
- **Alternativen:** llama.cpp direkt (mehr Kontrolle, aber komplexer); vLLM (GPU-intensiver)

### ADR-002: CompositeRetriever-Pattern
- **Entscheidung:** Ein CompositeRetriever fasst SearXNG + Darknet-Ergebnisse zusammen
- **Grund:** GPT Researcher erwartet einen einzelnen Retriever. Composite mergt parallel.
- **Alternativen:** Zwei separate Research-Durchläufe (langsamer); CustomSearchTool (komplexer)

### ADR-003: Embeddings auf CPU
- **Entscheidung:** nomic-embed-text läuft auf CPU, GPU bleibt exklusiv für LLM
- **Grund:** GTX 1070 hat nur 8 GB VRAM. LLM in Q4_K_M belegt ~4.8 GB + KV-Cache ~1 GB.
  Bleiben ~2.2 GB – zu wenig für parallele Embedding-Berechnungen.
- **Alternativen:** Kleinere Embedding-Batch-Size auf GPU (VRAM-Risiko)

### ADR-004: Whoosh statt Elasticsearch/Meilisearch für Darknet-Index
- **Entscheidung:** Whoosh (Pure-Python, dateibasiert)
- **Grund:** Keine zusätzliche Server-Infrastruktur. Für Darknet-Forum-Größenordnung ausreichend.
- **Alternativen:** Elasticsearch (Overkill, RAM-hungrig); Meilisearch (externer Prozess)

### ADR-005: Synthetische URIs für Darknet-Quellen
- **Entscheidung:** `darknet://<forum-id>/post/<post_id>` als Quellen-URL
- **Grund:** GPT Researcher erwartet URLs für Zitate. Synthetische URIs ermöglichen Referenzierung
  ohne dass die Original-.onion-Adresse im Report erscheinen muss.

## Datenfluss

### Recherche-Ablauf (conduct_research)
1. User stellt Query über Web-UI oder API
2. Orchestrator zerlegt Query in Subtopics (MAX_SUBTOPICS=3)
3. Für jedes Subtopic:
   a. CompositeRetriever.search(subtopic_query) → parallele SearXNG + Darknet-Abfrage
   b. Ergebnisse mergen und deduplizieren (anhand URL)
   c. LLM bewertet Relevanz der Ergebnisse
   d. ChromaDB speichert Embeddings der relevanten Quellen
4. LLM generiert finalen Report aus allen Subtopics
5. Report mit Quellenangaben an User zurückgeben

### Darknet-Crawling (Cron, out-of-band)
1. Tor-Client verbindet über SOCKS5 (127.0.0.1:9050)
2. Crawler meldet sich im Forum an (requests + BeautifulSoup)
3. Crawlt Thread-Seiten (max_pages pro Lauf)
4. Extrahiert: URL, Autor, Timestamp, Content
5. Schreibt in Whoosh-Index
6. Pausiert (time.sleep) zwischen Requests
7. Index-Optimierung nach jedem Crawl-Lauf

## Schnittstellen

### Ollama REST API
| Endpoint | Methode | Zweck |
|---|---|---|
| `/api/generate` | POST | Textgenerierung (LLM) |
| `/api/embeddings` | POST | Vektorerzeugung (Embedding) |
| `/api/tags` | GET | Verfügbare Modelle |

### SearXNG JSON-API
| Endpoint | Methode | Zweck |
|---|---|---|
| `/search?q=<query>&format=json` | GET | Websuche |

### CompositeRetriever
```python
def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
    """Parallele Suche in SearXNG + Darknet. Dedupliziert anhand URL."""
```

### DarknetRetriever
```python
def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
    """Volltextsuche im Whoosh-Index."""
```

### ChromaDB
| Operation | Beschreibung |
|---|---|
| `collection.add(embeddings, metadatas, documents)` | Embeddings speichern |
| `collection.query(query_embeddings, n_results)` | Ähnlichkeitssuche |

## Konfigurationsmanagement

Alle Konfiguration erfolgt über `.env` + `config/config.py`:
- `.env` für Umgebungsvariablen (nicht versioniert)
- `.env.example` als Vorlage (versioniert)
- `config/config.py` als Single Source of Truth für Defaults

## Fehlertoleranz

| Komponente | Fehlerszenario | Fallback |
|---|---|---|
| SearXNG | Nicht erreichbar | Nur Darknet-Ergebnisse, Warnung im Report |
| Darknet-Index | Leer / korrupt | Nur SearXNG-Ergebnisse |
| Ollama LLM | Timeout | Retry (max 3), dann Fehler |
| ChromaDB | Nicht erreichbar | Recherche ohne Wissensspeicherung |
| Tor | Nicht erreichbar | Darknet-Suche überspringen |

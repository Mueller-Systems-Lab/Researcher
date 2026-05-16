# Architektur-Dokumentation: Lokales Research-System

## Metadaten
- **Erstellt:** 2026-05-16
- **Version:** 1.0.0
- **Blueprint:** blueprint.md

## Systemkontext

Das System ist ein vollständig lokaler, zensurfreier Recherche-Assistent. Es läuft auf einer einzelnen Workstation (NVIDIA GTX 1070, 8 GB VRAM) und benötigt keine externen API-Zugriffe. Der Nutzer interagiert über einen Browser mit der GPT-Researcher-Web-UI.

### Systemgrenzen

```
┌───────────────────────────────────────────────────┐
│  Lokale Workstation (GTX 1070, 8GB VRAM)          │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │  GPT Researcher (Orchestrator)              │  │
│  │  ┌───────────┐  ┌───────────┐  ┌─────────┐ │  │
│  │  │Composite  │  │  LLM      │  │ChromaDB │ │  │
│  │  │Retriever  │  │  Service  │  │  Store   │ │  │
│  │  └─────┬─────┘  └─────┬─────┘  └────┬────┘ │  │
│  │        │              │              │      │  │
│  └────────┼──────────────┼──────────────┼──────┘  │
│           │              │              │         │
│  ┌────────▼──────┐ ┌────▼──────┐ ┌────▼──────┐   │
│  │ SearXNG       │ │ Ollama    │ │ nomic-    │   │
│  │ (Docker)      │ │ Server    │ │ embed     │   │
│  │ :8080         │ │ :11434    │ │ (CPU)     │   │
│  └───────┬───────┘ └───────────┘ └───────────┘   │
│          │                                        │
│  ┌───────▼───────┐  ┌─────────────────────────┐   │
│  │ Internet      │  │ Darknet Crawler +       │   │
│  │ (via Host)    │  │ Whoosh Index            │   │
│  └───────────────┘  │ (via Tor :9050)         │   │
│                     └─────────────────────────┘   │
└───────────────────────────────────────────────────┘
```

## Architekturmuster

### Primäres Muster: Orchestrator-Pipeline

GPT Researcher fungiert als Orchestrator, der den Recherche-Prozess steuert:
1. Query-Zerlegung in Subtopics
2. Parallele Quellensuche (CompositeRetriever)
3. LLM-basierte Relevanzbewertung
4. Report-Generierung (LLM)
5. Wissensspeicherung (ChromaDB)

### Sekundäre Muster

| Muster | Anwendung | Komponente |
|---|---|---|
| **Composite** | Parallele Suche + einheitliche Schnittstelle | CompositeRetriever |
| **Strategy** | Austauschbare Such-Backends | SearXNG / DarknetRetriever |
| **Repository** | Abstraktion des Wissensspeichers | ChromaDB |
| **Adapter** | Ollama REST API Kapselung | LLM_Service |
| **Observer (Cron)** | Periodischer Darknet-Crawl | Darknet_Crawler |

## Komponentendiagramm (C4 – Container)

```
Person(nutzer, "Forscher", "Startet Recherche-Anfragen über Browser")

Container(web_ui, "GPT Researcher Web UI", "Python/FastAPI", "Web-Interface auf :8000")
Container(orchestrator, "Orchestrator", "Python", "conduct_research()")
Container(ollama, "Ollama Server", "Go", "LLM + Embeddings auf :11434")
Container(searxng, "SearXNG", "Docker", "Websuche auf :8080")
Container(chromadb, "ChromaDB", "Python", "Vektordatenbank (Disk)")
Container(crawler, "Darknet Crawler", "Python", "Forum-Crawler via Tor")
ContainerDb(whoosh, "Whoosh Index", "Dateibasiert", "Volltextindex Darknet")

Rel(nutzer, web_ui, "Recherche-Anfrage", "HTTPS")
Rel(web_ui, orchestrator, "Forschungsauftrag", "Interner Call")
Rel(orchestrator, ollama, "Textgenerierung", "REST /api/generate")
Rel(orchestrator, searxng, "Websuche", "REST /search?format=json")
Rel(orchestrator, crawler, "Darknet-Suche", "Whoosh Query")
Rel(orchestrator, chromadb, "Embeddings speichern/lesen", "ChromaDB API")
Rel(ollama, chromadb, "Embedding-Berechnung", "Intern (CPU)")
Rel(crawler, whoosh, "Index schreiben", "Whoosh API")
```

## Laufzeitsicht

### Recherche-Sequenz

```
Nutzer        Web-UI      Orchestrator    CompositeR    SearXNG    DarknetR    LLM       ChromaDB
  │              │              │              │            │          │          │           │
  │─Query───────►│              │              │            │          │          │           │
  │              │─research()──►│              │            │          │          │           │
  │              │              │─subtopics───►│            │          │          │           │
  │              │              │              │─search()──►│          │          │           │
  │              │              │              │─search()─────────────►│          │           │
  │              │              │              │◄───results─│          │          │           │
  │              │              │              │◄───results────────────│          │           │
  │              │              │              │─merge+ddup │          │          │           │
  │              │              │◄──results────│            │          │          │           │
  │              │              │──────────────────────────────────────►│          │           │
  │              │              │◄─────────────report──────────────────│          │           │
  │              │              │──────────────────────────────────────────────────►│           │
  │              │◄──report─────│              │            │          │          │           │
  │◄──report────│              │              │            │          │          │           │
```

## Deployment-Sicht

### Terminal-Layout (Entwicklung)

```
┌──────────────────┬──────────────────┬──────────────────┐
│ Terminal 1       │ Terminal 2       │ Terminal 3       │
│ ollama serve     │ docker run       │ python crawler   │
│ (LLM + Embed)    │ searxng/searxng  │ (Darknet Cron)   │
│                  │ :8080            │                  │
├──────────────────┴──────────────────┴──────────────────┤
│ Terminal 4                                              │
│ python -m gpt_researcher --stream                       │
│ (Web-UI :8000)                                         │
└─────────────────────────────────────────────────────────┘
```

## Querschnittliche Aspekte

### Sicherheit
- Alle Dienste binden nur an `127.0.0.1` (kein externer Netzwerkzugriff)
- SearXNG im isolierten Docker-Container
- Darknet-Crawler über Tor (SOCKS5-Proxy, kein Exit-Node)
- Wegwerf-Account für Forum-Zugang
- Keine personenbezogenen Daten im Crawler

### Performance
- LLM: Q4_K_M-Quantisierung, max. 4.8 GB VRAM
- KV-Cache: ~1 GB (num_ctx=4096)
- Embedding: CPU-only, Batch-Size=8
- Keine parallelen LLM-Anfragen (MAX_CONCURRENT=1)
- SearXNG: Max. 10 Ergebnisse pro Query
- Composite: Max. 20 Ergebnisse gesamt

### Fehlertoleranz
- SearXNG down → Fallback auf Darknet-Only
- Darknet-Index leer → Fallback auf SearXNG-Only
- ChromaDB down → Recherche ohne Wissensspeicherung
- Ollama timeout → Retry (max. 3), dann Fehler
- Tor down → Darknet-Suche deaktiviert

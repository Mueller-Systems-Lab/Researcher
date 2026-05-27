# Modul-Map

## Metadaten
- **Erstellt:** 2026-05-16
- **Basiert auf:** blueprint.md, design.md

## Modulübersicht

```
┌─────────────────────────────────────────────────────────┐
│                    Lokales Research-System                │
├───────────────┬───────────────┬───────────────┬─────────┤
│ LLM_Service   │ Search_       │ Vector_Store  │ Darknet_ │
│               │ Composite     │ + Embedding   │ Crawler  │
├───────────────┤               │               │          │
│ - Ollama API  │ ┌─────────────┤ - ChromaDB    │ - Tor    │
│ - Qwen3.5-9B  │ │ SearXNG_    │ - nomic-embed │ - Login  │
│ - GPU Mgmt    │ │ Gateway     │               │ - Parser │
│ - VRAM Tuning │ │             │               │ - Cron   │
│               │ │ - Docker    │               │          │
│               │ │ - JSON API  │               │          │
│               │ ├─────────────┤               ├──────────┤
│               │ │ Darknet_    │               │ Darknet_ │
│               │ │ Search      │               │ Index    │
│               │ │             │               │          │
│               │ │ - Whoosh    │               │ - Schema │
│               │ │ - Retriever │               │ - Write  │
│               │ │ - URI Synth │               │ - Query  │
├───────────────┴─┴─────────────┴───────────────┴─────────┤
│                    Orchestrator                           │
│                    (GPT Researcher)                       │
│                    - conduct_research()                   │
│                    - Subtopics                            │
│                    - Report Generation                    │
└─────────────────────────────────────────────────────────┘
```

## Modul-Steckbriefe

### LLM_Service
| Attribut | Wert |
|---|---|
| **Verantwortung** | Textgenerierung, Report-Erstellung |
| **Technologie** | llama-server (eigenständig), Gemma 4 E4B OBLITERATED GGUF |
| **Schnittstelle** | OpenAI-kompatible REST API `localhost:8081/v1` |
| **Abhängigkeiten** | Keine (externer Dienst, eigenständiger Prozess) |
| **Kritikalität** | 🔴 Systemkritisch – ohne LLM keine Reports |
| **Dateien** | `serve_gemma4_obliterated_researcher.sh`, llama-server-Konfiguration |

### Search_Composite
| Attribut | Wert |
|---|---|
| **Verantwortung** | Parallele Suche in Web + Darknet, Result-Merge |
| **Technologie** | Python, asyncio |
| **Schnittstelle** | `CompositeRetriever.search(query, max_results)` |
| **Abhängigkeiten** | SearXNG_Gateway, Darknet_Search |
| **Kritikalität** | 🟡 Hoch – zentrale Suchlogik |
| **Dateien** | `gpt_researcher/retrievers/custom/custom.py` |

### SearXNG_Gateway
| Attribut | Wert |
|---|---|
| **Verantwortung** | Öffentliche Websuche |
| **Technologie** | Docker, SearXNG |
| **Schnittstelle** | JSON-API `localhost:8080/search` |
| **Abhängigkeiten** | Docker |
| **Kritikalität** | 🟡 Hoch – primäre Web-Quelle |
| **Dateien** | `searxng/settings.yml`, Docker-Run-Konfiguration |

### Darknet_Search
| Attribut | Wert |
|---|---|
| **Verantwortung** | Volltextsuche im Darknet-Forum-Index |
| **Technologie** | Whoosh (Pure-Python), DarknetRetriever |
| **Schnittstelle** | `DarknetRetriever.search(query, max_results)` |
| **Abhängigkeiten** | Darknet_Crawler, Darknet_Index |
| **Kritikalität** | 🟢 Mittel – optionale Quelle |
| **Dateien** | `gpt_researcher/retrievers/darknet/darknet.py` |

### Darknet_Crawler
| Attribut | Wert |
|---|---|
| **Verantwortung** | Forum-Crawling via Tor, HTML→Text |
| **Technologie** | Python, requests[socks], BeautifulSoup, Tor SOCKS5 |
| **Schnittstelle** | Cron-Job, schreibt in Whoosh-Index |
| **Abhängigkeiten** | Tor (127.0.0.1:9050) |
| **Kritikalität** | 🟢 Mittel – Datenquelle, kein Echtzeit-Dienst |
| **Dateien** | `crawlers/darknet_crawler.py` |

### Darknet_Index
| Attribut | Wert |
|---|---|
| **Verantwortung** | Whoosh-Volltextindex für Darknet-Posts |
| **Technologie** | Whoosh |
| **Schnittstelle** | Dateibasiert (`darknet_index/`) |
| **Abhängigkeiten** | Keine (reine Daten) |
| **Kritikalität** | 🟢 Mittel |
| **Dateien** | `darknet_index/` (Verzeichnis) |

### Vector_Store
| Attribut | Wert |
|---|---|
| **Verantwortung** | Wissensspeicherung und -abruf |
| **Technologie** | ChromaDB, nomic-embed-text |
| **Schnittstelle** | ChromaDB API, Ollama Embedding API |
| **Abhängigkeiten** | Ollama (Embedding), Embedding_Service |
| **Kritikalität** | 🟢 Niedrig – optional für Lernfähigkeit |
| **Dateien** | `chroma_db/`, `.env`-Konfiguration |

### Embedding_Service
| Attribut | Wert |
|---|---|
| **Verantwortung** | Text→Vektor-Transformation |
| **Technologie** | Ollama, nomic-embed-text (CPU) |
| **Schnittstelle** | Ollama `/api/embeddings` |
| **Abhängigkeiten** | Ollama Server |
| **Kritikalität** | 🟢 Niedrig |
| **Dateien** | Ollama-Konfiguration |

### Orchestrator
| Attribut | Wert |
|---|---|
| **Verantwortung** | Forschungsablauf-Steuerung |
| **Technologie** | GPT Researcher (Fork) |
| **Schnittstelle** | Web-UI (:8000), API |
| **Abhängigkeiten** | ALLE anderen Module |
| **Kritikalität** | 🔴 Systemkritisch |
| **Dateien** | `gpt_researcher/`, `config/`, `.env` |

## Modul-Abhängigkeiten (Matrix)

| | LLM | Composite | SearXNG | DarknetSearch | DarknetCrawl | Vector | Embedding | Orchestrator |
|---|---|---|---|---|---|---|---|---|
| **LLM** | - | | | | | | | ← |
| **Composite** | | - | → | → | | | | ← |
| **SearXNG** | | | - | | | | | ← |
| **DarknetSearch** | | | | - | ← | | | ← |
| **DarknetCrawl** | | | | → | - | | | |
| **Vector** | ←(emb) | | | | | - | ← | ← |
| **Embedding** | ← | | | | | → | - | ← |
| **Orchestrator** | → | → | → | → | | → | → | - |

Legende: `→` = "ruft auf", `←` = "wird aufgerufen von"

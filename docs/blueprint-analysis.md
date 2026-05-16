# Blueprint-Analyse

## Metadaten
- **Erstellt:** 2026-05-16
- **Blueprint:** blueprint.md (649 Zeilen)
- **Analyst:** Issue Orchestrator (AI)

## Zusammenfassung

Der Blueprint beschreibt den Aufbau eines vollständig lokalen, unzensierten Recherche-Assistenten auf Basis von GPT Researcher. Das System läuft auf einer NVIDIA GeForce GTX 1070 (8 GB VRAM), nutzt ein unzensiertes LLM (Qwen3-8B), integriert SearXNG für Websuche und einen eigenen Darknet-Forum-Crawler. Wissen wird in einer ChromaDB-Vektordatenbank persistiert.

## Blueprint-Vollständigkeitsprüfung

| Kriterium | Status | Anmerkung |
|---|---|---|
| Modulübersicht & Schnittstellen | ✅ | Abschnitt 5 – ASCII-Art Architekturdiagramm mit allen Komponenten und Datenflüssen |
| Technologie-Stack | ✅ | Abschnitte 1–4: Ollama, GPT Researcher, SearXNG, ChromaDB, Whoosh, Tor, nomic-embed-text |
| Architekturmuster | ✅ | Orchestrator-Pattern implizit im Diagramm; Composite-Strategy für Retriever |
| Funktionale Anforderungen | ✅ | Web-Suche, Darknet-Suche, Report-Generierung, Lernfähigkeit durch Vektordatenbank |
| Nicht-funktionale Anforderungen | ✅ | VRAM-Limit (8 GB), lokale Ausführung, keine externen APIs, Isolation, rechtliche Rahmenbedingungen |
| Datenfluss & Integrationspunkte | ✅ | Schritt-für-Schritt-Fahrplan in Abschnitt 5; Architekturdiagramm zeigt alle Verbindungen |
| Deployment & Betrieb | ✅ | Terminal-Layout, Docker-Commands, Cron-Job-Beschreibung, Ollama-Konfiguration |

**Fazit:** Blueprint ist vollständig und ausreichend detailliert für die OpenSpec-Artefakt-Erstellung.

## Kernkomponenten

### 1. LLM-Service (Ollama + Qwen3-8B-Uncensored)
- **Betrieb:** Ollama Server auf `localhost:11434`
- **Modell:** Qwen3-8B-Instruct-Uncensored (Abliterated), Q4_K_M GGUF
- **VRAM:** ~4.8 GB (Modell) + ~1 GB (KV-Cache bei ctx=4096) ≈ 5.8 GB / 8 GB
- **Template:** ChatML-Format mit `<|system|>`, `<|user|>`, `<|assistant|>` Tokens
- **Temperatur:** 0.7, Top-P: 0.9

### 2. Websuche (SearXNG)
- **Betrieb:** Docker-Container, Port `127.0.0.1:8080`
- **API:** JSON-API (`/search?q=...&format=json`)
- **Konfiguration:** settings.yml für Suchmaschinen-Auswahl
- **Rate-Limits:** Deaktiviert für lokale IPs

### 3. Darknet-Forum-Suche
- **Crawler:** Python-Skript mit `requests[socks]` über Tor SOCKS5
- **Login:** CSRF-Token-Extraktion via BeautifulSoup
- **Index:** Whoosh (Pure-Python, dateibasiert)
- **Retriever:** DarknetRetriever implementiert GPT-Researcher-Retriever-Schnittstelle
- **URIs:** Synthetisch (`darknet://<forum-id>/post/<id>`)

### 4. Vektordatenbank (ChromaDB + nomic-embed-text)
- **Embedding:** nomic-embed-text (137M Parameter, CPU-only)
- **Persistenz:** `chroma_db/` auf Disk
- **Collection:** `gpt_researcher`
- **Integration:** Autoconfig über `.env`-Variablen in GPT Researcher

### 5. Orchestrator (GPT Researcher)
- **Framework:** Fork von `assafelovic/gpt-researcher`
- **Customization:** CompositeRetriever, DarknetRetriever, SearXNG-Konfiguration
- **Ablauf:** Query → Subtopics → Search → LLM-Evaluation → Report

## Technische Risiken

| Risiko | Bewertung |
|---|---|
| **VRAM-Überlauf** – LLM (4.8 GB) + KV-Cache (1 GB) + Embedding (wenn GPU) = > 8 GB | 🔴 Hoch – Gegenmaßnahmen: Embedding auf CPU, num_ctx=4096, MAX_CONCURRENT=1 |
| **Darknet-Crawler-Blocking** – Forum erkennt und blockiert Crawler | 🟡 Mittel – Gegenmaßnahmen: Crawl-Pausen, User-Agent-Rotation |
| **Rechtliche Risiken Darknet** – Crawlen/Speichern illegaler Inhalte | 🔴 Kritisch – Gegenmaßnahmen: Fachanwalt konsultieren, Wegwerf-Account, Isolation |
| **Modell-Verfügbarkeit** – Qwen3-8B-Uncensored ist fiktiv | 🟡 Mittel – Gegenmaßnahmen: Alternatives unzensiertes 7B-Modell (z.B. Dolphin-Mistral) |
| **SearXNG-Kompatibilität** – API-Änderungen in neueren Versionen | 🟢 Niedrig – Gegenmaßnahmen: Version pinnen |
| **ChromaDB-Speicherüberlauf** – Wachsender Embedding-Speicher | 🟢 Niedrig – Gegenmaßnahmen: Persistenz auf Disk, regelmäßige Optimierung |

## Architekturentscheidungen (extrahiert aus Blueprint)

1. **Ollama statt llama.cpp direkt** → Begründung: Einfachere Modellverwaltung, Embeddings inklusive
2. **CompositeRetriever** → Begründung: GPT Researcher erwartet einen Retriever; Composite fasst Web + Darknet zusammen
3. **Embeddings auf CPU** → Begründung: GPU exklusiv für LLM reservieren
4. **Whoosh (nicht Elasticsearch)** → Begründung: Keine zusätzliche Server-Infrastruktur
5. **Synthetische Darknet-URIs** → Begründung: Quellenangaben im Report ohne .onion-Leak

## Empfohlene Modulaufteilung

Siehe `docs/module-map.md` und `design.md`.

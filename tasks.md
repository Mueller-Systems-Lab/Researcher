# Aufgabenzerlegung (Tasks)

## Metadaten
- **Erstellt:** 2026-05-16
- **Basiert auf:** blueprint.md, design.md, specs/delta-specs.md

## Übersicht

| ID | Task | Modul | Größe | Priorität | Abhängigkeiten |
|---|---|---|---|---|---|
| T-001 | Repository & Basis-Umgebung | Infrastructure | small | high | – |
| T-002 | Ollama + Qwen3.5-9B-Uncensored-HauhauCS-Aggressive einrichten | LLM_Service | small | high | – |
| T-003 | SearXNG Docker-Container aufsetzen | SearXNG_Gateway | small | high | – |
| T-004 | GPT Researcher Fork klonen & konfigurieren | Orchestrator | small | high | T-001 |
| T-005 | Darknet-Crawler implementieren | Darknet_Crawler | medium | high | – |
| T-006 | Whoosh-Index + DarknetRetriever | Darknet_Search | medium | high | T-005 |
| T-007 | CompositeRetriever implementieren | Search_Composite | medium | high | T-003, T-006 |
| T-008 | ChromaDB + Embeddings konfigurieren | Vector_Store, Embedding_Service | small | medium | T-004 |
| T-009 | VRAM-Optimierungen & GPU-Tuning | LLM_Service | small | high | T-002 |
| T-010 | Integrationstests & Systemvalidierung | – | medium | medium | T-007, T-008, T-009 |
| T-011 | Dokumentation & Betriebsanleitung | – | small | medium | T-010 |

---

## Task-Details

### T-001: Repository & Basis-Umgebung
- **Modul:** Infrastructure
- **Größe:** size:small
- **Priorität:** priority:high
- **Beschreibung:**
  - Git-Repository initialisieren
  - Python-Virtualenv anlegen
  - Abhängigkeiten aus `requirements.txt` installieren
  - `.env.example`-Vorlage erstellen
  - `.gitignore` konfigurieren
- **Betroffene Dateien (geschätzt):** 3
- **Akzeptanzkriterien:**
  - GIVEN das Repository ist geklont WHEN `pip install -r requirements.txt` ausgeführt wird THEN sind alle Abhängigkeiten installiert.
  - GIVEN `.env.example` existiert WHEN der Nutzer es nach `.env` kopiert THEN sind alle Variablen dokumentiert.

### T-002: Ollama + Qwen3.5-9B-Uncensored-HauhauCS-Aggressive einrichten
- **Modul:** LLM_Service
- **Größe:** size:small
- **Priorität:** priority:high
- **Beschreibung:**
  - Ollama-Installation prüfen
  - Modelfile für Qwen3.5-9B-Uncensored-HauhauCS-Aggressive erstellen
  - Modell in Ollama registrieren
  - Funktionalitätstest: Unzensierte Antwort prüfen
- **Betroffene Dateien (geschätzt):** 2
- **Akzeptanzkriterien:**
  - GIVEN Ollama läuft WHEN `ollama run qwen3.5-9b-uncensored-hauhaucs-aggressive "Erkläre das Darknet"` ausgeführt wird THEN zeigt das Modell KEINE Sicherheits-Verweigerung.
  - GIVEN das Modell ist geladen WHEN `ollama list` ausgeführt wird THEN erscheint `qwen3.5-9b-uncensored-hauhaucs-aggressive:latest` in der Liste.

### T-003: SearXNG Docker-Container aufsetzen
- **Modul:** SearXNG_Gateway
- **Größe:** size:small
- **Priorität:** priority:high
- **Beschreibung:**
  - Docker-Container mit SearXNG starten
  - Port-Bindung nur an 127.0.0.1
  - settings.yml anpassen (JSON-API aktivieren)
  - API-Erreichbarkeit testen
- **Betroffene Dateien (geschätzt):** 2
- **Akzeptanzkriterien:**
  - GIVEN Docker läuft WHEN `docker run -d -p 127.0.0.1:8080:8080 searxng/searxng` ausgeführt wird THEN ist SearXNG erreichbar.
  - GIVEN SearXNG läuft WHEN `curl http://localhost:8080/search?q=test\&format=json` ausgeführt wird THEN wird JSON zurückgegeben.

### T-004: GPT Researcher Fork klonen & konfigurieren
- **Modul:** Orchestrator
- **Größe:** size:small
- **Priorität:** priority:high
- **Beschreibung:**
  - GPT Researcher klonen/forken
  - `.env` konfigurieren (LLM, SearXNG, Embeddings)
  - `config/config.py` anpassen
  - Basisfunktionalität der Web-UI testen
- **Betroffene Dateien (geschätzt):** 3
- **Akzeptanzkriterien:**
  - GIVEN GPT Researcher ist geklont WHEN `python -m gpt_researcher` ausgeführt wird THEN startet die Web-UI.
  - GIVEN die `.env` ist konfiguriert WHEN eine Test-Recherche ausgeführt wird THEN wird das lokale LLM verwendet (kein OpenAI-API-Key nötig).

### T-005: Darknet-Crawler implementieren
- **Modul:** Darknet_Crawler
- **Größe:** size:medium
- **Priorität:** priority:high
- **Beschreibung:**
  - Tor-SOCKS5-Verbindung konfigurieren
  - Login-Skript mit CSRF-Token-Extraktion
  - Thread-Crawler mit HTML-Parsing (BeautifulSoup)
  - Crawl-Pausen und Rate-Limiting
  - Cron-Job für periodische Ausführung
- **Betroffene Dateien (geschätzt):** 4
- **Akzeptanzkriterien:**
  - GIVEN Tor läuft auf 127.0.0.1:9050 WHEN der Crawler gestartet wird THEN werden Forum-Posts extrahiert.
  - GIVEN der Crawler läuft WHEN eine Seite gecrawlt wird THEN wird `time.sleep()` zwischen Requests eingehalten.

### T-006: Whoosh-Index + DarknetRetriever
- **Modul:** Darknet_Search
- **Größe:** size:medium
- **Priorität:** priority:high
- **Abhängigkeiten:** T-005
- **Beschreibung:**
  - Whoosh-Schema definieren und Index anlegen
  - Crawler-Output in Index schreiben
  - DarknetRetriever-Klasse implementieren (erweitert GPT-Researcher Retriever)
  - In `gpt_researcher/retrievers/__init__.py` registrieren
  - Synthetische URI-Generierung
- **Betroffene Dateien (geschätzt):** 4
- **Akzeptanzkriterien:**
  - GIVEN der Whoosh-Index ist befüllt WHEN nach einem Begriff gesucht wird THEN werden relevante Posts zurückgegeben.
  - GIVEN ein Suchergebnis existiert WHEN es formatiert wird THEN enthält es eine `darknet://`-URI.

### T-007: CompositeRetriever implementieren
- **Modul:** Search_Composite
- **Größe:** size:medium
- **Priorität:** priority:high
- **Abhängigkeiten:** T-003, T-006
- **Beschreibung:**
  - CompositeRetriever-Klasse implementieren
  - Parallele Abfrage SearXNG + DarknetRetriever
  - Deduplizierung anhand URL
  - Fehlertoleranz: Fallback bei Ausfall eines Backends
  - In config.py registrieren (RETRIEVER=custom)
- **Betroffene Dateien (geschätzt):** 3
- **Akzeptanzkriterien:**
  - GIVEN beide Backends sind verfügbar WHEN `search(query)` aufgerufen wird THEN werden Ergebnisse aus beiden Quellen gemerged.
  - GIVEN SearXNG ist nicht erreichbar WHEN `search(query)` aufgerufen wird THEN werden nur Darknet-Ergebnisse zurückgegeben (kein Fehler).
  - GIVEN beide Backends liefern dieselbe URL WHEN gemerged wird THEN erscheint sie nur einmal.

### T-008: ChromaDB + Embeddings konfigurieren
- **Modul:** Vector_Store, Embedding_Service
- **Größe:** size:small
- **Priorität:** priority:medium
- **Abhängigkeiten:** T-004
- **Beschreibung:**
  - nomic-embed-text in Ollama pullen
  - ChromaDB-Persistenz konfigurieren
  - `.env`-Variablen setzen (EMBEDDING_PROVIDER, CHROMA_PERSIST_DIRECTORY, etc.)
  - Test: Embedding speichern und abrufen
- **Betroffene Dateien (geschätzt):** 2
- **Akzeptanzkriterien:**
  - GIVEN Ollama läuft WHEN `ollama pull nomic-embed-text` ausgeführt wird THEN ist das Modell verfügbar.
  - GIVEN ChromaDB ist konfiguriert WHEN eine Recherche abgeschlossen ist THEN sind Embeddings in `chroma_db/` persistiert.

### T-009: VRAM-Optimierungen & GPU-Tuning
- **Modul:** LLM_Service
- **Größe:** size:small
- **Priorität:** priority:high
- **Abhängigkeiten:** T-002
- **Beschreibung:**
  - num_ctx auf 4096 setzen
  - GPU-Layers in Ollama begrenzen
  - MAX_CONCURRENT_REQUESTS=1
  - OLLAMA_NUM_PARALLEL=1
  - Embedding-Batch-Size auf 8
  - VRAM-Monitoring und Dokumentation
- **Betroffene Dateien (geschätzt):** 2
- **Akzeptanzkriterien:**
  - GIVEN alle Tuning-Parameter sind gesetzt WHEN das System unter Last läuft THEN bleibt der VRAM-Verbrauch unter 7.5 GB.
  - GIVEN eine Embedding-Anfrage läuft WHEN gleichzeitig eine LLM-Anfrage kommt THEN wird sequenziell verarbeitet (kein VRAM-Overflow).

### T-010: Integrationstests & Systemvalidierung
- **Modul:** –
- **Größe:** size:medium
- **Priorität:** priority:medium
- **Abhängigkeiten:** T-007, T-008, T-009
- **Beschreibung:**
  - Integrationstest für CompositeRetriever (beide Backends)
  - Integrationstest für ChromaDB (Embeddings speichern + lesen)
  - End-to-End-Test: Recherche mit Web + Darknet-Quellen
  - VRAM-Monitoring unter Last
  - Fehlertoleranz-Tests (SearXNG down, Tor down, etc.)
- **Betroffene Dateien (geschätzt):** 5
- **Akzeptanzkriterien:**
  - GIVEN alle Komponenten laufen WHEN ein End-to-End-Test durchgeführt wird THEN wird ein vollständiger Report mit Quellen aus beiden Backends generiert.
  - GIVEN SearXNG ist gestoppt WHEN eine Recherche gestartet wird THEN werden nur Darknet-Quellen genutzt und eine Warnung ausgegeben.

### T-011: Dokumentation & Betriebsanleitung
- **Modul:** –
- **Größe:** size:small
- **Priorität:** priority:medium
- **Abhängigkeiten:** T-010
- **Beschreibung:**
  - README.md mit Setup-Anleitung
  - Betriebsanleitung (alle Terminal-Befehle)
  - Troubleshooting-Guide
  - Changelog finalisieren
- **Betroffene Dateien (geschätzt):** 3
- **Akzeptanzkriterien:**
  - GIVEN ein neuer Nutzer folgt der README.md WHEN alle Schritte ausgeführt wurden THEN läuft das System.
  - GIVEN das System zeigt einen Fehler WHEN der Troubleshooting-Guide konsultiert wird THEN ist der Fehler dokumentiert und hat eine Lösung.

---

## Abhängigkeitsgraph

```
T-001 ─────────────────────────────────────────────┐
                                                    │
T-002 ────── T-009 ─────────────────────────────────┤
                                                    │
T-003 ────────────────────┐                        │
                           ├── T-007 ──┐            │
T-005 ────── T-006 ────────┘           │            │
                                       ├── T-010 ── T-011
T-004 ────── T-008 ────────────────────┘            │
                                                    │
                                                    ▼
                                               System Ready
```

## Geschätzte Zeit

| Phase | Tasks | Geschätzte Zeit |
|---|---|---|
| Infrastruktur-Setup | T-001, T-002, T-003, T-004 | 4 × small = ~6 h |
| Darknet-Integration | T-005, T-006 | 2 × medium = ~8 h |
| Composite + Vektor | T-007, T-008 | 1 × medium + 1 × small = ~8 h |
| Optimierung + Tests | T-009, T-010 | 1 × small + 1 × medium = ~8 h |
| Dokumentation | T-011 | 1 × small = ~2 h |
| **Gesamt** | **11 Tasks** | **~32 h** |

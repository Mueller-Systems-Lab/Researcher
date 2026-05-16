# Delta-Specs: Initiale Spezifikation

## Metadaten
- **Status:** Draft
- **Erstellt:** 2026-05-16
- **Baseline:** Erster Durchlauf – keine Vorgängerversion

---

## SPEC-001: LLM-Integration (Ollama + Qwen3.5-9B-Uncensored-HauhauCS-Aggressive)

### HINZUGEFÜGT

#### LLM-001: Modell-Bereitstellung
- **SHALL** das System ein unzensiertes LLM über Ollama bereitstellen.
- **SHALL** das Modell in Q4_K_M-Quantisierung geladen werden (max. 5 GB VRAM).
- **SHALL** die Kontextgröße auf 4096 Tokens begrenzt sein.
- **MUST** die GPU exklusiv vom LLM genutzt werden (keine parallelen GPU-Workloads).

#### LLM-002: Textgenerierung
- **GIVEN** eine Prompt-Anfrage an `/api/generate` **WHEN** das Modell antwortet **THEN** **SHALL** die Antwort in weniger als 30 Sekunden zurückgegeben werden.
- **GIVEN** das System erhält eine unzensierte Anfrage **WHEN** das LLM antwortet **THEN** **MUST** das LLM keine Sicherheits-Verweigerung zeigen.

#### LLM-003: VRAM-Management
- **SHALL** `MAX_CONCURRENT_REQUESTS=1` gesetzt sein.
- **SHALL** `OLLAMA_NUM_PARALLEL=1` gesetzt sein.
- **SHALL** der VRAM-Verbrauch 7.5 GB nicht überschreiten.

---

## SPEC-002: Web-Suche (SearXNG)

### HINZUGEFÜGT

#### WEB-001: SearXNG-Bereitstellung
- **SHALL** SearXNG als Docker-Container laufen.
- **MUST** SearXNG nur an `127.0.0.1:8080` binden (kein externer Zugriff).
- **SHALL** die JSON-API aktiviert sein (`format=json`).

#### WEB-002: GPT-Researcher-Integration
- **SHALL** GPT Researcher SearXNG als `RETRIEVER=searx` ansprechen.
- **SHALL** `SEARX_MAX_RESULTS=10` als Default gelten.

---

## SPEC-003: Darknet-Forum-Crawler & Index

### HINZUGEFÜGT

#### DARK-001: Crawler-Architektur
- **SHALL** der Crawler über Tor SOCKS5 (127.0.0.1:9050) verbinden.
- **SHALL** der Crawler HTTP-Anfragen über `requests[socks]` ausführen.
- **MUST** der Crawler nur passives HTML-Parsing (BeautifulSoup/LXML) verwenden – kein JavaScript.
- **SHALL** der Crawler Login mit CSRF-Token unterstützen.

#### DARK-002: Whoosh-Volltextindex
- **SHALL** der Index ein Schema mit `url`, `author`, `timestamp`, `content` verwenden.
- **SHALL** `url` als unique key dienen.
- **SHALL** der Index auf Disk persistiert werden (`darknet_index/`).

#### DARK-003: Periodischer Crawl
- **SHALL** der Crawler per Cron periodisch ausgeführt werden.
- **SHALL** Crawl-Pausen (`time.sleep()`) zwischen Requests eingehalten werden.

#### DARK-004: DarknetRetriever
- **SHALL** der DarknetRetriever die abstrakte `Retriever`-Klasse von GPT Researcher erweitern.
- **SHALL** Suchergebnisse synthetische URIs (`darknet://<forum-id>/post/<id>`) enthalten.
- **SHALL** `max_results` aus der Retriever-Schnittstelle respektiert werden.

---

## SPEC-004: CompositeRetriever

### HINZUGEFÜGT

#### COMP-001: Parallele Suche
- **SHALL** der CompositeRetriever SearXNG und DarknetRetriever parallel abfragen.
- **SHALL** Ergebnisse anhand der URL dedupliziert werden.
- **SHALL** die Ergebnisliste auf maximal 20 Einträge begrenzt sein.

#### COMP-002: Fehlertoleranz
- **GIVEN** SearXNG ist nicht erreichbar **WHEN** eine Suche ausgeführt wird **THEN** **SHALL** nur Darknet-Ergebnisse zurückgegeben werden.
- **GIVEN** der Darknet-Index ist leer **WHEN** eine Suche ausgeführt wird **THEN** **SHALL** nur SearXNG-Ergebnisse zurückgegeben werden.

---

## SPEC-005: Vektordatenbank & Embeddings

### HINZUGEFÜGT

#### VEC-001: Embedding-Modell
- **SHALL** `nomic-embed-text` über Ollama als Embedding-Provider genutzt werden.
- **SHALL** Embeddings auf der CPU berechnet werden.
- **SHALL** `EMBEDDING_BATCH_SIZE=8` als Default gelten.

#### VEC-002: ChromaDB-Konfiguration
- **SHALL** ChromaDB persistent auf Disk speichern (`chroma_db/`).
- **SHALL** die Collection `gpt_researcher` heißen.
- **SHALL** Embeddings bei jeder Deep-Research-Iteration gespeichert werden.

#### VEC-003: Wissensabruf
- **GIVEN** eine frühere Recherche-Session hat Embeddings zu Thema X gespeichert **WHEN** eine neue Recherche zu Thema X gestartet wird **THEN** **SHALL** ChromaDB relevante Embeddings zurückliefern.

---

## SPEC-006: Konfiguration & Deployment

### HINZUGEFÜGT

#### CFG-001: Umgebungsvariablen
- **SHALL** alle Konfigurationen in `.env` definiert sein.
- **SHALL** eine `.env.example` ohne Secrets versioniert werden.
- **MUST** die `.env`-Datei in `.gitignore` stehen.

#### CFG-002: Isolation
- **SHOULD** der gesamte Stack in einer VM oder Docker-Compose-Umgebung laufen.
- **SHALL** SearXNG nur an `127.0.0.1` gebunden sein.

---

## SPEC-007: Test-Strategie

### HINZUGEFÜGT

#### TEST-001: Integrationstests
- **SHALL** jede Retriever-Implementierung einen Integrationstest haben.
- **SHALL** der CompositeRetriever Deduplizierung testen.
- **SHALL** die Ollama-Verbindung vor jedem Testlauf geprüft werden.

#### TEST-002: Infrastruktur-Tests
- **SHALL** SearXNG-Erreichbarkeit geprüft werden.
- **SHALL** ChromaDB-Verbindung geprüft werden.
- **SHALL** Whoosh-Index-Integrität geprüft werden.

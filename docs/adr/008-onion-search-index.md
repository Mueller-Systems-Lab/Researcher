# ADR-008: Onion Search Index

**Status:** Proposed

**Date:** 2026-05-16

**Deciders:** Architecture Review Agent

## Context

Issue #13 fordert einen Suchindex für die Onion Discovery Engine und nennt Meilisearch, Typesense und OpenSearch als mögliche Backends. Diese Forderung steht im Spannungsfeld zu bestehenden Entscheidungen:

- **ADR-004** in `design.md` etabliert Whoosh als Pure-Python, dateibasierten MVP-Index für Darknet-Inhalte, weil keine zusätzliche Server-Infrastruktur nötig ist.
- **ADR-006** definiert eine evidence-first Pipeline mit strikter Zonentrennung: Onion Zone disabled by default, Tor-Egress nur dort, Human Approval vor dauerhafter Speicherung, keine Live-Tor-Abfragen aus Retriever-/GPT-Researcher-Anfragen.
- **ADR-007** entscheidet für die Onion Discovery Engine Option A: Erweiterung des bestehenden Whoosh-basierten Darknet-Crawler-/Retriever-Pfads. Meilisearch/Typesense/OpenSearch bleiben dort als späterer Skalierungspfad offen.
- `onion_discovery/engine.py` ist bereits nach ADR-006/ADR-007 implementiert und indexiert freigegebene, niedrig riskante Discovery-Ergebnisse über `darknet_search.index.WhooshIndex`.
- `darknet_search/index.py` kapselt den aktuellen Whoosh-Index mit `add_post()`, `search()`, `optimize()`, `doc_count` und `clear()`.
- Die Zielumgebung ist eine lokale Workstation mit GTX 1070 und 8 GB VRAM. Parallel laufen bereits Ollama, ChromaDB und SearXNG; zusätzliche dauerhaft laufende Dienste müssen deshalb klar begründet werden.

Die Architekturfrage für Issue #13 lautet daher nicht nur „welcher Suchserver hat die meisten Features?“, sondern: Welcher Index ist der beste nächste Schritt für einen lokalen, sicherheitsbegrenzten Onion-MVP, der GPT-Researcher nur aus bereits freigegebenen lokalen Daten versorgt?

## Decision

Wir wählen **Option A: Whoosh bleibt der Suchindex für den MVP der Onion Discovery Engine**.

Gleichzeitig wird die Entscheidung präzisiert:

1. **T-013 / Issue #13 soll keinen sofortigen Wechsel auf Meilisearch, Typesense oder OpenSearch erzwingen.**
2. `darknet_search.index.WhooshIndex` bleibt das produktive Backend für den aktuellen Onion-/Darknet-MVP.
3. Die nächste Architekturverbesserung ist eine **Index-Repository-/Adapter-Schnittstelle** oberhalb von `WhooshIndex`, damit ein späteres Backend ohne Kopplung der Discovery Pipeline an einen konkreten Suchserver möglich wird.
4. **Meilisearch wird als bevorzugter späterer Skalierungspfad** vorgemerkt, wenn die konkreten Wechselkriterien erreicht werden.
5. Typesense bleibt zweite Skalierungsoption für sehr latenzkritische, RAM-bewusst dimensionierte Keyword-Suche.
6. OpenSearch wird für diese Single-Workstation-Architektur nicht als nächster Schritt empfohlen.

### Konkrete Schwellenwerte

Whoosh bleibt empfohlen, solange alle folgenden Bedingungen überwiegend erfüllt sind:

| Kriterium | MVP-Schwelle für Whoosh |
|---|---:|
| Freigegebene Dokumente | bis ca. 50.000 Dokumente |
| Suchbarer Text | bis ca. 1-2 GB bereinigter Text |
| Indexgröße auf Disk | bis ca. 2-5 GB |
| Schreibmuster | batch-/cron-basiert, wenige parallele Writes |
| Query-Last | Einzelplatzbetrieb, typ. < 1-2 Queries/Sekunde |
| Query-Ziel | Top 10-50 Treffer in < 500 ms bis ca. 2 s auf SSD |
| Feature-Bedarf | Volltext, Feldsuche, Basisscoring, Snippets reichen aus |

Ein Wechsel wird neu bewertet, wenn mindestens eines der folgenden Signale stabil erreicht wird:

- > 50.000-100.000 freigegebene Onion-Dokumente oder > 2 GB suchbarer Text.
- Wiederholte Query-Latenzen > 2 s für Top-20-Suchen trotz optimiertem Index.
- Mehrere gleichzeitige Leser/Writer oder häufige inkrementelle Updates führen zu Locking-/Stabilitätsproblemen.
- Facetten, Filter, Typo-Toleranz, Synonyme, Ranking-Regeln oder HTTP-basierte Search API werden funktional notwendig.
- Der Index soll als separater lokaler Dienst durch andere Tools konsumiert werden.

## Alternatives Considered

### Option A: Whoosh bleiben (ADR-004, ADR-007 Status Quo)

- **Ressourcen:** Kein eigener Dienst, kein Port, kein VRAM-Verbrauch. RAM-Verbrauch liegt im Python-Prozess und steigt mit Query/Writer-Operationen, bleibt für MVP typischerweise deutlich unter einem dedizierten Suchserver. Disk: dateibasierter Index unter `darknet_index/`.
- **Features:** Volltext, Feldsuche, Scoring, Parser, Snippets/Stored Fields möglich. Keine native Typo-Toleranz wie Meilisearch/Typesense, keine komfortablen Facetten, keine HTTP-API.
- **ADR-006-Konformität:** Sehr gut. Der Index ist lokal und offline nutzbar; Retriever löst keine Live-Tor-Abfragen aus. Human Approval kann vor `add_post()` erzwungen werden.
- **Betriebsaufwand:** Niedrig. Python-Abhängigkeit, Dateibackup, kein Docker-/Service-/Port-/Auth-Betrieb.
- **Security:** Gut. Keine Netzwerkoberfläche, dadurch minimale Expositionsfläche. Schutzbedarf liegt primär bei Dateirechten, Content-Redaktion und Ausgabe-Gates.
- **Wartbarkeit:** Gut für den Projektzustand, weil bereits implementiert. Risiko: Whoosh ist weniger aktiv als moderne Suchserver; deshalb Adapter-Schicht vorsehen.
- **Bewertung für GTX-1070-Workstation:** Beste Passung für den MVP, weil Ollama, ChromaDB und SearXNG nicht durch einen weiteren Dauerprozess belastet werden.
- **Entscheidung:** Gewählt.

### Option B: Auf Meilisearch wechseln

- **Ressourcen:** Zusätzlicher lokaler Suchserver, Standardport `localhost:7700`, eigener Datenpfad. Offizielle Doku zeigt Self-Hosting als separaten Prozess mit REST API, Master Key und `--http-addr`. RAM hängt vom Datensatz ab; für kleine Indizes leichtgewichtig, aber dauerhaft zusätzlich zu Ollama/Chroma/SearXNG.
- **Features:** Sehr gute Volltextsuche, Typo-Toleranz, Ranking-Regeln, Filter/Facetten, REST API, asynchrone Indexierungs-Tasks, Docker-/Binary-Betrieb.
- **ADR-006-Konformität:** Vereinbar, wenn ausschließlich `127.0.0.1`, API-Key, keine Clearnet-Exposition und Indexierung erst nach Human Approval. Zusätzlicher HTTP-Dienst erhöht aber Fehlkonfigurationsfläche.
- **Betriebsaufwand:** Mittel. Installation/Binary oder Docker, Konfiguration, Schlüsselverwaltung, Dumps/Backups, Health Checks, Upgrade-Pfad.
- **Security:** Akzeptabel bei `--http-addr 127.0.0.1:7700` und starkem Key. Riskanter als Whoosh, weil eine API existiert, die versehentlich exponiert werden könnte.
- **Wartbarkeit:** Gut. Aktive Entwicklung, breite Community, einfache Clients. Zusätzliche Schema-/Migrationslogik nötig.
- **Bewertung für GTX-1070-Workstation:** Sinnvoll als nächster Skalierungsschritt, sobald Whoosh-Latenz/Features nicht reichen. Für den aktuellen MVP noch nicht nötig.
- **Entscheidung:** Späterer bevorzugter Upgrade-Pfad, nicht sofort.

### Option C: Auf Typesense wechseln

- **Ressourcen:** Zusätzlicher lokaler Dienst, Standardport `8108`. Laut offizieller Doku ist Typesense ein In-Memory-Datastore; der Prozess startet leichtgewichtig (~20 MB ohne Daten), benötigt für Keyword-Suche aber typischerweise etwa 2x-3x RAM der durchsuchbaren Feldwerte und mindestens 2 vCPUs.
- **Features:** Sehr schnelle Keyword-Suche, Typisierung/Schemas, Filter/Facetten, Typo-Toleranz, API Keys, Docker/Binary, optional Vector/Semantic Search.
- **ADR-006-Konformität:** Vereinbar bei localhost-only, API-Key und Indexierung nur nach Approval. Wegen In-Memory-Design muss bewusst entschieden werden, welche Felder suchbar sind und welche nur auf Disk bleiben.
- **Betriebsaufwand:** Mittel. Schema-Design ist strikter als bei Meilisearch/Whoosh; Backup/Restore und Service-Betrieb erforderlich.
- **Security:** Gut konfigurierbar, aber wie Meilisearch zusätzlicher HTTP-Dienst. API-Key und Bind-Adresse sind Pflicht.
- **Wartbarkeit:** Gut, aktive Entwicklung. Stärkere Kopplung an Collection-Schemas und RAM-Kalkulation.
- **Bewertung für GTX-1070-Workstation:** Technisch attraktiv, aber der In-Memory-Index konkurriert mit lokalen LLM-/Embedding-/Browser-/Docker-Prozessen um RAM. Für MVP nicht der beste erste Schritt.
- **Entscheidung:** Nicht für MVP; Alternative, wenn niedrige Latenz und Facetten wichtiger als minimaler Betrieb sind.

### Option D: Auf OpenSearch wechseln

- **Ressourcen:** Java-basierter Suchserver, typischerweise mehrere GB RAM/Heap plus OS-Cache; Docker-/Cluster-Parameter, Ports `9200/9600`, Security Plugin, ggf. Dashboards. Kein VRAM-Verbrauch, aber deutliche CPU-/RAM-/Disk-Last.
- **Features:** Sehr umfangreich: Volltext, Analyzer, DSL, Aggregationen/Facetten, Security, Snapshots, Index Lifecycle, Observability, Vektorsuche.
- **ADR-006-Konformität:** Möglich, aber operational schwerer sicher zu halten. Viele Netzwerk-/Security-/Cluster-Einstellungen erhöhen Fehlkonfigurationsrisiko.
- **Betriebsaufwand:** Hoch. Installation, JVM/Heap-Tuning, Zertifikate/Security, Backups/Snapshots, Upgrades, Monitoring.
- **Security:** Stark, wenn korrekt konfiguriert; für localhost-MVP aber unnötig komplex. Falsch konfigurierte OpenSearch-Instanzen sind ein größeres Risiko als dateibasierte Indizes.
- **Wartbarkeit:** Langfristig gut für große Deployments, kurzfristig schlecht für dieses Projekt wegen hoher Komplexität.
- **Bewertung für GTX-1070-Workstation:** Überdimensioniert. Der Ressourcenverbrauch widerspricht dem lokalen Single-Workstation-MVP mit Ollama und ChromaDB.
- **Entscheidung:** Abgelehnt für MVP und nächsten Schritt.

### Option E: SQLite FTS5

- **Ressourcen:** Kein separater Server, kein Port, dateibasierte SQLite-DB. RAM/CPU kontrollierbar, Backups einfach. SQLite FTS5 ist als Virtual Table für Volltextsuche verfügbar und unterstützt `MATCH`, Phrasen, Prefix, NEAR, Boolean Queries, `bm25()`, `highlight()` und `snippet()`.
- **Features:** Gute Volltextbasis, Ranking via BM25, Snippets/Highlighting, SQL-Filter über Metadaten. Keine native moderne Typo-Toleranz, keine dedizierte Suchserver-API, weniger komfortables Ranking als Meilisearch/Typesense.
- **ADR-006-Konformität:** Sehr gut. Lokale Datei, keine Netzwerkschnittstelle, Human Approval vor Insert möglich.
- **Betriebsaufwand:** Niedrig bis mittel. Schema-/Migrationen nötig, aber kein Dienstbetrieb. Gute Kombinierbarkeit mit Evidence-/Metadata-Store aus ADR-006.
- **Security:** Gut. Dateirechte, Verschlüsselung/Backup-Policy optional; keine API-Exposition.
- **Wartbarkeit:** Sehr gut, weil SQLite stabil und breit verfügbar ist. Vorteilhaft, falls Evidence Store und Search-Metadaten konsolidiert werden sollen.
- **Bewertung für GTX-1070-Workstation:** Sehr passend als möglicher Nachfolger von Whoosh, wenn das Projekt ohnehin SQLite für Evidence/Metadata nutzt.
- **Entscheidung:** Nicht sofort, aber als niedriginfrastruktureller Ersatzpfad ernsthaft prüfen, bevor ein Suchserver eingeführt wird.

### Option F: PostgreSQL FTS

- **Ressourcen:** Zusätzlicher Datenbankdienst, falls PostgreSQL nicht ohnehin läuft. RAM/CPU/Disk abhängig von DB-Konfiguration; kein VRAM. Ports/Service/Backups erforderlich.
- **Features:** Volltextsuche mit `tsvector`/`tsquery`, Ranking, Highlighting, GIN/GiST-Indizes, starke Metadaten-, Transaktions- und Audit-Fähigkeiten. Keine moderne Such-UX wie Typo-Toleranz out of the box.
- **ADR-006-Konformität:** Gut, wenn PostgreSQL als lokaler Evidence Store ohnehin eingeführt wird. Human Approval, Audit, Review Queue und Indexstatus können relational sauber abgebildet werden.
- **Betriebsaufwand:** Mittel bis hoch. Migrationen, DB-Administration, Backups, lokale Auth, Rollen/Rechte.
- **Security:** Gut bei localhost-only, rollenbasierter Zugriffskontrolle und separaten DB-Usern. Mehr Angriffsfläche als Whoosh/SQLite, aber beherrschbar.
- **Wartbarkeit:** Gut, wenn PostgreSQL bereits Kernbestandteil wird; schlecht, wenn es nur für Search eingeführt wird.
- **Bewertung für GTX-1070-Workstation:** Nur sinnvoll, wenn PostgreSQL ohnehin für Evidence Store, Audit und Research Runs betrieben wird. Als isolierter Search-Wechsel zu schwergewichtig.
- **Entscheidung:** Späterer Konsolidierungspfad, nicht MVP.

## Recommendation

Der beste nächste Schritt für dieses Projekt ist:

1. **Whoosh behalten.**
2. **Keinen neuen Suchserver für T-013 einführen.**
3. **Indexzugriff abstrahieren**, damit `DiscoveryPipeline` nicht dauerhaft direkt an `WhooshIndex` gekoppelt bleibt.
4. **Messpunkte einführen:** `doc_count`, Indexgröße auf Disk, Query-Latenz p50/p95, Fehler-/Locking-Rate, Rebuild-Dauer.
5. **Meilisearch als ADR-pflichtigen späteren Wechsel vorbereiten**, wenn die Schwellenwerte überschritten werden oder Typo-Toleranz/Facetten funktional notwendig sind.

Whoosh reicht für den erwarteten MVP der Onion Discovery Engine, weil Onion Discovery durch Seeds, Tor-Latenzen, Rate-Limits, Human Approval und Content-Limits natürlich begrenzt ist. Die Pipeline wird nicht durch millionenfache Echtzeitindexierung, sondern durch sichere Beschaffung, Review und Reproduzierbarkeit limitiert.

Ein Wechsel lohnt sich erst, wenn Suche selbst zum Engpass wird oder Search-UX-Features wichtiger werden als Minimalbetrieb. Dann ist **Meilisearch** wegen geringerer Betriebskomplexität gegenüber OpenSearch und weniger strikter RAM-Orientierung gegenüber Typesense der wahrscheinlich beste Suchserver-Kandidat. **SQLite FTS5** sollte vorher geprüft werden, wenn der Haupttreiber nicht Such-UX, sondern Konsolidierung mit Evidence-/Metadaten ist.

## Consequences

### Positive

- ADR-004 und ADR-007 bleiben konsistent; Issue #13 verursacht keinen unnötigen Infrastrukturbruch.
- Keine zusätzlichen Ports, Keys, Docker-Container oder Suchserver-Prozesse im MVP.
- Die ADR-006-Sicherheitsgrenzen bleiben einfacher prüfbar: lokale Indexsuche statt HTTP-Dienst.
- Die GTX-1070-Workstation behält RAM/CPU-Spielraum für Ollama, ChromaDB und SearXNG.
- Bestehende Implementierung in `darknet_search.index.WhooshIndex` und `onion_discovery.engine.DiscoveryPipeline` bleibt lauffähig.

### Negative

- Keine native Typo-Toleranz, Facetten oder moderne Ranking-Regel-UI im MVP.
- Whoosh bleibt bei großen Korpora, parallelen Writes und hohen Query-Raten begrenzt.
- Ein späterer Wechsel erfordert Migration oder Rebuild aus Evidence-/Snapshot-Daten.

### Erforderliche Moduländerungen bei Umsetzung der Entscheidung

Diese ADR verlangt keine sofortige Codeänderung, definiert aber den nächsten Architekturpfad:

- `darknet_search.index.WhooshIndex` bleibt bestehen und wird nicht durch Meilisearch/Typesense/OpenSearch ersetzt.
- Mittelfristig sollte eine Schnittstelle wie `SearchIndexRepository` oder `OnionIndexBackend` eingeführt werden:
  - `add_document(document)`
  - `search(query, limit, filters)`
  - `stats()`
  - `rebuild_from_evidence()`
- `onion_discovery.engine.DiscoveryPipeline` sollte perspektivisch nicht direkt `WhooshIndex()` importieren, sondern einen Index-Adapter injizieren. Das reduziert Kopplung und erhöht Testbarkeit.
- GPT-Researcher bleibt über Custom Retriever / CompositeRetriever angebunden und liest nur aus freigegebenen lokalen Indexdaten. Es gibt weiterhin **keine Live-Tor-Suche** innerhalb einer GPT-Researcher-Anfrage.
- Search Broker MCP darf nur `search_existing_index` / `get_onion_index_stats` bereitstellen, nicht `crawl_anything` oder Live-Fetch-Tools.

### Backward Compatibility und Migration

- Bestehende Whoosh-Indizes müssen für den MVP nicht migriert werden.
- Bei späterem Wechsel soll kein direkter Whoosh-Dateiformat-Migrationszwang entstehen. Stattdessen wird der neue Index aus Evidence Store/Snapshots oder exportierten, freigegebenen Dokumenten neu aufgebaut.
- Falls der Evidence Store noch nicht vollständig ist, muss `WhooshIndex` optional einen Exportpfad für gespeicherte Felder erhalten, bevor ein Backend-Wechsel durchgeführt wird.

### Sicherheitsanforderungen für jeden späteren Suchserver

Falls Meilisearch, Typesense, OpenSearch oder PostgreSQL später eingeführt werden, gelten mindestens:

- Bind ausschließlich an `127.0.0.1`.
- Auth/API-Key/DB-User verpflichtend; keine Default-Keys.
- Keine `.onion`-Originaladressen in öffentlichen Reports; synthetische URIs oder gehashte Host-Identifier verwenden.
- Indexierung nur nach Human Approval.
- Blocklist/Opt-out vor Speicherung und vor Ausgabe prüfen.
- Keine Live-Tor-Abfragen aus Retriever, MCP Search Tool oder GPT-Researcher Request Path.
- Backups verschlüsseln oder mit restriktiven Dateirechten schützen.
- Keine sensiblen Rohinhalte oder API-Keys in Logs.

## Architecture Review Checklist

- [x] Neue Dependency gerechtfertigt? **Nein für MVP; daher keine neue Suchserver-Dependency.**
- [x] Module Coupling akzeptabel? **Aktuell noch direkte Kopplung `DiscoveryPipeline` → `WhooshIndex`; Adapter empfohlen.**
- [x] Data Flow dokumentiert und sicher? **Ja: Onion Zone → Review → lokaler Index → Retriever; keine Live-Tor-Suche.**
- [x] Error Handling konsistent? **Whoosh-Fehler werden aktuell geloggt; spätere Adapter sollten explizite Result-/Error-Typen liefern.**
- [x] Scaling Bottlenecks identifiziert? **Whoosh-Limits bei >50k-100k Dokumenten, >2 GB Text, parallelen Writes, >2 s p95 Query.**
- [x] Security Boundaries klar? **Ja: localhost/file-only, Approval, Blocklist/Opt-out, keine API-Exposition.**
- [x] Testing Strategy ausreichend? **Für ADR ja; Umsetzung braucht Index-Adapter-Tests, Query-Latenz-Benchmark, Export/Rebuild-Test.**

## References

- Issue #13: <https://github.com/xxammaxx/Researcher/issues/13>
- ADR-004: `design.md` — Whoosh statt Elasticsearch/Meilisearch für Darknet-Index
- ADR-006: `docs/adr/006-evidence-first-pipeline.md`
- ADR-007: `docs/adr/007-onion-discovery-engine.md`
- `darknet_search/index.py` — aktueller Whoosh-Wrapper
- `onion_discovery/engine.py` — aktuelle Discovery Pipeline mit `WhooshIndex`
- `docs/architecture.md` — lokale Workstation, Dienste, Ports, Sicherheitsannahmen
- `docs/module-map.md` — Module `Darknet_Search` und `Darknet_Index`
- `researcher_research_first_rule.md` — keine Live-Tor-Abfragen im Retriever, Blocklist/Opt-out, Custom-Retriever-Format
- Meilisearch Self-hosted Getting Started / Configuration: <https://www.meilisearch.com/docs/learn/self_hosted/getting_started_with_self_hosted_meilisearch>, <https://www.meilisearch.com/docs/learn/self_hosted/configure_meilisearch_at_launch>
- Typesense Install / System Requirements: <https://typesense.org/docs/guide/install-typesense.html>, <https://typesense.org/docs/guide/system-requirements.html>
- OpenSearch Install / Docker Docs: <https://docs.opensearch.org/docs/latest/install-and-configure/install-opensearch/>, <https://docs.opensearch.org/docs/latest/install-and-configure/install-opensearch/docker/>
- SQLite FTS5: <https://www.sqlite.org/fts5.html>
- PostgreSQL Full Text Search: <https://www.postgresql.org/docs/current/textsearch.html>

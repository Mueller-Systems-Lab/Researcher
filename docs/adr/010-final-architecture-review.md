# ADR-010: Finale Architektur-Review Researcher

**Status:** Accepted  
**Datum:** 2026-05-16  
**Autor:** Architecture Review Agent  
**Kontext:** Abschlussreview nach Issues #1-#23

---

## Context

Das Researcher-Projekt ist nach Umsetzung von **23 Issues**, **9 vorherigen ADRs** und einer gemeldeten Testsuite von **127 passierenden Tests** in einem MVP-nahen Endzustand. Ziel ist ein lokales, unzensiertes Research-System auf Basis von GPT Researcher, das auf einer einzelnen Workstation mit **NVIDIA GTX 1070, 8 GB VRAM** betrieben wird.

Die verbindlichen Architekturprinzipien bleiben:

- **local-first:** Dienste binden lokal; keine Cloud-Pflicht.
- **open-source:** Ollama/llama-server, SearXNG, Tor, Whoosh, ChromaDB und Python-Tooling statt proprietärer Plattformdienste.
- **zero-API-dependency:** keine externen kommerziellen LLM-, Search- oder Embedding-APIs im Kernpfad.
- **evidence-first:** Quellen, Claims, Audit und Human-Gates haben Vorrang vor reiner Textgenerierung.
- **security-by-default:** Onion Discovery ist deaktiviert, Clearnet/Onion/Offline-Zonen sind getrennt, Retriever führen keine Live-Tor-Abfragen aus.

Gelesene Review-Grundlage:

- `docs/architecture.md` — Systemkontext, C4-Komponenten, Laufzeit- und Deployment-Sicht.
- `design.md` — ADR-001 bis ADR-005.
- `docs/adr/006-evidence-first-pipeline.md` — ADR-006.
- `docs/adr/007-onion-discovery-engine.md` — ADR-007.
- `docs/adr/008-onion-search-index.md` — ADR-008.
- `docs/adr/009-architecture-review-gaps.md` — ADR-009.
- `docs/code-review-2026-05-16.md` — 8 Code-Review-Findings.
- `docs/dependency-research-2026-05-16.md` — Dependency- und CVE-Bewertung.
- `docs/testing-strategy.md` — Testpyramide und offene Testlücken.
- `deepresearch-agent-stack.md` — Zielbild der Evidence-first Research Pipeline.
- Stichproben in Kernmodulen: `search/`, `darknet_search/`, `onion_discovery/`, `crawlers/`, `vectordb/`, `mcp_tools/`, `dashboard/`, `config/`.

---

## Decision / Assessment

ADR-010 akzeptiert die finale MVP-Architektur als **tragfähige lokale Single-Workstation-Architektur** mit mehreren bewusst akzeptierten Folgerisiken. Die Gesamtbewertung ist **YELLOW**: Der Kernzuschnitt ist kohärent und sicherheitsbewusst, aber einige Architekturentscheidungen sind noch nicht vollständig durch Adapter, E2E-Tests, CI, technische Determinismus-Gates und eigene ADRs für neuere Teilentscheidungen abgesichert.

| Dimension | Bewertung | Begründung |
|---|---|---|
| Global Architecture | **YELLOW** | Modulgrenzen sind überwiegend klar: Retrieval, Onion Discovery, Crawler, VectorDB, MCP und Dashboard sind getrennt. Direkte Kopplungen wie `onion_discovery.engine` → `darknet_search.index.WhooshIndex` und `search.composite` → `darknet_search.retriever.DarknetRetriever` sind für MVP akzeptabel, sollten aber über Ports/Adapter entkoppelt werden. |
| ADR-Konsistenz | **YELLOW** | ADR-001 bis ADR-009 sind inhaltlich konsistent: Ollama, CompositeRetriever, CPU-Embeddings, Whoosh, synthetische URIs, Evidence-first, Onion Discovery und Whoosh-MVP-Index passen zusammen. ADR-007 und ADR-008 stehen noch auf `Proposed`, obwohl Implementierungen vorhanden sind. |
| Code-Review-Findings | **YELLOW** | Die drei HIGH-Findings sind im Code sichtbar adressiert. Vier MEDIUM/LOW-Findings bleiben offen oder nur teilweise gelöst. |
| Missing ADRs | **YELLOW** | Signifikante Entscheidungen für MCP-Tool-Registry, Dashboard-SSE und Dependency-Versionierung sind implementiert bzw. dokumentiert, aber nicht als eigene ADRs festgehalten. |
| Risk Assessment | **YELLOW** | Größte Risiken liegen in Onion/Crawler-Governance, unmaintained Whoosh, lokalen Dienst-/Dependency-Versionen, fehlenden E2E-/CI-Gates und Single-Workstation-SPOFs. Keine RED-Bewertung, solange Betrieb lokal und nicht öffentlich exponiert bleibt. |
| Testing Strategy | **YELLOW** | 127 Tests sind gut für den MVP. Offene Lücken aus `docs/testing-strategy.md`: Crawler-Unit-Tests, echte Playwright-Browser-Tests, E2E-Szenarien, CI und Whoosh-Latenz-Benchmarks. |
| Security Boundaries | **YELLOW** | Clearnet/Onion/Offline-Grenzen, SSRF-Fix, Human-Review-Trennung und Path-Traversal-Schutz sind vorhanden. Restrisiken bestehen durch DNS-Rebind/TOCTOU im Web-Fetch, CLI-basierte Approvals ohne starke Auth, CORS `*` im lokalen Dashboard und gpt-researcher-CVEs bei öffentlicher Exposition. |

---

## ADR-Konsistenz und Status

| ADR | Status aktuell | Bewertung | Empfehlung |
|---|---|---|---|
| ADR-001 Ollama statt llama.cpp direkt (`design.md`) | Draft-Abschnitt | Konsistent mit GTX-1070-Ziel und zero-API-dependency. | In separater ADR-Datei nachziehen oder `design.md` als historische Sammel-ADR beibehalten. |
| ADR-002 CompositeRetriever-Pattern (`design.md`) | Draft-Abschnitt | Konsistent mit `search/composite.py`. | Akzeptiert behandeln; später Search-Port abstrahieren. |
| ADR-003 Embeddings auf CPU (`design.md`) | Draft-Abschnitt | Konsistent mit 8-GB-VRAM-Limit. | Akzeptiert behandeln; Messwerte für Batch-Größen ergänzen. |
| ADR-004 Whoosh statt Elasticsearch/Meilisearch (`design.md`) | Draft-Abschnitt | Konsistent mit ADR-008 und lokalen Ressourcen. | Akzeptiert für MVP; Ersatzpfad aktiv beobachten. |
| ADR-005 Synthetische Darknet-URIs (`design.md`) | Draft-Abschnitt | Konsistent mit `darknet_search/retriever.py`. | Akzeptiert behandeln; Hash-Algorithmus/Collision-Risiko dokumentieren. |
| ADR-006 Evidence-first Pipeline | Accepted | Zentrale Zielentscheidung. | Beibehalten. |
| ADR-007 Onion Discovery Engine | Proposed | Inhalt und Code sind weitgehend umgesetzt. | **Auf Accepted wechseln**, sobald die fehlenden Gate-/Review-Tests abgedeckt sind. |
| ADR-008 Onion Search Index | Proposed | Whoosh-MVP-Entscheidung ist umgesetzt und konsistent. | **Auf Accepted wechseln**, sobald Index-Adapter-Backlog explizit erfasst ist. |
| ADR-009 Architecture Review Gaps | Accepted | Konsistenter Gap-Nachweis. | Beibehalten; offene ⏳-Punkte in Roadmap übernehmen. |

Es wurden keine harten Widersprüche zwischen ADRs gefunden. Der wichtigste Spannungsbogen ist bewusst dokumentiert: **minimaler lokaler MVP** versus **skalierbare Evidence-/Search-Infrastruktur**. ADR-008 löst diesen Konflikt für den MVP zugunsten von Whoosh und verschiebt Meilisearch/Qdrant/PostgreSQL auf spätere ADR-pflichtige Iterationen.

---

## Module Coupling Matrix

Instability ist qualitativ nach `ausgehende Abhängigkeiten / (ausgehende + eingehende Abhängigkeiten)` geschätzt. Werte dienen als Review-Indikator, nicht als statische Analysemetrik.

| Modul | Hängt ab von | Wird genutzt von | Instability |
|---|---|---|---:|
| `darknet_search` | `whoosh`, `os`, `datetime` | `search`, `onion_discovery`, Tests | 0.40 |
| `search` | `darknet_search`, `requests`, `concurrent.futures`, SearXNG | GPT-Researcher/Custom Retriever, `mcp_tools`-Zielbild | 0.60 |
| `onion_discovery` | `requests`, `bs4`, `darknet_search`, Tor SOCKS5, lokale Queues | CLI, `mcp_tools/human_review`, Crawler-/Discovery-Workflows | 0.55 |
| `crawlers` | `requests`, `bs4`, `crawlers.config`, Tor SOCKS5 | Offline Crawl-/Index-Jobs | 0.70 |
| `vectordb` | `chromadb`, `os`, Embedding-Vektoren | Research Pipeline, RAG/MCP-Zielbild | 0.65 |
| `mcp_tools` | `requests`, `bs4`, `onion_discovery`, lokale JSON-/Audit-/Evidence-Stores | MCP-Tool-Layer, Research Coordinator | 0.50 |
| `dashboard` | `http.server`, `subprocess`, `nvidia-smi`, static assets | Nutzer/Browser, lokale Ops | 0.75 |
| `config` | `os`, `.env`/Umgebung | fast alle Kernmodule indirekt | 0.25 |
| `docs/adr` | Projektentscheidungen, Reviews | alle Architektur- und Folgearbeiten | 0.10 |

Bewertung:

- **Niedrige bis mittlere Kopplung** in den meisten Kernpfaden.
- **Direkte Domain-zu-Infrastruktur-Kopplung** in `onion_discovery.engine` an `WhooshIndex` ist der wichtigste Entkopplungskandidat.
- **Crawler-Konfiguration** mutiert aktuell globale Config und erzeugt versteckte Test-/Laufzeitkopplung.
- **Dashboard** ist kohäsiv und weitgehend isoliert, aber wegen eigenem HTTP-Server und SSE eine ADR-pflichtige technische Entscheidung.

---

## Code-Review Finding Status

| Finding | Level | Status | Issue | Nachweis / Kommentar |
|---|---|---|---|---|
| SSRF `web_fetch` | HIGH | ✅ Fixed | #19 | `mcp_tools/web_fetch.py` blockiert `.onion`, prüft `PolicyGateway` und private/loopback/link-local IP-Ranges via `socket.getaddrinfo` + `ipaddress` (`web_fetch.py:13-169`). Restrisiko: DNS-Rebind/TOCTOU, weil vor Fetch validiert und danach erneut per URL gefetcht wird. |
| Human-Review-Gate | HIGH | ✅ Fixed | #20 | `mcp_tools/human_review.py` erlaubt nur `request`, `list_pending`, `stats`; `approve`/`reject` werden über MCP abgelehnt (`human_review.py:46-97`). |
| Dashboard Path-Traversal | HIGH | ✅ Fixed | #21 | `dashboard/server.py` nutzt `_resolve_static()`, blockiert `..`/absolute Pfade und prüft `realpath` gegen `STATIC_DIR` (`server.py:60-91`). |
| CLI-Import `os` in `onion_discovery/__main__.py` | MEDIUM | ❌ Offen | #22 | `os.getenv` wird in `--config-only` verwendet, aber `os` ist nicht importiert (`__main__.py:7-10`, `__main__.py:66-76`). |
| Crawler Config-Mutation | MEDIUM | ❌ Offen | — | `DarknetCrawler.__init__` setzt `self.config = config` und schreibt Overrides direkt in das globale Objekt (`crawlers/darknet_crawler.py:52-58`). |
| Playwright-Test kein Browser-Test | MEDIUM | ⏳ Offen / Teststrategie geplant | — | `docs/testing-strategy.md` fordert echte Playwright-Visual-Tests, listet diese aber unter offenen Punkten (`docs/testing-strategy.md:54-74`, `164-170`). |
| `VectorStore.query` mehrere Embeddings | MEDIUM | ❌ Offen | — | Implementierung verarbeitet nur `results["documents"][0]` und ignoriert weitere Query-Resultsets (`vectordb/store.py:135-177`). |
| Blocklist-vs-Allowlist | LOW | ❌ Offen | — | Kommentar und Code prüfen Allowlist vor Blocklist (`policy_gateway.py:64-83`); Deny-overrides-allow ist nicht umgesetzt. |

---

## Missing ADRs (Proposed)

Folgende signifikante Entscheidungen sollten in der nächsten Iteration als eigene ADRs dokumentiert werden.

### Proposed ADR-011: MCP Tool Registry und Sicherheitsmodell

- **Context:** `mcp_tools/registry.py` registriert fünf Tools (`web-fetch`, `evidence-store`, `claim-validator`, `audit-log`, `human-review-request`) zentral. Diese Tool-Schicht ist sicherheitsrelevant, weil sie Fetching, Evidence, Audit und Review-Gates exponiert.
- **Decision:** Tool-Registry mit explizitem Manifest, deny-by-default für unbekannte Tools, keine generischen `crawl_anything`-/Live-Onion-Tools, Trennung von request-fähigen Tools und human-only Approval-Pfaden.
- **Alternativen:** (A) direkte Imports ohne Registry; (B) dynamische Plugin-Discovery. Beide erhöhen Kopplung bzw. Angriffsfläche.
- **Konsequenzen:** Bessere Auditierbarkeit und Sicherheitsprüfung; zusätzlicher Aufwand für Tool-Versionierung und Berechtigungsmodell.

### Proposed ADR-012: Dashboard Live-Updates via SSE statt WebSocket

- **Context:** `dashboard/server.py` nutzt HTTP + Server-Sent Events für `/api/gpu/stream`.
- **Decision:** SSE bleibt MVP-Mechanismus für einseitige GPU-/VRAM-Telemetrie.
- **Alternativen:** (A) WebSocket für bidirektionale Kontrolle; (B) Polling `/api/gpu`. WebSocket ist unnötig komplex; Polling ist einfacher, aber weniger effizient.
- **Konsequenzen:** Geringe Komplexität und gute Browser-Kompatibilität; keine bidirektionalen Dashboard-Aktionen ohne spätere Erweiterung.

### Proposed ADR-013: Dependency- und Versionierungsstrategie

- **Context:** `docs/dependency-research-2026-05-16.md` nennt CVEs/Updates: gpt-researcher nur lokal, Whoosh unmaintained, ChromaDB 1.x pinnen, requests/lxml aktualisieren, Ollama/SearXNG pinnen.
- **Decision:** Für lokale Kernabhängigkeiten werden Mindestversionen und Container-/Binary-Versionen gepinnt; Sicherheitsupdates werden als regelmäßiger Review-Prozess dokumentiert.
- **Alternativen:** (A) lose Mindestversionen; (B) vollständiges Lockfile mit reproduzierbarem Build. Lose Versionen sind unsicherer; vollständige Lockfiles erhöhen Pflegeaufwand, sind aber für Reproduzierbarkeit attraktiver.
- **Konsequenzen:** Bessere Security und Reproduzierbarkeit; mehr Upgrade-/Testaufwand.

---

## Risk Assessment

### Höchstes Ausfallrisiko

1. **Ollama/LLM auf GTX 1070:** begrenzter VRAM, ein lokaler Prozess, kein Cloud-Fallback. Ausfall blockiert Synthese.
2. **Whoosh-Index:** dateibasiert, unmaintained, begrenzte parallele Writes; Ausfall degradiert Onion-/Darknet-Suche.
3. **Tor/Onion-Pipeline:** Netzwerk-Latenz, Verfügbarkeit, Policy-Gates und rechtliche Randbedingungen können Crawls blockieren.
4. **SearXNG Docker-Service:** Clearnet-Suche hängt an lokalem Container und externen Search-Engines.
5. **Human Review Queue:** Sicherheitsstärke, aber manueller Bottleneck und Single Point in der Freigabekette.

### Am schlechtesten getestete Bereiche

- `crawlers/`: laut Teststrategie **0 Unit-Tests**, Ziel ≥80 % (`docs/testing-strategy.md:33-43`).
- E2E-Szenarien mit laufenden Diensten: alle noch geplant (`docs/testing-strategy.md:75-83`, `164-170`).
- Echte Playwright-Browser-/Screenshot-Tests: geplant, nicht nachgewiesen.
- Deterministischer Report-Replay inklusive fixer Prompt-/Evidence-/Sortier-Versionen: architektonisch definiert, technisch noch nicht vollständig nachgewiesen.
- Performance-Benchmarks für Whoosh p50/p95 und Index-Rebuild-Dauer: geplant.

### Sicherheitsrestrisiken trotz Fixes

- `web-fetch`: SSRF-Grundschutz vorhanden; DNS-Rebind/Redirect-Validierung und IP-Pinning pro Request sollten ergänzt werden.
- `human-review`: MCP kann nicht approven; CLI-Approvals sind aber noch kein rollen-/authentisierter Human-only Kanal.
- `dashboard`: localhost-default ist gut; CORS `*` und statischer HTTP-Server sollten nur lokal betrieben werden.
- `gpt-researcher`: Dependency Research nennt relevante CVEs und empfiehlt ausschließlich lokalen Betrieb.
- Onion-Inhalte: Klassifikation und Human Gates sind vorhanden, aber Binary-/Low-Confidence-/PII-Gates sind nicht vollständig als technische Pipeline-Gates nachgewiesen.

### Single Points of Failure

- Eine Workstation, eine GPU, ein Ollama-Prozess.
- Lokaler SearXNG-Container.
- Lokaler Tor-SOCKS5-Endpunkt.
- Dateibasierter Whoosh-Index unter `darknet_index/`.
- Lokale ChromaDB-Persistenz unter `CHROMA_PERSIST_DIRECTORY`.
- Manuelle Human-Review-Queue ohne verteiltes Review-/Backup-Modell.

---

## Alternatives Considered

### Alternative A: MVP-Architektur akzeptieren und gezielt härten

- **Vorteile:** Niedrige Betriebskomplexität, passend zur GTX 1070, minimale neue Dependencies, lokale Sicherheitsgrenzen bleiben prüfbar.
- **Nachteile:** Adapter, CI/E2E, Determinismus und Versionierung bleiben Folgearbeit.
- **Bewertung:** **Gewählt.** Beste Balance aus Kohäsion, Ressourcenverbrauch, Maintainability und Security.

### Alternative B: Sofort auf Microservices mit PostgreSQL/Qdrant/Meilisearch migrieren

- **Vorteile:** Klarere Servicegrenzen, bessere Skalierung, stärkere Metadaten-/Evidence-Query-Fähigkeiten.
- **Nachteile:** Mehr Ports, Auth, Backups, RAM/CPU-Last, Migrationsaufwand und Fehlkonfigurationsfläche; überdimensioniert für Single-Workstation-MVP.
- **Bewertung:** Abgelehnt für nächste Iteration; als späterer Upgrade-Pfad ADR-pflichtig.

### Alternative C: Sicherheitskritische Onion-/MCP-Funktionen einfrieren

- **Vorteile:** Reduziert rechtliche und operative Risiken kurzfristig.
- **Nachteile:** Verfehlt den Projektzweck eines lokalen, unzensierten Research-Systems und schwächt Evidence-/Governance-Funktionalität.
- **Bewertung:** Nicht empfohlen; besser: disabled-by-default beibehalten und Gates ausbauen.

---

## Architecture Recommendation

**Gesamtbewertung: YELLOW mit stabiler MVP-Basis.**  
Die Architektur ist für den lokalen Betrieb auf einer GTX-1070-Workstation sinnvoll zugeschnitten. Die wichtigsten Designentscheidungen sind konsistent: Ollama/CPU-Embeddings entlasten VRAM, CompositeRetriever integriert SearXNG und lokale Onion-Suche, Whoosh vermeidet zusätzlichen Suchserver, MCP-Tools kapseln Evidence/Governance, und Dashboard-SSE bleibt leichtgewichtig. Die nächste Iteration sollte nicht primär neue Features hinzufügen, sondern Architekturhärtung, Tests und Reproduzierbarkeit abschließen.

### Top-5-Empfehlungen für die nächste Iteration

1. **Offene Code-Review-Findings schließen:** `os`-Import in `onion_discovery/__main__.py`, Config-Kopie im Crawler, `VectorStore.query` für mehrere Query-Embeddings, deny-overrides-allow in `PolicyGateway`, echte Playwright-Tests.
2. **Ports/Adapter einführen:** `OnionIndexBackend`/`SearchIndexRepository` zwischen `onion_discovery` und `darknet_search.index.WhooshIndex`; optional `SearchProvider` zwischen `search.composite` und konkreten Backends.
3. **AC-7/AC-8/AC-10 technisch abschließen:** deterministisches Profil mit Replay-Test, MCP-Tool-Sicherheits-ADR, Binary-/Low-Confidence-/PII-Human-Gates als getestete Pipeline-Stufen.
4. **Test- und CI-Gates vervollständigen:** Crawler-Unit-Tests, E2E-Szenarien 1-5, echte Playwright-Screenshot-Tests, GitHub Actions, Whoosh p50/p95 Benchmark.
5. **Dependency-/Versionierungsstrategie festlegen:** requests/lxml/Ollama/SearXNG/ChromaDB pinnen, gpt-researcher nur localhost, Whoosh-Ersatzpfad mit Messschwellen aus ADR-008 prüfen.

---

## Consequences

### Wird einfacher

- Der MVP kann als konsistente lokale Architektur weiterbetrieben werden.
- Offene Risiken sind priorisiert und konkreten Dateien/ADRs zugeordnet.
- Folgeentscheidungen für MCP, Dashboard und Dependencies sind ADR-pflichtig vorbereitet.
- ADR-006 bis ADR-009 bleiben das verbindliche Zielbild für Evidence-first und Onion-Security.

### Wird schwieriger

- Die nächste Iteration muss stärker Engineering-Härtung statt Feature-Umfang priorisieren.
- Adapter und Determinismus-Gates erhöhen Code- und Testumfang.
- Dependency-Pinning und CI machen Builds reproduzierbarer, aber auch wartungsintensiver.
- Human Review bleibt ein bewusster Durchsatz-Bottleneck.

### Akzeptierte Risiken

- Whoosh bleibt für den MVP trotz Wartungsrisiko akzeptiert, solange ADR-008-Schwellen nicht überschritten werden.
- Single-Workstation-Betrieb bleibt ein SPOF, ist aber Teil des local-first-Ziels.
- Onion Discovery bleibt disabled-by-default und darf nur unter Policy-/Human-Gates betrieben werden.

---

## References

- ADR-001: `design.md:42-45` — Ollama statt llama.cpp direkt.
- ADR-002: `design.md:47-50` — CompositeRetriever-Pattern.
- ADR-003: `design.md:52-56` — Embeddings auf CPU.
- ADR-004: `design.md:58-61` — Whoosh statt Elasticsearch/Meilisearch.
- ADR-005: `design.md:63-67` — synthetische Darknet-URIs.
- ADR-006: `docs/adr/006-evidence-first-pipeline.md`.
- ADR-007: `docs/adr/007-onion-discovery-engine.md`.
- ADR-008: `docs/adr/008-onion-search-index.md`.
- ADR-009: `docs/adr/009-architecture-review-gaps.md`.
- C4-/Systemkontext: `docs/architecture.md`.
- Code Review: `docs/code-review-2026-05-16.md`.
- Dependency Research: `docs/dependency-research-2026-05-16.md`.
- Teststrategie: `docs/testing-strategy.md`.
- Blueprint: `deepresearch-agent-stack.md`.
- CompositeRetriever: `search/composite.py`.
- Whoosh-Index und Retriever: `darknet_search/index.py`, `darknet_search/retriever.py`.
- Onion Discovery: `onion_discovery/engine.py`, `onion_discovery/policy_gateway.py`, `onion_discovery/human_review.py`, `onion_discovery/__main__.py`.
- Darknet Crawler: `crawlers/darknet_crawler.py`.
- VectorStore: `vectordb/store.py`.
- MCP Tools: `mcp_tools/registry.py`, `mcp_tools/web_fetch.py`, `mcp_tools/human_review.py`.
- Dashboard: `dashboard/server.py`, `dashboard/gpu_monitor.py`.

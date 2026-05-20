# ADR-013: Dependency Versioning Policy und Whoosh→SQLite FTS5 Migration

**Status:** Accepted  
**Date:** 2026-05-18  
**Deciders:** Architecture Review Agent, Issue Orchestrator  
**Context:** Architecture Review nach ADR-010, Block 6.3; ADR-008 Whoosh Migration

---

## Context

Das Researcher-Projekt hat mehrere Abhängigkeiten mit unterschiedlichen Wartungs- und Sicherheitsprofilen:

- **Aktiv maintained:** ChromaDB, requests, beautifulsoup4, lxml, Ollama (externer Dienst)
- **Selbst gehostet:** SearXNG, Tor (externe Dienste)
- **Unmaintained/Kritisch:** Whoosh (letztes Release 2016, Python 2/3-Classifier)

Das Projekt folgt dem Prinzip **local-first, zero-API-dependency** — alle Abhängigkeiten müssen lokal lauffähig sein, ohne Cloud- oder API-Zwang.

Die aktuelle Versionierungsstrategie ist inkonsistent:
- Root `requirements.txt` pinnt `gpt-researcher==0.14.8`, aber Submodule `pyproject.toml` deklariert `0.14.7`
- `chromadb>=0.5.20` ist zu loose für Reproduzierbarkeit
- `whoosh>=2.7.4` ist deprecated und muss migriert werden

## Decision

### 1. Exaktes Pinning als Policy

Alle direkten Abhängigkeiten werden **exakt gepinnt**:

| Abhängigkeit | Vorher | Nachher | Begründung |
|---|---|---|---|
| `gpt-researcher` | `==0.14.8` (root) / `0.14.7` (submodule) | `==0.14.8` (beide) | Versionsdrift behoben |
| `chromadb` | `>=0.5.20` | `==1.5.9` | Stabile getestete Version, Apache-2.0 |
| `lxml` | `>=6.1.0` | `>=6.1.0` | CVE-2026-41066 Fix; Minimum-Pin ausreichend |
| `requests[socks]` | `>=2.34.2` | `>=2.34.2` | Minimum-Pin; Patch-Updates sicher |
| `whoosh` | `>=2.7.4` | `>=2.7.4` (deprecated) | Wird durch SQLite FTS5 ersetzt |

### 2. Whoosh → SQLite FTS5 Migration

Whoosh wird durch **SQLite FTS5** ersetzt, implementiert als `SQLiteFTS5Adapter`:

- **Kein neuer Server:** SQLite FTS5 verwendet Python-stdlib `sqlite3`.
- **Adapter-Pattern:** `SearchIndexRepository` (Port) ← `SQLiteFTS5Adapter` / `WhooshIndexAdapter` (Adapter).
- **Feature-Flag:** `SEARCH_INDEX_BACKEND=whoosh|sqlite_fts5` in `.env`.
- **Default:** `whoosh` für Rückwärtskompatibilität; `sqlite_fts5` nach Validierung.
- **Migrationspfad:**
  1. Beide Adapter parallel betreiben (Dual-Run).
  2. Parity-Tests für `search()`, `index()`, `delete()`, `clear()`, `doc_count`.
  3. p50/p95 Latenz-Benchmark für 100/1000/10000 Dokumente.
  4. Switch auf `sqlite_fts5` als Default nach bestandenen Tests.
  5. Whoosh aus `requirements.txt` entfernen nach Rollback-Fenster.

### 3. Update-Prozess

- Sicherheitskritische Updates (CVEs): sofort patchen und pinnen.
- Feature-Updates: ADR-pflichtig mit Test-Validierung.
- ChromaDB: Major-Version-Update nur mit Migrationstest.
- GPT Researcher Submodule: Version muss mit root `requirements.txt` synchron sein.

## Alternatives Considered

### Alternative A: Loose Minimum-Versionen

- **Pros:** Automatische Patch-Updates, weniger Wartungsaufwand.
- **Cons:** Nicht-reproduzierbare Builds, überraschende Breaking Changes, Sicherheitsrisiko durch ungetestete Updates.
- **Decision:** Abgelehnt. Exaktes Pinning ist für Reproduzierbarkeit und Sicherheit notwendig.

### Alternative B: Vollständiges Lockfile (poetry.lock / pip freeze)

- **Pros:** Vollständig reproduzierbare Builds, inklusive transitiver Abhängigkeiten.
- **Cons:** Höherer Pflegeaufwand, Lockfile-Konflikte bei Updates, überdimensioniert für Single-Workstation.
- **Decision:** Für nächste Iteration vorgemerkt; aktuell reicht exaktes Pinning der direkten Abhängigkeiten.

### Alternative C: Whoosh behalten, nicht migrieren

- **Pros:** Kein Migrationsaufwand.
- **Cons:** Unmaintained Dependency (seit 2016), keine Security-Patches, Python-Versions-Kompatibilitätsrisiko.
- **Decision:** Abgelehnt. Whoosh-Migration ist architekturkritisch.

## Consequences

### Positive

- Konsistente Versionen zwischen Root und Submodule.
- Reproduzierbare Builds durch exakte Pins.
- SQLite FTS5 eliminiert unmaintained Dependency.
- Adapter-Pattern ermöglicht einfachen Backend-Wechsel.
- Keine neuen Server-Dependencies (stdlib sqlite3).

### Negative

- Manuelle Updates statt automatischer Patches.
- SQLite FTS5 Query-Syntax unterscheidet sich von Whoosh.
- Adapter-Schicht erhöht Code-Umfang.
- FTS5 muss im SQLite-Build verfügbar sein (Startup-Check nötig).

### Risiken

| Risiko | Impact | Mitigation |
|---|---|---|
| SQLite Build ohne FTS5 | Migration blockiert | Startup-Check: `CREATE VIRTUAL TABLE ... USING fts5` |
| Query-Semantik-Unterschiede | User-visible changes | Parity-Tests + Dual-Run-Validierung |
| Datenverlust bei Migration | Verlust lokaler Indexdaten | Never in-place; rebuild from source/evidence |
| Concurrent Writes | Locking | Write-Serialisierung, kurze Transaktionen |

## References

- `docs/adr/ADR-014-whoosh-migration.md` — Detaillierter Whoosh→SQLite FTS5 Migrationsplan (renamed from adr-008-whoosh-migration.md)
- `docs/adr/008-onion-search-index.md` — Ursprüngliche Whoosh-Entscheidung
- `gpt_researcher/ports/search_index_repository.py` — Port-Definition
- `gpt_researcher/adapters/whoosh_index_adapter.py` — Whoosh-Adapter
- `gpt_researcher/adapters/sqlite_fts5_adapter.py` — SQLite FTS5-Adapter
- `requirements.txt` — Gepinnte Abhängigkeiten
- `.env.example` — `SEARCH_INDEX_BACKEND` Feature-Flag
- ADR-010: Final Architecture Review (Missing ADR-013 identifiziert)

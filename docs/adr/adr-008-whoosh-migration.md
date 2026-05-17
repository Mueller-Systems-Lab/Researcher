# ADR-008: Whoosh Migration

**Status:** Proposed  
**Date:** 2026-05-17  
**Deciders:** Architecture Review Agent  
**Context:** Issue #35 — migrate away from unmaintained `whoosh 2.7.4`

---

## Context

The Researcher project currently uses `whoosh>=2.7.4` for the local Darknet full-text index. Whoosh 2.7.4 was last published in 2016 and is unmaintained, creating dependency, compatibility, and long-term security risks.

Current usage is intentionally small and local:

- `darknet_search/index.py` defines `WhooshIndex` with `add_post()`, `add_posts()`, `search()`, `optimize()`, `doc_count`, and `clear()`.
- `darknet_search/retriever.py` wraps `WhooshIndex` in `DarknetRetriever` and returns GPT-Researcher-compatible result dictionaries with synthetic `darknet://` URIs.
- `requirements.txt` includes Whoosh as the only dedicated full-text search dependency.
- `docs/architecture.md` defines a single-workstation, privacy-sensitive, local-first architecture with no cloud search and no live Tor calls from the research request path.
- Existing ADRs, especially `docs/adr/008-onion-search-index.md` and `docs/adr/010-final-architecture-review.md`, accepted Whoosh as a pragmatic MVP choice while explicitly identifying it as a future replacement risk.

Project constraints for the migration:

- Must run locally on Linux without cloud services.
- Must not expose Darknet/onion data to remote systems.
- Should avoid additional always-on services unless clearly justified.
- Expected corpus is small: approximately 1,000-10,000 documents.
- Python 3.11+ is the target runtime.
- The replacement should preserve the existing `DarknetRetriever.search(max_results)` contract and result shape.

## Decision

Migrate the Darknet full-text index from Whoosh to **SQLite FTS5** behind a new `SearchIndexRepository` / `DarknetIndexBackend` adapter.

SQLite FTS5 is the recommended replacement because it best matches the current architecture constraints: it is local, file-based, Linux-compatible, available through Python's standard-library `sqlite3` module, and does not require a separate server, port, API key, Docker container, or cloud component.

The migration should not directly replace imports throughout the codebase. Instead:

1. Introduce a backend interface with the current semantic operations: `add_post`, `add_posts`, `search`, `optimize`, `doc_count`, and `clear`.
2. Implement a new SQLite FTS5 backend.
3. Keep a temporary Whoosh backend only for rollback/export during the migration window.
4. Update `DarknetRetriever` to depend on the interface, not on `WhooshIndex` directly.
5. Remove Whoosh from `requirements.txt` only after functional parity, migration tests, and rebuild/export tooling exist.

## Alternatives Considered

### Alternative A: SQLite FTS5

- **Pros:**
  - No new runtime service, port, or network attack surface.
  - Uses Python stdlib `sqlite3`; no dedicated Python search dependency is required.
  - Good fit for 1,000-10,000 local documents.
  - Supports `MATCH`, phrase/prefix/boolean queries, `bm25()`, `highlight()`, and `snippet()`.
  - Can store metadata and full-text content in one local database file.
  - Easy backups and rebuilds; aligns with evidence/metadata storage paths already discussed in existing ADRs.
- **Cons:**
  - Query syntax and ranking differ from Whoosh; tests must pin expected behavior at the contract level, not exact scores.
  - No built-in typo tolerance like Meilisearch/Typesense.
  - Requires careful query parameter binding and escaping to avoid malformed FTS expressions.
  - Concurrent writes are more limited than a dedicated search service; write serialization should remain explicit.
- **Decision:** **Chosen** as the best migration target.

### Alternative B: Tantivy with Python bindings

- **Pros:**
  - Modern Rust-based search library with strong performance.
  - Embeddable in-process; no separate HTTP service is required.
  - Closer to a dedicated search engine than SQLite FTS5.
- **Cons:**
  - Adds a non-stdlib dependency and Rust/native packaging considerations.
  - If no binary wheel is available, installation requires a Rust toolchain.
  - Smaller Python ecosystem surface than SQLite; more operational risk for a small project.
  - More search-engine-specific adapter code than SQLite.
- **Decision:** Keep as a future upgrade path if SQLite FTS5 cannot meet latency or ranking requirements.

### Alternative C: Meilisearch

- **Pros:**
  - Actively maintained search engine with strong search UX, typo tolerance, ranking rules, filtering, and REST API.
  - Easy to run locally and has mature client libraries.
- **Cons:**
  - Requires an additional local server process, localhost port, API key, data directory, health checks, and backup process.
  - Increases security configuration surface for privacy-sensitive Darknet data.
  - Operationally unnecessary for 1,000-10,000 documents and single-user local retrieval.
- **Decision:** Not selected for this migration; reasonable later if search UX features become a hard requirement.

### Alternatives Rejected Early

- **Typesense:** capable and fast, but still introduces a server process, API key, schema management, and memory-oriented operational concerns that are not justified at current scale.
- **Elasticsearch:** rejected as overkill for a local single-workstation corpus; JVM/service complexity and security surface are disproportionate.

## Consequences

### Positive

- Removes reliance on an unmaintained Whoosh dependency.
- Preserves the local-first and privacy-sensitive architecture: no cloud and no extra search daemon.
- Reduces dependency and service coupling while improving maintainability.
- Enables better cohesion between full-text index, metadata, migration state, and possible evidence-store records.
- Keeps the Retriever API stable for GPT-Researcher integration.

### Negative

- Requires implementation and test work for a new backend and migration script.
- Existing Whoosh query semantics and scores will not be identical.
- SQLite FTS5 support should be verified in the runtime SQLite build during startup/tests.
- FTS query parsing must be constrained; raw user query strings must not be interpolated into SQL.

## Migration Path

1. **Add backend contract**
   - Define `DarknetIndexBackend` or `SearchIndexRepository` with `add_post`, `add_posts`, `search`, `optimize`, `doc_count`, and `clear`.
   - Make `DarknetRetriever` accept the backend or select it from configuration.

2. **Implement SQLite FTS5 backend**
   - Store the database at a configurable path, for example `DARKNET_INDEX_PATH` interpreted as a `.sqlite3` file or a directory containing `darknet_index.sqlite3`.
   - Use a normal `posts` table for stored fields: `post_id`, `url`, `author`, `title`, `timestamp`, `content`, `forum_id`.
   - Use an FTS5 virtual table for searchable fields: `author`, `title`, `content`, `forum_id`.
   - Use parameterized SQL and explicit transactions.
   - Return the same result dictionary keys currently returned by `WhooshIndex.search()`.

3. **Add parity tests**
   - Test add/update behavior using URL-derived `post_id`.
   - Test empty query handling.
   - Test search across `content`, `author`, `title`, and `forum_id`.
   - Test result truncation to 500 characters and GPT-Researcher result conversion.
   - Test `doc_count`, `clear`, and rebuild behavior.

4. **Add export/rebuild tooling**
   - Prefer rebuilding SQLite from approved evidence/snapshot records if available.
   - If no source-of-truth export exists, add a temporary Whoosh export path for stored fields.
   - Write migration output to a new SQLite index path, never in-place over the existing Whoosh directory.

5. **Dual-run validation**
   - For a representative local corpus, run Whoosh and SQLite FTS5 searches side by side.
   - Compare result presence and basic ordering, not exact score equality.
   - Capture p50/p95 query latency and index rebuild time.

6. **Switch default backend**
   - Set SQLite FTS5 as the default backend after parity tests pass.
   - Keep Whoosh backend/config available for one release or migration window.

7. **Remove Whoosh**
   - Remove `whoosh>=2.7.4` from `requirements.txt` after rollback confidence is sufficient.
   - Update `docs/architecture.md` and references from “Whoosh Index” to “SQLite FTS5 Darknet Index”.

## Risk Assessment

| Risk | Impact | Mitigation |
|---|---|---|
| SQLite build lacks FTS5 | Migration backend unavailable | Add startup/test probe: `CREATE VIRTUAL TABLE ... USING fts5`; fail with clear message. |
| Query syntax differs from Whoosh | User-visible search differences | Contract tests and dual-run validation; document accepted score/order differences. |
| SQL/FTS query injection or malformed query errors | Reliability/security issue | Use parameterized SQL, sanitize/quote FTS tokens, catch `sqlite3.Error`, never string-format SQL. |
| Concurrent writes during crawler runs | Locking or delayed indexing | Serialize writes, use short transactions, configure timeout, keep batch/cron write pattern. |
| Data loss during migration | Loss of local index data | Never migrate in-place; rebuild from source records; keep Whoosh index until validation completes. |
| Sensitive Darknet data exposure | Privacy/security breach | Keep database file local with restrictive permissions; no server ports; no cloud sync; preserve synthetic URI output. |

## Architecture Review Checklist

- [x] New dependency justified? **No new dedicated search dependency; SQLite uses Python stdlib `sqlite3`.**
- [x] Module coupling acceptable? **Improves coupling by adding an index backend interface instead of direct `DarknetRetriever` → `WhooshIndex` dependency.**
- [x] Data flow documented and secure? **Crawler/approved records → local SQLite FTS5 file → DarknetRetriever → synthetic `darknet://` results.**
- [x] Error handling strategy consistent? **Backend should catch and log storage/search errors and return empty results consistently with current behavior.**
- [x] Scaling bottlenecks identified? **SQLite write serialization and FTS query syntax are the main bottlenecks; acceptable for 1,000-10,000 documents.**
- [x] Security boundaries clearly defined? **No network service, no cloud, restrictive local file permissions, no live Tor retrieval in search path.**
- [x] Testing strategy adequate? **Requires parity tests, migration/rebuild tests, and latency checks before removing Whoosh.**

## References

- Issue #35: Whoosh migration plan.
- `darknet_search/index.py` — current Whoosh wrapper.
- `darknet_search/retriever.py` — GPT-Researcher-compatible Darknet retriever.
- `requirements.txt` — current `whoosh>=2.7.4` dependency.
- `docs/architecture.md` — local single-workstation architecture and security constraints.
- `docs/adr/008-onion-search-index.md` — prior MVP decision retaining Whoosh and identifying replacement paths.
- `docs/adr/010-final-architecture-review.md` — final review listing Whoosh as a dependency risk.
- SQLite FTS5 documentation: <https://www.sqlite.org/fts5.html>
- Python 3.11 `sqlite3` documentation: <https://docs.python.org/3.11/library/sqlite3.html>
- Meilisearch self-hosted documentation: <https://www.meilisearch.com/docs/learn/self_hosted/getting_started_with_self_hosted_meilisearch>
- Typesense install documentation: <https://typesense.org/docs/guide/install-typesense.html>
- Tantivy Python bindings: <https://github.com/quickwit-oss/tantivy-py>

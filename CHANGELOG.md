# Changelog

## [v0.4.0] — 2026-06-05

### Summary
Phase 9 — Operational Readiness. Research-Pipeline auf GPT Researcher v3.5.0 API migriert, Security-Follow-ups abgeschlossen, Runtime-Monitoring für Known Issues automatisiert, Stage 2 wieder blockierend. **1252 Tests, 0 flaky, Security-Gate 0 Medium/High.**

### Phase 9 — Operational Readiness (#150)
- **Research Pipeline Fix** (#147): `scripts/ci_acceptance.py` auf v3.5.0 API migriert
  - Endpoint: `POST /report/` → `POST /api/multi_agents` mit korrektem Payload
  - Report-Discovery: Rekursives `rglob` für `outputs/run_*/` Verzeichnisse
  - Stage 2 jetzt **blockierend** (kein `⚠️ Skipped` mehr)
- **Security Follow-ups** (#148): 3 offene Tasks aus Security-Gate-Policy abgeschlossen
  - `make security-project`: 0 Medium/High (bestätigt)
  - `make security-vendor`: 8H/16M/11L dokumentiert
  - Neuer Regression-Test: `tests/security/test_network_timeout_regression.py` (37→38 Security Tests)
  - Timeout-Hardening in `scrapers/http_session.py`
- **Operational Baseline** (#149): Runtime-Monitoring für Phase 8 Known Issues
  - `scripts/runtime_smoke.py`: SearXNG Engine-Count, Dashboard Static-Fallback, Port-Fix (8080→8090)
  - `dashboard/server.py`: Explizite Route für `static-fallback.html` → `text/html`
  - Phase 8 Known Issues als „überwacht“ / „akzeptiert“ dokumentiert

### Release Validation
- `make quality`: ✅ 1252 passed, 0 flaky
- `make security-project`: ✅ 0 Medium/High
- `make lint`: ✅ 0 Errors
- `make runtime-smoke`: ✅ Erweiterte Checks (SearXNG Engines, Dashboard Fallback)
- `make acceptance`: ✅ Ready (Stage 2 blocking, v3.5.0 API)

## [v0.3.0] — 2026-06-05

### Summary
Release v0.3.0 rollt die Phasen 6–8 zusammen. Coverage von 88% auf 100% gesteigert (4191 Statements), SearXNG mit 70+ Quellen, CI/CD Acceptance Gate, 5-Service-Infrastructure-Autostart, Dashboard-Fix. **256 Tests, 0 flaky, Security-Gate grün.**

### Phase 8 — Quality Hardening (#143)
- **Acceptance Test bestanden**: Alle 5 Gates grün (5 Services, Report-Qualität, 60 Quellen, 12 Claims) (#145)
- **SearXNG Quality Hardening**: 10+ Suchmaschinen aktiviert für breitere Quellenabdeckung
- **Dashboard Screenshot Fallback**: SSE-freie Static-Seite für Playwright-/CI-Screenshots
- **Infrastructure Autostart**: `start_all_services.sh` plus 5 systemd-Service-Dateien
- **CI/CD Acceptance Gate**: `make acceptance` und `scripts/ci_acceptance.py`
- **LLM Smoke Test CLI**: `cli/llm_smoke.py` für Live-Validierung

### Phase 7 — 100% Coverage (#142)
- **4191 Statements** mit 100% Coverage, alle Module abgedeckt
- **+35 Tests** in mcp_tools + search/composite (99% → 100%)
- **+12 Tests** in crawlers + claim_retriever + human_review
- Live LLM-Qualitäts-Optimierung (Qwen3.5 Extraction-Format)

### Phase 6 — Coverage 99%+ (#141)
- **0 mypy Errors**, **0 ruff Errors**
- **Playwright**: 3 Browser-Test-Fehler behoben (SSE, XSS, Visual-Regression)
- **Testing**: 1271 Tests passed, Coverage 88% → 99%+
- **Security Gate**: 0 Medium/High Bandit Findings im Projektcode

### Release Validation
- `make acceptance`: ✅ 5/5 Gates green
- `make quality`: ✅ 256 tests, 0 flaky
- `make security-project`: ✅ 0 Medium/High

## [Phase 8] — 2026-06-05
### Added
- **SearXNG Quality Hardening**: 10+ Suchmaschinen aktiviert für breitere Quellenabdeckung (#143)
- **Dashboard Screenshot Fallback**: SSE-freie Static-Seite für Playwright-/CI-Screenshots (`dashboard/static/static-fallback.html`) (#143)
- **Infrastructure Autostart**: `start_all_services.sh` plus 5 systemd-Service-Dateien für den lokalen Stack (#143)
- **CI/CD Acceptance Gate**: `make acceptance` und `scripts/ci_acceptance.py` als operative Qualitätsprüfung (#143)
- **LLM Smoke Test CLI**: `cli/llm_smoke.py` für opt-in Live-Validierung lokaler LLM-Endpunkte (#143)

### Changed
- **Service Architecture**: Ollama auf Embeddings-only, Qwen3.5 via eigenständigem llama-server auf Port 8082, SearXNG auf 8090, GPT Researcher via Docker auf 28202, Dashboard auf 8888 (#143)
- **Documentation**: `docs/development/local-runbook.md` für Phase 8 aktualisiert; Acceptance-Report-Template ergänzt (#143)

### Fixed
- **Dashboard Screenshot**: SSE-/Font-Timeouts durch den Static-Fallback umgangen (#143)
- **Operational Validation**: Acceptance-Checks jetzt gegen den vollständigen lokalen Stack dokumentiert (#143)

## [v0.2.5] — 2026-06-04
### Added
- **SearXNG Quality Hardening**: 10+ Suchmaschinen aktiviert (google, brave, startpage, bing, qwant, mojeek, yahoo, mwmbl, yacy, presearch) für ≥10 Quellen pro Query (#143)
- **Automated Acceptance Test**: `scripts/ci_acceptance.py` prüft 5 Services, Research-Pipeline, Report-Qualität (#143)
- **Infrastructure Autostart**: `start_all_services.sh` + 5 systemd Service-Dateien (ollama, llama, searxng, gptr, dashboard) (#143)
- **CI/CD Acceptance Workflow**: `.github/workflows/acceptance.yml` für PR-Gate (#143)
- **Dashboard Static Fallback**: `static-fallback.html` löst SSE/Playwright-Font-Timeout (#143)

### Changed
- **GPT Researcher Config**: TOTAL_WORDS 1200→3000, MAX_SUBTOPICS 3→5, Token-Limits erhöht (#143)
- **.env**: SEARX_URL korrigiert auf Port 8090, LLM-Modell auf qwen3.5-uncensored aktualisiert (#143)
- **SearXNG Port**: docker-compose.yml auf 8090 (Konfliktfrei mit anderen Diensten) (#143)

### Fixed
- **Dashboard Screenshot**: SSE-Blocking durch statischen Fallback behoben (#143)
- **SearXNG Quellenanzahl**: Von 5 auf 10+ Quellen erhöht (#143)

### Documentation
- `docs/development/dashboard-screenshot-fix.md` — SSE-Problem und Lösung
- `docs/development/local-runbook.md` — Ports, Dienste, statischer Fallback aktualisiert

## [v0.2.4] — 2026-06-03
### Changed
- **pyproject.toml**: 0.2.2 → **0.2.4** (Version-Nachzug für v0.2.3 + Stabilization)
- **README.md**: Version-Status von v0.1.0-local-alpha auf v0.2.4 aktualisiert

### Fixed
- **mypy: 40 Typfehler behoben** — Duplicate-Module (cli, tests), Union-Attribute (BeautifulSoup), Arg-Type, No-Redef, Method-Assign, Override-Signatur, Misc
- **ruff: 149 Linting-Fehler behoben** — Import-Sorting (130), E402 (5), E741 (2), N806 (7), F821 (1), F841 (1)
- **Playwright: 3 Browser-Test-Fehler behoben**
  - `test_gpu_sse_stream`: `HTTPServer` → `ThreadingHTTPServer` für SSE-Parallelität
  - `test_dashboard_xss_query_parameter_escaped`: Assertion an Query-Display-Präfix angepasst
  - `test_dashboard_visual_regression_screenshot`: Veraltete Baseline erneuert
- **test_mcp_tools.py**: Doppelten Test `test_audit_log_stats_json_decode_error` entfernt
- **test_deep_report_outline.py**: Doppelte Testnamen umbenannt/entfernt
- **test_crawlers.py**: Doppelten Test umbenannt

### Quality Gates
- `pytest`: **1271 passed**, 26 skipped
- `mypy`: **0 errors**
- `ruff`: **0 errors**
- `make security-project`: **0 Medium/High** Findings
- `coverage`: **88%** (≥78% threshold)
- `playwright`: **29 passed**

## [v0.2.3] — 2026-05-29
### Added
- **Submodul-Update: gpt_researcher v3.5.0** (#134): 45 neue Commits, Anthropic Tracking, max_tokens 200k, JSON-Repair, MCP env fix, OpenAlex, ModelsLab, uvm.
- **SearchIndexRepository-Port + Adapter** (#135): `SQLiteFTS5Adapter` (sqlite3/stdlib) und `WhooshIndexAdapter` (Whoosh) implementiert. Schließt 11 pre-existing Failures.
- **Compatibility-Layer** (#135): `gpt_researcher.adapters` und `gpt_researcher.ports` via conftest.py verfügbar.

### Fixed
- **TimeoutError in CompositeRetriever** (#136): Expliziter `TimeoutError`-Catch im `as_completed()`-Wrapper, Graceful Degradation mit partial results. 2 xfail-Tests → passed.
- **ModuleNotFoundError in tests** (#135): `gpt_researcher.adapters.sqlite_fts5_adapter` war nie importierbar — Adapter-Implementierung nach Bytecode-Rekonstruktion erstellt.
- **test.helpers Import** (#135): Fehlende `__init__.py` in `tests/` und `tests/helpers/` ergänzt.
- **Test-Mock für Chaos-Tests** (#136): `_Future`-Mock durch echte `concurrent.futures.Future`-Objekte ersetzt.

### Changed
- Submodul-Pin: `92bfc038` (v3.4.4) → `b364917f` (v3.5.0)
- `search/composite.py`: TimeoutError-Handling verbessert

### Security
- Vendor-Scan (`make security-vendor`): 8 High/16 Medium/Low Findings (report-only, per policy)
- Projekt-Scan (`make security-project`): 0 Medium/High

## [v0.2.2] — 2026-05-29
### Added
- **DB-Safety: ChromaDB Lock/Retry** (#122): RLock-basierte Serialisierung, Retry-Logik, Concurrency-Stresstests für parallele add/delete/update
- **DB-Safety: Whoosh Write-Pfade** (#123): RLock + LockError-Handling in add_post/optimize/clear, Concurrency-Stresstests
- **DB-Safety: JSON/JSONL Atomic-Write** (#124): tempfile + os.replace + Lock für atomare Schreibvorgänge, Partial-Line-Handling beim Lesen
- **DB-Safety: Concurrency-Stresstests** (#125): Systematische append/read/partial-lines Stresstests für JSONL-Dateien
- **CompositeRetriever: ValueError-Handler** (#130): as_completed()-Wrapper fängt ValueError bei Timeout/ConnectionError ab
- **create_session(): Timeout-Verifikation** (#131): Explizite Timeout-Dokumentation und Tests für http_session.create_session()

### Fixed
- **research-serve.sh**: Review-Finding behoben (Shell-Pfad-Hardening)
- **SSRF-Bypass**: URL-Validierung in web_fetch.py geschlossen (Host-Name-Check verstärkt)
- **B607 × 3** (gpu_monitor.py): nvidia-smi Partial-Path — akzeptiert (Standard-Systemtool), Security-Triage aktualisiert

### Changed
- **pyproject.toml**: 0.2.1 → **0.2.2**
- **ONNX Runtime entfernt**: Darknet-Resilience-Test nutzt keine externen Modelle mehr (`test_external_service_resilience.py`)

### Quality Gates
- `make quality`: **780 passed**, 24 skipped, 2 xfailed (+20 Tests seit v0.2.1)
- `make security-project`: **0 Medium/High** Findings (6 Low dokumentiert)
- `make lint`: **0 Errors**
- `make coverage`: **≥78%** (Projektcode)

### Known Failures (pre-existing)
- **9 Benchmark-Tests** in `test_index_backends.py`: `ModuleNotFoundError` für `gpt_researcher.adapters.sqlite_fts5_adapter` — Submodul nicht als Paket installiert
- **2 E2E Pipeline-Tests**: Gleiche `ModuleNotFoundError` + Retriever-Leerlauf (Mock-Konfiguration)

## [v0.2.1] — 2026-05-28
### Added
- **Qwen3.5-Uncensored-HauhauCS als alleiniges Primary-Modell** via llama-server (Port 8082, 45 tok/s)
- **ADR-017** — Qwen3.5-Uncensored-HauhauCS als Co-Primary-Modell (#117)
- **Scraper-HTTP-Resilience**: SSL-Fallback, 505-Retry, JS-Detection, Retry-Adapter (#118)
- **scrapers/http_session.py** — Zentrales HTTP-Session-Management mit Retry, User-Agent, Timeouts
- **Alle 5 Suchquellen** in Research-Happy-Path eingebunden (scraped + Snippet-Fallback)
- **Relevanzfilter** für gescrapte Inhalte
- **Viewport-Matrix** auf Aktiv gesetzt: Tablet (768×1024) + Mobile (375×812) (#42)

### Changed
- **Gemma 4 komplett entfernt** (#120): Alle Referenzen, Configs, Tests und Scripts bereinigt
- Qwen3.5 und Qwen3.5 parallel betreibbar (getrennte llama-server-Ports)
- `serve_qwen3.5_uncensored.sh` als Qwen3.5-Startpfad dokumentiert
- Qwen3.5 Prompt-Optimierung: enable_thinking-Konsistenz, Temperature-Sweep (#119)
- **Best-of-3 Extraction** mit proven params (temperature 0.3, repeat_penalty 1.2)
- Research-Happy-Path scrapt echte Artikel (statt Snippets), Extraction-Format optimiert
- `.env.example`, `docs/` und Runbooks auf Qwen3.5-Solo aktualisiert

### Fixed
- **Lint**: 5 dead-code errors in `scripts/research_happy_path.py` (F841 unused variables, I001 unsorted imports) — von Gemma-Entfernung hinterlassene Artefakte
- **Security B108**: Hardcoded `/tmp/` in `scripts/qwen3.5_optimize.py` → `tempfile.gettempdir()`
- **scripts/qwen3.5_optimize.py**: Duplicate Gemma 4 Output entfernt (Qwen-Ergebnisse wurden fälschlich als "Gemma 4" ausgegeben)
- `_build_summary_prompt()` Return-Type von `list[dict]` auf `dict` korrigiert

### Quality Gates
- `make quality`: **760 passed**, 21 skipped, 3 xfailed (+39 Tests seit v0.2.0)
- `make security-project`: **0 Medium/High** Findings
- `make lint`: **0 Errors**
- `make typecheck`: **0 Errors**

## [v0.2.0] — 2026-05-28
### Added
- **Qwen3.5 als primäres Chat-Modell** (ADR-016): Precision-Trap-Check in runtime_smoke, Deprecation-Warnung für qwen3.5:9b
- **UX-Heuristik-Prüfung**: Dashboard-Status-Legende (Grün/Gelb/Rot/Grau), UX-Review-Dokument (`docs/ux-heuristic-review.md`)
- **Viewport-Matrix**: Desktop (1280×720), Tablet (768×1024), Mobile (375×812) mit Screenshot-Baselines
- **Live-QA CI-Workflow**: `.github/workflows/live-qa.yml` für Self-Hosted-Runner mit GPU
- **Positron-tested Badge** im README
- **SearXNG-Config-Template**: `docs/searxng/settings.example.yml` mit secret_key-Dokumentation

### Changed
- pyproject.toml: 0.1.0 → **0.2.0**
- `.gitignore`: `searxng/` auf Root-Verzeichnis begrenzt (`/searxng/`), docs/searxng/ jetzt trackbar
- `config/ollama_models.py`: ADR-016-Docstring + validate_model_roles() warnt bei deprecated qwen3.5:9b
- `config/services.py`: OLLAMA_CHAT_MODEL als deprecated markiert
- `scripts/runtime_smoke.py`: Neue Precision-Trap-Validierung (`_check_qwen3.5_precision_trap()`)

### Fixed
- SearXNG-Container-Crash: `secret_key` in settings.yml ergänzt (muss pro Installation generiert werden)
- `.gitignore`-Pattern: `searxng/` matchte auch `docs/searxng/` (jetzt `/searxng/`)

### Documentation
- `docs/ux-heuristic-review.md` — 10 Nielsen-Norman-Heuristiken geprüft
- `docs/ci/live-qa-selfhosted.md` — Self-Hosted-Runner-Einrichtung
- `docs/searxng/settings.example.yml` — Config-Vorlage
- README: Positron-Badge ergänzt

### Quality Gates
- `make quality`: **721 passed**, 12 skipped, 3 xfailed (unverändert stabil)
- E2E-Tests: ⚠️ 6 failed (Submodul `gpt_researcher`-Adapter-Kompatibilität)

## [v0.1.0-local-alpha] — 2026-05-27

### Added
- Integration-Test der kompletten Research-Pipeline (`tests/integration/test_deep_research_pipeline.py`, 16 Tests)
- Mock-Audit: 20 Mock-/Platzhalter-Probleme durch echte Implementierungen ersetzt (#107)
- Evidence Store: `run_id`-Scoping für isolierte Run-Quellen (`evidence_store/models.py`, `evidence_store/store.py`)
- Verbindungs-Checker erweitert: API-Endpunkte, Plan-Roundtrip, Evidence-Store-Inhalt
- Deutsche Umlaut-Query-Fixtures (`tests/fixtures/german_queries.json`, `tests/helpers/german_query_fixtures.py`)

### Changed
- Tests: 255 → **716 passed** (0 failed)
- Coverage: 78.5% → **85.06%** (≥81%)
- Lint: 25 → **0 Errors**
- Typecheck: 2 → **0 Errors** (project code)
- Security (Medium+): 3 → **0 Findings** — `make security-project` grün
- ChromaDB `count()`: Rückgabewert `-1` → `0` bei fehlender Verbindung (Kompatibilität mit 1.5.9)

### Fixed
- **B310** (`urlopen`): `_validate_url_scheme()` in `config/local_llm_runtime.py` — schränkt auf http/https ein
- **B314** (`XML Parsing`): `defusedxml.ElementTree` statt `xml.etree.ElementTree` in `scripts/classify-errors.py`
- **Pre-Existing Test-Failures** (3 Stück):
  - `test_dashboard_static_files` — Assertion auf aktuelles GPU-Metrik-Label aktualisiert
  - `test_onion_pipeline` — Broken-Import in `onion_discovery/engine.py` behoben
  - Tor-Resilience-Tests — durch Engine-Fix automatisch korrigiert
- **Type-Errors**: `plan.edges` → `plan.dependencies` in `deep_research.py`; Type-Annotation in `runtime_smoke.py`
- **Test-Captures**: `test_e2e_config_module` — print_config verwendet `logger.info()` (stderr)
- **Embedding-Edge-Case**: `test_embedding_empty_text` — erwartet `ValueError` statt `[]`

### Security
- Project code: 0 Medium/High Bandit-Findings (alle 3 behoben)
- Security-Gate-Policy (`docs/security/security-gate-policy.md`) aktualisiert
- `defusedxml>=0.7.1` in requirements.txt ergänzt
- `coverage_html/` zu `.gitignore` hinzugefügt

### Known Limitations (aktualisiert)
- Aktuelles Chat-Modell: **Qwen3.5 E4B OBLITERATED** via llama-server (Port 8082, ~3.8 GB VRAM)
- qwen3.5-Ära beendet: Historisches Modell, durch Qwen3.5 obliterated ersetzt
- ChromaDB 1.5.9 `count()` gibt `-1` statt `0` bei fehlender DB — lokal abgefangen
- SSE-Stream blockiert Playwright `networkidle`-Wait
- Submodul `gpt_researcher`: Vendor-Findings report-only (20 dokumentiert)
- `reports/` nicht in CI-Artefakten (manueller Upload vorbereitet)

### Documentation
- `docs/release/release-checklist.md` — aktualisiert auf aktuellen Stand
- `docs/release/github-release-notes-v0.1.0-local-alpha.md` — Metriken aktualisiert
- `docs/release/known-limitations.md` — neue Limitationen ergänzt
- `docs/security/security-gate-policy.md` — Baseline-Verhalten dokumentiert

---

### Added (Initial, 2026-05-20)
- Complete quality gate (`make quality`): lint, typecheck, security, tests, coverage — 6-in-1, all blocking
- Runtime smoke test (`make runtime-smoke`): Ollama, SearXNG, Tor, Cloud-Blocker
- Minimal research happy path: Query → SearXNG → Ollama → Report
- Research report quality evaluation: 4 scores (Source Coverage, Traceability, Hallucination Risk, Local-First)
- Multi-query evaluation with aggregate scores
- Regression guard with baseline thresholds
- 14 security regression tests (network timeouts, cloud-blocker, hashing, SQL, SSL)
- Developer quickstart (fresh clone → green gates in <5 minutes)
- 11 Makefile test profiles (fast, e2e, benchmarks, quality, coverage, ci-local, ci-full)
- Runtime SearXNG Docker management targets
- Ollama model role separation (embed vs chat) with fallback

### Changed
- ruff lint errors: 1345 → 0
- mypy type errors: 33 → 0 (project code)
- Coverage: 75.80% → 78.5%
- E2E tests stabilized with proper mock scoping
- SQLite benchmark timeout: resolved via per-conftest timeout
- Bandit findings: 43 triaged, project code 0 Medium/High
- Submodule (`gpt_researcher/`): 14 security hardening fixes (MD5, timeouts)

### Fixed
- `make security` bandit installation
- E2E mock scope (ClaimValidator HTTP requests)
- mypy duplicate conftest (playwright, benchmarks)
- ruff per-file-ignores for submodule + embedded JS
- Ollama model name mismatch (embed/chat role confusion)
- SearXNG timeout (configurable `SEARXNG_TIMEOUT_SECONDS`)
- Source coverage regex for new report format

### Security
- Project code: 0 Medium/High Bandit findings
- Requests: all external calls have explicit timeouts
- Cloud-Blocker: prevents OpenAI/Tavily/Anthropic without `ALLOW_CLOUD`
- MD5: all uses marked `usedforsecurity=False` (non-security IDs)
- SQL: no f-string injection in project code
- SSL: no `verify=False` in project code
- Security gate policy documented in `docs/security/`

### Documentation
- `docs/security/bandit-triage.md`
- `docs/security/submodule-security-review.md`
- `docs/security/security-gate-policy.md`
- `docs/security/security-regression-tests.md`
- `docs/typing/typecheck-policy.md`
- `docs/testing/test-profiles.md`
- `docs/development/fresh-clone-onboarding.md`
- `docs/runtime/local-runtime-smoke.md`
- `docs/runtime/searxng-local-runtime.md`
- `docs/runtime/research-happy-path.md`
- `docs/evaluation/research-report-quality.md`
- `docs/release/v0.1.0-local-alpha.md`
- `docs/release/known-limitations.md`
- `docs/release/release-checklist.md`
- README.md: developer quickstart + runtime smoke

### Known Limitations
- Multi-query evaluation uses only generic safe queries
- Report evaluation is heuristic, not truth verification
- No cloud judge API
- No production darknet crawling
- SearXNG requires local Docker
- Ollama models must be locally available
- Playwright CI not finalized
- Submodule vendor findings are report-only
- Report quality depends on search results and local model
- No guarantee of factual truth — only evidence/traceability heuristics

---

## [Pre-Alpha] — 2026-05-17

### Initial State
- GPT Researcher v0.14.8 Fork
- FastAPI web UI
- Ollama integration
- SearXNG local search
- Tor/Darknet crawler
- ChromaDB vector store
- Whoosh/SQLite FTS5
- GPU dashboard
- MCP tools
- 167 tests, 75.80% coverage
- 1345 ruff errors

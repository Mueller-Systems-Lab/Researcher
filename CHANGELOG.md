# Changelog

## [v0.2.0] — 2026-05-28
### Added
- **Gemma 4 als primäres Chat-Modell** (ADR-016): Precision-Trap-Check in runtime_smoke, Deprecation-Warnung für qwen3.5:9b
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
- `scripts/runtime_smoke.py`: Neue Precision-Trap-Validierung (`_check_gemma4_precision_trap()`)

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
- Aktuelles Chat-Modell: **Gemma 4 E4B OBLITERATED** via llama-server (Port 8081, ~3.8 GB VRAM)
- qwen3.5-Ära beendet: Historisches Modell, durch Gemma 4 obliterated ersetzt
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

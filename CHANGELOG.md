# Changelog

## [v0.1.0-local-alpha] — 2026-05-20

### Added
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

# Known Limitations — v0.1.0-local-alpha

---

## Research Quality

- **Heuristic evaluation only**: Scores are based on structural features (source count, metadata, language patterns), not factual verification.
- **No truth detection**: The system cannot verify whether search results or LLM summaries are factually correct.
- **Query-dependent**: Report quality varies significantly with query domain and SearXNG result quality.
- **Generic queries only**: Multi-query evaluation uses only safe generic queries. No domain-specific validation.
- **No cloud judge**: Evaluation is purely local and heuristic. No external LLM-as-judge.

---

## Runtime Dependencies

- **SearXNG requires Docker**: Must be started separately (`make searxng-up`). Not included in `make quality`.
- **Ollama models must be local**: Chat and embedding models must be pre-downloaded (`ollama pull`).
- **Tor optional**: Darknet features require Tor SOCKS proxy (port 9050). Gracefully skipped if unavailable.
- **GPU optional**: GPU monitor runs only with NVIDIA hardware. Gracefully skipped otherwise.
- **First SearXNG query**: May take 20-30s due to engine initialization. Configurable via `SEARXNG_TIMEOUT_SECONDS`.

---

## Runtime Stability

- **qwen3.5-Modellinstabilität**: Lokale LLM-Modelle (qwen3.5-uncensored-no-thinking, qwen3.5:9b) crashen gelegentlich mit "llama runner process has terminated". Startup dauert 40-120s.
- **ChromaDB 1.5.9 count-Verhalten**: `count()` gibt `-1` statt `0` bei fehlender Verbindung. Wird lokal in `vectordb/store.py` abgefangen.
- **SSE blockiert Playwright**: Der Server-Sent-Events-Stream (SSE) der Dashboard-API verhindert, dass Playwright `networkidle` als Wait-Strategy verwenden kann.

## Testing

- **No live E2E in CI**: E2E tests use mocks. Real runtime tests require `RUN_E2E_TESTS=true` and running services.
- **Playwright CI not finalized**: Visual regression and accessibility tests need Playwright + Chromium. SSE-Stream blockiert networkidle-Wait.
- **Benchmarks optional**: `make test-benchmarks` takes ~3min, not in `make quality`.
- **Coverage floor**: 78.5% covers project code. Submodule code not measured.

---

## Security

- **Vendor findings report-only**: 20 submodule Bandit findings documented, not fixed.
- **SSL fallback in submodule**: PDF scraper uses `verify=False` as fallback after SSLError.
- **No automated dependency scanning**: Manual bandit/deptrack audit only.
- **MD5 accepted for non-security IDs**: Research IDs, cache keys use MD5 with `usedforsecurity=False`.

---

## Architecture

- **Submodule (`gpt_researcher/`)**: Vendor code, not maintained in this repo. Changes only via upstream or documented fork patches.
- **Whoosh index**: Used for darknet search. Not migrated to SQLite.
- **No production cloud fallback**: System is local-first. Cloud providers blocked by design.
- **Single-user local**: No multi-user, no clustering, no distributed deployment.

---

## Documentation

- **README + 14 docs files**: Developer quickstart, runtime guides, security policy, evaluation docs, release notes.
- **No API reference**: MCP tool APIs documented via inline help, not OpenAPI/Swagger.
- **No architecture diagram**: Text-only architecture overview in README.

---

## Next Steps (v0.2.0+)

1. Broader query evaluation dataset (deutsche Umlaut-Queries eingeführt ✅)
2. Truth-adjacent evaluation (cross-reference, contradiction detection)
3. Playwright CI integration (SSE-Blockade als bekanntes Problem dokumentiert)
4. Upstream PR for security hardening
5. Production darknet crawl validation
6. LLM-Modell-Stabilität verbessern (Ollama-Config, Fallback-Mechanismen)
7. Security-Regression-Tests vollständig in CI integrieren

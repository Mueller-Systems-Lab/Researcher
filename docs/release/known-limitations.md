# Known Limitations — v0.2.2

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

- **Qwen3.5-Uncensored-HauhauCS (Chat/Solo)**: Alleiniges Primary-Modell via llama-server (Port 8082, ~3.8 GB VRAM). 45 tok/s. Keine Ollama-Abhängigkeit für Chat — eigener Prozess. Gemma 4 komplett entfernt (#120).
- **Precision Trap (Qwen3.5 + Pascal)**: Auf GTX 1070 (Pascal) muss der KV-Cache in FP32 laufen (`-ctk f32 -ctv f32`). FP16 erzeugt garbled Output. `--flash-attn off` ist ebenfalls nötig, da Pascal keine Tensor Cores besitzt. Diese Flags sind in `serve_qwen3.5_obliterated_researcher.sh` gesetzt.
- **qwen3.5 (Deprecated)**: Historisches Chat-Modell. Crashte gelegentlich mit "llama runner process has terminated". Vollständig durch Qwen3.5 obliterated ersetzt.
- **nomic-embed-text (Embedding)**: Läuft weiterhin via Ollama (Port 11434). 274 MB, stabil.
- **ChromaDB 1.5.9 count-Verhalten**: `count()` gibt `-1` statt `0` bei fehlender Verbindung. Wird lokal in `vectordb/store.py` abgefangen.
- **SSE blockiert Playwright**: Der Server-Sent-Events-Stream (SSE) der Dashboard-API verhindert, dass Playwright `networkidle` als Wait-Strategy verwenden kann.

## Testing

- **No live E2E in CI**: E2E tests use mocks. Real runtime tests require `RUN_E2E_TESTS=true` and running services.
- **Playwright CI not finalized**: Visual regression and accessibility tests need Playwright + Chromium. SSE-Stream blockiert networkidle-Wait.
- **Benchmarks optional**: `make test-benchmarks` takes ~3min, not in `make quality`.
- **11 pre-existing Test-Failures**: 9 Benchmark + 2 E2E — `gpt_researcher.adapters.*` nicht pip-installiert. Kein Regression durch v0.2.2.
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

## Next Steps (v0.2.2+)

1. DB-Safety-Runde 2: SQLite FTS5, Research-Orchestrator-Storage, Evidence-Store ✅
2. Pre-existing Test-Failures beheben: 9 Benchmark + 2 E2E (Submodul-Adapters pip-installieren)
3. Truth-adjacent evaluation (cross-reference, contradiction detection)
4. Playwright CI integration (SSE-Blockade als bekanntes Problem dokumentiert)
5. Upstream PR for security hardening
6. Production darknet crawl validation
7. LLM-Modell-Stabilität verbessern (Ollama-Config, Fallback-Mechanismen)
8. Security-Regression-Tests vollständig in CI integrieren

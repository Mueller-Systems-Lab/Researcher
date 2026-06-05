# Phase 10 Planning — Post Operational Readiness

**Status:** Proposed  
**Date:** 2026-06-05  
**Scope:** Researcher Phase 10 roadmap after Phase 9 / v0.4.0  
**Deciders:** Researcher maintainers

## Context: Phase 9 Completion

Phase 9 — Operational Readiness is complete and released as `v0.4.0`.
The release established a stable operational baseline for the local Researcher stack:

- Ollama for embeddings
- llama-server / Qwen3.5 for chat and extraction
- SearXNG for metasearch
- GPT Researcher Docker backend for research execution
- Dashboard for runtime monitoring

Validation state at Phase 10 handoff:

- `make acceptance`: all 5 gates green
- Security gate: 0 project Medium/High findings via `make security-project`
- Flakiness: 0 flaky tests reported
- Live E2E: validated
- Test count: Phase 10 handoff reports 1254 tests; `CHANGELOG.md` release entry records 1252 tests at the v0.4.0 cut

Known operational issues from Phase 8 are no longer release blockers, but remain design inputs:

- Dashboard SSE can still block Playwright `networkidle`; static fallback is monitored.
- Qwen3.5 precision settings remain important on Pascal GPUs.
- SearXNG engine availability varies due to upstream CAPTCHA/rate limiting.

## Planning Criteria

Each Phase 10 candidate is evaluated against:

- **User value:** Does it improve research outcomes or operator confidence?
- **Blocker status:** Is it blocking future work or release quality?
- **Risk:** Security, legal/compliance, runtime, coupling, or maintenance risk.
- **Feasibility:** Fit with current stack and available Makefile targets.
- **Architecture fit:** Low coupling, high cohesion, clear data flow, testability, and security boundaries.

Effort estimate scale:

- **S:** 1–3 focused days
- **M:** 1–2 weeks
- **L:** multi-week or cross-cutting initiative

## Candidate Evaluation

| Candidate | User Value | Blocker Status | Risk | Feasibility | Effort | Assessment |
|---|---|---|---|---|---:|---|
| Research Quality Benchmarking | **High** — directly measures answer quality, hallucination rate, German-query performance, and claim support | **High** — needed before optimizing retrieval, darknet integration, or MCP evidence tools | Medium — benchmark design can bias results if fixtures are weak | **High** — Makefile already has `research-evaluate-multi`, `research-evaluate-german`, and `research-evaluate-strict` | M | Best first theme because Phase 9 proved the system runs; Phase 10 should prove it is consistently useful. |
| Darknet-Search-Integration | Medium/High — expands source coverage for specialized OSINT/security research | Low/Medium — valuable but not required for baseline research quality | **High** — Tor crawling, legal boundaries, rate limits, robots/opt-out behavior, abuse prevention, and evidence provenance | Medium — isolated `darknet_search/` exists, but pipeline integration needs strict boundaries | L | Defer until quality benchmark and safety policy can measure and constrain impact. |
| Submodul-Upstream-PRs | Medium — reduces long-term vendor security debt and helps upstream | Medium — security policy lists upstream timeout findings as follow-up | Low/Medium — PR review and submodule drift risk | **High** — scoped to known 8 timeout findings; `security-vendor` is report-only | S/M | Good parallel or second-track item; does not change local runtime architecture. |
| MCP-Tool-Erweiterung | Medium/High — enables structured external access to evidence, audit exports, and possibly darknet search | Medium — useful once evidence schemas and benchmark metrics are stable | **High** — MCP tools need explicit trust boundaries, argument validation, audit logging, and no ambient tool exposure | Medium — repo-local `researcher-mcp` is allowed, but new tool contracts need ADRs/tests | M/L | Defer broad expansion until evidence retrieval and audit data models are stabilized by benchmarking work. |
| Dashboard Live-Überwachung | Medium — improves operator confidence and production-like observability | Medium — SSE issue remains accepted but unresolved | Medium — metrics endpoints and alerts must avoid leaking sensitive prompts/results | **High** — Dashboard and `runtime-smoke` already exist; Prometheus export is cohesive | M | Good Phase 10 theme after or alongside benchmarking; reduces operational blind spots. |

## ADR-Phase10-001: Prioritize Quality Measurement Before New Source Expansion

**Status:** Proposed  
**Date:** 2026-06-05  
**Deciders:** Researcher maintainers  
**Context:** Phase 10 roadmap selection after Phase 9 Operational Readiness

### Context

Phase 9 validated that the five-service local stack can run reliably and pass acceptance gates. The next decision is whether Phase 10 should expand capabilities immediately or first improve measurement of research quality. The most important constraint is that future changes must preserve the Phase 9 baseline: 0 project Medium/High security findings, 0 flaky tests, and green acceptance gates.

### Decision

Phase 10 should prioritize **Research Quality Benchmarking** as the first theme, followed by **Dashboard Live-Überwachung** and **Submodul-Upstream-PRs** as the next two roadmap items.

Darknet pipeline integration and broad MCP tool expansion should be deferred until quality metrics, evidence schemas, and security boundaries are stable enough to evaluate their impact.

### Alternatives Considered

#### Alternative A — Integrate Darknet Search First

- **Pros:** Adds differentiated capability and broader OSINT coverage.
- **Cons:** High security/compliance risk; introduces Tor crawling into the main data flow before hallucination and source-quality metrics are mature; increases coupling between isolated `darknet_search/` and the research pipeline.
- **Decision:** Not selected for first Phase 10 work. Revisit after quality benchmarks define safe acceptance criteria.

#### Alternative B — Expand MCP Tools First

- **Pros:** Improves automation surface for evidence retrieval, audit export, and future integrations.
- **Cons:** Tool contracts would be premature without stable evidence schemas; MCP tools require strict trust boundaries, validation, and audit logging; darknet-search as a tool would compound risk.
- **Decision:** Not selected as a primary Phase 10 starting point. Do only narrow design spikes after benchmarking defines required evidence artifacts.

#### Alternative C — Quality Benchmarking First

- **Pros:** Directly improves confidence in research output; uses existing evaluation targets; creates measurable gates for hallucination rate, claim support, German-query quality, and source diversity; keeps coupling low by focusing on evaluation harnesses and fixtures.
- **Cons:** Does not immediately add new user-facing capabilities; requires careful fixture design to avoid benchmark gaming.
- **Decision:** Selected as first theme.

### Consequences

Easier:

- Compare changes across retrieval, extraction, and reporting.
- Set measurable acceptance criteria for future darknet and MCP work.
- Detect regressions in German queries, claim verification, and hallucination behavior.

Harder:

- Feature expansion is delayed until measurement is stronger.
- Benchmark maintenance becomes a recurring responsibility.

## Proposed Phase 10 Roadmap

### 1. Research Quality Benchmarking — First Theme

**Priority:** P0  
**Effort:** M  
**Goal:** Turn the Phase 9 operational baseline into a measurable quality baseline.

Deliverables:

- Multi-query evaluation plan using German and mixed-language query fixtures.
- Hallucination-rate measurement based on unsupported or weakly supported claims.
- Systematic claim verification report: supported / partially supported / unsupported.
- Baseline thresholds for `research-evaluate-multi-strict` and `research-evaluate-german`.
- Documentation of scoring limitations and manual-review rules.

Suggested validation:

- `make research-evaluate-multi`
- `make research-evaluate-german`
- `make research-evaluate-strict`
- `make acceptance`
- `make quality`

### 2. Dashboard Live-Überwachung

**Priority:** P1  
**Effort:** M  
**Goal:** Improve observability without weakening the static fallback used by tests.

Deliverables:

- Stabilized SSE behavior or explicit documented split between live UI and automation-safe views.
- Prometheus-style metrics endpoint for GPU/runtime health.
- Alert thresholds for GPU availability, llama-server health, SearXNG engine count, and acceptance-critical service health.
- Security review of metrics to ensure no prompts, reports, secrets, or source URLs are leaked unintentionally.

Suggested validation:

- `make runtime-smoke`
- `make acceptance-services`
- `make playwright` where applicable
- `make security-project`

### 3. Submodul-Upstream-PRs

**Priority:** P1/P2  
**Effort:** S/M  
**Goal:** Reduce vendor security debt by upstreaming the remaining requests-without-timeout fixes to GPT Researcher.

Deliverables:

- Minimal upstream PR(s) for the 8 timeout findings referenced by the security follow-ups.
- Local documentation update after upstream status is known.
- Re-run of vendor scan and project scan after any submodule pin changes.

Suggested validation:

- `make security-vendor`
- `make security-report`
- `make security-project`
- `make ci-local` if the submodule pin changes locally

## Deferred Themes

### Darknet-Search-Integration

Defer until Phase 10 quality metrics can answer whether darknet sources improve or degrade report quality. Before integration, define:

- Tor/data-flow boundary between `darknet_search/` and the research pipeline.
- Rate limits, opt-out/robots handling where applicable, and legal-use warnings.
- Source provenance markers and safe content handling.
- Dedicated security tests and acceptance criteria.

Estimated future effort: **L**.

### MCP-Tool-Erweiterung

Defer broad tool expansion until benchmark outputs define stable evidence and audit artifacts. Before implementation, define ADRs for each significant tool surface:

- `evidence-retrieval`: read-only, provenance-preserving, input-limited.
- `audit-export`: redaction and export boundary required.
- `darknet-search`: only after darknet integration policy is accepted.

Estimated future effort: **M/L**.

## Dependencies

| Dependency | Affects | Notes |
|---|---|---|
| Existing evaluation scripts and fixtures | Research Quality Benchmarking | Makefile already exposes multi-query and German evaluation targets. |
| Stable report/evidence schema | MCP tools, audit export, claim verification | Benchmarking should define or validate the schema before tools expose it. |
| Security Gate Policy | All themes | Project Medium/High findings remain blocking; vendor findings remain report-only unless local code changes introduce risk. |
| Dashboard static fallback | Dashboard monitoring, Playwright | Live SSE improvements must not break automation-safe screenshots. |
| SearXNG engine stability | Benchmarking, acceptance, darknet comparison | Engine variance must be measured separately from model quality. |
| Tor safety policy | Darknet integration, darknet MCP tool | Required before connecting isolated darknet functionality to the main pipeline. |

## Architecture Review Checklist

- [x] New dependency justified: no new dependency is proposed for the first theme; later Prometheus export may need separate justification.
- [x] Module coupling acceptable: benchmarking remains separate from runtime services; darknet and MCP expansion deferred to avoid premature coupling.
- [x] Data flow documented and secure: current plan keeps sensitive report/prompt data out of metrics and requires provenance for future evidence flows.
- [x] Error handling strategy consistent: use existing acceptance, runtime-smoke, and evaluation gates as regression checks.
- [x] Scaling bottlenecks identified: multi-query evaluation will stress SearXNG variance, local LLM throughput, and report generation time.
- [x] Security boundaries clearly defined: darknet and MCP expansion require separate ADRs before implementation.
- [x] Testing strategy adequate for planning: reuse `make quality`, `make acceptance`, evaluation targets, and security targets.

## Recommended First Action

Start with **Research Quality Benchmarking**.

Rationale:

1. Phase 9 proved operational readiness; Phase 10 should now prove output quality.
2. Existing Makefile targets already support multi-query and German-query evaluation, making this feasible without major architecture changes.
3. Quality metrics become prerequisites for safely judging darknet source expansion and MCP evidence tools.
4. This keeps risk lower than adding Tor crawling or new tool surfaces before measurement and security boundaries are mature.

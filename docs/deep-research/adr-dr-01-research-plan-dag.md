# ADR-DR-01: Local Research Plan DAG Architecture

**Status:** Accepted  
**Date:** 2026-05-24  
**Context:** Issue DR-01 — Collaborative Planner + Research Plan DAG

## Decisions

### 1. Data Model: `dataclasses` over Pydantic or dicts

Use Python `dataclasses` + `Enum` types for `ResearchPlan`, `ResearchNode`, etc.

**Rationale:** Lightweight, no extra dependencies, explicit typing, easy to test.

### 2. DAG Validation: Kahn Topological Sort

Validate DAG acyclicity via in-degree-based topological sort.

**Rationale:** Detects cycles AND produces execution order needed by DR-02.

### 3. Serialization: Stable JSON with Schema Version

JSON is the canonical machine format (`schema_version: research-plan/v1`). Markdown export for human review.

**Rationale:** Portable, testable, API-friendly.

### 4. Planner Strategy: Hybrid (Deterministic + Optional LLM)

1. Deterministic rule/template-based decomposition (always available baseline)
2. Optional local LLM refinement via llama-server
3. Strict fallback to deterministic on any LLM failure

**Rationale:** Testable offline, local-first, handles GTX 1070 constraints.

### 5. Approval Gate: Explicit `assert_plan_approved()`

DR-02 Orchestrator must call `assert_plan_approved()` before starting.

**Rationale:** Human-in-the-loop enforced at code level, not just UI.

### 6. Module Boundaries: Planner owns only plan artifacts

`research_planner` generates and validates plans. It delegates execution, searching, evidence, and reporting to later modules.

## Risks

- Manual validation required (dataclasses lack built-in schema validation).
- LLM planner is nondeterministic; tests target deterministic fallback.
- Approval can be bypassed if DR-02 skips the guard.

## References

- Issue: [#98](https://github.com/xxammaxx/Researcher/issues/98)
- Code: `research_planner/`

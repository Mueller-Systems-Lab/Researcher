# Research Planner — DAG-based Research Planning (DR-01)

## Overview

The `research_planner` package implements a Collaborative Planner that converts a user query into an editable, DAG-based ResearchPlan. This is the first step in the Deep Research pipeline.

## Architecture

```
User Query
  → generate_plan()
     ├─ Deterministic planner (template decomposition) ← always available
     └─ Optional LLM planner (llama-server) ← fallback to deterministic
  → validate_plan()  (Kahn topological sort)
  → JSON / Markdown export
  → approve_plan()  → Human-in-the-loop
```

## Data Model

- **ResearchPlan** — Root container: query, nodes, dependencies, status, metadata
- **ResearchNode** — Atomic research sub-question with dependencies
- **ResearchDependency** — Directed edge between nodes
- **ResearchPlanStatus** — draft → approved → running → completed / failed / cancelled

## Key Design Decisions (ADR-DR-01)

1. **dataclasses** over Pydantic — lightweight, local-first, no extra deps
2. **Kahn topological sort** for validation — detects cycles AND produces orchestration order
3. **JSON as canonical format** with schema version
4. **Hybrid planner** — deterministic baseline + optional LLM with fallback
5. **No content filtering** — uncensored research, including security/darknet topics

## Usage

```python
from research_planner.planner import generate_plan
from research_planner.approval import approve_plan, assert_plan_approved
from research_planner.serialization import plan_to_json, plan_to_markdown

plan = generate_plan("Vergleiche Python und Rust für ML-Pipelines.")
print(plan_to_markdown(plan))

approve_plan(plan)
assert_plan_approved(plan)  # Gate for DR-02 Orchestrator

json_str = plan_to_json(plan)
```

## File Structure

```
research_planner/
  __init__.py       — Package init
  models.py         — ResearchPlan, ResearchNode, ResearchDependency, Status
  planner.py        — generate_plan() — hybrid decomposition
  validation.py     — validate_plan() — Kahn topological sort
  serialization.py  — JSON import/export, Markdown export
  approval.py       — approve_plan(), assert_plan_approved()
```

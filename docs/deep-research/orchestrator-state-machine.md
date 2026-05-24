# Research Orchestrator — Durable Execution Engine (DR-02)

## Overview

The `research_orchestrator` implements a Master Orchestrator that traverses an approved ResearchPlan DAG topologically, persists execution state, logs events, and supports resume after interruption.

## Architecture

```
Approved ResearchPlan
  → create_run()          — initialize RunState, persist state.json
  → start_run(worker)     — execute DAG topologically
     ├─ compute ready nodes
     ├─ execute via worker callback
     ├─ persist state.json after each step
     └─ log events to events.jsonl
  → resume_run(run_id)    — reload state + continue
```

## State Machine

```
CREATED → RUNNING → COMPLETED
                  → FAILED
                  → CANCELLED

Per-node: PENDING → READY → RUNNING → COMPLETED
                                   → FAILED
                            PENDING → BLOCKED (dependency failed)
```

## Storage

```
reports/deep_research/runs/<run_id>/
  state.json     — full RunState snapshot
  events.jsonl   — append-only event log
```

## Key Design Decisions

1. **Filesystem-based storage** — no database, no migration
2. **Sequential default** — GTX 1070 friendly, parallel optional
3. **Worker callback pattern** — orchestrator doesn't do research, it delegates
4. **Event sourcing** — events.jsonl provides full audit trail
5. **Resume by replay** — reload state.json, skip completed nodes

## Usage

```python
from research_planner.planner import generate_plan
from research_planner.approval import approve_plan
from research_orchestrator.orchestrator import create_run, start_run, resume_run

plan = generate_plan("Research topic")
approve_plan(plan)

state = create_run(plan)
state = start_run(state, worker=my_research_worker)

# Later, resume:
state = resume_run(run_id, worker=my_research_worker)
```

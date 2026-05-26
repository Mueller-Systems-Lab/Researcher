# Issue DR-02 — Master Orchestrator + Persistent Research State

## Ziel

Implementiere einen Master Orchestrator, der einen freigegebenen ResearchPlan-DAG topologisch abarbeitet, Status persistiert und Wiederaufnahme nach Fehlern ermöglicht.

---

# Kontext

Deep-Research-Systeme laufen länger als einfache LLM-Calls. Sie brauchen durable execution, Zwischenspeicher, Event-Logs, Resume und klare Zustandsübergänge.

---

# Betroffene Module

Neu:

```text
research_orchestrator/
  __init__.py
  orchestrator.py
  state.py
  events.py
  scheduler.py
  storage.py
tests/test_research_orchestrator.py
docs/deep-research/orchestrator-state-machine.md
```

---

# Anforderungen

## State Store

Persistiere:

```text
run_id
plan_id
node_statuses
started_at
updated_at
completed_at
events
errors
artifacts
```

Storage minimal:

```text
reports/deep_research/runs/<run_id>/state.json
reports/deep_research/runs/<run_id>/events.jsonl
```

Keine Datenbankmigration.

---

# Orchestrator-Verhalten

Der Orchestrator:

1. lädt approved ResearchPlan
2. berechnet ready nodes
3. startet Researcher Worker pro ready node
4. speichert Ergebnisse
5. markiert Knoten completed/failed
6. startet abhängige Knoten
7. erzeugt Abschlussstatus

Parallelität:

```text
Default: sequential
Optional: max_parallel=2
```

Für GTX 1070 zunächst sequential bevorzugen.

---

# Event Log

Events:

```text
RUN_CREATED
NODE_READY
NODE_STARTED
NODE_COMPLETED
NODE_FAILED
RUN_COMPLETED
RUN_FAILED
RUN_CANCELLED
```

---

# Tests

- draft plan wird abgelehnt
- approved plan startet
- topologische Reihenfolge stimmt
- abhängige Knoten starten erst nach Dependencies
- failed node blockiert abhängige Knoten
- state.json wird geschrieben
- events.jsonl wird geschrieben
- Resume lädt Zustand
- sequential mode stabil

---

# Akzeptanzkriterien

Given ein freigegebener DAG  
When der Orchestrator startet  
Then werden Knoten in gültiger Reihenfolge verarbeitet.

Given ein Knoten schlägt fehl  
When abhängige Knoten geprüft werden  
Then werden sie nicht gestartet.

Given ein Run wurde unterbrochen  
When Resume ausgeführt wird  
Then wird der letzte persistierte Zustand geladen.

---

# Validierung

```bash
python3 -m pytest tests/test_research_orchestrator.py -q
make quality
make coverage
```

---

# Nicht-Ziele

- kein echtes Crawling
- keine parallele Massenverarbeitung
- keine UI
- keine Cloud

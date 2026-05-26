# Issue DR-01 — Collaborative Planner + Research Plan DAG

## Ziel

Implementiere einen lokalen Collaborative Planner, der eine Nutzerfrage in einen editierbaren Forschungsplan als gerichteten azyklischen Graphen (DAG) überführt.

Dieses Issue erzeugt noch keine Webrecherche. Es erzeugt nur Planungsartefakte.

---

# Kontext

Deep-Research-Systeme starten nicht direkt mit Crawling, sondern erzeugen zuerst einen mehrstufigen Forschungsplan. Der Nutzer kann diesen Plan prüfen, ändern und freigeben. Erst danach startet die eigentliche Recherche.

---

# Betroffene Module

Neu:

```text
research_planner/
  __init__.py
  models.py
  planner.py
  validation.py
  serialization.py
tests/test_research_planner.py
docs/deep-research/planner-dag.md
```

---

# Anforderungen

## Datenmodell

Erzeuge:

```python
ResearchPlan
ResearchNode
ResearchDependency
ResearchPlanStatus
```

Pflichtfelder:

```text
plan_id
query
created_at
status
nodes
dependencies
assumptions
constraints
user_notes
```

Knoten:

```text
node_id
title
question
rationale
depends_on
expected_sources
status
risk_level
```

Status:

```text
draft
approved
running
completed
failed
cancelled
```

---

# Planner-Verhalten

Der Planner soll aus einer Frage einen DAG erzeugen.

Beispiel:

```text
User Query:
"Vergleiche lokale LLM-Runtimes für GTX 1070 und bestimme den besten Pfad für Researcher."

Plan:
1. Hardware Constraints erfassen
2. Modellkandidaten erfassen
3. Runtime-Optionen vergleichen
4. Stabilität/Performance bewerten
5. Integrationsentscheidung formulieren
```

---

# Human-in-the-loop

Der Plan muss freigegeben werden.

Regel:

```text
Ohne status=approved darf kein Orchestrator starten.
```

---

# Tests

Pflichttests:

- Plan aus Query erzeugbar
- Plan enthält mindestens 3 Knoten
- Knoten haben eindeutige IDs
- Abhängigkeiten sind azyklisch
- ungültiger Zyklus wird abgelehnt
- Plan kann JSON exportieren/importieren
- Plan kann Markdown exportieren
- unapproved Plan kann nicht gestartet werden

---

# Akzeptanzkriterien

Given eine komplexe Nutzerfrage  
When der Planner ausgeführt wird  
Then entsteht ein validierter DAG mit mehreren Forschungsfragen.

Given ein DAG mit Zyklus  
When er validiert wird  
Then wird er abgelehnt.

Given ein Plan im Status draft  
When der Orchestrator ihn starten will  
Then wird der Start blockiert.

Given ein Plan im Status approved  
When er serialisiert wird  
Then bleiben alle Knoten und Abhängigkeiten erhalten.

---

# Validierung

```bash
python3 -m pytest tests/test_research_planner.py -q
make quality
make coverage
```

---

# Nicht-Ziele

- keine Websuche
- kein Crawling
- keine Report-Erzeugung
- keine UI-Pflicht
- keine Cloud

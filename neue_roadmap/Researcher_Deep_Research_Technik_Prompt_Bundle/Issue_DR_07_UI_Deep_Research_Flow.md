# Issue DR-07 — UI Integration: Plan → Approve → Run → Report

## Ziel

Verdrahte GPT-Researcher UI oder lokales Dashboard so, dass der Nutzer den lokalen Deep-Research-Flow bedienen kann.

---

# Kontext

Deep Research ist ohne UI- oder CLI-Interaktion schwer benutzbar, weil der Plan freigegeben, Fortschritt beobachtet und der Bericht geprüft werden muss.

---

# Betroffene Module

Erweitert:

```text
dashboard/server.py
dashboard/static/index.html
gpt_researcher frontend/backend integration
scripts/gpt_researcher_ui_smoke.py
tests/playwright/test_deep_research_ui.py
docs/deep-research/ui-flow.md
```

---

# UI Flow

```text
1. Query eingeben
2. Plan erzeugen
3. Plan anzeigen
4. Plan freigeben
5. Research starten
6. Fortschritt pro DAG-Knoten anzeigen
7. Evidence Count anzeigen
8. Report anzeigen
9. Evaluation anzeigen
10. Export/Markdown-Pfad anzeigen
```

---

# API-Endpunkte

```text
POST /api/deep-research/plan
GET  /api/deep-research/plans/{id}
POST /api/deep-research/plans/{id}/approve
POST /api/deep-research/runs
GET  /api/deep-research/runs/{id}
GET  /api/deep-research/runs/{id}/events
GET  /api/deep-research/runs/{id}/report
GET  /api/deep-research/runs/{id}/evaluation
```

---

# SSE / Streaming

Fortschritt darf per SSE laufen.

Playwright Tests dürfen NICHT `networkidle` als alleinige Readiness nutzen.

Nutze:

```text
domcontentloaded
visible element assertions
event count assertions
```

---

# Tests

- Plan UI sichtbar
- Approve Button funktioniert
- Run startet
- Event Stream zeigt Fortschritt
- Report Link sichtbar
- Evaluation sichtbar
- keine Console Errors
- Screenshot erzeugt
- fehlende Services zeigen verständliche Fehler

---

# Akzeptanzkriterien

Given Nutzer gibt Query ein  
When Plan erzeugt wird  
Then sieht er editierbaren Plan.

Given Plan approved  
When Run startet  
Then sieht Nutzer DAG-Fortschritt.

Given Run completed  
When Bericht erzeugt wurde  
Then sieht Nutzer Report und Evaluation.

---

# Validierung

```bash
UI_BASE_URL=http://127.0.0.1:8000 python3 scripts/gpt_researcher_ui_smoke.py --deep-research
RUN_PLAYWRIGHT_TESTS=true pytest tests/playwright/test_deep_research_ui.py -v
make quality
make coverage
```

---

# Nicht-Ziele

- kein neues großes Frontend-Framework
- keine Cloud
- keine Online-CI
- kein Release

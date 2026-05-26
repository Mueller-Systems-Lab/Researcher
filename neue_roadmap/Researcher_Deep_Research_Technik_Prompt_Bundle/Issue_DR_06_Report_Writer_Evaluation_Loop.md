# Issue DR-06 — Report Writer + Evaluation Loop

## Ziel

Implementiere einen Deep-Research Report Writer, der aus ResearchPlan, Knotenresultaten und Evidence Store einen zitierten Bericht erzeugt und automatisch bewertet.

---

# Kontext

Der Report Writer synthetisiert die strukturierten Teilergebnisse, entfernt Redundanzen, harmonisiert den Stil und verankert präzise Inline-Zitate. Die bestehende Report-Evaluation wird auf Deep Research erweitert.

---

# Betroffene Module

Neu/Erweitert:

```text
deep_report/
  __init__.py
  writer.py
  outline.py
  citation_inserter.py
  evaluator.py
  revision_loop.py
tests/test_deep_report_writer.py
docs/deep-research/report-writer-evaluation.md
```

---

# Report-Struktur

Pflichtsektionen:

```text
Title
Executive Summary
Research Question
Method / Search Plan
Findings by DAG Node
Evidence Table
Limitations
Uncertainty
Source List
Evaluation Summary
```

---

# Zitierregeln

- jede zentrale Behauptung braucht Citation
- Citation Format: `[S1]`
- Source List am Ende
- keine Citation ohne Evidence Store
- keine erfundenen Quellen
- keine rohen untrusted Prompt-Injection-Inhalte übernehmen

---

# Evaluation Scores

Erweitere bestehende Evaluation um:

```text
source_coverage
traceability
evidence_diversity
node_completion
hallucination_risk
local_first
injection_risk
overall
```

---

# Revision Loop

Wenn:

```text
overall < 90
source_coverage < 80
traceability < 90
local_first < 100
```

Dann:

- Bericht nicht final
- Missing Evidence benennen
- Gap Queries erzeugen
- Orchestrator kann neue Searcher-Runde starten

---

# Tests

- Report aus Dummy Evidence erzeugt
- Inline Citations vorhanden
- Source List vollständig
- Missing Citation wird erkannt
- Evaluation Scores erzeugt
- Low score triggert Revision Request
- Local-First bleibt 100 ohne Cloud
- Prompt-Injection-Text wird nicht als Anweisung übernommen

---

# Akzeptanzkriterien

Given ein abgeschlossener ResearchRun  
When Report Writer läuft  
Then entsteht ein Markdown-Bericht mit Zitaten.

Given Evidence fehlt  
When Evaluation läuft  
Then Score sinkt und Revision wird angefordert.

Given Prompt-Injection-Segment  
When Bericht erzeugt wird  
Then wird es neutralisiert oder als Risiko markiert, nicht ausgeführt.

---

# Validierung

```bash
python3 -m pytest tests/test_deep_report_writer.py -q
make quality
make coverage
```

---

# Nicht-Ziele

- keine PDF/Docx-Exports
- keine Cloud-Judges
- keine UI-Pflicht

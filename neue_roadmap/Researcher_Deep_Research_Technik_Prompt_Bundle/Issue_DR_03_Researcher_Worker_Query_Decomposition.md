# Issue DR-03 — Researcher Worker + Query Decomposition

## Ziel

Implementiere einen Researcher Worker, der einen ResearchNode in konkrete Suchqueries und Gap-Followups zerlegt.

---

# Kontext

Der Researcher Agent dekomponiert Teilfragen, vertieft Keywords und übersetzt Lücken aus vorherigen Schritten in neue Suchanfragen.

---

# Betroffene Module

Neu:

```text
research_workers/
  __init__.py
  query_decomposer.py
  gap_analyzer.py
  worker.py
tests/test_research_worker_queries.py
docs/deep-research/researcher-worker.md
```

---

# Anforderungen

## Query Decomposition

Aus ResearchNode:

```text
question
rationale
expected_sources
context_from_dependencies
```

werden erzeugt:

```text
primary_queries
entity_queries
gap_queries
negative_queries
```

---

# Mehrsprachigkeit

Für deutsche Queries:

- Originalquery behalten
- deutsche Search Keys nutzen
- optional englische Variante erzeugen
- keine Umlaute zerstören

---

# Tests

- einfache Node erzeugt Primary Queries
- Dependency-Kontext erzeugt Entity Queries
- bekannte Gap erzeugt Gap Query
- negative Query wird erzeugt
- deutsche Query behält Umlaute
- ASCII-Fallback existiert
- Query-Decomposition funktioniert mit beliebigen Research-Themen (keine Inhaltsfilterung)
- keine Cloud

---

# Akzeptanzkriterien

Given ein ResearchNode  
When der Worker Query Decomposition ausführt  
Then entstehen strukturierte Suchqueries (Primary, Entity, Gap, Negative).

Given eine deutsche Query mit Umlauten  
When sie verarbeitet wird  
Then bleibt Originaltext erhalten und Search Keys werden ergänzt.

Given beliebige Research-Themen (auch Security/Darknet)  
When Query Decomposition läuft  
Then werden Queries ohne Inhaltsfilterung erzeugt.

---

# Validierung

```bash
python3 -m pytest tests/test_research_worker_queries.py -q
make quality
make coverage
```

---

# Nicht-Ziele

- keine Suche ausführen
- kein Crawling
- kein Report
- keine Cloud

# Issue DR-05 — Evidence Store + Citation Model

## Ziel

Implementiere einen Evidence Store, der Deep-Research-Quellen, Segmente, Hashes und Zitier-IDs nachvollziehbar persistiert.

---

# Kontext

Ein Deep-Research-Bericht ist nur brauchbar, wenn jede zentrale Aussage auf nachvollziehbare Quellen zurückgeführt werden kann.

---

# Betroffene Module

Neu/Erweitert:

```text
evidence_store/
  __init__.py
  models.py
  store.py
  citations.py
  dedup.py
tests/test_evidence_store.py
docs/deep-research/evidence-store.md
```

---

# Datenmodell

EvidenceSource:

```text
source_id
url
canonical_url
title
domain
retrieved_at
robots_status
cache_status
content_hash
```

EvidenceSegment:

```text
segment_id
source_id
text
normalized_text
quote_safe_text
section
position
score
mmr_group
injection_flags
```

Citation:

```text
citation_id
segment_id
label [S1]
quote
url
retrieved_at
```

---

# Regeln

- keine Quelle ohne retrieved_at
- kein Segment ohne source_id
- Content Hash Pflicht
- Duplikate erkennen
- Prompt-Injection-Markierungen speichern
- Zitate dürfen nur aus EvidenceSegmenten kommen
- Bericht darf nicht aus ungeprüftem Webtext zitieren

---

# Tests

- Source speichern/laden
- Segment speichern/laden
- Citation Labels stabil
- Duplicate Source erkannt
- Duplicate Segment erkannt
- injection flag bleibt erhalten
- quote_safe_text wird erzeugt
- JSONL Export funktioniert

---

# Akzeptanzkriterien

Given Evidence Candidates  
When sie gespeichert werden  
Then entstehen stabile Source- und Segment-IDs.

Given ein Report Writer möchte zitieren  
When er Citation anfordert  
Then bekommt er ein existierendes EvidenceSegment mit URL und retrieved_at.

Given Duplicate Content  
When gespeichert wird  
Then wird dedupliziert oder verlinkt.

---

# Validierung

```bash
python3 -m pytest tests/test_evidence_store.py -q
make quality
make coverage
```

---

# Nicht-Ziele

- keine neue Datenbankmigration
- keine Cloud
- keine Report-Synthese

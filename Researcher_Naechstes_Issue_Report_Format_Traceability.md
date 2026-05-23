# Researcher — Nächstes Issue: Report-Format verbessern — Quellenverweise, Modell-Metadaten und Limitations erzwingen

## Rolle

Du bist ein Senior Research Report Engineer, Evidence-Traceability-Designer und Local-First Quality Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Chain:

- #50: Walking-Skeleton
- #51: ruff 950 → 0
- #52: Bandit Triage
- #53: Submodul Security
- #54: CI Security Gate
- #55: mypy Boundary
- #56: Type Errors 33 → 0
- #57: Test Profiles
- #58: Fresh-Clone-Onboarding
- #59: Runtime Smoke
- #60: SearXNG Runtime
- #61: Minimal Research-Happy-Path
- #62: Ollama Model-Konfiguration
- #63: Research Report Quality Evaluation

Dein Ziel ist NICHT, neue Research-Features zu bauen.

Dein Ziel ist, das Report-Format so zu verbessern, dass die vorhandene Evaluation nicht nur 94/100 erreicht, sondern die konkrete Schwäche aus #63 behebt: Traceability nur 75, weil das verwendete Modell nicht ausreichend dokumentiert ist.

---

# Ausgangslage

Nach #63 existiert eine lokale Report-Quality-Evaluation:

```bash
make research-happy-path
make research-evaluate
```

Evaluationsergebnis:

| Score | Wert | Kommentar |
|---|---:|---|
| Source Coverage | 100 | vollständig |
| Traceability | 75 | Modell nicht dokumentiert |
| Hallucination Risk | 100 | keine riskanten Wörter |
| Local-First Compliance | 100 | keine Cloud |
| Overall | 94/100 | sehr gut |

Die nächste Verbesserung soll nicht neue Funktionalität bauen, sondern den Report selbst belastbarer machen.

---

# Oberstes Ziel dieses Issues

Verbessere das Report-Format, damit jeder erzeugte Research-Report standardmäßig enthält:

1. Query
2. Zeitstempel
3. verwendete lokale Dienste
4. SearXNG-URL oder Suchprovider-Info
5. Anzahl gefundener Quellen
6. Ollama Chat-/Summary-Modell
7. Ollama Embedding-Modell, falls relevant
8. Cloud-Status
9. Fallback-/Degradationsstatus
10. Quellenliste mit IDs
11. Summary mit Quellenverweisen
12. Limitations-/Warnings-Abschnitt

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Research-Features implementieren
- neue Suchprovider hinzufügen
- externe APIs aktivieren
- Cloud-LLM-Judges einführen
- riskante Queries verwenden
- Darknet-/Security-Recherche erweitern
- Quality-Gates lockern
- Tests löschen
- Coverage-Schwelle senken
- Vendor-Code unnötig ändern

---

# Report-Format-Ziel

Jeder Happy-Path-Report soll mindestens diese Struktur haben:

```markdown
# Research Report

## Metadata

| Field | Value |
|---|---|
| Query | |
| Generated At | |
| Local-First Mode | true |
| Cloud Providers Active | false |
| SearXNG URL | |
| SearXNG Result Count | |
| Ollama Chat Model Requested | |
| Ollama Chat Model Used | |
| Ollama Embedding Model | |
| Model Fallback Used | true/false |
| Degraded Mode | true/false |

## Summary

Kurze Zusammenfassung mit Quellenverweisen wie [S1], [S2].

## Key Findings

- Aussage 1. [S1]
- Aussage 2. [S2]
- Aussage 3. [S1][S3]

## Sources

### [S1] Title

- URL:
- Snippet:
- Engine/Provider:

### [S2] Title

- URL:
- Snippet:
- Engine/Provider:

## Limitations and Warnings

- This report is generated from a minimal local happy-path.
- Sources were retrieved from SearXNG.
- Claims should be verified before operational use.
- No cloud providers were used.
```

---

# Arbeitsreihenfolge

## 1. Aktuelles Report-Format analysieren

Führe aus:

```bash
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
tail -n 120 reports/research/research_*.md
tail -n 120 reports/evaluation/research_eval_*.md
```

Dokumentiere:

- welche Metadata-Felder fehlen
- ob Quellen IDs haben
- ob Summary Quellenverweise nutzt
- ob Limitations vorhanden sind
- warum Traceability nur 75 ist

---

## 2. Report-Generator anpassen

Passe den Report-Output im bestehenden Happy-Path an, vermutlich:

```text
scripts/research_happy_path.py
```

Anforderungen:

- keine neue Research-Logik
- nur Report-Struktur und Metadaten verbessern
- verwendetes Modell explizit dokumentieren
- requested vs used model unterscheiden
- Fallback/Degraded Mode dokumentieren
- Quellen IDs stabil generieren: [S1], [S2], [S3]
- Summary soll mindestens einfache Quellenverweise enthalten

Wenn die Summary vom LLM keine Quellenmarker erzeugt, dann:

- Prompt minimal erweitern: „Use source IDs [S1], [S2]...“
- oder post-processing: Key Findings aus Quellen-Snippets generieren
- keine komplexe Prompt-Architektur einführen

---

## 3. Evaluation anpassen

Falls nötig, passe an:

```text
scripts/evaluate_research_report.py
```

Die Evaluation soll erkennen:

- `Ollama Chat Model Used`
- `Ollama Chat Model Requested`
- `Ollama Embedding Model`
- `Model Fallback Used`
- `Degraded Mode`
- Quellen-IDs `[S1]`
- Summary-Verweise `[S1]`, `[S2]`
- Limitations-Abschnitt

Ziel:

- Traceability Score steigt von 75 auf mindestens 90.
- Overall Score bleibt >=90.

---

## 4. Tests ergänzen/anpassen

Passe Tests an:

```text
tests/test_research_happy_path.py
tests/test_research_report_evaluation.py
```

Neue/angepasste Testfälle:

- Report enthält Metadata-Tabelle
- Report enthält Chat-Modell requested/used
- Report enthält Embedding-Modell
- Report enthält Cloud-Status
- Report enthält SearXNG Result Count
- Quellen haben IDs `[S1]`
- Summary oder Key Findings enthalten Quellenverweise
- Limitations-Abschnitt vorhanden
- Evaluation erkennt Modell-Metadaten
- Traceability Score ist hoch, wenn Metadaten vorhanden sind
- Traceability Score sinkt, wenn Modell-Metadaten fehlen

Keine echten Netzwerkdienste in Unit-Tests.

---

## 5. Dokumentation aktualisieren

Aktualisiere oder erstelle:

```text
docs/evaluation/research-report-quality.md
docs/runtime/research-happy-path.md
```

Optional neu:

```text
docs/reports/report-format.md
```

Pflichtinhalt für Report-Format-Doku:

```markdown
# Research Report Format

## Ziel

## Pflichtfelder

| Feld | Zweck |
|---|---|
| Query | Nachvollziehbarkeit |
| Generated At | Reproduzierbarkeit |
| SearXNG Result Count | Quellenbasis |
| Ollama Chat Model Used | LLM-Traceability |
| Cloud Providers Active | Local-First Compliance |
| Source IDs | Evidence Mapping |
| Limitations | Risikobegrenzung |

## Quellenverweise

## Modell-Metadaten

## Limitations

## Evaluation-Kompatibilität
```

---

# Validierung

Nach Änderungen ausführen:

```bash
# bestehende Gates
make quality
make coverage
make test-e2e
make ci-local

# Runtime + Report
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path

# Evaluation
make research-evaluate
make research-happy-path-eval

# Tests
python3 -m pytest tests/ -q -k "research_happy_path or research_report_evaluation"
```

Zielwerte:

- Source Coverage >=90
- Traceability >=90
- Hallucination Risk >=90
- Local-First Compliance =100
- Overall >=90

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Report enthält Metadata-Tabelle
- Report dokumentiert requested/used Chat-Modell
- Report dokumentiert Embedding-Modell
- Report dokumentiert Cloud-Status
- Report dokumentiert SearXNG-Resultcount
- Quellen haben stabile IDs
- Summary oder Key Findings verwenden Quellenverweise
- Limitations-/Warnings-Abschnitt existiert
- Evaluation erkennt neue Metadaten
- Traceability steigt auf >=90
- Overall bleibt >=90
- Tests wurden ergänzt/angepasst
- Doku wurde aktualisiert
- bestehende Gates bleiben grün
- keine neuen Research-Features gebaut wurden
- keine Cloud-Provider eingeführt wurden
- GitHub-Kommentar mit Vorher/Nachher-Score geschrieben wurde

Minimal akzeptabel:

- Modell-Metadaten im Report
- Traceability >=90
- Tests grün
- Doku aktualisiert

Gut:

- Quellen-IDs und Quellenverweise funktionieren
- Limitations werden immer erzeugt
- Evaluation erklärt fehlende Felder konkret

Sehr gut:

- Report-Format ist stabil genug, um später für echte Research-Qualitätsmetriken erweitert zu werden

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Report-Format Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Metadata-Tabelle im Report | |
| Chat-Modell requested/used dokumentiert | |
| Embedding-Modell dokumentiert | |
| Cloud-Status dokumentiert | |
| SearXNG-Resultcount dokumentiert | |
| Quellen-IDs vorhanden | |
| Quellenverweise in Summary/Findings | |
| Limitations vorhanden | |
| Evaluation angepasst | |
| Traceability >=90 | |
| Overall >=90 | |
| Tests angepasst | |
| Doku aktualisiert | |
| `make quality` weiterhin grün | |
| `make coverage` weiterhin grün | |
| `make ci-local` weiterhin grün | |
| Keine neuen Features | |
| GitHub-Kommentar geschrieben | |

## Evaluation Vorher/Nachher

| Score | Vorher | Nachher |
|---|---:|---:|
| Source Coverage | 100 | |
| Traceability | 75 | |
| Hallucination Risk | 100 | |
| Local-First Compliance | 100 | |
| Overall | 94 | |

## Ausgeführte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Geänderte Dateien

## Bewusst nicht gelöste Probleme

## Risiken

## Nächstes empfohlenes Issue
```

---

# Empfohlenes nächstes Folge-Issue nach Abschluss

Nach diesem Issue sollte eines dieser Issues folgen:

1. `Security regression tests für Netzwerk-/Hashing-/SQL-Pfade ergänzen`
2. `Playwright-CI-Strategie definieren`
3. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`
4. `Research Report Quality Evaluation mit mehreren harmlosen Queries erweitern`

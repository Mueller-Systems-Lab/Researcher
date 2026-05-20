# Researcher — Nächstes Issue: Source Coverage wieder auf ≥95 bringen ohne Traceability-Verlust

## Rolle

Du bist ein Senior Research Report Quality Engineer und Evidence-Mapping-Agent.

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
- #63: Report Quality Evaluation
- #64: Report-Format Traceability

Dein Ziel ist NICHT, neue Research-Features zu bauen.

Dein Ziel ist, die nach #64 gesunkene Source Coverage wieder zu verbessern, ohne die neue hohe Traceability zu verlieren.

---

# Ausgangslage

Nach #64:

| Score | Vorher #63 | Nachher #64 |
|---|---:|---:|
| Source Coverage | 100 | 80 |
| Traceability | 75 | 95 |
| Hallucination Risk | 100 | 100 |
| Local-First | 100 | 100 |
| Overall | 94 | 92 |

#64 war erfolgreich, weil:

- Metadata-Tabelle im Report existiert
- Chat-Modell requested/used dokumentiert ist
- Embedding-Modell dokumentiert ist
- Cloud-Status dokumentiert ist
- SearXNG-Resultcount dokumentiert ist
- Quellen-IDs `[S1]`, `[S2]`, `[S3]` vorhanden sind
- Key Findings Quellenverweise enthalten
- Limitations vorhanden sind
- Traceability auf 95 gestiegen ist

Offenes Qualitätsproblem:

- Source Coverage ist auf 80 gefallen.
- Vermutlich fehlen einzelne Anforderungen der Evaluation, z. B. vollständige Quellenfelder, Snippets, URLs, Quellenverweise oder Summary/Sources-Kopplung.

---

# Oberstes Ziel dieses Issues

Bringe Source Coverage wieder auf mindestens 95, ohne Traceability, Hallucination Risk oder Local-First zu verschlechtern.

Zielwerte:

| Score | Ziel |
|---|---:|
| Source Coverage | >=95 |
| Traceability | >=95 |
| Hallucination Risk | >=90 |
| Local-First | 100 |
| Overall | >=95, wenn realistisch; mindestens >=92 |

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Research-Features bauen
- neue Suchprovider hinzufügen
- externe APIs aktivieren
- Cloud-Judge einführen
- riskante Queries verwenden
- Darknet-/Security-Recherche erweitern
- produktive Architektur umbauen
- Quality-Gates lockern
- Tests löschen
- Coverage-Schwelle senken
- Vendor-Code unnötig ändern

---

# Arbeitsreihenfolge

## 1. Ursache für Source-Coverage-Abfall analysieren

Führe aus:

```bash
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
tail -n 140 reports/research/research_*.md
tail -n 140 reports/evaluation/research_eval_*.md
```

Dokumentiere:

- Warum Source Coverage nur 80 ist.
- Welche Source-Coverage-Kriterien nicht erfüllt sind.
- Ob Quellen Titel enthalten.
- Ob Quellen URLs enthalten.
- Ob Quellen Snippets enthalten.
- Ob Quellen Provider/Engine enthalten.
- Ob jede Quelle eine stabile ID hat.
- Ob Summary/Key Findings auf Quellen-IDs verweisen.
- Ob Quellenanzahl und SearXNG Result Count plausibel zusammenpassen.

---

## 2. Evaluation transparenter machen

Passe bei Bedarf an:

```text
scripts/evaluate_research_report.py
```

Die Evaluation soll bei Source Coverage nicht nur Score, sondern konkrete fehlende Kriterien ausgeben.

Beispiel:

```text
Source Coverage: 80
Missing:
- Source [S2] has no snippet
- Source [S3] has no URL
- Summary has only 1 source reference, expected >=2
```

Erzeuge im JSON/Markdown:

```json
"source_coverage_details": {
  "sources_found": 3,
  "sources_with_url": 3,
  "sources_with_title": 3,
  "sources_with_snippet": 2,
  "summary_source_refs": 1,
  "missing": []
}
```

---

## 3. Report-Generator verbessern

Passe den Report im bestehenden Happy-Path an:

```text
scripts/research_happy_path.py
```

Anforderungen:

- Jede Quelle `[Sx]` erhält:
  - Title
  - URL
  - Snippet
  - Provider/Engine, falls verfügbar
- Wenn Snippet fehlt:
  - `Snippet: Not provided by search result`
  - aber als fehlend markieren oder sauber dokumentieren
- Key Findings sollen möglichst mindestens zwei unterschiedliche Quellen referenzieren, falls genug Quellen vorhanden sind.
- Quellenverweise dürfen nicht erfunden werden.
- Wenn nur wenige Quellen existieren, muss Limitations das sagen.

---

## 4. Keine Halluzination durch Quellenzwang

Wichtig:

- Nicht einfach beliebige Quellenmarker an Aussagen hängen.
- Keine Aussage darf eine Quelle referenzieren, wenn sie nicht aus deren Titel/Snippet ableitbar ist.
- Wenn Summary unsicher ist, besser knapper und quellengebunden bleiben.

Bevorzugt:

```markdown
## Key Findings

- SearXNG returned a result titled "...". [S1]
- Another result refers to "...". [S2]
- The current happy-path report is based on 3 local search results and should be treated as a smoke-test output. [S1][S2][S3]
```

Nicht bevorzugt:

```markdown
- Search engines are always unbiased. [S1]
```

---

## 5. Tests ergänzen/anpassen

Passe an:

```text
tests/test_research_report_evaluation.py
tests/test_research_happy_path.py
```

Testfälle:

- vollständige Quellenfelder → Source Coverage >=95
- fehlender Snippet → Score sinkt und Missing-Liste erklärt warum
- fehlende URL → Score sinkt
- Quellen ohne IDs → Score sinkt
- Key Findings ohne Quellenverweise → Score sinkt
- Report mit Metadata + vollständigen Quellen → Traceability >=95 und Source Coverage >=95
- keine Verschlechterung bei Local-First

Keine echten Netzwerkdienste in Unit-Tests.

---

## 6. Dokumentation aktualisieren

Aktualisiere:

```text
docs/evaluation/research-report-quality.md
docs/runtime/research-happy-path.md
```

Optional:

```text
docs/reports/report-format.md
```

Ergänze:

- Pflichtfelder pro Quelle
- wie Source Coverage berechnet wird
- warum fehlende Snippets/URLs den Score senken
- wie Quellenverweise verwendet werden sollen
- Grenzen der heuristischen Evaluation

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

```text
Source Coverage >=95
Traceability >=95
Hallucination Risk >=90
Local-First Compliance =100
Overall >=92
```

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Ursache des Source-Coverage-Abfalls dokumentiert ist
- Evaluation erklärt fehlende Source-Coverage-Kriterien konkret
- jede Quelle stabile ID hat
- jede Quelle URL enthält oder fehlende URL klar markiert ist
- jede Quelle Titel enthält oder fehlender Titel klar markiert ist
- jede Quelle Snippet enthält oder fehlender Snippet klar markiert ist
- Key Findings nutzen Quellenverweise
- Source Coverage steigt auf >=95
- Traceability bleibt >=95
- Local-First bleibt 100
- Hallucination Risk bleibt >=90
- Overall bleibt >=92
- Tests angepasst/ergänzt
- Doku aktualisiert
- bestehende Gates bleiben grün
- keine neuen Research-Features gebaut wurden
- keine Cloud-Provider eingeführt wurden
- GitHub-Kommentar mit Vorher/Nachher-Score geschrieben wurde

Minimal akzeptabel:

- Source Coverage >=95
- Traceability >=90
- Tests grün
- Doku aktualisiert

Gut:

- Evaluation erklärt fehlende Quellenfelder präzise
- Report-Format enthält vollständige Source-Blöcke
- Key Findings sind quellengebunden

Sehr gut:

- Source Coverage und Traceability beide >=95
- Overall steigt wieder auf >=95 oder bleibt nachvollziehbar knapp darunter

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Source-Coverage Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Source-Coverage-Abfall analysiert | |
| Evaluation erklärt Missing-Kriterien | |
| Quellen-IDs stabil | |
| Quellen-URLs vollständig/markiert | |
| Quellen-Titel vollständig/markiert | |
| Quellen-Snippets vollständig/markiert | |
| Key Findings mit Quellenverweisen | |
| Source Coverage >=95 | |
| Traceability >=95 | |
| Hallucination Risk >=90 | |
| Local-First =100 | |
| Overall >=92 | |
| Tests angepasst | |
| Doku aktualisiert | |
| `make quality` weiterhin grün | |
| `make coverage` weiterhin grün | |
| `make ci-local` weiterhin grün | |
| Keine neuen Features | |
| GitHub-Kommentar geschrieben | |

## Evaluation Vorher/Nachher

| Score | Vorher #64 | Nachher |
|---|---:|---:|
| Source Coverage | 80 | |
| Traceability | 95 | |
| Hallucination Risk | 100 | |
| Local-First | 100 | |
| Overall | 92 | |

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
2. `Research Report Quality Evaluation mit mehreren harmlosen Queries erweitern`
3. `Playwright-CI-Strategie definieren`
4. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`

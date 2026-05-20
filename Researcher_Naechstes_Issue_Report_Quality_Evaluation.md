# Researcher — Nächstes Issue: Research Report Quality Evaluation — Quellen, Evidenz, Halluzinationen

## Rolle

Du bist ein Senior Research Quality Engineer, LLM Evaluation Designer und Evidence-Gated Reliability Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Repair-/Runtime-Chain:

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
- #62: Ollama Model-Konfiguration stabilisiert

Dein Ziel ist NICHT, neue Research-Features zu bauen.

Dein Ziel ist, die Qualität des erzeugten Research-Reports messbar, reproduzierbar und evidence-gated bewertbar zu machen.

---

# Ausgangslage

Nach #62 ist der lokale End-to-End-Pfad stabil:

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
```

Runtime-Status:

- Ollama Embedding-Modell: ✅ `nomic-embed-text:latest`
- Ollama Chat-/Summary-Modell: ✅ `qwen3.5-uncensored-no-thinking:latest`
- SearXNG: ✅ Results
- Tor: ✅ SOCKS5 erreichbar
- Cloud: ✅ keine Cloud aktiv
- Report: ✅ Markdown-Report wird erzeugt

Jetzt muss geprüft werden:

> Ist der erzeugte Report gut, nachvollziehbar, quellenbasiert und frei von offensichtlichen Halluzinationen?

---

# Oberstes Ziel dieses Issues

Erstelle eine kleine, reproduzierbare Report-Quality-Evaluation für den minimalen Research-Happy-Path.

Die Evaluation soll prüfen:

1. Report existiert.
2. Query ist dokumentiert.
3. Quellen sind enthalten.
4. Quellen sind mit SearXNG-Ergebnissen rückverfolgbar.
5. Summary behauptet nichts Wesentliches ohne Quelle.
6. Report enthält klare Unsicherheiten.
7. Keine Cloud-Provider wurden genutzt.
8. Evaluation gibt strukturierte Scores aus.
9. Evaluation ist lokal und ohne externe Bewertungs-API ausführbar.
10. Ergebnisse werden als Markdown/JSON gespeichert.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Research-Features bauen
- vollständige wissenschaftliche Evaluierung implementieren
- externe LLM-Judge-APIs verwenden
- Cloud-Evaluation einführen
- riskante oder personenbezogene Queries verwenden
- Exploit-/CVE-/Darknet-Recherchen durchführen
- produktive Report-Architektur groß umbauen
- Quality-Gates lockern
- Tests löschen
- Coverage-Schwelle senken

---

# Bewertungsprinzipien

## 1. Evidence-Gated Output

Eine Aussage im Report ist nur stark, wenn sie einer Quelle zugeordnet werden kann.

## 2. Lokale Evaluation

Die Evaluation darf nur lokale Heuristiken, Parsing, Regex, einfache NLP-Regeln oder optional das lokale Ollama-Modell verwenden.

Keine Cloud-Judges.

## 3. Kleine Metriken statt Perfektion

Ziel ist ein erster Qualitätsrahmen, nicht perfekte Wahrheitserkennung.

## 4. Deterministische Checks zuerst

Bevor LLM-basierte Bewertung verwendet wird, sollen deterministische Checks laufen:

- Report-Datei vorhanden
- Quellenabschnitt vorhanden
- Mindestanzahl Quellen
- Query vorhanden
- Cloud-Blocker vermerkt
- SearXNG-Resultcount vermerkt
- Summary-Abschnitt vorhanden
- Warning/Limitations-Abschnitt vorhanden

---

# Arbeitsreihenfolge

## 1. Aktuellen Report analysieren

Führe aus:

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
ls -lah reports/research/
tail -n 80 reports/research/research_*.md
```

Dokumentiere:

- Dateiname
- Größe
- Query
- Anzahl Quellen
- ob Summary vorhanden ist
- ob Modellname dokumentiert ist
- ob Cloud-Status dokumentiert ist
- ob SearXNG-Resultcount dokumentiert ist
- ob Warnungen/Degradationsstatus dokumentiert sind

---

## 2. Evaluation-Skript erstellen

Erstelle:

```text
scripts/evaluate_research_report.py
```

Das Skript soll einen Report-Pfad akzeptieren:

```bash
python3 scripts/evaluate_research_report.py reports/research/research_*.md
```

Optional:

```bash
python3 scripts/evaluate_research_report.py --latest
```

Ausgabe:

- Console Summary
- JSON Report
- Markdown Evaluation Report

Zielpfade:

```text
reports/evaluation/research_eval_*.json
reports/evaluation/research_eval_*.md
```

---

## 3. Erste Metriken implementieren

Implementiere einfache Scores von 0–100.

### Source Coverage Score

Prüft:

- mindestens 3 Quellen
- Quellen haben Titel/URL/Snippet
- Quellen sind im Report sichtbar
- Summary verweist auf Quellen oder Quellenabschnitt

### Traceability Score

Prüft:

- Query im Report vorhanden
- SearXNG-Resultcount vorhanden
- Quellenanzahl stimmt mit Ergebnisliste überein oder ist plausibel
- verwendetes Modell ist dokumentiert

### Hallucination Risk Heuristic

Prüft einfache Risikoindikatoren:

- starke Behauptungen ohne Quellenmarker
- absolute Formulierungen ohne Unsicherheit
- fehlender Quellenabschnitt
- fehlender Limitations-/Warnings-Abschnitt
- Summary länger als Quellenbasis plausibel hergibt

Beispiele für riskante Wörter:

```text
always
never
proves
guaranteed
definitely
all experts agree
without any doubt
```

Deutsch optional:

```text
immer
niemals
beweist
garantiert
zweifelsfrei
alle Experten
```

### Local-First Compliance Score

Prüft:

- Cloud-Status dokumentiert
- kein OpenAI/Tavily/Anthropic/Gemini im Report als verwendeter Provider
- Ollama-Modell dokumentiert
- SearXNG dokumentiert

### Overall Score

Einfacher gewichteter Score:

```text
overall = 0.35 * source_coverage
        + 0.25 * traceability
        + 0.25 * local_first_compliance
        + 0.15 * hallucination_risk_inverse
```

Keine komplexe Statistik nötig.

---

## 4. Makefile-Targets ergänzen

Ergänze:

```makefile
research-evaluate:
	python3 scripts/evaluate_research_report.py --latest

research-happy-path-eval:
	$(MAKE) research-happy-path
	$(MAKE) research-evaluate
```

Optional strict:

```makefile
research-evaluate-strict:
	python3 scripts/evaluate_research_report.py --latest --min-score 70
```

Wichtig:

- nicht Bestandteil von `make quality`
- nicht Bestandteil von `make ci-local`
- optionaler Runtime-/Quality-Check

---

## 5. Tests ergänzen

Erstelle:

```text
tests/test_research_report_evaluation.py
```

Gemockte/fixture-basierte Tests:

- guter Report → hoher Score
- Report ohne Quellen → niedriger Source Score
- Report ohne Query → niedriger Traceability Score
- Report mit Cloud-Provider → niedriger Local-First Score
- Report mit starken unbelegten Aussagen → höheres Halluzinationsrisiko
- `--latest` findet neuesten Report
- JSON/Markdown-Evaluation wird erzeugt
- `--min-score` schlägt bei zu niedrigem Score fehl

Keine echten Netzwerkdienste in Tests verwenden.

---

# 6. Dokumentation erstellen

Erstelle:

```text
docs/evaluation/research-report-quality.md
```

Pflichtinhalt:

```markdown
# Research Report Quality Evaluation

## Ziel

## Was bewertet wird

| Score | Zweck |
|---|---|
| Source Coverage | Quellenbasis |
| Traceability | Rückverfolgbarkeit |
| Hallucination Risk | Heuristische Risikoprüfung |
| Local-First Compliance | Keine Cloud-/Remote-Judges |

## Befehle

```bash
make research-happy-path
make research-evaluate
make research-happy-path-eval
```

## Score-Interpretation

| Score | Bedeutung |
|---:|---|
| 90–100 | Sehr gut |
| 70–89 | Nutzbar |
| 50–69 | Verbesserungsbedürftig |
| <50 | Nicht belastbar |

## Grenzen

## Keine Wahrheitserkennung

## Nächste Schritte
```

README optional verlinken.

---

# Validierung

Nach Änderungen ausführen:

```bash
# bestehende Gates
make quality
make coverage
make test-e2e
make ci-local

# Runtime
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path

# Evaluation
make research-evaluate
make research-happy-path-eval

# Tests
python3 -m pytest tests/ -q -k "research_report_evaluation or research_happy_path"
```

Optional:

```bash
make research-evaluate-strict
```

Nur wenn Score-Schwelle realistisch ist.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Evaluation-Skript existiert
- Report per `--latest` evaluierbar ist
- JSON-Evaluation erzeugt wird
- Markdown-Evaluation erzeugt wird
- Source Coverage Score existiert
- Traceability Score existiert
- Hallucination Risk Heuristic existiert
- Local-First Compliance Score existiert
- Overall Score existiert
- Makefile-Targets existieren
- Tests ohne echte Dienste existieren
- Doku existiert
- README optional verlinkt ist
- bestehende Gates bleiben grün
- keine Cloud-Judge-API eingeführt wurde
- keine riskanten Queries eingeführt wurden
- keine neuen Research-Features gebaut wurden
- GitHub-Kommentar mit Evaluationsergebnis geschrieben wurde

Minimal akzeptabel:

- deterministische Evaluation
- JSON + Markdown Output
- Tests
- Doku
- keine Regression

Gut:

- `make research-happy-path-eval` erzeugt Report + Evaluation in einem Lauf
- Score erklärt konkrete Mängel
- `--min-score` optional vorhanden

Sehr gut:

- Evaluation macht sichtbar, ob Report durch Quellen gedeckt ist
- Nächste Verbesserungen werden datenbasiert statt gefühlt abgeleitet

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Report-Quality-Evaluation Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Evaluation-Skript erstellt | |
| `--latest` unterstützt | |
| JSON-Evaluation erzeugt | |
| Markdown-Evaluation erzeugt | |
| Source Coverage Score | |
| Traceability Score | |
| Hallucination Risk Heuristic | |
| Local-First Compliance Score | |
| Overall Score | |
| Makefile-Targets erstellt | |
| Tests vorhanden | |
| Doku erstellt | |
| `make quality` weiterhin grün | |
| `make coverage` weiterhin grün | |
| `make ci-local` weiterhin grün | |
| Keine Cloud-Judge-API | |
| Keine neuen Research-Features | |
| GitHub-Kommentar geschrieben | |

## Evaluationsergebnis

| Score | Wert | Kommentar |
|---|---:|---|
| Source Coverage | | |
| Traceability | | |
| Hallucination Risk | | |
| Local-First Compliance | | |
| Overall | | |

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

1. `Report-Format verbessern: Quellenverweise und Limitations erzwingen`
2. `Security regression tests für Netzwerk-/Hashing-/SQL-Pfade ergänzen`
3. `Playwright-CI-Strategie definieren`
4. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`

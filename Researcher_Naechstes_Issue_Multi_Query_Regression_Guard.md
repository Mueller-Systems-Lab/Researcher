# Researcher — Nächstes Issue: Multi-Query Live-Validation und Report-Quality Regression Guard

## Rolle

Du bist ein Senior Research Evaluation Engineer, Runtime Reliability Agent und Quality Regression Designer.

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
- #62: Ollama Config
- #63: Report Eval
- #64: Report Traceability
- #65: Source Coverage
- #66: Multi-Query Eval

Dein Ziel ist NICHT, neue Research-Features zu bauen.

Dein Ziel ist, die Multi-Query-Evaluation aus #66 nicht nur prognostiziert, sondern live reproduzierbar zu validieren und daraus einen optionalen Regression Guard für Report-Qualität zu erstellen.

---

# Ausgangslage

Nach #66 existieren:

- `scripts/research_multi_query_eval.py`
- `tests/test_research_multi_query_eval.py`
- Makefile-Targets für Multi-Query Evaluation
- 5 harmlose Standard-Queries
- JSON-/Markdown-Summary
- Mean/Min-Aggregation
- `--limit`
- `--min-overall`
- `--min-query-overall`
- Query-Safety-Guard

Berichteter Zustand:

```text
make quality: 241 passed, 0 Errors
Single Query Overall: 99/100
Multi-Query Mean Overall: ~91
Multi-Query Min Overall: ~88
```

Wichtiger Punkt:

Die Multi-Query-Ergebnisse wurden als „prognostiziert“ beschrieben. Deshalb braucht es nun eine live reproduzierbare Validierung und einen optionalen Regression Guard.

---

# Oberstes Ziel dieses Issues

Erstelle einen belastbaren Multi-Query-Live-Validation- und Regression-Guard-Prozess.

Der Prozess soll:

1. Runtime-Smoke vorab prüfen.
2. mindestens 3 harmlose Queries live ausführen.
3. pro Query Report und Evaluation erzeugen.
4. aggregierte Werte live berechnen.
5. Thresholds anwenden.
6. Ergebnisse als historische Artefakte speichern.
7. Regressionen gegenüber einem Baseline-Snapshot sichtbar machen.
8. nicht Teil von `make quality` oder `make ci-local` sein.
9. optional lokal oder manuell ausführbar sein.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Research-Features bauen
- Cloud-LLM-Judges einführen
- Cloud-Suchprovider aktivieren
- riskante Queries verwenden
- Security-, CVE-, Exploit-, Darknet- oder personenbezogene Queries verwenden
- normale schnelle CI verlangsamen
- Quality-Gates lockern
- Coverage-Schwelle senken
- Tests löschen
- Vendor-Code ändern

---

# Sicherheits- und Scope-Regeln

## Nur harmlose Queries

Erlaubt:

```text
What is a search engine?
What is SearXNG?
What is local-first software?
What is open source software?
What is a web crawler?
```

Nicht erlaubt:

```text
CVE
exploit
vulnerability
credentials
darknet
onion forum
site:
person:
target domain
```

## Kein Cloud-Fallback

Vor Live-Ausführung muss gelten:

```text
Cloud Providers Active: false
ALLOW_CLOUD != true
```

Wenn Cloud aktiv ist:

- abbrechen
- klare Meldung ausgeben
- kein Fallback

## Optionaler Guard

Der Regression Guard ist optional und darf nicht den schnellen Entwicklerloop blockieren.

Er gehört in:

- manuelles Makefile-Target
- optionales CI `workflow_dispatch`
- später optional nightly/scheduled

Nicht in:

- `make quality`
- `make ci-local`
- normale PR-fast-Gates

---

# Arbeitsreihenfolge

## 1. Live-Zustand reproduzieren

Führe aus:

```bash
make quality
make coverage
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
make research-evaluate-multi
```

Dokumentiere:

- ob Multi-Query wirklich live Reports erzeugt
- wie viele Queries real gelaufen sind
- welche Reports erzeugt wurden
- welche Evaluations erzeugt wurden
- Mean Overall
- Min Overall
- Ausreißer
- Laufzeit

---

## 2. Live-/Mock-Modus explizit machen

Prüfe:

```text
scripts/research_multi_query_eval.py
```

Der Runner soll klar unterscheiden:

- `live` mode: ruft reale lokale Runtime auf
- `mock`/test mode: nur gemockte Tests
- `dry-run` mode: zeigt Queries, führt aber nichts aus

Optional CLI:

```bash
python3 scripts/research_multi_query_eval.py --mode live --limit 3
python3 scripts/research_multi_query_eval.py --dry-run
```

Wenn bereits live gearbeitet wird:

- dokumentieren
- Ausgabe eindeutiger machen

---

## 3. Regression-Baseline einführen

Erstelle eine kleine Baseline-Datei:

```text
docs/evaluation/report-quality-baseline.json
```

oder, wenn runtime-spezifisch besser:

```text
reports/evaluation/baseline/report-quality-baseline.json
```

Empfehlung:

- Baseline in `docs/evaluation/` committen
- Laufreports in `reports/` nicht committen

Baseline-Beispiel:

```json
{
  "version": 1,
  "created_from_issue": "#66/#67",
  "query_count": 3,
  "thresholds": {
    "overall_mean_min": 85,
    "overall_query_min": 75,
    "source_coverage_min": 80,
    "traceability_min": 85,
    "local_first_min": 100
  },
  "reference_scores": {
    "overall_mean": 91,
    "overall_min": 88
  }
}
```

Wichtig:

- Schwellen realistisch setzen.
- Nicht auf 99 optimieren.
- Ziel ist Regressionserkennung, nicht Perfektionszwang.

---

## 4. Regression-Guard implementieren

Erweitere Multi-Query-Runner:

```bash
python3 scripts/research_multi_query_eval.py   --limit 3   --baseline docs/evaluation/report-quality-baseline.json   --fail-on-regression
```

Regeln:

- fail, wenn Mean Overall unter Schwelle
- fail, wenn einzelne Query unter Min-Schwelle
- fail, wenn Local-First <100
- warn, wenn Source Coverage leicht sinkt, aber über Mindestwert bleibt
- JSON/Markdown enthalten Regressionsergebnis

Markdown-Summary soll enthalten:

```markdown
## Regression Guard

| Check | Threshold | Actual | Status |
|---|---:|---:|---|
| Overall Mean | >=85 | 91 | PASS |
| Overall Min | >=75 | 88 | PASS |
| Local-First | 100 | 100 | PASS |
```

---

## 5. Makefile-Targets ergänzen

Ergänze oder verfeinere:

```makefile
research-evaluate-multi-live:
	SEARXNG_TIMEOUT_SECONDS=30 ALLOW_OLLAMA_MODEL_FALLBACK=true python3 scripts/research_multi_query_eval.py --mode live --limit 3

research-evaluate-regression:
	SEARXNG_TIMEOUT_SECONDS=30 ALLOW_OLLAMA_MODEL_FALLBACK=true python3 scripts/research_multi_query_eval.py --mode live --limit 3 --baseline docs/evaluation/report-quality-baseline.json --fail-on-regression
```

Optional:

```makefile
research-evaluate-dry-run:
	python3 scripts/research_multi_query_eval.py --dry-run
```

Nicht in `make quality` aufnehmen.

---

## 6. Optionalen GitHub Actions Workflow ergänzen

Nur wenn sinnvoll:

```text
.github/workflows/research-evaluation.yml
```

Trigger:

```yaml
workflow_dispatch:
```

Optional später:

```yaml
schedule:
  - cron: "0 3 * * 1"
```

Aber Vorsicht:

- Nur wenn Runner lokale Dienste bereitstellen kann.
- Ohne Ollama/SearXNG/Tor wird der Workflow scheitern.
- Sonst nur Doku vorbereiten, nicht aktivieren.

Empfehlung für dieses Issue:

- Dokumentiere manuelle CI-Strategie.
- Aktiviere `workflow_dispatch` nur, wenn lokale Dienste im CI wirklich verfügbar sind.
- Andernfalls kein CI-Workflow erzwingen.

---

## 7. Tests ergänzen

Erweitere:

```text
tests/test_research_multi_query_eval.py
```

Testfälle:

- Baseline-Datei wird geladen
- Regression PASS bei Scores über Schwelle
- Regression FAIL bei Mean unter Schwelle
- Regression FAIL bei einzelner Query unter Schwelle
- Local-First unter 100 fails
- Dry-run führt keine Research-Subprozesse aus
- Live-Modus ruft erwartete Pipeline auf, aber gemockt
- Markdown enthält Regression Guard Tabelle
- JSON enthält Regression-Status

Keine echten Netzwerkdienste in Unit-Tests.

---

# 8. Dokumentation erstellen/aktualisieren

Aktualisiere oder erstelle:

```text
docs/evaluation/multi-query-evaluation.md
docs/evaluation/report-quality-regression-guard.md
```

Pflichtinhalt:

```markdown
# Report Quality Regression Guard

## Ziel

## Warum Regression Guard?

## Live vs Dry Run

## Baseline

## Schwellen

| Metrik | Schwelle | Begründung |
|---|---:|---|
| Overall Mean | >=85 | |
| Single Query Overall | >=75 | |
| Local-First | 100 | |
| Traceability | >=85 | |
| Source Coverage | >=80 | |

## Befehle

```bash
make research-evaluate-multi-live
make research-evaluate-regression
```

## Was bei Failure zu tun ist

## Warum nicht Teil von make quality?

## Sicherheitsgrenzen

## Keine Cloud-Judges
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

# Multi-Query Live
make research-evaluate-multi-live

# Regression Guard
make research-evaluate-regression

# Tests
python3 -m pytest tests/ -q -k "multi_query or regression"
```

Wenn lokale Dienste nicht stabil verfügbar sind:

- Unit-Tests müssen trotzdem grün sein.
- Doku muss erklären, dass Regression Guard runtime-abhängig ist.
- `research-evaluate-regression` bleibt optional.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Multi-Query-Live-Ausführung eindeutig dokumentiert ist
- mindestens 3 Queries live validiert wurden oder Runtime-Abhängigkeit sauber dokumentiert ist
- Baseline-Datei existiert
- Regression-Guard-Logik existiert
- `make research-evaluate-multi-live` existiert
- `make research-evaluate-regression` existiert
- JSON-Summary enthält Regression-Status
- Markdown-Summary enthält Regression-Tabelle
- Tests ohne echte Dienste existieren
- Doku existiert
- bestehende Gates bleiben grün
- keine Cloud-Judges eingeführt wurden
- keine riskanten Queries eingeführt wurden
- keine neuen Research-Features gebaut wurden
- GitHub-Kommentar mit Live-/Regression-Ergebnis geschrieben wurde

Minimal akzeptabel:

- Baseline + Regression Guard
- Tests
- Doku
- keine Regression bei Quality Gates

Gut:

- Live-Run mit 3 Queries erfolgreich
- Mean/Min und Regression PASS dokumentiert
- Dry-run vorhanden

Sehr gut:

- Reportqualität ist nicht nur punktuell messbar, sondern gegen zukünftige Verschlechterungen geschützt

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Multi-Query Regression Guard Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Multi-Query Live-Modus dokumentiert | |
| Mindestens 3 Queries live validiert | |
| Baseline-Datei erstellt | |
| Regression Guard implementiert | |
| `research-evaluate-multi-live` Target | |
| `research-evaluate-regression` Target | |
| JSON enthält Regression-Status | |
| Markdown enthält Regression-Tabelle | |
| Tests vorhanden | |
| Doku erstellt | |
| `make quality` weiterhin grün | |
| `make coverage` weiterhin grün | |
| `make ci-local` weiterhin grün | |
| Keine Cloud-Judges | |
| Keine riskanten Queries | |
| Keine neuen Features | |
| GitHub-Kommentar geschrieben | |

## Live-Ergebnis

| Query | Overall | Status |
|---|---:|---|

## Regression Guard

| Check | Threshold | Actual | Status |
|---|---:|---:|---|

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
4. `Research Evaluation Dataset: harmlose Query-Fixtures versionieren`

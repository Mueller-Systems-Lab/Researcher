# Researcher — Nächstes Issue: Report-Quality-Evaluation mit mehreren harmlosen Queries erweitern

## Rolle

Du bist ein Senior Research Evaluation Engineer und Local-First Reliability Agent.

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
- #64: Report Traceability
- #65: Source Coverage Stabilisierung

Dein Ziel ist NICHT, neue Research-Features zu bauen.

Dein Ziel ist, die Report-Quality-Evaluation von einer einzelnen Default-Query auf mehrere harmlose Queries zu erweitern, damit der 99/100-Score nicht nur auf einem optimierten Beispiel basiert.

---

# Ausgangslage

Nach #65:

```bash
make research-happy-path
make research-evaluate
```

liefert:

| Score | Wert |
|---|---:|
| Source Coverage | 100 |
| Traceability | 95 |
| Hallucination Risk | 100 |
| Local-First | 100 |
| Overall | 99 |

Das ist sehr gut, aber noch nicht robust gegen Query-Varianz.

Nächster Qualitätsbeweis:

> Mehrere harmlose Queries laufen durch denselben lokalen Pfad und erreichen reproduzierbar gute Qualitätswerte.

---

# Oberstes Ziel dieses Issues

Erstelle einen kleinen Multi-Query-Evaluation-Runner für harmlose Standardqueries.

Er soll:

1. mehrere harmlose Queries ausführen
2. pro Query einen Report erzeugen
3. pro Report eine Evaluation erzeugen
4. aggregierte Scores berechnen
5. Ausreißer sichtbar machen
6. keine Cloud-Provider nutzen
7. keine riskanten Queries zulassen
8. JSON- und Markdown-Summary erzeugen

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Research-Features implementieren
- Cloud-Evaluation oder externe LLM-Judges einführen
- Security-, CVE-, Exploit-, Darknet- oder personenbezogene Queries verwenden
- echte Zielrecherche automatisieren
- Quality-Gates lockern
- Tests löschen
- Coverage-Schwelle senken
- Vendor-Code ändern

---

# Harmlose Query-Suite

Starte mit maximal 3–5 harmlosen Queries.

Beispiele:

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
darknet forum
site:
person name
target domain
```

Die Query-Safety-Guard aus #61 muss auch für Multi-Query gelten.

---

# Arbeitsreihenfolge

## 1. Aktuellen Single-Query-Zustand reproduzieren

Führe aus:

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
```

Dokumentiere:

- aktueller Report-Pfad
- aktueller Evaluation-Pfad
- Scores
- verwendetes Modell
- Query

---

## 2. Multi-Query-Runner erstellen

Erstelle:

```text
scripts/research_multi_query_eval.py
```

oder erweitere bestehende Skripte minimal, falls sauberer.

Der Runner soll:

- Standardqueries enthalten
- optional `--queries-file` unterstützen
- optional `--limit` unterstützen
- pro Query `research_happy_path`-Logik wiederverwenden oder sauber aufrufen
- pro Query `evaluate_research_report` nutzen
- Ergebnisse aggregieren

Beispiel:

```bash
python3 scripts/research_multi_query_eval.py --limit 3
```

Output:

```text
Query 1/3: What is a search engine?
  Overall: 99
Query 2/3: What is SearXNG?
  Overall: 94
Query 3/3: What is local-first software?
  Overall: 91

Aggregate:
  Mean Overall: 94.6
  Min Overall: 91
  Failed: 0
```

---

## 3. Ergebnisformate

Erzeuge:

```text
reports/evaluation/multi_query_eval_*.json
reports/evaluation/multi_query_eval_*.md
```

JSON sollte enthalten:

```json
{
  "generated_at": "...",
  "query_count": 3,
  "passed": 3,
  "failed": 0,
  "aggregate_scores": {
    "overall_mean": 0,
    "overall_min": 0,
    "source_coverage_mean": 0,
    "traceability_mean": 0,
    "hallucination_risk_mean": 0,
    "local_first_mean": 0
  },
  "results": [
    {
      "query": "...",
      "report_path": "...",
      "evaluation_path": "...",
      "scores": {}
    }
  ]
}
```

Markdown sollte eine Tabelle enthalten:

```markdown
| Query | Source | Traceability | Hallucination | Local-First | Overall | Status |
|---|---:|---:|---:|---:|---:|---|
```

---

## 4. Makefile-Targets ergänzen

Ergänze:

```makefile
research-evaluate-multi:
	ALLOW_OLLAMA_MODEL_FALLBACK=true python3 scripts/research_multi_query_eval.py --limit 3

research-evaluate-multi-strict:
	ALLOW_OLLAMA_MODEL_FALLBACK=true python3 scripts/research_multi_query_eval.py --limit 3 --min-overall 80 --min-query-overall 70
```

Wichtig:

- nicht Bestandteil von `make quality`
- nicht Bestandteil von `make ci-local`
- optionaler Runtime-/Evaluation-Check

---

## 5. Tests ergänzen

Erstelle oder erweitere:

```text
tests/test_research_multi_query_eval.py
```

Testfälle:

- Standardqueries sind harmlos
- riskante Query wird blockiert
- Aggregation berechnet Mean/Min korrekt
- fehlgeschlagene Query wird gezählt
- JSON-Summary wird erzeugt
- Markdown-Summary wird erzeugt
- `--limit` begrenzt Query-Anzahl
- `--min-overall` schlägt bei schlechtem Durchschnitt fehl
- `--min-query-overall` schlägt bei Ausreißer fehl

Keine echten Netzwerkdienste in Unit-Tests.

---

# 6. Dokumentation erstellen

Erstelle:

```text
docs/evaluation/multi-query-evaluation.md
```

Pflichtinhalt:

```markdown
# Multi-Query Research Evaluation

## Ziel

## Warum mehrere Queries?

## Standardqueries

## Befehle

```bash
make research-evaluate-multi
make research-evaluate-multi-strict
```

## Scores

## Aggregation

## Sicherheitsgrenzen

## Keine Cloud-Judges

## Grenzen der Evaluation

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

# Single Query
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate

# Multi Query
make research-evaluate-multi

# Tests
python3 -m pytest tests/ -q -k "multi_query or research_report_evaluation or research_happy_path"
```

Optional:

```bash
make research-evaluate-multi-strict
```

Nur mit realistischen Schwellen.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Multi-Query-Runner existiert
- mindestens 3 harmlose Queries laufen
- Query-Safety-Guard greift
- pro Query Report erzeugt wird
- pro Query Evaluation erzeugt wird
- aggregierte JSON-Summary erzeugt wird
- aggregierte Markdown-Summary erzeugt wird
- Mean/Min-Scores berechnet werden
- Ausreißer sichtbar sind
- Makefile-Targets existieren
- Tests ohne echte Dienste existieren
- Doku existiert
- bestehende Gates bleiben grün
- keine Cloud-Judges eingeführt wurden
- keine riskanten Queries eingeführt wurden
- keine neuen Research-Features gebaut wurden
- GitHub-Kommentar mit Multi-Query-Ergebnis geschrieben wurde

Minimal akzeptabel:

- 3 Queries
- JSON + Markdown Summary
- Tests
- Doku
- keine Regression

Gut:

- Strict-Schwellen für Durchschnitt und Einzelquery
- Ausreißer werden klar markiert
- Report-/Eval-Pfade werden sauber verlinkt

Sehr gut:

- Multi-Query-Evaluation zeigt, ob die Reportqualität queryübergreifend stabil ist und nicht nur für eine optimierte Default-Query funktioniert

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Multi-Query-Evaluation Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Multi-Query-Runner erstellt | |
| Mindestens 3 harmlose Queries | |
| Query-Safety-Guard aktiv | |
| Reports pro Query erzeugt | |
| Evaluation pro Query erzeugt | |
| JSON-Summary erzeugt | |
| Markdown-Summary erzeugt | |
| Aggregierte Scores berechnet | |
| Ausreißer sichtbar | |
| Makefile-Targets erstellt | |
| Tests vorhanden | |
| Doku erstellt | |
| `make quality` weiterhin grün | |
| `make coverage` weiterhin grün | |
| `make ci-local` weiterhin grün | |
| Keine Cloud-Judges | |
| Keine riskanten Queries | |
| Keine neuen Features | |
| GitHub-Kommentar geschrieben | |

## Multi-Query-Ergebnis

| Query | Source | Traceability | Hallucination | Local-First | Overall | Status |
|---|---:|---:|---:|---:|---:|---|

## Aggregation

| Metrik | Wert |
|---|---:|
| Overall Mean | |
| Overall Min | |
| Source Coverage Mean | |
| Traceability Mean | |
| Hallucination Risk Mean | |
| Local-First Mean | |
| Failed Queries | |

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
4. `Report Quality Trend: Evaluation-Historie und Regression Guard`

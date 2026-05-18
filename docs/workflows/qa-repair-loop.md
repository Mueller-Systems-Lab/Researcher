# QA-Repair-Loop Workflow

## Überblick

Der QA-Repair-Loop (`scripts/run-qa-loop.sh`) ist ein beobachtbarer 12-Schritte-Testzyklus,
der das Researcher-Projekt automatisiert prüft, Fehler klassifiziert und einen strukturierten
Report erzeugt.

**Regel: Kein Issue ist fertig ohne Live-Testbeweis.**

## 12 Schritte

| # | Schritt | Befehl |
|---|---|---|
| 1 | Repo-Zustand erfassen | `git status`, `git log -1` |
| 2 | make all | Unit + Lint + Type + Security |
| 3 | make playwright | Visuelle Browser-Tests |
| 4 | E2E-Tests | `RUN_E2E_TESTS=true` oder `--e2e` Flag |
| 5 | Artefakte sammeln | Screenshots nach `qa/live/artifacts/screenshots/` |
| 6 | Fehler klassifizieren | `classify-errors.py` parst JUnit XML |
| 7 | Testabdeckung prüfen | Coverage-Report |
| 8 | Visuelle Probleme | Playwright Diff prüfen |
| 9 | Reparaturvorschlag | Branch erstellen (nie Auto-Merge) |
| 10 | Tests erneut ausführen | Nach Reparatur |
| 11 | Markdown-Report | `qa/live/latest-qa-loop-report.md` |
| 12 | Human-Gate | Riskante Änderungen nur mit Freigabe |

## Ausführung

```bash
# Vollständiger Loop
bash scripts/run-qa-loop.sh

# Mit E2E-Tests
RUN_E2E_TESTS=true bash scripts/run-qa-loop.sh
```

## Fehlerklassifikation

Das Skript `scripts/classify-errors.py` klassifiziert Fehler automatisch:

| Kategorie | Beschreibung | Beispiel |
|---|---|---|
| **INFRA** 🔧 | Infrastruktur | ConnectionError, Timeout, ImportError, DNS |
| **PRODUCT** 🐛 | Produktfehler | AssertionError, falsches Verhalten |
| **TEST** 🧪 | Testfehler | Fragiler Selektor, falsches Setup |

## Artefakte

Nach jedem Loop-Lauf sind folgende Beweisartefakte verfügbar:

- **Report:** `qa/live/latest-qa-loop-report.md`
- **Screenshots:** `qa/live/artifacts/screenshots/`
- **Logs:** `qa/live/artifacts/logs/`
- **JUnit XML:** `qa/live/artifacts/junit.xml`
- **Coverage:** `coverage_html/index.html`

## Human-Gates

Manuelle Freigabe erforderlich bei:
- Änderungen an `config/config.py`
- DB-Migrationen (Whoosh → SQLite FTS5)
- Deployment-Änderungen
- Security-relevanten Änderungen

## Repair-Regeln

1. **Max. 3 automatische Repair-Versuche** pro Issue
2. **Kein Auto-Merge** — jeder Repair-Branch braucht Human-Review
3. **Keine Tests löschen** — nur um "grün zu werden"
4. **Keine Akzeptanzkriterien reduzieren**
5. Nach jedem Repair: **Loop erneut ausführen** und **neuen Evidence-Kommentar posten**

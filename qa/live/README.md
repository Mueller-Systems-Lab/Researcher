# Live-QA Evidence — README

## Zweck

Dieses Verzeichnis enthält das Live-QA-Evidence-System für das Researcher-Projekt.
Jeder Testlauf erzeugt sichtbare Beweisartefakte (Screenshots, Logs, Reports),
die im zugehörigen GitHub-Issue als Kommentar dokumentiert werden.

## Regel: Kein Issue ist fertig ohne Screenshot-Beweis.

## Struktur

```
qa/
  live/
    README.md                       # Diese Datei
    live-test-plan.md               # Testplan: getestete Flows, Viewports, Akzeptanzkriterien
    latest-live-test-report.md      # Auto-generierter Report des letzten Laufs
    artifacts/
      screenshots/                  # PNG-Screenshots pro Flow
      videos/                       # Playwright-Videos (bei Fehlern)
      traces/                       # Playwright-Traces (bei Fehlern)
      html-report/                  # pytest-html / Playwright-HTML-Report
      logs/                         # live-test.log
  scripts/
    run-live-tests.sh               # Orchestriert den gesamten Live-Testlauf
```

## Ausführung

```bash
# Lokal
bash qa/scripts/run-live-tests.sh

# In CI (GitHub Actions)
qa/scripts/run-live-tests.sh
```

## Tech-Stack

- **Test-Framework:** pytest + Playwright (Python sync_api)
- **Browser:** Chromium (headless)
- **Echte App:** `dashboard/server.py` (wird von pytest-Fixture gestartet)
- **App-URL:** `http://127.0.0.1:8889`
- **Mock-Status:** KEIN Mock — echter HTTP-Server, echter Browser

## Akzeptanzkriterien für Issue-Abschluss

Ein QA-/Test-/Repair-Issue gilt nur als erledigt, wenn:

1. Die echte App wurde lokal gestartet (nicht gemockt)
2. Ein echter User-Flow wurde im Browser ausgeführt
3. Ein Screenshot der geladenen App existiert als Beweis
4. Der Testbericht wurde als GitHub-Issue-Kommentar gepostet
5. Artefakte sind in `qa/live/artifacts/` gespeichert

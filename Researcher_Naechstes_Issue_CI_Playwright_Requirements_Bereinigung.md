# Researcher — Nächstes Issue: CI-/Playwright-/Requirements-Bereinigung vor Release-Tag

## Rolle

Du bist ein Senior CI/CD Engineer, Python Test Infrastructure Engineer und Release-Safety-Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis des aktuellen Codebase Audit Reports vom 20. Mai 2026 auf Branch `qa/accessibility-tests`, Commit `deb7d58`.

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, die im Audit gefundenen strukturellen CI-/Test-/Dependency-Probleme minimal zu beheben, bevor `v0.1.0-local-alpha` endgültig getaggt und als GitHub Release veröffentlicht wird.

---

# Ausgangslage

Der Audit bestätigt einen sehr guten Projektzustand:

- Python 3.12.3, erlaubt >=3.11
- Ruff: 0 Fehler
- mypy: 0 Fehler in 45 Quelldateien
- Bandit: 0 Medium/High im Projektcode
- Tests: 259 passed, 11 skipped Playwright, 5 skipped E2E-Dienste
- Coverage: 78.52%, Schwelle 78%
- `gpt_researcher` Submodule importierbar, Fork-Version 0.14.8
- Playwright 1.57.0 installiert, Chromium 1200 verfügbar
- Kein P0/P1-Blocker

Gefundene strukturelle Probleme:

1. `.github/workflows/test.yml` enthält einen GitHub-Actions-Syntaxfehler: ein Step kombiniert `run:` und `uses:`.
2. Es gibt zwei Workflows mit Namen `CI`, die potenziell parallel und inkonsistent laufen: `ci.yml` und `test.yml`.
3. Playwright-Tests skippen teilweise mit „Playwright Python package is not installed“, obwohl Playwright installiert ist.
4. `requirements.txt` enthält `gpt-researcher==0.14.8`, obwohl das Projekt offenbar das Git-Submodul nutzt.

---

# Oberstes Ziel dieses Issues

Bereinige die Release-blockierenden Infrastrukturprobleme:

1. `test.yml` syntaktisch korrekt machen.
2. CI-Workflow-Duplikation analysieren und eine klare kanonische Strategie dokumentieren oder minimal korrigieren.
3. Playwright-Skip-Logik untersuchen und beheben, soweit ohne größere Architekturänderung möglich.
4. `requirements.txt` mit Submodul-Realität abgleichen oder dokumentieren.
5. Alle bestehenden Quality Gates grün halten.
6. Keine produktive Logik verändern.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- produktive Research-Logik ändern
- Release taggen
- GitHub Release veröffentlichen
- Force-Push ausführen
- Coverage-Schwelle senken
- Tests löschen
- Playwright-Tests pauschal deaktivieren
- CI-Gates lockern
- Submodul `gpt_researcher/` ändern
- große Dependency-Upgrades durchführen
- Branch wechseln oder rebasen

---

# Prioritäten

## P1 — Pflicht vor Release-Tag

- `.github/workflows/test.yml` Syntaxfehler beheben.
- Lokale Gates erneut validieren.

## P2 — Stark empfohlen

- CI-Duplikation klären: `ci.yml` vs `test.yml`.
- Playwright-Skip-Ursache klären.

## P3 — Dokumentations-/Dependency-Konsistenz

- `requirements.txt` und README/Fresh-Clone-Doku bezüglich `gpt_researcher` Submodul bereinigen.

---

# Arbeitsreihenfolge

## 1. Audit-Fakten verifizieren

Führe aus:

```bash
git branch --show-current
git rev-parse --short HEAD
git status --short

python3 --version
make quality
make coverage
make test-e2e
RUN_PLAYWRIGHT_TESTS=true make playwright
```

Dokumentiere:

- Branch
- Commit
- Working Tree Status
- ob Submodul dirty ist
- Quality Gate Ergebnis
- Playwright Ergebnis
- Skip-Anzahl

Wenn Working Tree nicht sauber ist:

- Änderungen kategorisieren
- keine unerwarteten Dateien committen
- Release-Tag weiterhin blockieren

---

## 2. `.github/workflows/test.yml` Syntaxfehler beheben

Audit-Befund:

```yaml
- name: E2E pipeline tests
  run: make test-e2e
  uses: actions/upload-artifact@v4
```

Ein GitHub-Actions-Step darf nicht gleichzeitig `run:` und `uses:` enthalten.

Korrigiere zu separaten Steps:

```yaml
- name: E2E pipeline tests
  run: make test-e2e

- name: Upload coverage HTML
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: coverage-html-${{ matrix.python-version }}
    path: coverage_html/
    if-no-files-found: ignore
```

Falls `coverage_html/` nicht erzeugt wird:

- entweder Pfad auf existierenden Report korrigieren
- oder Upload-Step entfernen/kommentieren
- nicht fehlschlagen lassen, wenn Artefakt optional ist

---

## 3. CI-Workflow-Duplikation analysieren

Dateien:

```text
.github/workflows/ci.yml
.github/workflows/test.yml
```

Audit-Befund:

- beide heißen offenbar `CI`
- beide triggern auf `push`/`pull_request`
- `ci.yml` ist detaillierter
- `test.yml` ist einfacher, aber matrix-basiert

Optionen:

### Option A — `ci.yml` behalten, `test.yml` deaktivieren/umbenennen

Geeignet, wenn `ci.yml` die vollständige Gate-Strategie enthält.

### Option B — `test.yml` behalten, `ci.yml` deaktivieren

Geeignet, wenn `test.yml` einfacher und ausreichend ist.

### Option C — Beide behalten, aber klar benennen und triggern

Empfohlen, wenn beide unterschiedliche Zwecke haben:

```yaml
name: CI Fast Gate
```

und:

```yaml
name: CI Extended Gate
```

z. B.:

- `test.yml`: Fast PR Gate
- `ci.yml`: Manual/extended/nightly oder Playwright/Benchmarks

Wichtig:

- Keine komplette CI-Neuarchitektur in diesem Issue.
- Minimaler, sicherer Fix bevorzugt.
- Wenn unklar: Nur Namen eindeutig machen und Syntax fixen.

---

## 4. Playwright-Skip untersuchen

Audit-Befund:

- Playwright 1.57.0 installiert
- Chromium 1200 verfügbar
- Dennoch 11/15 Tests skipped: „Playwright Python package is not installed“
- Vermutung: `sync_playwright` wird in Skip-Bedingung `None`, evtl. wegen `try/except ImportError` oder transitivem Importfehler.

Prüfe:

```bash
python3 - <<'PY'
from playwright.sync_api import sync_playwright
print(sync_playwright)
PY

RUN_PLAYWRIGHT_TESTS=true python3 -m pytest tests/playwright/ -v --tb=long -rs
```

Dann Datei prüfen:

```text
tests/playwright/test_dashboard_accessibility.py
tests/playwright/test_dashboard_visual_regression.py
tests/playwright/test_dashboard_browser.py
```

Ziel:

- Skip-Grund korrekt machen.
- Wenn Playwright-Paket installiert ist, soll nicht fälschlich wegen Paketmangel geskippt werden.
- Wenn Browser fehlt, soll die Meldung Browser-Installationshinweis geben.

Mögliche Reparatur:

```python
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_IMPORT_ERROR = None
except ImportError as exc:
    sync_playwright = None
    PLAYWRIGHT_IMPORT_ERROR = exc

pytestmark = pytest.mark.skipif(
    sync_playwright is None,
    reason=f"Playwright Python package is not installed: {PLAYWRIGHT_IMPORT_ERROR}",
)
```

Oder besser:

- ImportError genau loggen
- Browser-/Runtime-Fehler im Test separat behandeln
- nicht alle Tests pauschal skippen, wenn nur Browser fehlt

Nicht erlaubt:

- Playwright-Tests löschen
- Skip pauschal entfernen, wenn CI dadurch unkontrolliert bricht

---

## 5. `requirements.txt` mit Submodul-Realität abgleichen

Audit-Befund:

```text
requirements.txt enthält gpt-researcher==0.14.8,
aber Projekt nutzt Git-Submodul gpt_researcher/
```

Prüfe:

```bash
grep -n "gpt-researcher" requirements.txt
git submodule status
python3 -c "import sys; sys.path.insert(0, 'gpt_researcher'); from gpt_researcher import GPTResearcher; print('OK')"
```

Optionen:

### Option A — Eintrag entfernen

Wenn `pip install -r requirements.txt` sonst fehlschlägt oder irreführend ist.

### Option B — Kommentar ergänzen

Beispiel:

```text
# GPT Researcher is provided via git submodule `gpt_researcher/`, not PyPI.
# Run: git submodule update --init --recursive
```

### Option C — Doku ergänzen

README/Fresh-Clone-Doku muss klar sagen:

```bash
git submodule update --init --recursive
pip install -r requirements.txt
```

Empfehlung:

- Keine komplexe Dependency-Umstellung.
- Kein Submodul-Update.
- Nur Konsistenz herstellen.

---

# 6. Validierung

Nach Änderungen ausführen:

```bash
make quality
make coverage
make test-e2e
make ci-local
RUN_PLAYWRIGHT_TESTS=true make playwright
```

Zusätzlich optional:

```bash
python3 -m ruff check . --line-length=88
python3 -m mypy config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts --ignore-missing-imports
make security-project
make security-regression
```

Wenn GitHub Actions lokal via `act` verfügbar ist:

```bash
act -W .github/workflows/test.yml
```

Nur optional, nicht erzwingen.

---

# 7. Dokumentation aktualisieren

Falls CI-Strategie verändert wird, aktualisiere:

```text
docs/testing/test-profiles.md
docs/release/release-checklist.md
README.md
```

Falls requirements/Submodul angepasst wird:

```text
docs/development/fresh-clone-onboarding.md
README.md
```

Dokumentiere:

- welcher Workflow kanonisch ist
- wie Playwright lokal läuft
- ob Browserinstallation nötig ist
- wie Submodule initialisiert werden

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- `.github/workflows/test.yml` keine `run`/`uses`-Kollision mehr enthält
- CI-Workflow-Duplikation dokumentiert oder minimal bereinigt ist
- Playwright-Skip-Ursache dokumentiert ist
- Playwright-Tests nicht mehr fälschlich wegen fehlendem Paket skippen, sofern Playwright installiert ist
- `requirements.txt` und Submodul-Doku konsistent sind
- `make quality` grün bleibt
- `make coverage` grün bleibt
- `make test-e2e` grün bleibt
- `make ci-local` grün bleibt
- keine produktive Logik geändert wurde
- kein Release-Tag erstellt wurde
- kein GitHub Release erstellt wurde
- GitHub-Kommentar mit Ergebnissen geschrieben wurde

Minimal akzeptabel:

- `test.yml` Syntaxfix
- requirements/Submodul-Klarstellung
- Quality Gates grün
- Release bleibt ungetaggt

Gut:

- CI-Workflows eindeutig benannt/aufgeteilt
- Playwright-Skip-Meldung korrekt und nicht irreführend
- Doku aktualisiert

Sehr gut:

- Playwright-Tests laufen lokal vollständig oder skippen nur noch echte Browser-/Runtime-Fälle
- GitHub Actions sind bereit für Release-Tag

---

# Abschlussbericht-Vorlage

```markdown
# Researcher CI-/Playwright-/Requirements-Bereinigung Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| `test.yml` Syntaxfehler behoben | |
| CI-Duplikation geklärt | |
| Playwright-Skip-Ursache dokumentiert | |
| Playwright-Skip verbessert | |
| requirements/Submodul-Konsistenz hergestellt | |
| `make quality` grün | |
| `make coverage` grün | |
| `make test-e2e` grün | |
| `make ci-local` grün | |
| Kein Release-Tag erstellt | |
| Kein GitHub Release erstellt | |
| GitHub-Kommentar geschrieben | |

## CI-Entscheidung

## Playwright-Ergebnis

| Befehl | Ergebnis |
|---|---|

## Requirements/Submodul-Entscheidung

## Geänderte Dateien

## Validierte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Bewusst nicht gelöste Probleme

## Risiken

## Nächster Schritt
```

---

# Empfohlener nächster Schritt nach Abschluss

Wenn dieses Issue abgeschlossen ist:

1. Working Tree erneut sauber committen/pushen.
2. Tag-Existenz erneut prüfen.
3. GitHub Release-Existenz erneut prüfen.
4. Erst dann: `FREIGABE TAG UND RELEASE`.

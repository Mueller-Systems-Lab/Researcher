# Researcher — Reparatur-Prompt aus Codebase Audit

## Rolle

Du bist ein Senior Software Reliability Engineer, Python-Test-Engineer und Brownfield-Repair-Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis des vorhandenen Codebase-Audits vom 2026-05-18.

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, die bestehende Codebase in einen stabilen, CI-fähigen Walking-Skeleton-Zustand zu bringen.

---

# Ausgangslage aus dem Audit

Das Projekt ist grundsätzlich strukturiert und weitgehend funktionsfähig:

- Python 3.12.3
- GPT Researcher Fork / lokales Research-System
- FastAPI / GPT Researcher Web-UI
- Ollama
- SearXNG
- Tor / Darknet-Crawler
- ChromaDB
- Whoosh / SQLite FTS5
- GPU-Dashboard
- MCP-Tools
- pytest
- ruff
- mypy
- Playwright
- GitHub Actions

Der aktuelle Stand laut Audit:

- `make test` besteht: 167 passed, 5 skipped
- Playwright-Strukturtests bestehen teilweise: 10 passed, 5 skipped
- `make coverage` schlägt fehl: 75.80% < 78%
- `make security` schlägt fehl: `bandit` fehlt
- E2E-Pipeline-Test schlägt fehl wegen Mock-Scope-Fehler
- SQLite-Benchmark läuft in Timeout bei `conn.commit()`
- ruff meldet 1345 Fehler
- mypy meldet Duplicate-`conftest`-Problem
- CI würde aktuell fehlschlagen

---

# Oberstes Ziel

Stelle einen CI-fähigen Walking Skeleton her.

Ein Walking Skeleton gilt hier als erreicht, wenn:

1. Dependencies installierbar sind.
2. `make test` grün bleibt.
3. `make security` ausführbar ist.
4. der E2E-Mock-Test grün ist oder sauber begründet isoliert wird.
5. Coverage entweder durch echte Tests auf >=78% gebracht oder die Schwelle begründet temporär angepasst wird.
6. mypy keine blockierenden Fehler mehr meldet.
7. ruff so weit reduziert ist, dass echte Fehler nicht mehr in Stilrauschen untergehen.
8. CI lokal nachvollziehbar grün oder mit exakt dokumentierten Restblockern reproduzierbar ist.
9. README/Docs den realen Zustand beschreiben.
10. Keine neuen Features eingeführt wurden.

---

# Harte Verbote

Während dieser Reparatur ist verboten:

- neue Features bauen
- neue Architektur einführen
- Frameworks austauschen
- Ollama-/Tor-/SearXNG-Architektur umbauen
- Whoosh→SQLite-Migration erzwingen
- Darknet-Crawler fachlich erweitern
- GPU-Dashboard erweitern
- Coverage-Schwelle blind senken, ohne Begründung
- Tests löschen, um Grün zu erzwingen
- CI deaktivieren, um Grün zu erzwingen
- großflächige automatische Fixes ohne vorherigen Kontrollpunkt

---

# Reparaturstrategie

Arbeite strikt in kleinen, überprüfbaren Schritten.

Jeder Schritt muss:

- einen konkreten Fehler aus dem Audit adressieren
- klein sein
- einen klaren Nachweisbefehl haben
- dokumentiert werden
- keine Nebenfeatures enthalten

Nach jedem Schritt:

1. relevanten Test/Befehl ausführen
2. Ergebnis dokumentieren
3. erst dann zum nächsten Schritt gehen

---

# Priorisierte Reparaturreihenfolge

## Schritt 1 — `bandit` als Security-Dependency ergänzen

### Problem

`make security` schlägt fehl, weil `bandit` nicht installiert ist.

### Erwartete Änderung

- `bandit` in `requirements.txt` oder die dafür vorgesehene Dev-Dependency-Liste aufnehmen.
- Keine anderen Dependency-Upgrades durchführen.

### Verifikation

```bash
pip install -r requirements.txt
python3 -m bandit -r . --skip B101,B311,B404,B603
make security
```

### Abschlusskriterium

`make security` ist ausführbar. Falls Bandit Findings meldet, diese dokumentieren und nicht stillschweigend ignorieren.

---

## Schritt 2 — E2E-Mock-Scope-Fehler reparieren

### Problem

`tests/e2e/test_full_research_pipeline.py` schlägt fehl, weil der `requests.get`-Mock offenbar endet, bevor der `ClaimValidator` ausgeführt wird. Dadurch entstehen echte HTTP-Requests oder leere Quellen.

### Erwartete Änderung

- Den Mock-Scope so erweitern, dass alle Codepfade, die `requests.get` im Test benötigen, innerhalb des Patch-Kontexts laufen.
- Alternativ eine robuste Mock-Lösung wie `responses` oder pytest-Fixture verwenden, aber nur wenn bereits im Projekt vorhanden oder minimal ergänzbar.
- Keine produktive Logik ändern, wenn der Fehler eindeutig im Test liegt.

### Verifikation

```bash
python3 -m pytest tests/e2e/test_full_research_pipeline.py -v --timeout=60
python3 -m pytest tests/e2e/ -v --timeout=60
```

### Abschlusskriterium

E2E-Tests bestehen oder ein verbleibender externer Dienstblocker ist exakt dokumentiert.

---

## Schritt 3 — mypy Duplicate-`conftest` reparieren

### Problem

`mypy` meldet ein Duplicate-Module-Problem zwischen:

- `tests/conftest.py`
- `tests/playwright/conftest.py`

### Erwartete Änderung

Bevorzugte Optionen in dieser Reihenfolge prüfen:

1. `tests/playwright/__init__.py` hinzufügen, falls dadurch die Package-Grenze sauber wird.
2. mypy-Konfiguration gezielt anpassen, falls Playwright-Tests nicht Teil des Typecheck-Scope sein sollen.
3. Keine Testdateien verschieben, außer es ist zwingend nötig.

### Verifikation

```bash
python3 -m mypy . --ignore-missing-imports
make lint-types
```

### Abschlusskriterium

mypy meldet keinen Duplicate-`conftest`-Blocker mehr.

---

## Schritt 4 — Coverage auf >=78% bringen

### Problem

Coverage liegt bei 75.80%, benötigt aber 78%.

Audit nennt besonders:

- `vectordb/embedding.py` mit ca. 65%
- `vectordb/store.py` mit ca. 73%

### Erwartete Änderung

- Keine Coverage-Schwelle senken, außer der Nutzer verlangt es ausdrücklich oder es wird als temporärer Notfall-Fix separat dokumentiert.
- Bevorzugt echte Tests ergänzen.
- Ollama-/ChromaDB-Abhängigkeiten mocken, damit Tests lokal und CI-fähig bleiben.
- Fokus auf deterministische Unit-Tests für Fehlerpfade, Konfiguration, Fallbacks und Grenzfälle.

### Verifikation

```bash
python3 -m pytest tests/ --cov --cov-report=term
make coverage
```

### Abschlusskriterium

Coverage >=78% und Tests grün.

---

## Schritt 5 — SQLite-FTS5-Benchmark-Timeout isolieren

### Problem

`tests/benchmarks/test_index_backends.py::TestSQLiteFTS5Benchmark::test_sqlite_index_100` läuft in einen Timeout bei `conn.commit()`.

### Erwartete Änderung

Zuerst Ursachenanalyse, dann Minimalfix.

Prüfe:

- wiederverwendete SQLite-Dateien zwischen Benchmark-Runs
- fehlende Connection-Close- oder Cleanup-Pfade
- WAL-Checkpoint-Verhalten
- zu niedrigen Timeout für Benchmark-Kontext
- parallele Testausführung oder Lock-Contention

Erlaubte Fixrichtungen:

- Benchmark-Fixture isolieren
- temporäre DB-Datei pro Test erzwingen
- Connection-Cleanup sicherstellen
- WAL-Checkpoint nach Testlauf ausführen
- Benchmark-Timeout begründet erhöhen, falls es ein legitimer Langläufer ist

Nicht erlaubt:

- Benchmark einfach löschen
- SQLite-Adapter fachlich groß umbauen, bevor Root Cause klar ist

### Verifikation

```bash
python3 -m pytest tests/benchmarks/test_index_backends.py::TestSQLiteFTS5Benchmark::test_sqlite_index_100 -v --timeout=120
python3 -m pytest tests/benchmarks/ -v --timeout=120
```

### Abschlusskriterium

SQLite-Benchmark ist stabil oder ein legitimer Performance-/Benchmark-Folgeblocker ist dokumentiert.

---

## Schritt 6 — ruff-Rauschen kontrolliert reduzieren

### Problem

ruff meldet 1345 Fehler, überwiegend Stil-/Modernisierungsfehler wie `UP045`.

### Erwartete Änderung

Nicht sofort alles blind mit `--unsafe-fixes` ändern.

Arbeite in zwei Phasen:

1. Sichere automatische Fixes:

```bash
python3 -m ruff check . --fix
```

2. Danach erneut prüfen:

```bash
python3 -m ruff check . --line-length=88
```

Wenn `--unsafe-fixes` nötig erscheint:

- vorher diff prüfen
- nur auf klar begrenzte Fehlerklasse anwenden
- danach vollständige Tests ausführen

### Verifikation

```bash
python3 -m ruff check . --line-length=88
make test
make coverage
```

### Abschlusskriterium

ruff-Fehler sind deutlich reduziert oder ein klarer Folgeplan ist dokumentiert. Tests bleiben grün.

---

## Schritt 7 — CI lokal nachstellen

### Problem

CI würde aktuell wahrscheinlich wegen Coverage und Security fehlschlagen.

### Erwartete Änderung

- GitHub Actions `test.yml` mit lokalen Befehlen abgleichen.
- Dokumentieren, welche CI-Schritte lokal geprüft wurden.
- Keine CI-Schritte entfernen, nur um Grün zu erzeugen.

### Verifikation

```bash
pip install -r requirements.txt
make lint
make lint-types
make security
make coverage
make test
```

Falls `make lint` wegen großer Stilaltlasten noch nicht grün ist, dokumentiere:

- Restanzahl
- wichtigste Fehlerklassen
- ob CI `make lint` wirklich blockierend ausführt
- nächstes fokussiertes Lint-Issue

---

# Definition of Done

Die Reparatur gilt nur als abgeschlossen, wenn dieser Bericht ausgefüllt wurde:

```markdown
# Researcher Repair Abschlussbericht

## Ergebnis

- [ ] Dependencies installierbar
- [ ] `make test` grün
- [ ] `make security` ausführbar
- [ ] E2E-Pipeline-Test grün oder sauber isoliert
- [ ] Coverage >=78% oder temporäre Ausnahme begründet
- [ ] mypy Duplicate-`conftest` behoben
- [ ] SQLite-Benchmark stabil oder sauber dokumentiert
- [ ] ruff-Rauschen reduziert oder Folge-Issue definiert
- [ ] CI lokal nachvollzogen
- [ ] README/Docs aktualisiert
- [ ] GitHub-Kommentar geschrieben

## Verifizierte Befehle

```bash
# exakte Befehle und Ergebnisse eintragen
```

## Geänderte Dateien

## Nicht geänderte Bereiche

## Bewusst nicht gelöste Probleme

## Risiken

## Nächstes empfohlenes Issue
```

Wenn ein Punkt nicht erfüllbar ist:

- Issue nicht schließen
- Blocker dokumentieren
- kleinsten nächsten Reparaturschritt vorschlagen

---

# GitHub-Kommentar-Vorlage

```markdown
## Repair Progress — Walking Skeleton Stabilisierung

### Ziel
CI-fähigen Walking Skeleton herstellen, ohne neue Features oder Architekturumbau.

### Bearbeitete Punkte
- [ ] bandit / make security
- [ ] E2E-Mock-Scope
- [ ] mypy duplicate conftest
- [ ] Coverage >=78%
- [ ] SQLite-Benchmark
- [ ] ruff-Rauschen
- [ ] CI-Abgleich

### Verifikation

```bash
<exakte Befehle>
```

### Ergebnis

### Restblocker

### Nächster Schritt
```

---

# Startanweisung

Beginne mit Schritt 1. Führe keine Feature-Arbeit aus. Nach jedem Reparaturschritt muss der passende Verifikationsbefehl ausgeführt und dokumentiert werden.

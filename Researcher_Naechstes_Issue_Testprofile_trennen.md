# Researcher — Nächstes Issue: Testprofile trennen (`fast`, `e2e`, `benchmarks`, `security`, `full`)

## Rolle

Du bist ein Senior Python CI/CD Engineer und Test-Strategy-Architekt.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Repair-Chain:

- #50: Walking-Skeleton/Repair
- #51: ruff Lint-/CI-Gate, 950 → 0
- #52: Bandit-/Security-Triage
- #53: Submodul-Security-Review
- #54: CI-Security-Gate
- #55: mypy Vendor-/Submodul-Grenze
- #56: Projekt-Type-Errors 33 → 0, `make typecheck` blockierend

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, die jetzt stabilen Quality Gates in sinnvolle, schnelle und getrennte Testprofile aufzuteilen, damit lokale Entwicklung und CI zuverlässig, schneller und besser steuerbar werden.

---

# Ausgangslage

Nach #56 sind alle fünf Quality Gates blockierend und grün:

- `ruff`: 0 Errors
- `bandit/security-project`: 0 Medium/High im Projektcode
- `mypy/typecheck`: 0 Projekt-Type-Errors
- Tests: 195 passed
- Coverage: ca. 78.5%, Schwelle >=78%

Offene Prozessprobleme:

- Test-/Quality-Befehle sind noch nicht optimal als Profile getrennt.
- Benchmarks können lange laufen.
- E2E braucht eigene Steuerung.
- Security-Reports sollten getrennt von schnellen Checks laufen.
- Lokaler Entwickler-Loop sollte schnell bleiben.
- CI sollte klare Stufen haben:
  - Fast Gate
  - E2E Gate
  - Security Gate
  - Benchmark/slow Gate
  - Full Gate

---

# Oberstes Ziel dieses Issues

Erstelle klare Makefile- und CI-Testprofile:

1. `make test-fast` — schneller lokaler Standardcheck
2. `make test-e2e` — E2E/Integration wiederholbar
3. `make test-benchmarks` — langsame Benchmarks getrennt
4. `make quality` — ruff + typecheck + security-project + fast tests
5. `make coverage` — Coverage-Gate
6. `make ci-local` — lokal reproduzierbares CI-Minimum
7. `make ci-full` — kompletter Qualitätslauf inklusive E2E, Security-Reports und Benchmarks

Bestehende Targets sollen möglichst rückwärtskompatibel bleiben.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- produktive Logik ändern
- Tests löschen
- Coverage-Schwelle senken
- ruff/typecheck/security lockern
- Vendor-Code anfassen
- Benchmarks durch pauschales Skippen verstecken
- E2E-Tests deaktivieren, ohne eigenes Profil dafür bereitzustellen
- Playwright-CI endgültig lösen, wenn das ein eigenes Issue erfordert

---

# Testprofil-Prinzipien

## 1. Fast Loop muss schnell sein

`make test-fast` soll für lokale Entwicklung geeignet sein.

Es sollte ausschließen:

- Benchmarks
- live E2E
- schwere Playwright-Visual-/Accessibility-Tests, falls sie optional/env-gated sind

## 2. Langsame Tests sind sichtbar, aber getrennt

Benchmarks und E2E dürfen nicht verschwinden.

Sie sollen eigene Targets bekommen.

## 3. CI ist stufenweise

Empfohlen:

- PR/push: `quality` + `coverage`
- optional/cron/manual: `ci-full`
- separate Artefakte: security reports, benchmark reports, coverage reports

## 4. Keine Qualitätsabsenkung

Trennung heißt nicht Abschwächung.

Alle Gates bleiben vorhanden, nur klarer gegliedert.

---

# Arbeitsreihenfolge

## 1. Ist-Zustand analysieren

Lies:

```text
Makefile
pyproject.toml
.github/workflows/test.yml
.github/workflows/*.yml
README.md
docs/typing/typecheck-policy.md
docs/security/security-gate-policy.md
```

Führe aus:

```bash
make help || true
make test
make coverage
make typecheck
make security-project
python3 -m ruff check . --line-length=88
```

Dokumentiere:

- bestehende Makefile-Targets
- welche Targets langsam sind
- welche Targets Benchmarks enthalten
- welche Targets E2E enthalten
- welche Targets in CI laufen
- welche Befehle lokal reproduzierbar sind

---

## 2. Zielprofile definieren

Erstelle oder aktualisiere eine Tabelle in der Dokumentation:

```markdown
| Profil | Zweck | Blocking | Enthält | Enthält nicht |
|---|---|---|---|---|
| test-fast | schneller lokaler Testlauf | Ja | Unit/Integration ohne schwere Tests | Benchmarks, E2E live, visuelle Playwright |
| test-e2e | Pipeline-/E2E-Stabilität | Ja in full/optional | tests/e2e | Benchmarks |
| test-benchmarks | Performance-/Regression-Check | Optional/slow | tests/benchmarks | Unit/E2E |
| quality | schnelles Qualitätsgate | Ja | ruff, typecheck, security-project, test-fast | vendor report, benchmarks |
| coverage | Coverage-Gate | Ja | Coverage ohne schwere Tests | Benchmarks/E2E |
| ci-local | lokales CI-Minimum | Ja | quality + coverage + e2e quick | Benchmarks |
| ci-full | kompletter Lauf | Ja/Manual | alles inkl. reports/benchmarks | nichts |
```

---

## 3. Makefile-Targets ergänzen

Bevorzugter Zielzustand:

```makefile
.PHONY: test-fast test-e2e test-benchmarks quality ci-local ci-full

test-fast:
	python3 -m pytest tests/ \
		--ignore=tests/benchmarks \
		--ignore=tests/e2e \
		--ignore=tests/playwright/test_dashboard_accessibility.py \
		--ignore=tests/playwright/test_dashboard_visual_regression.py -q

test-e2e:
	python3 -m pytest tests/e2e/ -v --timeout=30 --count=3 -q

test-benchmarks:
	python3 -m pytest tests/benchmarks/ -v --timeout=300

quality:
	python3 -m ruff check . --line-length=88
	$(MAKE) typecheck
	$(MAKE) security-project
	$(MAKE) test-fast

ci-local:
	$(MAKE) quality
	$(MAKE) coverage
	$(MAKE) test-e2e

ci-full:
	$(MAKE) ci-local
	$(MAKE) security-vendor
	$(MAKE) security-report
	$(MAKE) test-benchmarks
```

Passe Pfade an, wenn sie im Repo anders sind.

Wichtig:

- Makefile verwendet Tabs.
- Bestehende Targets nicht unnötig brechen.
- `make test` kann auf `test-fast` zeigen oder als historischer Full-Test erhalten bleiben, aber das muss dokumentiert werden.
- `make all` sollte bewusst definiert sein: entweder `ci-local` oder `ci-full`.

---

## 4. Coverage-Target prüfen

`make coverage` soll weiterhin die Schwelle >=78% enforce’n.

Es sollte keine Benchmarks/E2E enthalten, wenn diese die Coverage unnötig verlangsamen.

Beispiel:

```makefile
coverage:
	python3 -m pytest tests/ \
		--ignore=tests/benchmarks \
		--ignore=tests/e2e \
		--ignore=tests/playwright/test_dashboard_accessibility.py \
		--ignore=tests/playwright/test_dashboard_visual_regression.py \
		--cov --cov-report=term -q
```

---

## 5. CI anpassen

In `.github/workflows/test.yml` oder passender CI-Datei:

Empfohlen:

```yaml
- name: Quality gate
  run: make quality

- name: Coverage gate
  run: make coverage

- name: E2E quick gate
  run: make test-e2e

- name: Security reports
  if: always()
  run: make security-report

- name: Upload security reports
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: security-reports-${{ matrix.python-version }}
    path: reports/
```

Benchmarks:

- entweder eigenes CI-Job mit `workflow_dispatch`
- oder nightly/scheduled
- oder non-blocking in PRs

Nicht blind Benchmarks in jeden PR-Lauf erzwingen, wenn sie >3 Minuten dauern.

---

## 6. Dokumentation aktualisieren

Erstelle oder aktualisiere:

```text
docs/testing/test-profiles.md
```

Pflichtinhalt:

```markdown
# Test Profiles

## Ziel

## Profile

| Target | Zweck | Lokal | CI | Geschwindigkeit |
|---|---|---|---|---|

## Lokaler Standardworkflow

```bash
make quality
make coverage
make test-e2e
```

## Vollständiger Lauf

```bash
make ci-full
```

## Langsame Tests

## Benchmarks

## Playwright-Hinweis

## Security-Reports

## Wann welches Profil genutzt wird

## Bekannte Grenzen
```

Optional README ergänzen:

```markdown
## Development Quality Loop

```bash
make quality
make coverage
make test-e2e
```
```

---

# Validierung

Nach Änderungen ausführen:

```bash
# Einzelprofile
make test-fast
make coverage
make typecheck
make security-project
make security-vendor
make security-report
make test-e2e
make test-benchmarks

# Aggregierte Profile
make quality
make ci-local
make ci-full

# Lint direkt
python3 -m ruff check . --line-length=88
```

Erwartung:

- `test-fast` grün
- `coverage` >=78%
- `typecheck` grün
- `security-project` grün
- `test-e2e` grün
- `test-benchmarks` grün oder klar dokumentiert, falls zu langsam/optional
- `quality` grün
- `ci-local` grün
- `ci-full` grün oder sauber dokumentiert, wenn Benchmarks/Playwright optional sind

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Testprofile im Makefile existieren
- `make test-fast` schnell und grün läuft
- `make quality` grün läuft
- `make ci-local` lokal reproduzierbar grün läuft
- `make coverage` weiterhin >=78% enforced
- E2E eigenes Target hat
- Benchmarks eigenes Target haben
- Security-Reports eigenes Target behalten
- CI nutzt die neuen Profile
- Doku unter `docs/testing/test-profiles.md` existiert
- README oder Entwicklerdoku den neuen Standardworkflow erwähnt
- keine produktive Logik geändert wurde
- keine Quality Gates gelockert wurden
- GitHub-Kommentar mit Vorher/Nachher-Workflow geschrieben wurde

Minimal akzeptabel:

- Makefile-Profile vorhanden
- `quality`, `coverage`, `test-e2e` grün
- CI nutzt mindestens `quality` und `coverage`
- Doku vorhanden

Gut:

- `ci-local` bildet den lokalen CI-Pfad exakt ab
- `ci-full` läuft lokal vollständig
- Benchmarks sind getrennt und dokumentiert

Sehr gut:

- CI unterscheidet PR-fast und slow/manual/cron Jobs
- Security-Reports und Coverage-Reports sind Artefakte
- Entwickler kann mit einem Befehl den Standardloop laufen lassen

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Testprofile Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| `test-fast` erstellt | |
| `test-e2e` erstellt | |
| `test-benchmarks` erstellt | |
| `quality` erstellt | |
| `coverage` stabil | |
| `ci-local` erstellt | |
| `ci-full` erstellt | |
| CI angepasst | |
| Testprofil-Doku erstellt | |
| README/Developer-Doku aktualisiert | |
| ruff weiterhin grün | |
| typecheck weiterhin grün | |
| security-project weiterhin grün | |
| Tests weiterhin grün | |
| Coverage weiterhin >=78% | |
| Keine produktive Logik geändert | |
| GitHub-Kommentar geschrieben | |

## Profile Vorher/Nachher

| Zweck | Vorher | Nachher |
|---|---|---|
| schneller lokaler Test | | |
| Coverage | | |
| E2E | | |
| Benchmarks | | |
| Security | | |
| lokaler CI-Lauf | | |
| kompletter Lauf | | |

## Ausgeführte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Geänderte Dateien

## CI-Änderungen

## Bewusst nicht gelöste Probleme

## Risiken

## Nächstes empfohlenes Issue
```

---

# Empfohlenes nächstes Folge-Issue nach Abschluss

Nach diesem Issue sollte eines dieser Issues folgen:

1. `Playwright-CI-Strategie definieren`
2. `Security regression tests für Netzwerk-/Hashing-/SQL-Pfade ergänzen`
3. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`
4. `Developer Onboarding: fresh clone → green gates in README absichern`

# Researcher — Nächstes Issue: Bandit-Baseline und CI-Security-Gate definieren

## Rolle

Du bist ein Senior Python Security CI Engineer und Release-Gate-Designer.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Repair-Chain:

- #50: Walking-Skeleton/Repair
- #51: Lint-/CI-Gate, ruff 950 → 0
- #52: Bandit-/Security-Triage, 43 Findings triagiert
- #53: Submodul-Security-Review, 32 → 20 Submodul-Findings

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, aus der dokumentierten Bandit-Triage ein reproduzierbares Security-Gate zu bauen, das bekannte Vendor-/Legacy-Findings kontrolliert akzeptiert, aber neue relevante Security-Findings sichtbar macht.

---

# Ausgangslage

Aus #53:

- Submodul-Bandit-Ausgangswert: 32 Findings
- Submodul-Bandit-Endwert: 20 Findings
- 6/6 MD5-Findings entschärft mit `usedforsecurity=False`
- 8/8 Requests-Timeout-Findings gefixt mit `timeout=(5, 30)`
- 1 SSL-Verify-Finding als Fallback-Pattern akzeptiert
- 14/15 Sicherheits-Hardenings umgesetzt
- Tests grün: 195 passed, 7 skipped
- Coverage: 78.41%
- ruff grün
- `make security` ausführbar
- `docs/security/submodule-security-review.md` existiert

Offen:

- 20 verbleibende Vendor-/Submodul-Findings
- Bandit-Baseline fehlt
- CI-Security-Gate ist noch nicht sauber definiert
- Entscheidung fehlt, ob Security-Gate blocking oder non-blocking sein soll

---

# Oberstes Ziel dieses Issues

Erstelle ein sauberes, nachvollziehbares Bandit-Security-Gate.

Das Gate soll:

1. bekannte, dokumentierte Vendor-/Submodul-Findings kontrolliert akzeptieren
2. neue High-Findings sichtbar machen
3. neue Projekt-eigene Medium/High-Findings verhindern
4. lokal reproduzierbar sein
5. in CI ausführbar sein
6. die bestehende Repair-Chain nicht destabilisieren

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- produktive Logik verändern
- weitere Submodul-Security-Fixes ohne eigenes Review durchführen
- Bandit global deaktivieren
- alle Findings pauschal ignorieren
- CI so konfigurieren, dass Security-Probleme unsichtbar werden
- Coverage-Schwelle senken
- ruff-Regeln lockern
- Tests löschen
- den bekannten mypy-Submodulfehler reparieren

---

# Security-Gate-Prinzipien

## 1. Baseline ist kein Freifahrtschein

Eine Baseline darf nur bekannte, geprüfte Findings enthalten.

Neue Findings müssen sichtbar werden.

## 2. Projektcode ist strenger als Vendor-Code

Projekt-eigene Pfade sollen strenger geprüft werden als `gpt_researcher/`.

Projekt-eigene Pfade:

- `config/`
- `crawlers/`
- `darknet_search/`
- `search/`
- `dashboard/`
- `vectordb/`
- `mcp_tools/`
- `onion_discovery/`
- `scripts/`
- eigene Root-Dateien

Vendor-/Fork-Pfad:

- `gpt_researcher/`

## 3. CI-Stufen

Empfohlene Sicherheitsstufen:

### Stufe A — Blocking Project Security

Projekt-eigener Code darf keine neuen Medium/High-Findings haben.

### Stufe B — Non-blocking Vendor Watch

Vendor-/Submodul-Findings werden berichtet, aber nicht sofort blockierend, solange sie in der Baseline dokumentiert sind.

### Stufe C — Regression Guard

Wenn neue Vendor-High-Findings dazukommen, soll CI mindestens warnen und idealerweise fehlschlagen, abhängig von Konfigurationsentscheidung.

---

# Arbeitsreihenfolge

## 1. Ist-Zustand reproduzieren

Führe aus:

```bash
make security

python3 -m bandit -r .   --skip B101,B311,B404,B603   -f json -o reports/bandit-full-current.json

python3 -m bandit -r .   --skip B101,B311,B404,B603   -f txt -o reports/bandit-full-current.txt

python3 -m bandit -r config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts   --skip B101,B311,B404,B603   -f json -o reports/bandit-project-current.json

python3 -m bandit -r gpt_researcher   --skip B101,B311,B404,B603   -f json -o reports/bandit-vendor-current.json
```

Falls `reports/` nicht existiert:

```bash
mkdir -p reports
```

Entscheide danach, ob Reports versioniert werden sollen oder nur lokal erzeugte Artefakte sind. Empfehlung: JSON/TXT-Laufreports nicht dauerhaft committen, sondern `docs/security/*` und Baseline/Policy committen.

---

## 2. Bestehende Security-Dokumente lesen

Lies und vergleiche:

```text
docs/security/bandit-triage.md
docs/security/submodule-security-review.md
pyproject.toml
Makefile
.github/workflows/*.yml
```

Dokumentiere:

- Welche Findings bewusst akzeptiert sind.
- Welche Findings Vendor-only sind.
- Welche Findings Projektcode betreffen.
- Welche Kommandos aktuell in CI laufen.
- Ob `make security` in CI bereits aufgerufen wird.

---

## 3. Baseline-Strategie wählen

Wähle eine der folgenden Strategien und begründe sie.

## Strategie A — Bandit Baseline-Datei

Erzeuge:

```bash
python3 -m bandit -r .   --skip B101,B311,B404,B603   -f json -o bandit-baseline.json
```

Dann zukünftige Läufe gegen Baseline prüfen, falls mit vorhandener Tooling-Version sinnvoll möglich.

Vorteil:

- expliziter Snapshot bekannter Findings

Nachteil:

- Baseline kann veralten oder zu breit werden

## Strategie B — Project/Vendor Split

CI führt zwei Security-Checks aus:

1. Project-Code blocking
2. Vendor-Code non-blocking/report-only

Beispiel:

```bash
python3 -m bandit -r config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts   --skip B101,B311,B404,B603   --severity-level medium

python3 -m bandit -r gpt_researcher   --skip B101,B311,B404,B603   --severity-level high || true
```

Vorteil:

- keine breite Baseline nötig
- Projektcode bleibt streng

Nachteil:

- Vendor-Findings werden nicht blockierend

## Strategie C — Hybrid

Empfohlen.

- Project-Code: blocking ab Medium
- Vendor-Code: Baseline/report-only
- Full report: als CI-Artefakt
- neue Projekt-Highs blockieren immer
- Security-Policy dokumentiert Akzeptanz

---

# Empfohlene Umsetzung

Bevorzugt: Strategie C — Hybrid.

## Makefile-Ziele ergänzen

Prüfe bestehende Targets und ergänze nur minimal.

Mögliche Targets:

```makefile
security:
	python3 -m bandit -r . --skip B101,B311,B404,B603

security-project:
	python3 -m bandit -r config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts --skip B101,B311,B404,B603 --severity-level medium

security-vendor:
	python3 -m bandit -r gpt_researcher --skip B101,B311,B404,B603

security-report:
	mkdir -p reports
	python3 -m bandit -r . --skip B101,B311,B404,B603 -f json -o reports/bandit-full.json || true
	python3 -m bandit -r . --skip B101,B311,B404,B603 -f txt -o reports/bandit-full.txt || true
```

Wichtig:

- Tabs im Makefile verwenden.
- Bestehende Targets nicht kaputtmachen.
- `security-project` sollte blockierend sein.
- `security-vendor` kann zunächst non-blocking sein, aber dokumentiert.

## CI anpassen

In `.github/workflows/*.yml` nur minimal ändern.

Empfehlung:

```yaml
- name: Security scan project code
  run: make security-project

- name: Security report full repository
  run: make security-report

- name: Upload security reports
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: bandit-security-reports
    path: reports/bandit-*.*
```

Falls CI bewusst noch nicht blockieren soll:

- `security-project` kann vorübergehend non-blocking sein
- aber nur mit Kommentar und Folge-Issue
- bevorzugt: project-code blocking

---

# 4. Policy-Dokument aktualisieren

Aktualisiere:

```text
docs/security/bandit-triage.md
docs/security/submodule-security-review.md
```

Oder ergänze neu:

```text
docs/security/security-gate-policy.md
```

Pflichtinhalt:

```markdown
# Security Gate Policy

## Ziel

## Scope

## Projekt-Code vs Vendor-Code

## Blocking Rules

| Bereich | Severity | Blocking | Begründung |
|---|---|---|---|
| Projektcode | High | Ja | |
| Projektcode | Medium | Ja/Optional begründet | |
| Projektcode | Low | Nein/Review | |
| Vendor-Code | High | Warnung/Baseline | |
| Vendor-Code | Medium | Warnung/Baseline | |
| Tests | Low/Medium | Nur Review | |

## Makefile Targets

## CI-Verhalten

## Baseline-Verhalten

## Bekannte akzeptierte Findings

## Regression-Regeln

## Folge-Issues
```

---

# 5. Validierung

Nach Änderungen ausführen:

```bash
# Security-Gates
make security-project
make security-vendor
make security-report

# Bestehende Gates
python3 -m ruff check . --line-length=88

python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py -q

python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py   --cov --cov-report=term -q

python3 -m pytest tests/e2e/ -v --timeout=30 --count=3 -q
```

Optional:

```bash
python3 -m mypy . --ignore-missing-imports
```

Der bekannte `gpt_researcher/ports`-Fehler ist nicht Scope.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Security-Gate-Strategie dokumentiert ist
- Projektcode und Vendor-Code getrennt behandelt werden
- `make security-project` existiert und lokal reproduzierbar ist
- `make security-vendor` oder äquivalenter Vendor-Report existiert
- `make security-report` erzeugt nachvollziehbare Reports
- CI-Konfiguration Security-Gate/Report berücksichtigt
- bekannte Vendor-Findings nicht unsichtbar werden
- neue Projekt-Medium/High-Findings blockiert werden
- ruff grün bleibt
- Tests grün bleiben
- Coverage >=78% bleibt
- keine neue Feature-Logik eingebaut wurde
- GitHub-Kommentar mit Security-Gate-Entscheidung geschrieben wurde

Minimal akzeptabel:

- Security-Policy dokumentiert
- Makefile-Targets vorhanden
- Project-Code-Scan blockierend
- Vendor-Report non-blocking

Gut:

- CI lädt Security-Reports als Artefakte hoch
- Security-Gate ist in README oder docs verlinkt
- Baseline-/Vendor-Strategie klar beschrieben

Sehr gut:

- Neue Projekt-High/Medium-Findings würden CI zuverlässig failen
- Vendor-Findings bleiben als Artefakt sichtbar
- Policy ist für spätere Security-Fixes nutzbar

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Bandit-Baseline-/CI-Security-Gate Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Security-Gate-Strategie dokumentiert | |
| Projekt-/Vendor-Split umgesetzt | |
| `make security-project` vorhanden | |
| `make security-vendor` vorhanden | |
| `make security-report` vorhanden | |
| CI Security-Gate angepasst | |
| Reports als CI-Artefakte vorgesehen | |
| Neue Projekt-Medium/High-Findings blockierend | |
| Vendor-Findings sichtbar, aber kontrolliert | |
| ruff weiterhin grün | |
| Tests weiterhin grün | |
| Coverage weiterhin >=78% | |
| Keine neuen Features | |
| GitHub-Kommentar geschrieben | |

## Security-Gate-Strategie

## Bandit-Ergebnisse

| Bereich | Findings | Blocking | Bemerkung |
|---|---:|---|---|
| Projektcode | | | |
| Vendor/Submodul | | | |
| Gesamt | | | |

## Ausgeführte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Geänderte Dateien

## CI-Änderungen

## Akzeptierte Restrisiken

## Bewusst nicht gelöste Probleme

## Risiken

## Nächstes empfohlenes Issue
```

---

# Empfohlenes nächstes Folge-Issue nach Abschluss

Nach diesem Issue sollte eines dieser Issues folgen:

1. `mypy vendor/submodule boundary cleanup`
2. `make test in schnelle und langsame Testprofile trennen`
3. `Playwright-CI-Strategie definieren`
4. `Security regression tests für Netzwerk-/Hashing-/SQL-Pfade ergänzen`

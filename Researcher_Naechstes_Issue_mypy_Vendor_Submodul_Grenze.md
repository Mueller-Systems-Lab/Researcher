# Researcher — Nächstes Issue: mypy Vendor-/Submodul-Grenze bereinigen

## Rolle

Du bist ein Senior Python Typing/CI Engineer mit Fokus auf Monorepos, Vendor-/Fork-Code und pragmatische Typecheck-Gates.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Repair-Chain:

- #50: Walking-Skeleton/Repair
- #51: Lint-/CI-Gate, ruff 950 → 0
- #52: Bandit-/Security-Triage, 43 Findings triagiert
- #53: Submodul-Security-Review, 32 → 20 Submodul-Findings
- #54: Bandit-Baseline-/CI-Security-Gate, Projekt/Vendor-Split umgesetzt

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, den verbleibenden `mypy`-Fehler im `gpt_researcher/ports`-Submodulbereich sauber zu behandeln und daraus ein reproduzierbares, sinnvolles Typecheck-Gate zu machen.

---

# Ausgangslage

Der aktuelle Stand nach #54:

- Tests grün: 195 passed, 7 skipped
- Coverage: >=78%
- ruff grün
- Security-Gate umgesetzt:
  - Projektcode blockierend ab Medium
  - Vendor/Submodul report-only
- `make security-project`, `make security-vendor`, `make security-report` vorhanden
- bekannte Vendor-Findings dokumentiert
- keine produktiven Feature-Änderungen in der Repair-Chain

Bekanntes offenes Problem:

```bash
python3 -m mypy . --ignore-missing-imports
# → 1 pre-existing Error im gpt_researcher/ports-Submodulbereich
```

Vermutete Ursache:

- Vendor-/Submodul-Code wird vom globalen mypy-Lauf wie Projektcode behandelt.
- Der Fehler liegt nicht in projekt-eigenen Dateien.
- Ähnliches Muster wurde bereits bei ruff und Bandit durch Projekt-/Vendor-Split gelöst.

---

# Oberstes Ziel dieses Issues

Definiere ein sauberes Typecheck-Gate mit Projekt-/Vendor-Grenze.

Das Gate soll:

1. Projekt-eigenen Code sinnvoll und blockierend typechecken.
2. Vendor-/Submodul-Code nicht unkontrolliert als Projektcode behandeln.
3. Den bekannten `gpt_researcher/ports`-Fehler dokumentieren.
4. CI und Makefile so ausrichten, dass neue Type-Fehler im Projektcode auffallen.
5. Keine produktive Logik ändern.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- produktive Logik verändern
- den `gpt_researcher/`-Submodulcode großflächig umbauen
- Typfehler im Vendor-Code durch intrusive Refactorings reparieren
- `mypy` global deaktivieren
- `ignore_errors = true` für das gesamte Projekt setzen
- Tests löschen
- Coverage-Schwellen senken
- ruff- oder Security-Gates lockern
- Dependencies upgraden, außer minimal nötig und begründet

---

# Wichtige Prinzipien

## Projektcode ist blockierend

Projekt-eigene Pfade sollen typecheck-clean sein oder klar begründete, lokale Ausnahmen besitzen.

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
- `tests/`, soweit sinnvoll
- eigene Root-Dateien

## Vendor-Code ist getrennt

Vendor-/Fork-Pfad:

- `gpt_researcher/`

Dieser Pfad darf separat geprüft, aber nicht als Blocker für projekt-eigene CI-Gates behandelt werden, solange das Projekt ihn nicht aktiv warten oder upstream-kompatibel reparieren will.

## Keine pauschalen Ignorierungen

Verboten:

```toml
[tool.mypy]
ignore_errors = true
```

Erlaubt, wenn begründet:

```toml
[[tool.mypy.overrides]]
module = ["gpt_researcher.*"]
ignore_errors = true
```

oder besser: separate Makefile-Targets für Projekt/Vendor.

---

# Arbeitsreihenfolge

## 1. Ist-Zustand reproduzieren

Führe aus:

```bash
python3 -m mypy . --ignore-missing-imports
```

Zusätzlich:

```bash
python3 -m mypy config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts tests --ignore-missing-imports
```

Falls einzelne Pfade nicht existieren, Befehl entsprechend anpassen.

Dokumentiere:

- exakte Fehlermeldung
- betroffene Datei
- ob Fehler im Projektcode oder Vendor/Submodul liegt
- ob Projekt-eigener mypy-Lauf grün ist
- ob Tests durch Typecheck-Konfiguration beeinflusst werden

---

## 2. Bestehende Konfiguration prüfen

Lies:

```text
pyproject.toml
mypy.ini
setup.cfg
Makefile
.github/workflows/test.yml
docs/security/security-gate-policy.md
docs/security/bandit-triage.md
```

Dokumentiere:

- Wo mypy konfiguriert ist.
- Welches Makefile-Target existiert.
- Ob CI mypy aufruft.
- Ob `gpt_researcher/` bereits bei ruff/security getrennt behandelt wird.
- Welche Pattern aus #51 und #54 übernommen werden können.

---

## 3. Zielstrategie wählen

Wähle eine der folgenden Strategien und begründe sie.

## Strategie A — Project-only blocking Typecheck

Empfohlen.

Makefile bekommt getrennte Targets:

```makefile
typecheck:
	python3 -m mypy config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts tests --ignore-missing-imports

typecheck-vendor:
	python3 -m mypy gpt_researcher --ignore-missing-imports || true
```

Vorteil:

- Projektcode blockierend
- Vendor-Probleme sichtbar, aber nicht blockierend
- passt zu ruff/security-Grenze

## Strategie B — mypy Overrides

`pyproject.toml` erhält gezielte Overrides:

```toml
[[tool.mypy.overrides]]
module = ["gpt_researcher.*"]
ignore_errors = true
```

Vorteil:

- einfacher globaler mypy-Lauf

Nachteil:

- Vendor-Probleme werden weniger sichtbar
- kann zu breit sein

## Strategie C — Hybrid

Empfohlen, wenn CI-Artefakte/Reports gewünscht sind.

- `typecheck` blockierend für Projektcode
- `typecheck-vendor` non-blocking/report-only
- CI führt beide aus
- Vendor-Ergebnis wird dokumentiert

---

# Empfohlene Umsetzung

Bevorzugt: Strategie C.

## Makefile-Ziele ergänzen oder korrigieren

Prüfe vorhandene Targets wie:

- `lint-types`
- `typecheck`
- `mypy`

Ersetze nicht blind bestehende Targets, sondern halte Rückwärtskompatibilität, wenn möglich.

Möglicher Zielzustand:

```makefile
TYPECHECK_PROJECT_PATHS := config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts tests

typecheck:
	python3 -m mypy $(TYPECHECK_PROJECT_PATHS) --ignore-missing-imports

typecheck-vendor:
	python3 -m mypy gpt_researcher --ignore-missing-imports || true

lint-types: typecheck
```

Wenn einzelne Pfade nicht existieren oder mypy für `tests/` unpassend ist, begründet anpassen.

## CI anpassen

In `.github/workflows/test.yml` oder passender CI-Datei:

```yaml
- name: Typecheck project code
  run: make typecheck

- name: Typecheck vendor code
  run: make typecheck-vendor
```

Vendor-Step darf non-blocking sein, aber muss sichtbar bleiben.

Optional:

```yaml
continue-on-error: true
```

oder Makefile mit `|| true`.

Nicht beides gleichzeitig unnötig doppeln.

---

# Dokumentation

Erstelle oder aktualisiere:

```text
docs/typing/typecheck-policy.md
```

Pflichtinhalt:

```markdown
# Typecheck Policy

## Ziel

## Scope

## Projekt-Code vs Vendor-Code

## Blocking Rules

| Bereich | Blocking | Begründung |
|---|---|---|
| Projektcode | Ja | |
| Vendor/Submodul | Nein/Report-only | |
| Tests | Ja/Teilweise | |

## Makefile Targets

## CI-Verhalten

## Bekannter Vendor-Fehler

## Warum kein globales ignore_errors?

## Folge-Issues
```

---

# Validierung

Nach Änderungen ausführen:

```bash
# Typecheck
make typecheck
make typecheck-vendor

# Bestehende Gates
python3 -m ruff check . --line-length=88

python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py -q

python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py   --cov --cov-report=term -q

python3 -m pytest tests/e2e/ -v --timeout=30 --count=3 -q

# Security-Gates aus #54
make security-project
make security-vendor
make security-report
```

Optional:

```bash
python3 -m mypy . --ignore-missing-imports
```

Der globale Lauf darf weiterhin Vendor-Fehler zeigen, solange das dokumentiert ist und `make typecheck` grün ist.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- der aktuelle mypy-Fehler reproduziert und lokalisiert wurde
- Projekt-/Vendor-Grenze für Typechecking dokumentiert ist
- `make typecheck` oder äquivalentes Projekt-Typecheck-Gate existiert
- Projekt-Typecheck blockierend grün läuft
- Vendor-Typecheck sichtbar, aber nicht blockierend ist
- CI den Projekt-Typecheck nutzt
- CI den Vendor-Typecheck optional/report-only sichtbar macht
- keine produktive Logik geändert wurde
- ruff weiterhin grün bleibt
- Tests weiterhin grün bleiben
- Coverage weiterhin >=78% bleibt
- Security-Gates weiterhin funktionieren
- GitHub-Kommentar mit Vorher/Nachher-Status geschrieben wurde

Minimal akzeptabel:

- Projekt-Code typecheckt grün
- Vendor-Fehler ist dokumentiert und nicht mehr blockierend
- CI nutzt das neue Projekt-Typecheck-Gate

Gut:

- `typecheck-vendor` ist als report-only Target vorhanden
- Policy-Dokument erklärt die Entscheidung sauber

Sehr gut:

- Typecheck-Policy ist konsistent mit ruff- und Bandit-Grenze aus #51/#54
- Folge-Issue für echte Vendor-Typisierung oder Upstream-Fix ist klar benannt

---

# Abschlussbericht-Vorlage

```markdown
# Researcher mypy Vendor-/Submodul-Grenze Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| mypy-Ausgangsfehler reproduziert | |
| Fehler als Projekt/Vendor klassifiziert | |
| Projekt-Typecheck-Gate erstellt | |
| Vendor-Typecheck report-only erstellt | |
| CI Typecheck angepasst | |
| Typecheck-Policy erstellt | |
| ruff weiterhin grün | |
| Tests weiterhin grün | |
| Coverage weiterhin >=78% | |
| Security-Gates weiterhin ausführbar | |
| Keine produktive Logik geändert | |
| GitHub-Kommentar geschrieben | |

## mypy Vorher/Nachher

| Bereich | Vorher | Nachher | Blocking |
|---|---|---|---|
| Global | | | |
| Projektcode | | | |
| Vendor/Submodul | | | |

## Ausgeführte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Geänderte Dateien

## CI-Änderungen

## Bekannter Vendor-Fehler

## Begründete Ausnahmen

## Bewusst nicht gelöste Probleme

## Risiken

## Nächstes empfohlenes Issue
```

---

# Empfohlenes nächstes Folge-Issue nach Abschluss

Nach diesem Issue sollte eines dieser Issues folgen:

1. `make test in schnelle und langsame Testprofile trennen`
2. `Playwright-CI-Strategie definieren`
3. `Security regression tests für Netzwerk-/Hashing-/SQL-Pfade ergänzen`
4. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`

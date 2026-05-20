# Researcher — Nächstes Issue: 33 Projekt-Type-Errors beheben und `make typecheck` blockierend machen

## Rolle

Du bist ein Senior Python Typing Engineer und CI-Stabilisierungs-Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Repair-Chain:

- #50: Walking-Skeleton/Repair
- #51: ruff Lint-/CI-Gate, 950 → 0
- #52: Bandit-/Security-Triage
- #53: Submodul-Security-Review
- #54: CI-Security-Gate
- #55: mypy Vendor-/Submodul-Grenze

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, die 33 bekannten Projekt-Type-Errors in 12 Dateien so zu beheben, dass `make typecheck` blockierend grün laufen kann.

---

# Ausgangslage

Nach #55 existieren:

- `make typecheck`
- `make typecheck-vendor`
- Typecheck-Policy: `docs/typing/typecheck-policy.md`
- Vendor-Override für `gpt_researcher.*`
- CI-Typecheck-Steps

Aktueller Status laut #55:

| Bereich | Status | Blocking |
|---|---|---|
| Global | 1 Vendor Error | Non-blocking |
| Projektcode | 33 Errors in 12 Dateien | Noch non-blocking |
| Vendor/Submodul | 1 Error in `gpt_researcher/ports` | Report-only |

Wichtig:

`make typecheck` ist aktuell noch non-blocking (`|| true`) und soll erst nach Behebung der 33 Projektfehler blockierend aktiviert werden.

---

# Oberstes Ziel dieses Issues

1. Die 33 Projekt-Type-Errors reproduzieren.
2. Fehler nach Kategorien gruppieren.
3. Projektfehler minimal und korrekt beheben.
4. Keine produktive Logik verändern.
5. `make typecheck` von non-blocking auf blocking umstellen.
6. CI-Projekt-Typecheck blockierend machen.
7. Vendor-Typecheck weiter report-only lassen.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- produktive Logik fachlich verändern
- den `gpt_researcher/`-Vendor-Fehler reparieren
- Vendor-Code großflächig anfassen
- `ignore_errors = true` für Projektcode setzen
- Type-Errors durch pauschales `Any` verstecken
- Tests löschen
- Coverage-Schwelle senken
- ruff- oder Security-Gates lockern
- große Refactorings durchführen

---

# Typing-Prinzipien

## 1. Minimaler korrekter Fix

Bevorzugt:

- präzisere Type-Hints
- `Optional`/`None` korrekt behandeln
- Rückgabetypen ergänzen
- `cast()` nur mit Begründung
- `Protocol` nur wenn wirklich nötig
- kleine helper-Funktionen typisieren

Nicht bevorzugt:

- flächendeckend `Any`
- `# type: ignore` ohne Code und Begründung
- `ignore_errors` für ganze Projektmodule
- semantische Umbauten

## 2. Tests sind Sicherheitsnetz

Nach jedem Cluster von Type-Fixes:

- relevante Tests laufen lassen
- ruff prüfen
- Coverage stabil halten

## 3. Vendor bleibt getrennt

Der bekannte Vendor-Fehler in `gpt_researcher/ports` bleibt report-only und ist nicht Scope dieses Issues.

---

# Arbeitsreihenfolge

## 1. Ist-Zustand reproduzieren

Führe aus:

```bash
make typecheck
python3 -m mypy config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts tests --ignore-missing-imports
```

Falls `make typecheck` aktuell `|| true` enthält, zusätzlich direkten mypy-Befehl ausführen, um Exit-Code und Fehler sauber zu sehen.

Speichere oder dokumentiere:

```bash
python3 -m mypy config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts tests --ignore-missing-imports > /tmp/mypy-project-before.txt || true
```

Dokumentiere:

- alle 33 Fehler
- betroffene 12 Dateien
- Fehlercodes, falls vorhanden
- Root-Cause-Kategorien

---

## 2. Fehler clustern

Erstelle eine Tabelle:

```markdown
| Kategorie | Anzahl | Dateien | Fix-Strategie |
|---|---:|---|---|
| Optional/None handling | | | |
| Missing return annotation | | | |
| Incompatible assignment | | | |
| Untyped dict/list | | | |
| Attribute access | | | |
| Call argument mismatch | | | |
| Test typing issue | | | |
| Other | | | |
```

Behandle zuerst die einfachen, lokalen Fehler.

---

## 3. Fix-Strategie anwenden

### Optional/None

Bevorzugt:

```python
if value is None:
    return default
```

oder:

```python
assert value is not None
```

nur wenn logisch garantiert und testbar.

### Dict/List-Typen

Bevorzugt:

```python
from typing import Any

payload: dict[str, Any] = {}
items: list[str] = []
```

`Any` nur an externen JSON-/API-Grenzen verwenden.

### Rückgabetypen

Bevorzugt:

```python
def build_payload(...) -> dict[str, Any]:
    ...
```

### Mock-/Test-Typen

In Tests sind eng begrenzte `cast()` oder `Any` akzeptabler als im Produktcode, aber nicht pauschal.

### type: ignore

Nur wenn:

- externer Library-Typ falsch oder nicht vorhanden ist
- Grund in Kommentar steht
- spezifischer Error-Code verwendet wird, falls verfügbar

Beispiel:

```python
result = external_call()  # type: ignore[no-untyped-call]  # third-party library has no stubs
```

---

## 4. Typecheck-Gate scharf schalten

Wenn Projekt-Typecheck grün ist:

### Makefile

Entferne `|| true` aus dem Projekt-Typecheck.

Zielzustand:

```makefile
typecheck:
	python3 -m mypy $(TYPECHECK_PROJECT_PATHS) --ignore-missing-imports

typecheck-vendor:
	python3 -m mypy gpt_researcher --ignore-missing-imports || true
```

### CI

Projekt-Typecheck muss blockierend sein.

Vendor-Typecheck bleibt report-only.

Falls in CI `continue-on-error: true` für Projekt-Typecheck steht, entfernen.

---

## 5. Dokumentation aktualisieren

Aktualisiere:

```text
docs/typing/typecheck-policy.md
```

Ergänze:

- Datum/Issue
- Projekt-Typecheck ist jetzt blocking
- Anzahl der behobenen Projektfehler
- Vendor-Fehler bleibt report-only
- Regeln für künftige Type-Fixes
- erlaubte/unerlaubte `type: ignore`-Nutzung

---

# Validierung

Nach Änderungen ausführen:

```bash
# Typecheck
make typecheck
make typecheck-vendor

# Lint
python3 -m ruff check . --line-length=88

# Fast tests
python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py -q

# Coverage
python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py   --cov --cov-report=term -q

# E2E quick repeat
python3 -m pytest tests/e2e/ -v --timeout=30 --count=3 -q

# Security gates
make security-project
make security-vendor
make security-report
```

Optional:

```bash
python3 -m mypy . --ignore-missing-imports
```

Der globale Lauf darf weiterhin den bekannten Vendor-Fehler zeigen, solange `make typecheck` grün und blockierend ist.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- alle 33 Projekt-Type-Errors reproduziert und dokumentiert wurden
- alle Projekt-Type-Errors behoben sind
- `make typecheck` grün läuft
- `make typecheck` blockierend ist
- CI-Projekt-Typecheck blockierend ist
- `make typecheck-vendor` report-only bleibt
- bekannter Vendor-Fehler dokumentiert bleibt
- Typecheck-Policy aktualisiert ist
- ruff weiterhin grün bleibt
- Tests weiterhin grün bleiben
- Coverage weiterhin >=78% bleibt
- Security-Gates weiterhin funktionieren
- keine produktive Fachlogik geändert wurde
- GitHub-Kommentar mit Vorher/Nachher-Status geschrieben wurde

Minimal akzeptabel:

- Projekt-Typecheck grün
- Projekt-Typecheck blockierend
- Vendor-Fehler weiterhin report-only
- keine Regression bei Tests/Lint/Security

Gut:

- keine neuen `Any`-Ausweichlösungen in Produktcode ohne Grund
- keine pauschalen `type: ignore`
- Policy dokumentiert Regeln für zukünftige Typisierung

Sehr gut:

- Typecheck-Fehler sinken von 33 auf 0
- CI kann Typecheck als echtes Gate nutzen
- Folge-Issue für Vendor-Fehler oder Upstream-Fix ist klar benannt

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Projekt-Type-Errors Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| 33 Projekt-Type-Errors reproduziert | |
| Fehler geclustert | |
| Projekt-Type-Errors behoben | |
| `make typecheck` grün | |
| `make typecheck` blockierend | |
| CI-Projekt-Typecheck blockierend | |
| Vendor-Typecheck report-only | |
| Typecheck-Policy aktualisiert | |
| ruff weiterhin grün | |
| Tests weiterhin grün | |
| Coverage weiterhin >=78% | |
| Security-Gates weiterhin ausführbar | |
| Keine produktive Fachlogik geändert | |
| GitHub-Kommentar geschrieben | |

## mypy Vorher/Nachher

| Bereich | Vorher | Nachher | Blocking |
|---|---:|---:|---|
| Projektcode | 33 | 0 | Ja |
| Vendor/Submodul | 1 | 1 | Nein |
| Global | 1+33 | 1 Vendor | Nein |

## Fehlercluster

| Kategorie | Vorher | Nachher |
|---|---:|---:|
| Optional/None | | |
| Dict/List typing | | |
| Return annotations | | |
| Assignment mismatch | | |
| Test typing | | |
| Other | | |

## Ausgeführte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Geänderte Dateien

## CI-Änderungen

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

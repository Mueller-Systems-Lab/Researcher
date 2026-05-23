# Researcher — Nächstes Reparatur-Issue: Bandit-Findings triagieren und Security-Policy definieren

## Rolle

Du bist ein Senior Python Security Engineer und CI-Security-Gate-Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Issues:

- #50: Walking-Skeleton/Repair
- #51: Lint-/CI-Gate, ruff 950 → 0

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, die 44 Bandit-Findings aus dem vorherigen Repair-Lauf systematisch zu triagieren, echte Risiken minimal zu beheben und eine nachvollziehbare Security-Policy für verbleibende Findings zu definieren.

---

# Ausgangslage

`make security` ist seit #50 ausführbar.

Aktueller Stand laut Abschlussbericht:

- Bandit 1.9.4 läuft
- 44 Findings dokumentiert
- 7 High
- 18 Medium
- 19 Low

Genannte Schwerpunkte:

- MD5-Verwendung
- SSL-Verify-Deaktivierung
- Requests ohne Timeout
- mögliche SQL-Injection-Findings
- Policy für akzeptierte Findings fehlt

---

# Oberstes Ziel dieses Issues

Erzeuge aus den Bandit-Findings einen belastbaren Security-Zustand:

1. Findings reproduzieren.
2. Findings nach echter Relevanz triagieren.
3. Echte High-/Medium-Risiken minimal beheben.
4. False Positives oder akzeptierte Risiken explizit dokumentieren.
5. Eine Bandit-Baseline oder Policy nur verwenden, wenn sie begründet ist.
6. CI-Security-Gate so definieren, dass neue kritische Findings nicht unbemerkt hinzukommen.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- Architektur umbauen
- Darknet-/Crawler-Logik funktional erweitern
- Tests löschen
- Bandit global deaktivieren
- alle Findings pauschal mit `# nosec` unterdrücken
- SSL-Verify pauschal deaktiviert lassen, ohne dokumentierte Begründung
- SQL-Warnungen ignorieren, ohne Datenfluss zu prüfen
- große Dependency-Upgrades durchführen
- `gpt_researcher/`-Submodul ohne klare Begründung verändern

---

# Wichtige Security-Prinzipien

## Requests-Timeouts

Requests setzt standardmäßig kein Timeout. Ohne explizites Timeout können Requests sehr lange hängen. Deshalb sollen alle externen Netzwerkaufrufe, insbesondere Web-/Onion-/SearXNG-/Fetch-Aufrufe, ein explizites Timeout erhalten.

## SSL-Verify

Requests validiert TLS-Zertifikate standardmäßig. Explizites `verify=False` ist ein High-Risk-Finding und darf nur mit enger Begründung, Scope-Begrenzung und Dokumentation bestehen bleiben.

## MD5

MD5 ist für Sicherheitszwecke ungeeignet. Wenn MD5 nur für nicht-sicherheitsrelevante IDs, Cache-Keys oder deterministische Testwerte verwendet wird, muss das explizit dokumentiert werden. Wenn der Hash Sicherheitswirkung hat, muss auf SHA-256 oder besser migriert werden.

## Bandit-Baseline

Eine Bandit-Baseline darf nur für bekannte, bewusst akzeptierte Findings genutzt werden. Sie darf nicht dazu dienen, neue Security-Probleme zu verstecken.

---

# Arbeitsreihenfolge

## 1. Bandit-Ist-Zustand reproduzieren

Führe aus:

```bash
make security
python3 -m bandit -r . --skip B101,B311,B404,B603 -f json -o bandit-report.json
python3 -m bandit -r . --skip B101,B311,B404,B603 -f txt -o bandit-report.txt
```

Falls `gpt_researcher/` als Submodul/Vendor-Bereich behandelt wird, zusätzlich ausführen:

```bash
python3 -m bandit -r config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts tests   --skip B101,B311,B404,B603 -f json -o bandit-project-report.json
```

Dokumentiere:

- Gesamtzahl Findings
- Findings nach Severity
- Findings nach Confidence
- Findings nach Test-ID
- Findings in projekt-eigenen Dateien
- Findings im Submodul-/Vendor-Bereich
- Findings in Tests
- Findings in produktivem Code

## 2. Findings klassifizieren

Erstelle eine Tabelle:

```markdown
| ID | Severity | Confidence | Datei | Zeile | Kategorie | Entscheidung | Begründung |
|---|---|---|---|---:|---|---|---|
```

Entscheidungen:

- `FIX_NOW`
- `ACCEPT_WITH_REASON`
- `BASELINE_VENDOR`
- `TEST_ONLY_IGNORE`
- `FALSE_POSITIVE`
- `FOLLOW_UP_REQUIRED`

Priorität:

1. High + High/Medium confidence in produktivem Code
2. Medium + High confidence in produktivem Code
3. Netzwerkaufrufe ohne Timeout
4. SSL-Verify-Deaktivierung
5. SQL-String-Konstruktion
6. MD5/SHA1
7. Test-only Findings
8. Vendor/Submodule Findings

## 3. High-Findings bearbeiten

### MD5

Für jeden MD5-Fund:

1. Prüfen, ob Security-Kontext vorliegt.
2. Wenn ja: auf SHA-256 migrieren.
3. Wenn nein: entweder `usedforsecurity=False` verwenden, falls passend, oder klar kommentieren.
4. Tests aktualisieren.

Bevorzugte Migration:

```python
import hashlib

digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
```

Nur wenn wirklich kein Security-Kontext vorliegt:

```python
digest = hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()
```

### SSL Verify

Für jeden `verify=False`-Fund:

1. Prüfen, ob der Code produktiv ist.
2. Prüfen, ob lokale/onion/test-spezifische Ausnahme vorliegt.
3. Standard auf `verify=True` oder Entfernen des Parameters.
4. Falls Ausnahme nötig: Konfiguration explizit machen, Default sicher setzen, Warnung dokumentieren.

Bevorzugt:

```python
requests.get(url, timeout=(5, 30))
```

Nicht bevorzugt:

```python
requests.get(url, verify=False)
```

## 4. Medium-Findings bearbeiten

### Requests ohne Timeout

Alle produktiven `requests.*`-Aufrufe sollen ein Timeout erhalten.

Empfohlene Defaults:

```python
DEFAULT_CONNECT_TIMEOUT_SECONDS = 5
DEFAULT_READ_TIMEOUT_SECONDS = 30
DEFAULT_REQUEST_TIMEOUT = (
    DEFAULT_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_READ_TIMEOUT_SECONDS,
)
```

Dann:

```python
requests.get(url, timeout=DEFAULT_REQUEST_TIMEOUT)
requests.post(url, json=payload, timeout=DEFAULT_REQUEST_TIMEOUT)
```

Wenn bestehende Konfigurationswerte existieren, diese verwenden statt neue Defaults zu erfinden.

### SQL-Injection-Findings

Für jeden SQL-Fund:

1. Prüfen, ob User-Input in SQL gelangt.
2. Wenn ja: Parametrisierung verwenden.
3. Wenn nein: dokumentieren, warum kein Injection-Pfad besteht.
4. Keine `nosec`-Ausnahme ohne Datenflussbegründung.

Bevorzugt:

```python
cursor.execute(
    "SELECT * FROM documents WHERE id = ?",
    (document_id,),
)
```

Nicht bevorzugt:

```python
cursor.execute(f"SELECT * FROM documents WHERE id = '{document_id}'")
```

## 5. Tests ergänzen

Für jeden sicherheitsrelevanten Fix mindestens einen passenden Test ergänzen oder vorhandenen Test anpassen.

Beispiele:

- Timeout wird an `requests.get` weitergegeben
- `verify=False` ist nicht Default
- SHA-256 statt MD5 wird verwendet
- SQL-Parameterbindung wird genutzt
- akzeptierte Test-only Findings bleiben auf Testpfade beschränkt

## 6. Policy-Datei erstellen

Erstelle:

```text
docs/security/bandit-triage.md
```

Inhalt:

```markdown
# Bandit Triage Policy

## Stand

## Scope

## Ausgeführte Befehle

## Summary

| Severity | Anzahl vorher | Anzahl nachher | Entscheidung |
|---|---:|---:|---|

## Findings nach Kategorie

## Behobene Findings

## Akzeptierte Findings

| Test-ID | Datei | Begründung | Risiko | Ablauf/Folge-Issue |
|---|---|---|---|---|

## Vendor-/Submodul-Grenze

## Test-only Findings

## CI-Gate-Empfehlung

## Nächste Security-Issues
```

## 7. Optional: Bandit-Baseline

Nur wenn nach echten Fixes noch bekannte akzeptierte Findings verbleiben:

```bash
python3 -m bandit -r . --skip B101,B311,B404,B603 -f json -o bandit-baseline.json
```

Regeln:

- Baseline nur für bewusst akzeptierte Findings.
- Neue High-Findings dürfen CI nicht passieren.
- Baseline-Datei muss dokumentiert werden.
- Keine Baseline als Ersatz für Triage.

---

# Validierung

Nach Änderungen ausführen:

```bash
# Security
make security

# Bandit JSON/Text für Doku
python3 -m bandit -r . --skip B101,B311,B404,B603 -f json -o bandit-report-after.json
python3 -m bandit -r . --skip B101,B311,B404,B603 -f txt -o bandit-report-after.txt

# Tests
python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py -q

# Coverage
python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py   --cov --cov-report=term -q

# Lint
python3 -m ruff check . --line-length=88

# E2E quick repeat
python3 -m pytest tests/e2e/ -v --timeout=30 --count=3 -q
```

Optional:

```bash
python3 -m mypy . --ignore-missing-imports
```

Der bekannte `gpt_researcher/ports`-Submodulfehler ist nicht Scope dieses Issues.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Bandit-Findings vollständig triagiert sind
- High-Findings in produktivem Projektcode behoben oder mit starker Begründung akzeptiert sind
- Requests ohne Timeout in produktivem Projektcode behoben sind
- MD5-Verwendungen geprüft und passend migriert oder dokumentiert sind
- SQL-Findings datenflussbasiert geprüft sind
- `docs/security/bandit-triage.md` existiert
- `make security` weiterhin ausführbar ist
- Tests grün bleiben
- Coverage weiterhin >=78% bleibt
- ruff weiterhin grün bleibt
- keine neuen Features gebaut wurden
- GitHub-Kommentar mit Vorher/Nachher-Summary geschrieben wurde

Minimal akzeptabel:

- alle Findings triagiert
- alle produktiven High-Findings behandelt
- Security-Policy dokumentiert
- keine Regression bei Tests/Coverage/Lint

Gut:

- High-Findings auf 0 oder nur sauber akzeptierte Test/Vendor-Findings reduziert
- produktive Medium-Findings deutlich reduziert
- CI-Gate-Empfehlung dokumentiert

Sehr gut:

- `make security` kann als blockierender CI-Schritt genutzt werden oder es gibt eine saubere Baseline-Strategie für Legacy/Vendor-Findings

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Bandit-/Security-Triage Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Bandit Ausgangswert dokumentiert | |
| Bandit Endwert dokumentiert | |
| High-Findings triagiert | |
| Produktive High-Findings behoben/akzeptiert | |
| Requests-Timeouts geprüft | |
| SSL-Verify geprüft | |
| MD5/SHA1 geprüft | |
| SQL-Findings geprüft | |
| Policy-Datei erstellt | |
| Tests weiterhin grün | |
| Coverage weiterhin >=78% | |
| ruff weiterhin grün | |
| Keine produktive Feature-Logik geändert | |
| GitHub-Kommentar geschrieben | |

## Bandit Vorher/Nachher

| Severity | Vorher | Nachher | Davon akzeptiert | Davon behoben |
|---|---:|---:|---:|---:|
| High | | | | |
| Medium | | | | |
| Low | | | | |
| Gesamt | | | | |

## Findings nach Entscheidung

| Entscheidung | Anzahl |
|---|---:|
| FIX_NOW | |
| ACCEPT_WITH_REASON | |
| BASELINE_VENDOR | |
| TEST_ONLY_IGNORE | |
| FALSE_POSITIVE | |
| FOLLOW_UP_REQUIRED | |

## Ausgeführte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Geänderte Dateien

## Behobene Risiken

## Akzeptierte Risiken mit Begründung

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
